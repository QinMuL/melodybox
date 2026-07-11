import { useEffect, useState } from "react";
import {
  AudioLines,
  FolderTree,
  Eye,
  Loader2,
  Play,
  CheckCircle2,
  ArrowRight,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatRelativeTime } from "@/lib/format";
import type { OrganizeTask, PreviewResult } from "@/types";

type Mode = "rename" | "organize";

export default function Organize() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink">整理中心</h1>
        <p className="mt-1 text-sm text-gray-500">
          文件命名（基于元数据重命名）和文件整理（按艺术家-专辑归类）是两个独立操作，可分别执行。
        </p>
      </div>

      <OperationCard mode="rename" />
      <OperationCard mode="organize" />
    </div>
  );
}

/** 单个操作卡片 */
function OperationCard({ mode }: { mode: Mode }) {
  const isRename = mode === "rename";
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [task, setTask] = useState<OrganizeTask | null>(null);

  // 执行任务后轮询状态
  useEffect(() => {
    if (!task || task.status === "completed" || task.status === "failed") return;
    const timer = setInterval(async () => {
      const t = await api.organize.task(task.id);
      setTask(t);
      if (t.status === "completed" || t.status === "failed") {
        clearInterval(timer);
        setExecuting(false);
      }
    }, 1500);
    return () => clearInterval(timer);
  }, [task]);

  async function handlePreview() {
    setLoading(true);
    try {
      const result = await api.organize.preview(mode);
      setPreview(result);
    } finally {
      setLoading(false);
    }
  }

  async function handleExecute() {
    setExecuting(true);
    try {
      const { taskId } = await api.organize.start(mode);
      const t = await api.organize.task(taskId);
      setTask(t);
    } catch {
      setExecuting(false);
    }
  }

  const icon = isRename ? <AudioLines className="h-5 w-5" /> : <FolderTree className="h-5 w-5" />;
  const title = isRename ? "文件命名" : "文件整理";
  const desc = isRename
    ? "基于音乐元数据，把不规范的文件名重命名为「艺术家 - 歌曲名.扩展名」格式。不移动文件位置。"
    : "按「艺术家/专辑/」文件夹结构归类移动文件。不修改文件名，只改变文件所在目录。";
  const example = isRename
    ? "答案 - 冒海飞、徐丽东 - flac.flac  →  冒海飞 - 答案.flac"
    : "/music/冒海飞 - 答案.flac  →  /music/冒海飞/答案 (OST)/冒海飞 - 答案.flac";

  return (
    <div className="card p-6">
      {/* 标题区 */}
      <div className="flex items-start gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
          {icon}
        </div>
        <div className="flex-1">
          <h2 className="text-lg font-semibold text-ink">{title}</h2>
          <p className="mt-1 text-sm text-gray-500">{desc}</p>
          <div className="mt-2 rounded-lg bg-gray-50 px-3 py-2 font-mono text-xs text-gray-600">
            {example}
          </div>
        </div>
      </div>

      {/* 操作按钮 */}
      <div className="mt-5 flex gap-3">
        <button
          onClick={handlePreview}
          disabled={loading || executing}
          className="btn-secondary flex items-center gap-2 disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Eye className="h-4 w-4" />}
          预览结果
        </button>
        <button
          onClick={handleExecute}
          disabled={executing || loading}
          className="btn-primary flex items-center gap-2 disabled:opacity-50"
        >
          {executing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
          {executing ? "执行中..." : `执行${title}`}
        </button>
      </div>

      {/* 预览结果 */}
      {preview && (
        <div className="mt-5">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-ink">
              预览结果（共 {preview.totalChanges} 项
              {preview.skipped > 0 && `，${preview.skipped} 项跳过`}）
            </h3>
          </div>
          <div className="max-h-80 space-y-2 overflow-y-auto">
            {preview.changes.map((c, i) => (
              <div
                key={i}
                className="rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 text-xs"
              >
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded px-1.5 py-0.5 font-medium ${
                      c.action === "skip"
                        ? "bg-gray-200 text-gray-600"
                        : c.action === "move"
                          ? "bg-blue-100 text-blue-700"
                          : "bg-green-100 text-green-700"
                    }`}
                  >
                    {c.action === "skip" ? "跳过" : c.action === "move" ? "移动" : "复制"}
                  </span>
                  {c.reason && <span className="text-gray-400">{c.reason}</span>}
                </div>
                <div className="mt-1.5 font-mono text-gray-600">
                  <div className="truncate">{c.oldPath}</div>
                  <div className="flex items-center gap-1 text-primary">
                    <ArrowRight className="h-3 w-3 shrink-0" />
                    <span className="truncate">{c.newPath}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 执行进度 */}
      {task && (
        <div className="mt-5 rounded-lg border border-primary/20 bg-primary/5 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {task.status === "completed" ? (
                <CheckCircle2 className="h-5 w-5 text-primary" />
              ) : (
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
              )}
              <span className="text-sm font-semibold text-ink">
                {task.status === "completed" ? "已完成" : task.status === "failed" ? "失败" : "执行中"}
              </span>
            </div>
            <span className="text-sm text-gray-500">
              {task.processedFiles} / {task.totalFiles}（{task.progress.toFixed(0)}%）
            </span>
          </div>
          {/* 进度条 */}
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-gray-200">
            <div
              className="h-full bg-primary transition-all duration-500"
              style={{ width: `${task.progress}%` }}
            />
          </div>
          {/* 当前文件 */}
          {task.currentFile && (
            <div className="mt-2 truncate font-mono text-xs text-gray-500">
              {task.currentFile}
            </div>
          )}
          {/* 结果摘要 */}
          {task.status === "completed" && task.result && (
            <div className="mt-3 flex gap-4 text-xs">
              {Object.entries(task.result).map(([k, v]) => (
                <span key={k} className="text-gray-500">
                  {k}: <span className="font-semibold text-ink">{String(v)}</span>
                </span>
              ))}
            </div>
          )}
          {/* 日志 */}
          {task.logs && task.logs.length > 0 && (
            <div className="mt-3 max-h-40 space-y-1 overflow-y-auto rounded bg-black/80 p-3 font-mono text-xs text-green-400">
              {task.logs.map((l, i) => (
                <div key={i}>
                  <span className="text-gray-400">[{l.time}]</span>{" "}
                  <span className={l.level === "error" ? "text-red-400" : l.level === "warning" ? "text-yellow-400" : "text-green-400"}>
                    {l.message}
                  </span>
                </div>
              ))}
            </div>
          )}
          {task.startedAt && (
            <div className="mt-2 text-xs text-gray-400">
              开始于 {formatRelativeTime(task.startedAt)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
