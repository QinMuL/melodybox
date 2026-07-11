"""WebSocket 实时进度路由 /api/ws。"""
from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.task_manager import task_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/organize/{task_id}")
async def organize_progress(websocket: WebSocket, task_id: str) -> None:
    """实时推送任务进度。

    消息格式：{ "type": "progress"|"log"|"completed"|"error", "data": ... }
    """
    await websocket.accept()

    # 订阅任务消息
    queue = await task_manager.subscribe(task_id)

    # 先发送一次当前进度（便于客户端连接后立即获取状态）
    current = task_manager.get_progress(task_id)
    if current:
        await _send(websocket, {"type": "progress", "data": current})

    try:
        # 主循环：从队列读取消息并推送
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=30.0)
                await _send(websocket, message)
                # 任务结束消息（completed/error）后关闭连接
                if message.get("type") in ("completed", "error"):
                    break
            except asyncio.TimeoutError:
                # 心跳保活
                await _send(websocket, {"type": "ping", "data": {}})
    except WebSocketDisconnect:
        logger.info("WebSocket 客户端断开: task=%s", task_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("WebSocket 异常: %s", exc)
    finally:
        task_manager.unsubscribe(task_id, queue)


async def _send(websocket: WebSocket, message: dict) -> None:
    """发送 JSON 消息，失败时忽略。"""
    try:
        await websocket.send_text(json.dumps(message, ensure_ascii=False, default=str))
    except Exception as exc:  # noqa: BLE001
        logger.warning("发送 WebSocket 消息失败: %s", exc)
