"""异步任务管理器（单例）。

负责管理后台任务的执行与状态，并向 WebSocket 订阅者推送进度。

设计要点：
- 单例模式，全应用共享一个管理器
- 用 asyncio.create_task 执行后台协程
- 每个任务维护一个订阅者集合（asyncio.Queue），用于推送实时消息
- 任务状态同时持久化到数据库
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# WebSocket 消息类型
MSG_PROGRESS = "progress"
MSG_LOG = "log"
MSG_COMPLETED = "completed"
MSG_ERROR = "error"

# 任务状态
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


class TaskManager:
    """异步任务管理器单例。"""

    _instance: Optional["TaskManager"] = None
    _lock = asyncio.Lock()

    def __new__(cls) -> "TaskManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        # 任务内存状态
        self._tasks: Dict[str, asyncio.Task] = {}
        # 任务实时进度（progress, current_file 等）
        self._progress: Dict[str, Dict[str, Any]] = defaultdict(dict)
        # 每个任务的订阅者队列集合
        self._subscribers: Dict[str, Set[asyncio.Queue]] = defaultdict(set)
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    # ---------------- 内部状态 ----------------

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """记录当前事件循环，便于跨线程提交协程。"""
        self._loop = loop

    def get_progress(self, task_id: str) -> Dict[str, Any]:
        """获取任务内存中的实时进度。"""
        return dict(self._progress.get(task_id, {}))

    def is_running(self, task_id: str) -> bool:
        """任务是否在运行。"""
        task = self._tasks.get(task_id)
        return task is not None and not task.done()

    # ---------------- 订阅 ----------------

    async def subscribe(self, task_id: str) -> asyncio.Queue:
        """订阅指定任务的实时消息，返回一个 Queue。"""
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers[task_id].add(queue)
        return queue

    def unsubscribe(self, task_id: str, queue: asyncio.Queue) -> None:
        """取消订阅。"""
        self._subscribers.get(task_id, set()).discard(queue)

    async def _publish(self, task_id: str, message: Dict[str, Any]) -> None:
        """向所有订阅者推送消息。"""
        for queue in list(self._subscribers.get(task_id, set())):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                logger.warning("订阅者队列已满，丢弃消息: task=%s", task_id)

    # ---------------- 进度更新 ----------------

    async def update_progress(
        self,
        task_id: str,
        *,
        progress: Optional[float] = None,
        total_files: Optional[int] = None,
        processed_files: Optional[int] = None,
        current_file: Optional[str] = None,
    ) -> None:
        """更新任务进度并推送 progress 消息。"""
        state = self._progress[task_id]
        if progress is not None:
            state["progress"] = progress
        if total_files is not None:
            state["total_files"] = total_files
        if processed_files is not None:
            state["processed_files"] = processed_files
        if current_file is not None:
            state["current_file"] = current_file
        await self._publish(task_id, {
            "type": MSG_PROGRESS,
            "data": dict(state),
        })

    async def send_log(self, task_id: str, level: str, message: str) -> None:
        """推送日志消息。"""
        await self._publish(task_id, {
            "type": MSG_LOG,
            "data": {"level": level, "message": message, "timestamp": datetime.now().isoformat()},
        })

    # ---------------- 任务执行 ----------------

    def start_task(
        self,
        task_id: str,
        coro: Awaitable[Any],
    ) -> asyncio.Task:
        """启动一个后台任务。

        Args:
            task_id: 任务 ID（应已创建数据库记录）
            coro: 任务协程

        Returns:
            asyncio.Task 对象
        """
        loop = self._loop or asyncio.get_event_loop()

        async def _runner() -> Any:
            try:
                self._progress[task_id]["status"] = STATUS_RUNNING
                return await coro
            except Exception as exc:  # noqa: BLE001
                logger.exception("任务执行失败: %s", task_id)
                self._progress[task_id]["status"] = STATUS_FAILED
                self._progress[task_id]["error"] = str(exc)
                await self._publish(task_id, {
                    "type": MSG_ERROR,
                    "data": {"message": str(exc)},
                })
                raise
            finally:
                # 完成后通知订阅者并清理
                if self._progress.get(task_id, {}).get("status") != STATUS_FAILED:
                    self._progress[task_id]["status"] = STATUS_COMPLETED
                    await self._publish(task_id, {"type": MSG_COMPLETED, "data": self.get_progress(task_id)})

        task = loop.create_task(_runner())
        self._tasks[task_id] = task
        return task


# 全局单例
task_manager = TaskManager()
