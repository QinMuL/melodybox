import { useEffect, useState } from "react";
import {
  Wand2,
  Play,
  Eye,
  Loader2,
  CheckCircle2,
  AlertCircle,
  FolderInput,
  FileOutput,
  Settings2,
  Terminal,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { OrganizeConfig, OrganizeTask, PreviewResult } from "@/types";

export default function Organize() {
  const [config, setConfig] = useState<OrganizeConfig | null>(null);
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [task, setTask] = useState<OrganizeTask | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    api.organize.config().then(setConfig);
  }, []);

  const handlePreview = async () => {
    setPreviewing(true);
    const res = await api.organize.preview();
    setPreview(res);
    setPreviewing(false);
  };

  const handleStart = async () => {
    setStarting(true);
    const res = await api.organize.start(false);
    // 轮询任务状态
    const poll = async () => {
      const t = await api.organize.task(res.taskId);
      setTask(t);
      if (t.status === "running" || t.status === "pending") {
        setTimeout(poll, 2000);
      }
    };
    poll();
    setStarting(false);
  };

  const updateConfig = (key: keyof OrganizeConfig, value: unknown) => {
    setConfig((prev) => (prev ? { ...prev, [key]: value } : prev));
  };

  if (!config) {
    return (
      <div className="h-64 animate-pulse rounded-xl bg-surface-card dark:bg-dark-card" />
    );
  }

  const isRunning = task?.status === "running";

  return (
    <div className="space-y-5">
      <div className="grid gap-5 lg:grid-cols-2">
        {/* 整理配置 */}
        <div className="card p-5">
          <div className="mb-4 flex items-center gap-2">
            <Settings2 className="h-5 w-5 text-primary" />
            <h3 className="text-base font-semibold text-ink-primary dark:text-ink-light">
              整理配置
            </h3>
          </div>

          <div className="space-y-4">
            <ConfigField
              icon={FolderInput}
              label="输入目录"
              value={config.inputDir}
              onChange={(v) => updateConfig("inputDir", v)}
            />
            <ConfigField
              icon={FileOutput}
              label="输出目录"
              value={config.outputDir}
              onChange={(v) => updateConfig("outputDir", v)}
            />

            <div>
              <label className="mb-1.5 block text-sm font-medium text-ink-secondary dark:text-ink-lightSecondary">
                命名模板
              </label>
              <input
                type="text"
                value={config.namingTemplate}
                onChange={(e) => updateConfig("namingTemplate", e.target.value)}
                className="input-field font-mono"
                placeholder="{artist}/{album}/{track:02d}-{title}"
              />
              <div className="mt-2 flex flex-wrap gap-1.5">
                {["{artist}", "{album}", "{title}", "{track:02d}", "{year}"].map(
                  (tag) => (
                    <span
                      key={tag}
                      className="rounded bg-primary-50 px-2 py-0.5 font-mono text-xs text-primary dark:bg-primary-900/20 dark:text-primary-300"
                    >
                      {tag}
                    </span>
                  )
                )}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-ink-secondary dark:text-ink-lightSecondary">
                  操作模式
                </label>
                <select
                  value={config.moveInsteadOfCopy ? "move" : "copy"}
                  onChange={(e) =>
                    updateConfig("moveInsteadOfCopy", e.target.value === "move")
                  }
                  className="input-field"
                >
                  <option value="move">移动</option>
                  <option value="copy">复制</option>
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium text-ink-secondary dark:text-ink-lightSecondary">
                  冲突策略
                </label>
                <select
                  value={config.overwritePolicy}
                  onChange={(e) =>
                    updateConfig(
                      "overwritePolicy",
                      e.target.value as OrganizeConfig["overwritePolicy"]
                    )
                  }
                  className="input-field"
                >
                  <option value="skip">跳过</option>
                  <option value="overwrite">覆盖</option>
                  <option value="rename">重命名</option>
                </select>
              </div>
            </div>

            <button
              onClick={() => api.organize.updateConfig(config)}
              className="btn-secondary w-full"
            >
              保存配置
            </button>
          </div>
        </div>

        {/* 操作面板 */}
        <div className="card p-5">
          <div className="mb-4 flex items-center gap-2">
            <Wand2 className="h-5 w-5 text-primary" />
            <h3 className="text-base font-semibold text-ink-primary dark:text-ink-light">
              执行操作
            </h3>
          </div>

          <div className="space-y-4">
            <button
              onClick={handlePreview}
              disabled={previewing || isRunning}
              className="btn-secondary w-full disabled:opacity-50"
            >
              {previewing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
              预览整理结果
            </button>

            <button
              onClick={handleStart}
              disabled={starting || isRunning}
              className="btn-primary w-full disabled:opacity-50"
            >
              {starting ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : isRunning ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              {isRunning ? "整理进行中..." : "开始整理"}
            </button>

            {/* 任务进度 */}
            {task && (
              <div className="rounded-lg bg-surface-hover p-4 dark:bg-dark-hover">
                <div className="mb-2 flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-sm font-medium text-ink-primary dark:text-ink-light">
                    {task.status === "completed" ? (
                      <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                    ) : task.status === "failed" ? (
                      <AlertCircle className="h-4 w-4 text-red-500" />
                    ) : (
                      <Loader2 className="h-4 w-4 animate-spin text-sky-500" />
                    )}
                    任务进度
                  </span>
                  <span className="font-mono text-sm font-bold text-primary">
                    {task.progress}%
                  </span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-surface-border dark:bg-dark-border">
                  <div
                    className="h-full rounded-full bg-primary-gradient transition-all duration-500"
                    style={{ width: `${task.progress}%` }}
                  />
                </div>
                <div className="mt-2 flex justify-between text-xs text-ink-muted dark:text-ink-lightMuted">
                  <span>
                    {task.processedFiles} / {task.totalFiles} 文件
                  </span>
                  {task.currentFile && (
                    <span className="max-w-[50%] truncate">
                      当前：{task.currentFile}
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 预览结果 */}
      {preview && (
        <div className="card p-5">
          <h3 className="mb-3 text-base font-semibold text-ink-primary dark:text-ink-light">
            预览结果（{preview.totalChanges} 项变更）
          </h3>
          <div className="space-y-2">
            {preview.changes.map((change, idx) => (
              <div
                key={idx}
                className="rounded-lg border border-surface-border p-3 dark:border-dark-border"
              >
                <div className="mb-1 flex items-center gap-2">
                  <span
                    className={cn(
                      "rounded px-2 py-0.5 text-xs font-medium",
                      change.action === "rename"
                        ? "bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400"
                        : change.action === "move"
                        ? "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400"
                        : "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                    )}
                  >
                    {change.action === "rename"
                      ? "重命名"
                      : change.action === "move"
                      ? "移动"
                      : "跳过"}
                  </span>
                  <span className="text-xs text-ink-muted dark:text-ink-lightMuted">
                    {change.reason}
                  </span>
                </div>
                <div className="flex items-center gap-2 font-mono text-xs">
                  <span className="text-red-500 line-through">{change.oldPath}</span>
                  <span className="text-ink-muted">→</span>
                  <span className="text-emerald-500">{change.newPath}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 任务日志 */}
      {task && task.logs.length > 0 && (
        <div className="card overflow-hidden">
          <div className="flex items-center gap-2 border-b border-surface-border px-5 py-3 dark:border-dark-border">
            <Terminal className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold text-ink-primary dark:text-ink-light">
              任务日志
            </h3>
          </div>
          <div className="max-h-64 overflow-y-auto bg-surface-hover p-4 font-mono text-xs dark:bg-dark-hover">
            {task.logs.map((log, idx) => (
              <div key={idx} className="flex gap-2 py-0.5">
                <span className="text-ink-muted dark:text-ink-lightMuted">
                  {log.time}
                </span>
                <span
                  className={cn(
                    "font-semibold",
                    log.level === "error"
                      ? "text-red-500"
                      : log.level === "warning"
                      ? "text-amber-500"
                      : "text-emerald-500"
                  )}
                >
                  [{log.level.toUpperCase()}]
                </span>
                <span className="text-ink-secondary dark:text-ink-lightSecondary">
                  {log.message}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ConfigField({
  icon: Icon,
  label,
  value,
  onChange,
}: {
  icon: typeof FolderInput;
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-ink-secondary dark:text-ink-lightSecondary">
        {label}
      </label>
      <div className="relative">
        <Icon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted dark:text-ink-lightMuted" />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="input-field pl-10 font-mono"
        />
      </div>
    </div>
  );
}
