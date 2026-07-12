import { useEffect, useMemo, useState } from "react";
import {
  AudioLines,
  FolderTree,
  Eye,
  Loader2,
  Play,
  CheckCircle2,
  ArrowRight,
  Filter,
  FileMusic,
  SkipForward,
  Copy,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatRelativeTime } from "@/lib/format";
import type { OrganizeTask, PreviewResult, PreviewChange } from "@/types";
import { cn } from "@/lib/utils";

type Mode = "rename" | "organize";
type FilterType = "all" | "move" | "copy" | "skip";

export default function Organize() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-ink-primary dark:text-ink-light">整理中心</h1>
        <p className="mt-1 text-sm text-ink-muted dark:text-ink-lightMuted">
          文件命名（基于元数据重命名）和文件整理（按艺术家-专辑归类）是两个独立操作，可分别执行。
        </p>
      </div>

      <OperationCard mode="rename" />
      <OperationCard mode="organize" />
    </div>
  );
}

/** 拆分路径为「目录 + 文件名」便于样式区分 */
function splitPath(path: string): { dir: string; file: string } {
  const idx = path.lastIndexOf("/");
  if (idx < 0) return { dir: "", file: path };
  return { dir: path.slice(0, idx + 1), file: path.slice(idx + 1) };
}

/** 单个操作卡片 */
function OperationCard({ mode }: { mode: Mode }) {
  const isRename = mode === "rename";
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [task, setTask] = useState<OrganizeTask | null>(null);
  const [filter, setFilter] = useState<FilterType>("all");

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
    setPreview(null);
    try {
      const result = await api.organize.preview(mode);
      setPreview(result);
      setFilter("all");
    } finally {
      setLoading(false);
    }
  }

  async function handleExecute() {
    setExecuting(true);
    setPreview(null);
    try {
      const { taskId } = await api.organize.start(mode);
      const t = await api.organize.task(taskId);
      setTask(t);
    } catch {
      setExecuting(false);
    }
  }

  // 统计
  const stats = useMemo(() => {
    if (!preview) return { total: 0, move: 0, copy: 0, skip: 0 };
    const move = preview.changes.filter((c) => c.action === "move").length;
    const copy = preview.changes.filter((c) => c.action === "copy").length;
    const skip = preview.changes.filter((c) => c.action === "skip").length;
    return { total: preview.totalChanges, move, copy, skip };
  }, [preview]);

  // 筛选后的列表
  const filteredChanges = useMemo(() => {
    if (!preview) return [];
    if (filter === "all") return preview.changes;
    return preview.changes.filter((c) => c.action === filter);
  }, [preview, filter]);

  const icon = isRename ? <AudioLines className="h-5 w-5" /> : <FolderTree className="h-5 w-5" />;
  const title = isRename ? "文件命名" : "文件整理";
  const desc = isRename
    ? "基于音乐元数据，把不规范的文件名重命名为「艺术家 - 歌曲名.扩展名」格式。不移动文件位置。"
    : "按「艺术家/专辑/」文件夹结构归类移动文件。不修改文件名，只改变文件所在目录。";
  const example = isRename
    ? "答案 - 冒海飞、徐丽东 - flac.flac  →  冒海飞 & 徐丽东 - 答案.flac"
    : "/music/冒海飞 - 答案.flac  →  /music/冒海飞/答案 (OST)/冒海飞 - 答案.flac";

  return (
    <div className="card p-6">
      {/* 标题区 */}
      <div className="flex items-start gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
          {icon}
        </div>
        <div className="flex-1">
          <h2 className="text-lg font-semibold text-ink-primary dark:text-ink-light">{title}</h2>
          <p className="mt-1 text-sm text-ink-muted dark:text-ink-lightMuted">{desc}</p>
          <div className="mt-2 rounded-lg bg-surface-light px-3 py-2 font-mono text-xs text-ink-secondary dark:bg-dark-hover dark:text-ink-lightSecondary">
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

      {/* 预览加载提示 */}
      {loading && (
        <div className="mt-5 flex items-center gap-3 rounded-lg border border-primary/20 bg-primary/5 px-4 py-3 dark:border-primary/30 dark:bg-primary/10">
          <Loader2 className="h-4 w-4 animate-spin text-primary" />
          <span className="text-sm text-ink-secondary dark:text-ink-lightSecondary">
            正在读取音乐文件元数据并生成预览，请稍候...
          </span>
        </div>
      )}

      {/* 预览结果 */}
      {preview && !loading && (
        <div className="mt-5 space-y-4">
          {/* 顶部汇总统计 */}
          <div className="grid grid-cols-4 gap-2">
            <StatCard
              label="总计"
              value={stats.total}
              icon={<FileMusic className="h-3.5 w-3.5" />}
              active={filter === "all"}
              onClick={() => setFilter("all")}
            />
            <StatCard
              label="移动"
              value={stats.move}
              icon={<ArrowRight className="h-3.5 w-3.5" />}
              color="blue"
              active={filter === "move"}
              onClick={() => setFilter("move")}
            />
            <StatCard
              label="复制"
              value={stats.copy}
              icon={<Copy className="h-3.5 w-3.5" />}
              color="green"
              active={filter === "copy"}
              onClick={() => setFilter("copy")}
            />
            <StatCard
              label="跳过"
              value={stats.skip}
              icon={<SkipForward className="h-3.5 w-3.5" />}
              color="gray"
              active={filter === "skip"}
              onClick={() => setFilter("skip")}
            />
          </div>

          {/* 筛选切换 */}
          <div className="flex items-center gap-2 text-xs text-ink-muted dark:text-ink-lightMuted">
            <Filter className="h-3.5 w-3.5" />
            <span>
              {filter === "all" ? "显示全部" : `仅显示${filter === "move" ? "移动" : filter === "copy" ? "复制" : "跳过"}项`}
              （{filteredChanges.length} 条）
            </span>
          </div>

          {/* 列表 */}
          <div className="max-h-[420px] space-y-1.5 overflow-y-auto rounded-lg bg-surface-light p-2 dark:bg-dark-hover/50">
            {filteredChanges.length === 0 ? (
              <div className="py-8 text-center text-sm text-ink-muted dark:text-ink-lightMuted">
                无符合条件的项
              </div>
            ) : (
              filteredChanges.map((c, i) => <PreviewRow key={i} index={i + 1} item={c} />)
            )}
          </div>
        </div>
      )}

      {/* 执行进度 */}
      {task && (
        <div className="mt-5 rounded-lg border border-primary/20 bg-primary/5 p-4 dark:border-primary/30 dark:bg-primary/10">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {task.status === "completed" ? (
                <CheckCircle2 className="h-5 w-5 text-primary" />
              ) : (
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
              )}
              <span className="text-sm font-semibold text-ink-primary dark:text-ink-light">
                {task.status === "completed" ? "已完成" : task.status === "failed" ? "失败" : "执行中"}
              </span>
            </div>
            <span className="text-sm text-ink-muted dark:text-ink-lightMuted">
              {task.processedFiles} / {task.totalFiles}（{task.progress.toFixed(0)}%）
            </span>
          </div>
          {/* 进度条 */}
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-surface-border dark:bg-dark-border">
            <div
              className="h-full bg-primary-gradient transition-all duration-500"
              style={{ width: `${task.progress}%` }}
            />
          </div>
          {/* 当前文件 */}
          {task.currentFile && (
            <div className="mt-2 truncate font-mono text-xs text-ink-muted dark:text-ink-lightMuted">
              {task.currentFile}
            </div>
          )}
          {/* 结果摘要 */}
          {task.status === "completed" && task.result && (
            <div className="mt-3 flex flex-wrap gap-4 text-xs">
              {Object.entries(task.result).map(([k, v]) => (
                <span key={k} className="text-ink-muted dark:text-ink-lightMuted">
                  {k}: <span className="font-semibold text-ink-primary dark:text-ink-light">{String(v)}</span>
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
            <div className="mt-2 text-xs text-ink-muted dark:text-ink-lightMuted">
              开始于 {formatRelativeTime(task.startedAt)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/** 统计小卡片 */
function StatCard({
  label,
  value,
  icon,
  color = "primary",
  active,
  onClick,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
  color?: "primary" | "blue" | "green" | "gray";
  active: boolean;
  onClick: () => void;
}) {
  const colorClasses = {
    primary: "text-primary",
    blue: "text-blue-500",
    green: "text-emerald-500",
    gray: "text-ink-muted dark:text-ink-lightMuted",
  };
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-2 rounded-lg border px-3 py-2 text-left transition-all",
        active
          ? "border-primary bg-primary/5 dark:bg-primary/10"
          : "border-surface-border bg-surface-card hover:border-primary/40 dark:border-dark-border dark:bg-dark-card"
      )}
    >
      <span className={cn("flex h-6 w-6 items-center justify-center rounded-md bg-surface-hover dark:bg-dark-hover", colorClasses[color])}>
        {icon}
      </span>
      <div>
        <div className="text-[10px] uppercase tracking-wide text-ink-muted dark:text-ink-lightMuted">
          {label}
        </div>
        <div className="text-sm font-semibold text-ink-primary dark:text-ink-light">
          {value}
        </div>
      </div>
    </button>
  );
}

/** 单条预览项 */
function PreviewRow({ index, item }: { index: number; item: PreviewChange }) {
  const oldP = splitPath(item.oldPath);
  const newP = splitPath(item.newPath);

  const actionConfig = {
    move: { label: "移动", icon: <ArrowRight className="h-3 w-3" />, color: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300" },
    copy: { label: "复制", icon: <Copy className="h-3 w-3" />, color: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300" },
    skip: { label: "跳过", icon: <SkipForward className="h-3 w-3" />, color: "bg-gray-100 text-gray-600 dark:bg-gray-700/40 dark:text-gray-300" },
  };
  const cfg = actionConfig[item.action] || actionConfig.skip;

  return (
    <div className="rounded-md border border-transparent bg-surface-card px-3 py-2 transition-colors hover:border-surface-border hover:bg-surface-hover dark:bg-dark-card dark:hover:border-dark-border dark:hover:bg-dark-hover">
      {/* 第一行：序号 + 操作徽章 + 元数据 */}
      <div className="flex items-center gap-2">
        <span className="w-6 shrink-0 text-right font-mono text-[10px] text-ink-muted dark:text-ink-lightMuted">
          {String(index).padStart(2, "0")}
        </span>
        <span className={cn("inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium", cfg.color)}>
          {cfg.icon}
          {cfg.label}
        </span>
        {(item.artist || item.album || item.title) && (
          <span className="truncate text-xs text-ink-muted dark:text-ink-lightMuted">
            {item.artist && <span>{item.artist}</span>}
            {item.album && <span> · {item.album}</span>}
            {item.title && <span> · {item.title}</span>}
          </span>
        )}
        {item.reason && (
          <span className="ml-auto truncate text-[10px] italic text-ink-muted dark:text-ink-lightMuted">
            {item.reason}
          </span>
        )}
      </div>
      {/* 第二行：原路径 → 新路径 */}
      <div className="mt-1.5 flex items-start gap-2 pl-8">
        <div className="min-w-0 flex-1 truncate font-mono text-[11px]">
          <span className="text-ink-muted dark:text-ink-lightMuted">{oldP.dir}</span>
          <span className="text-ink-secondary dark:text-ink-lightSecondary">{oldP.file}</span>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          <ArrowRight className="h-3 w-3 text-primary" />
        </div>
        <div className="min-w-0 flex-1 truncate font-mono text-[11px]">
          {item.action === "skip" ? (
            <span className="text-ink-muted dark:text-ink-lightMuted italic">{newP.file}</span>
          ) : (
            <>
              <span className="text-ink-muted dark:text-ink-lightMuted">{newP.dir}</span>
              <span className="font-medium text-primary">{newP.file}</span>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
