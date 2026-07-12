import { useCallback, useEffect, useRef, useState } from "react";
import {
  ScrollText,
  Search,
  RefreshCw,
  Trash2,
  Play,
  Pause,
  Download,
  AlertCircle,
  Info,
  AlertTriangle,
  XCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { LogEntry, LogListResponse } from "@/types";

// 级别颜色映射
const LEVEL_STYLES: Record<string, { color: string; bg: string; Icon: typeof Info }> = {
  DEBUG: { color: "text-ink-muted", bg: "bg-surface-hover", Icon: Info },
  INFO: { color: "text-blue-600 dark:text-blue-400", bg: "bg-blue-50 dark:bg-blue-900/20", Icon: Info },
  WARNING: { color: "text-amber-600 dark:text-amber-400", bg: "bg-amber-50 dark:bg-amber-900/20", Icon: AlertTriangle },
  ERROR: { color: "text-red-600 dark:text-red-400", bg: "bg-red-50 dark:bg-red-900/20", Icon: AlertCircle },
  CRITICAL: { color: "text-red-700 dark:text-red-300", bg: "bg-red-100 dark:bg-red-900/40", Icon: XCircle },
};

const LEVEL_OPTIONS = ["", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"];

export default function Logs() {
  const [data, setData] = useState<LogListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [level, setLevel] = useState<string>("");
  const [search, setSearch] = useState("");
  const [limit, setLimit] = useState(500);
  const [autoRefresh, setAutoRefresh] = useState(
    () => localStorage.getItem("logs:autoRefresh") === "true"
  );
  const [followTail, setFollowTail] = useState(
    () => localStorage.getItem("logs:followTail") !== "false"
  );
  const [clearing, setClearing] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const refreshTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.logs.list({
        level: level || undefined,
        search: search || undefined,
        limit,
      });
      setData(res);
    } finally {
      setLoading(false);
    }
  }, [level, search, limit]);

  // 初始加载与依赖变化时重新加载
  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  // 搜索框防抖
  const handleSearchChange = (v: string) => {
    setSearch(v);
    if (searchTimer.current) clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => {
      // 触发 fetchLogs（通过依赖变化）
    }, 300);
  };

  // 自动刷新
  useEffect(() => {
    if (!autoRefresh) {
      if (refreshTimer.current) clearInterval(refreshTimer.current);
      return;
    }
    refreshTimer.current = setInterval(fetchLogs, 3000);
    return () => {
      if (refreshTimer.current) clearInterval(refreshTimer.current);
    };
  }, [autoRefresh, fetchLogs]);

  // 跟随底部滚动
  useEffect(() => {
    if (followTail && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [data, followTail]);

  // 持久化 UI 偏好到 localStorage
  useEffect(() => {
    localStorage.setItem("logs:followTail", String(followTail));
  }, [followTail]);
  useEffect(() => {
    localStorage.setItem("logs:autoRefresh", String(autoRefresh));
  }, [autoRefresh]);

  const handleClear = async () => {
    if (!confirm("确认清空当前主日志文件？轮转副本会保留。")) return;
    setClearing(true);
    try {
      await api.logs.clear();
      await fetchLogs();
    } finally {
      setClearing(false);
    }
  };

  const handleDownload = () => {
    if (!data?.entries.length) return;
    const text = data.entries
      .slice()
      .reverse() // 还原为时间正序
      .map((e) => e.raw)
      .join("\n");
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `melodybox-${new Date().toISOString().slice(0, 19)}.log`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mx-auto flex h-full max-w-6xl flex-col space-y-4">
      {/* 头部 */}
      <div className="card flex flex-wrap items-center gap-3 p-4">
        <div className="flex items-center gap-2">
          <ScrollText className="h-5 w-5 text-primary" />
          <h3 className="text-base font-semibold text-ink-primary dark:text-ink-light">
            系统日志
          </h3>
        </div>

        <div className="ml-auto flex flex-wrap items-center gap-2">
          {/* 级别筛选 */}
          <select
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            className="input-field h-9 w-32 text-sm"
          >
            {LEVEL_OPTIONS.map((l) => (
              <option key={l} value={l}>
                {l || "全部级别"}
              </option>
            ))}
          </select>

          {/* 行数 */}
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="input-field h-9 w-28 text-sm"
          >
            <option value={100}>100 行</option>
            <option value={500}>500 行</option>
            <option value={1000}>1000 行</option>
            <option value={5000}>5000 行</option>
          </select>

          {/* 刷新 */}
          <button
            onClick={fetchLogs}
            disabled={loading}
            className="btn-secondary h-9 px-3 text-sm"
            title="刷新"
          >
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
          </button>

          {/* 自动刷新 */}
          <button
            onClick={() => setAutoRefresh((v) => !v)}
            className={cn(
              "flex h-9 items-center gap-1.5 rounded-lg px-3 text-sm font-medium transition-colors",
              autoRefresh
                ? "bg-primary text-white"
                : "bg-surface-hover text-ink-secondary hover:text-primary dark:bg-dark-hover dark:text-ink-lightSecondary"
            )}
            title="每 3 秒自动刷新"
          >
            {autoRefresh ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            自动
          </button>

          {/* 下载 */}
          <button
            onClick={handleDownload}
            disabled={!data?.entries.length}
            className="btn-secondary h-9 px-3 text-sm"
            title="下载日志"
          >
            <Download className="h-4 w-4" />
          </button>

          {/* 清空 */}
          <button
            onClick={handleClear}
            disabled={clearing}
            className="flex h-9 items-center gap-1.5 rounded-lg bg-red-50 px-3 text-sm font-medium text-red-600 transition-colors hover:bg-red-100 disabled:opacity-50 dark:bg-red-900/20 dark:text-red-400 dark:hover:bg-red-900/40"
            title="清空主日志文件"
          >
            <Trash2 className="h-4 w-4" />
            清空
          </button>
        </div>
      </div>

      {/* 搜索栏 */}
      <div className="card flex items-center gap-2 p-3">
        <Search className="h-4 w-4 text-ink-muted" />
        <input
          type="text"
          value={search}
          onChange={(e) => handleSearchChange(e.target.value)}
          placeholder="搜索关键词（不区分大小写）..."
          className="flex-1 bg-transparent text-sm outline-none placeholder:text-ink-muted"
        />
        {search && (
          <button
            onClick={() => setSearch("")}
            className="text-ink-muted hover:text-ink-primary dark:hover:text-ink-light"
          >
            <XCircle className="h-4 w-4" />
          </button>
        )}
        <label className="flex items-center gap-1.5 text-xs text-ink-muted">
          <input
            type="checkbox"
            checked={followTail}
            onChange={(e) => setFollowTail(e.target.checked)}
            className="h-3 w-3"
          />
          跟随底部
        </label>
      </div>

      {/* 统计信息 */}
      {data && (
        <div className="flex items-center gap-4 px-1 text-xs text-ink-muted">
          <span>共 {data.total} 条</span>
          <span>文件大小: {formatSize(data.fileSize)}</span>
          <span className="truncate">文件: {data.file}</span>
        </div>
      )}

      {/* 日志列表 */}
      <div
        ref={containerRef}
        className="card flex-1 overflow-auto p-0"
        style={{ minHeight: "300px", maxHeight: "calc(100vh - 280px)" }}
      >
        {loading && !data ? (
          <div className="flex h-full items-center justify-center text-ink-muted">
            <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
            加载中...
          </div>
        ) : !data || data.entries.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-ink-muted">
            <ScrollText className="mb-2 h-10 w-10 opacity-30" />
            <p>暂无日志记录</p>
            <p className="mt-1 text-xs">触发扫描/整理任务后将产生日志</p>
          </div>
        ) : (
          <table className="w-full text-xs">
            <tbody>
              {data.entries.map((entry, idx) => {
                const style = LEVEL_STYLES[entry.level] || LEVEL_STYLES.INFO;
                const Icon = style.Icon;
                return (
                  <tr
                    key={idx}
                    className="border-b border-surface-border align-top transition-colors hover:bg-surface-hover dark:border-dark-border dark:hover:bg-dark-hover"
                  >
                    <td className="whitespace-nowrap px-2 py-1.5 font-mono text-ink-muted">
                      {entry.time || "—"}
                    </td>
                    <td className="px-2 py-1.5">
                      <span
                        className={cn(
                          "inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase",
                          style.bg,
                          style.color
                        )}
                      >
                        <Icon className="h-3 w-3" />
                        {entry.level}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-2 py-1.5 font-mono text-ink-muted">
                      {entry.logger || "—"}
                    </td>
                    <td className="px-2 py-1.5 font-mono text-ink-primary break-all dark:text-ink-light">
                      {entry.message}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// 简单的字节大小格式化
function formatSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`;
}
