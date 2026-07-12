import { useEffect, useState } from "react";
import {
  Copy,
  Search,
  Trash2,
  Recycle,
  Check,
  Star,
  Loader2,
  ShieldCheck,
} from "lucide-react";
import { api } from "@/lib/api";
import {
  formatSize,
  formatBitrate,
  formatSampleRate,
  formatRelativeTime,
} from "@/lib/format";
import { cn } from "@/lib/utils";
import type { DuplicateGroup, OrganizeTask } from "@/types";

export default function Duplicates() {
  const [groups, setGroups] = useState<DuplicateGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanTask, setScanTask] = useState<OrganizeTask | null>(null);
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await api.duplicates.groups(1, 50);
      setGroups(res.items);
    } catch {
      // ignore load errors
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // 轮询扫描任务状态
  useEffect(() => {
    if (!scanTask) return;
    if (scanTask.status === "completed" || scanTask.status === "failed") {
      setScanning(false);
      if (scanTask.status === "failed") {
        setError("扫描失败：" + (scanTask.result?.error || "未知错误"));
      } else {
        loadData();
      }
      return;
    }
    const taskId = scanTask.id;
    const timer = setInterval(async () => {
      try {
        const t = await api.organize.task(taskId);
        setScanTask(t);
        if (t.status === "completed" || t.status === "failed") {
          clearInterval(timer);
          setScanning(false);
          if (t.status === "failed") {
            setError("扫描失败：" + (t.result?.error || "未知错误"));
          } else {
            loadData();
          }
        }
      } catch {
        clearInterval(timer);
        setScanning(false);
        setError("扫描任务查询失败");
      }
    }, 1500);
    return () => clearInterval(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scanTask?.id]);

  const handleScan = async () => {
    setScanning(true);
    setError(null);
    try {
      const { taskId } = await api.duplicates.scan();
      const t = await api.organize.task(taskId);
      setScanTask(t);
    } catch {
      setScanning(false);
      setError("启动扫描失败");
    }
  };

  const handleResolve = async (
    group: DuplicateGroup,
    keepFileId: string,
    action: "recycle" | "delete"
  ) => {
    setResolvingId(group.id);
    setError(null);
    try {
      await api.duplicates.resolve(group.groupHash, keepFileId, action);
      setGroups((prev) => prev.filter((g) => g.id !== group.id));
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail || "处理失败"
          : "处理失败";
      setError(msg);
    } finally {
      setResolvingId(null);
    }
  };

  return (
    <div className="space-y-5">
      {/* 操作栏 */}
      <div className="card flex items-center justify-between p-4">
        <div className="flex items-center gap-2">
          <Copy className="h-5 w-5 text-primary" />
          <div>
            <h3 className="text-base font-semibold text-ink-primary dark:text-ink-light">
              重复文件管理
            </h3>
            <p className="text-xs text-ink-muted dark:text-ink-lightMuted">
              共发现 {groups.length} 组重复文件
            </p>
          </div>
        </div>
        <button
          onClick={handleScan}
          disabled={scanning}
          className="btn-primary"
        >
          {scanning ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Search className="h-4 w-4" />
          )}
          {scanning ? "扫描中..." : "扫描重复"}
        </button>
      </div>

      {/* 扫描进度 */}
      {scanning && scanTask && (
        <div className="card flex items-center gap-3 p-4">
          <Loader2 className="h-4 w-4 animate-spin text-primary" />
          <div className="flex-1">
            <p className="text-sm font-medium text-ink-primary dark:text-ink-light">
              正在扫描重复文件...
            </p>
            {scanTask.totalFiles > 0 && (
              <p className="text-xs text-ink-muted dark:text-ink-lightMuted">
                {scanTask.processedFiles} / {scanTask.totalFiles}
                （{scanTask.progress.toFixed(0)}%）
              </p>
            )}
            {scanTask.currentFile && (
              <p className="mt-0.5 truncate font-mono text-[10px] text-ink-muted dark:text-ink-lightMuted">
                {scanTask.currentFile}
              </p>
            )}
          </div>
        </div>
      )}

      {/* 错误提示 */}
      {error && (
        <div className="card flex items-center gap-2 border border-red-200 bg-red-50 p-3 dark:border-red-900/50 dark:bg-red-900/10">
          <span className="text-sm text-red-600 dark:text-red-400">{error}</span>
          <button
            onClick={() => setError(null)}
            className="ml-auto text-xs text-red-500 hover:underline"
          >
            关闭
          </button>
        </div>
      )}

      {/* 重复组列表 */}
      {loading ? (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div
              key={i}
              className="h-40 animate-pulse rounded-xl bg-surface-card dark:bg-dark-card"
            />
          ))}
        </div>
      ) : groups.length === 0 ? (
        <div className="card py-20 text-center">
          <ShieldCheck className="mx-auto mb-3 h-14 w-14 text-emerald-400" />
          <p className="text-sm font-medium text-ink-primary dark:text-ink-light">
            未发现重复文件
          </p>
          <p className="mt-1 text-xs text-ink-muted dark:text-ink-lightMuted">
            音乐库很干净，无需清理
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {groups.map((group) => (
            <DuplicateGroupCard
              key={group.id}
              group={group}
              resolving={resolvingId === group.id}
              onResolve={handleResolve}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function DuplicateGroupCard({
  group,
  resolving,
  onResolve,
}: {
  group: DuplicateGroup;
  resolving: boolean;
  onResolve: (
    group: DuplicateGroup,
    keepFileId: string,
    action: "recycle" | "delete"
  ) => void;
}) {
  const [selectedId, setSelectedId] = useState<string>(
    group.files.find((f) => f.recommended)?.songId || group.files[0].songId
  );

  return (
    <div className="card overflow-hidden">
      {/* 组头部 */}
      <div className="flex items-center justify-between border-b border-surface-border bg-surface-hover px-5 py-3 dark:border-dark-border dark:bg-dark-hover">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "flex h-9 w-9 items-center justify-center rounded-full text-xs font-bold",
              group.similarity === 100
                ? "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400"
                : group.similarity >= 95
                ? "bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400"
                : "bg-sky-100 text-sky-600 dark:bg-sky-900/30 dark:text-sky-400"
            )}
          >
            {group.similarity}%
          </div>
          <div>
            <h4 className="text-sm font-semibold text-ink-primary dark:text-ink-light">
              {group.files[0].title}
            </h4>
            <p className="text-xs text-ink-muted dark:text-ink-lightMuted">
              {group.files[0].artist} · {group.files.length} 个文件
            </p>
          </div>
        </div>
      </div>

      {/* 文件对比 */}
      <div className="divide-y divide-surface-border dark:divide-dark-border/50">
        {group.files.map((file) => {
          const isSelected = selectedId === file.songId;
          return (
            <div
              key={file.songId}
              className={cn(
                "flex items-center gap-4 px-5 py-3 transition-colors",
                isSelected
                  ? "bg-primary-50 dark:bg-primary-900/10"
                  : "hover:bg-surface-hover dark:hover:bg-dark-hover"
              )}
            >
              <button
                onClick={() => setSelectedId(file.songId)}
                className={cn(
                  "flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 transition-colors",
                  isSelected
                    ? "border-primary bg-primary text-white"
                    : "border-surface-border dark:border-dark-border"
                )}
              >
                {isSelected && <Check className="h-3 w-3" />}
              </button>

              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="truncate text-sm font-medium text-ink-primary dark:text-ink-light">
                    {file.filePath.split("/").pop()}
                  </span>
                  {file.recommended && (
                    <span className="flex items-center gap-0.5 rounded bg-primary-100 px-1.5 py-0.5 text-xs text-primary dark:bg-primary-900/30 dark:text-primary-300">
                      <Star className="h-3 w-3 fill-current" />
                      推荐
                    </span>
                  )}
                </div>
                <p className="truncate font-mono text-xs text-ink-muted dark:text-ink-lightMuted">
                  {file.filePath}
                </p>
              </div>

              <div className="hidden items-center gap-6 text-xs md:flex">
                <div className="text-center">
                  <p className="text-ink-muted dark:text-ink-lightMuted">格式</p>
                  <p className="font-mono font-semibold text-ink-secondary dark:text-ink-lightSecondary">
                    {file.format}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-ink-muted dark:text-ink-lightMuted">码率</p>
                  <p className="font-mono font-semibold text-ink-secondary dark:text-ink-lightSecondary">
                    {formatBitrate(file.bitrate)}
                  </p>
                </div>
                <div className="hidden text-center lg:block">
                  <p className="text-ink-muted dark:text-ink-lightMuted">采样率</p>
                  <p className="font-mono font-semibold text-ink-secondary dark:text-ink-lightSecondary">
                    {formatSampleRate(file.sampleRate)}
                  </p>
                </div>
                <div className="text-center">
                  <p className="text-ink-muted dark:text-ink-lightMuted">大小</p>
                  <p className="font-mono font-semibold text-ink-secondary dark:text-ink-lightSecondary">
                    {formatSize(file.fileSize)}
                  </p>
                </div>
                <div className="hidden text-center lg:block">
                  <p className="text-ink-muted dark:text-ink-lightMuted">修改时间</p>
                  <p className="font-mono font-semibold text-ink-secondary dark:text-ink-lightSecondary">
                    {formatRelativeTime(file.fileModified)}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* 操作按钮 */}
      <div className="flex items-center justify-end gap-2 border-t border-surface-border px-5 py-3 dark:border-dark-border">
        <button
          onClick={() => onResolve(group, selectedId, "recycle")}
          disabled={resolving}
          className="btn-secondary"
        >
          {resolving ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Recycle className="h-4 w-4" />
          )}
          移入回收站
        </button>
        <button
          onClick={() => onResolve(group, selectedId, "delete")}
          disabled={resolving}
          className="inline-flex items-center justify-center gap-2 rounded-pill bg-red-500 px-5 py-2.5 text-sm font-medium text-white transition-all hover:bg-red-600 active:scale-95 disabled:opacity-50"
        >
          <Trash2 className="h-4 w-4" />
          永久删除
        </button>
      </div>
    </div>
  );
}
