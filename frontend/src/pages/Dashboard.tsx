import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Music2,
  Users,
  Disc3,
  Copy,
  Wand2,
  RefreshCw,
  CheckCircle2,
  Loader2,
  Clock,
  HardDrive,
  ScanLine,
} from "lucide-react";
import { api } from "@/lib/api";
import { formatNumber, formatSize, formatRelativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { LibraryStats, OrganizeTask } from "@/types";

interface StatItem {
  key: string;
  label: string;
  value: string;
  icon: typeof Music2;
  gradient: string;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<LibraryStats | null>(null);
  const [tasks, setTasks] = useState<OrganizeTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [scanMsg, setScanMsg] = useState<{ type: "success" | "error" | "info"; text: string } | null>(null);

  const loadData = async () => {
    setLoading(true);
    const [statsRes, tasksRes] = await Promise.all([
      api.library.stats(),
      api.organize.tasks(1, 5),
    ]);
    setStats(statsRes);
    setTasks(tasksRes.items);
    setLoading(false);
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleScan = async () => {
    setScanning(true);
    setScanMsg({ type: "info", text: "扫描任务已提交..." });
    try {
      const res = await api.library.scan();
      setScanMsg({ type: "success", text: `扫描已启动（任务ID: ${res.taskId.slice(0, 8)}），请稍后刷新查看结果` });
      // 30 秒后自动刷新统计
      setTimeout(loadData, 30000);
    } catch (err) {
      setScanMsg({ type: "error", text: `扫描失败: ${err instanceof Error ? err.message : String(err)}` });
    } finally {
      setScanning(false);
      setTimeout(() => setScanMsg(null), 8000);
    }
  };

  const statItems: StatItem[] = stats
    ? [
        { key: "songs", label: "音乐总数", value: formatNumber(stats.totalSongs), icon: Music2, gradient: "from-emerald-400 to-emerald-600" },
        { key: "artists", label: "艺术家", value: formatNumber(stats.totalArtists), icon: Users, gradient: "from-sky-400 to-sky-600" },
        { key: "albums", label: "专辑", value: formatNumber(stats.totalAlbums), icon: Disc3, gradient: "from-violet-400 to-violet-600" },
        { key: "duplicates", label: "重复文件", value: formatNumber(stats.totalDuplicates), icon: Copy, gradient: "from-amber-400 to-amber-600" },
      ]
    : [];

  return (
    <div className="space-y-6">
      {/* 欢迎横幅 */}
      <div className="relative overflow-hidden rounded-2xl bg-primary-gradient p-6 text-white shadow-primary">
        <div className="relative z-10">
          <h2 className="text-2xl font-bold">MelodyBox 音律盒子</h2>
          <p className="mt-1 text-sm text-white/80">
            智能音乐文件整理工具 · 让你的音乐库井然有序
          </p>
          <div className="mt-4 flex items-center gap-2 text-sm text-white/90">
            <HardDrive className="h-4 w-4" />
            <span>库总大小：{stats ? formatSize(stats.totalSize) : "计算中..."}</span>
          </div>
        </div>
        <div className="absolute -right-8 -top-8 h-40 w-40 rounded-full bg-white/10" />
        <div className="absolute -bottom-12 right-16 h-32 w-32 rounded-full bg-white/5" />
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="h-28 animate-pulse rounded-xl bg-surface-card dark:bg-dark-card"
              />
            ))
          : statItems.map((item, idx) => {
              const Icon = item.icon;
              return (
                <div
                  key={item.key}
                  className="card group cursor-pointer p-5 hover:-translate-y-1 hover:shadow-cardHover"
                  style={{ animationDelay: `${idx * 60}ms` }}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-sm text-ink-muted dark:text-ink-lightMuted">
                        {item.label}
                      </p>
                      <p className="mt-2 font-mono text-3xl font-bold text-ink-primary dark:text-ink-light">
                        {item.value}
                      </p>
                    </div>
                    <div
                      className={cn(
                        "flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br text-white shadow-md",
                        item.gradient
                      )}
                    >
                      <Icon className="h-5 w-5" />
                    </div>
                  </div>
                </div>
              );
            })}
      </div>

      {/* 快速操作 */}
      <div className="card p-5">
        <h3 className="mb-4 text-base font-semibold text-ink-primary dark:text-ink-light">
          快速操作
        </h3>
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={handleScan}
            disabled={scanning}
            className="btn-primary"
          >
            {scanning ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ScanLine className="h-4 w-4" />
            )}
            扫描入库
          </button>
          <button
            onClick={() => navigate("/organize")}
            className="btn-secondary"
          >
            <Wand2 className="h-4 w-4" />
            一键整理
          </button>
          <button
            onClick={() => navigate("/duplicates")}
            className="btn-secondary"
          >
            <Copy className="h-4 w-4" />
            扫描去重
          </button>
          <button onClick={loadData} className="btn-secondary">
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
            刷新音乐库
          </button>
          {scanMsg && (
            <span
              className={cn(
                "text-sm font-medium",
                scanMsg.type === "success"
                  ? "text-emerald-600 dark:text-emerald-400"
                  : scanMsg.type === "error"
                  ? "text-red-500"
                  : "text-sky-600 dark:text-sky-400"
              )}
            >
              {scanMsg.text}
            </span>
          )}
        </div>
        <p className="mt-3 text-xs text-ink-muted dark:text-ink-lightMuted">
          点击「扫描入库」会扫描输入目录下所有音频文件并入库到数据库，扫描完成后音乐库将显示艺术家和专辑列表
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* 最近任务 */}
        <div className="card p-5">
          <h3 className="mb-4 text-base font-semibold text-ink-primary dark:text-ink-light">
            最近任务
          </h3>
          <div className="space-y-3">
            {loading ? (
              <div className="h-20 animate-pulse rounded-lg bg-surface-hover dark:bg-dark-hover" />
            ) : tasks.length === 0 ? (
              <p className="py-8 text-center text-sm text-ink-muted dark:text-ink-lightMuted">
                暂无任务记录
              </p>
            ) : (
              tasks.map((task) => <TaskItem key={task.id} task={task} />)
            )}
          </div>
        </div>

        {/* 格式分布 */}
        <div className="card p-5">
          <h3 className="mb-4 text-base font-semibold text-ink-primary dark:text-ink-light">
            音频格式分布
          </h3>
          {stats && stats.formatBreakdown.length > 0 ? (
            <div className="space-y-3">
              {stats.formatBreakdown.map((fmt) => {
                const max = stats.formatBreakdown[0].count;
                const percent = (fmt.count / max) * 100;
                return (
                  <div key={fmt.format} className="flex items-center gap-3">
                    <span className="w-12 text-sm font-medium text-ink-secondary dark:text-ink-lightSecondary">
                      {fmt.format}
                    </span>
                    <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-surface-hover dark:bg-dark-hover">
                      <div
                        className="h-full rounded-full bg-primary-gradient transition-all duration-500"
                        style={{ width: `${percent}%` }}
                      />
                    </div>
                    <span className="w-16 text-right font-mono text-xs text-ink-muted dark:text-ink-lightMuted">
                      {formatNumber(fmt.count)}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="py-8 text-center text-sm text-ink-muted dark:text-ink-lightMuted">
              暂无数据
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function TaskItem({ task }: { task: OrganizeTask }) {
  const typeLabel =
    task.taskType === "organize"
      ? "整理任务"
      : task.taskType === "duplicate_scan"
      ? "去重扫描"
      : "扫描任务";

  return (
    <div className="flex items-center gap-3 rounded-lg p-3 transition-colors hover:bg-surface-hover dark:hover:bg-dark-hover">
      <div
        className={cn(
          "flex h-9 w-9 shrink-0 items-center justify-center rounded-full",
          task.status === "completed"
            ? "bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400"
            : task.status === "running"
            ? "bg-sky-100 text-sky-600 dark:bg-sky-900/30 dark:text-sky-400"
            : task.status === "failed"
            ? "bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400"
            : "bg-amber-100 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400"
        )}
      >
        {task.status === "running" ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : task.status === "completed" ? (
          <CheckCircle2 className="h-4 w-4" />
        ) : (
          <Clock className="h-4 w-4" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-ink-primary dark:text-ink-light">
            {typeLabel}
          </span>
          <span
            className={cn(
              "rounded px-1.5 py-0.5 text-xs",
              task.status === "completed"
                ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
                : task.status === "running"
                ? "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400"
                : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
            )}
          >
            {task.status === "running" ? "进行中" : task.status === "completed" ? "已完成" : task.status === "failed" ? "失败" : "等待中"}
          </span>
        </div>
        <p className="mt-0.5 truncate text-xs text-ink-muted dark:text-ink-lightMuted">
          {formatRelativeTime(task.startedAt)} · {task.processedFiles}/{task.totalFiles} 文件
        </p>
      </div>
      <div className="text-right">
        <span className="font-mono text-sm font-semibold text-primary">
          {task.progress}%
        </span>
      </div>
    </div>
  );
}
