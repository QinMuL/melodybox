import { useEffect, useState } from "react";
import {
  Settings as SettingsIcon,
  Folder,
  Save,
  TestTube,
  CheckCircle2,
  XCircle,
  Loader2,
  FileMusic,
  Cpu,
  ScrollText,
} from "lucide-react";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { SystemSettings } from "@/types";

export default function Settings() {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [testResult, setTestResult] = useState<{
    path: string;
    accessible: boolean;
    fileCount?: number;
    error?: string;
  } | null>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    api.settings.get().then(setSettings);
  }, []);

  const update = (key: keyof SystemSettings, value: unknown) => {
    setSettings((prev) => (prev ? { ...prev, [key]: value } : prev));
  };

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    await api.settings.update(settings);
    setSaving(false);
  };

  const handleTestDir = async (path: string) => {
    setTesting(true);
    const res = await api.settings.testDir(path);
    setTestResult({ path, ...res });
    setTesting(false);
  };

  if (!settings) {
    return (
      <div className="h-64 animate-pulse rounded-xl bg-surface-card dark:bg-dark-card" />
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      {/* 目录配置 */}
      <div className="card p-5">
        <div className="mb-4 flex items-center gap-2">
          <Folder className="h-5 w-5 text-primary" />
          <h3 className="text-base font-semibold text-ink-primary dark:text-ink-light">
            目录配置
          </h3>
        </div>

        <div className="space-y-4">
          <DirField
            label="输入目录（原始音乐文件）"
            value={settings.inputDir}
            onChange={(v) => update("inputDir", v)}
            testResult={testResult}
            testing={testing}
            onTest={handleTestDir}
          />
          <DirField
            label="输出目录（整理后文件）"
            value={settings.outputDir}
            onChange={(v) => update("outputDir", v)}
            testResult={testResult}
            testing={testing}
            onTest={handleTestDir}
          />
          <DirField
            label="回收站目录（重复/废弃文件）"
            value={settings.recycleDir}
            onChange={(v) => update("recycleDir", v)}
            testResult={testResult}
            testing={testing}
            onTest={handleTestDir}
          />
        </div>
      </div>

      {/* 支持格式 */}
      <div className="card p-5">
        <div className="mb-4 flex items-center gap-2">
          <FileMusic className="h-5 w-5 text-primary" />
          <h3 className="text-base font-semibold text-ink-primary dark:text-ink-light">
            支持的音频格式
          </h3>
        </div>
        <div className="flex flex-wrap gap-2">
          {settings.supportedFormats.map((fmt) => (
            <span
              key={fmt}
              className="rounded-lg border border-surface-border bg-surface-light px-3 py-1.5 text-sm font-medium text-ink-secondary dark:border-dark-border dark:bg-dark-hover dark:text-ink-lightSecondary"
            >
              {fmt}
            </span>
          ))}
        </div>
      </div>

      {/* 任务配置 */}
      <div className="card p-5">
        <div className="mb-4 flex items-center gap-2">
          <Cpu className="h-5 w-5 text-primary" />
          <h3 className="text-base font-semibold text-ink-primary dark:text-ink-light">
            任务配置
          </h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-ink-secondary dark:text-ink-lightSecondary">
              并发数（同时处理的文件数）
            </label>
            <input
              type="number"
              min={1}
              max={16}
              value={settings.concurrency}
              onChange={(e) =>
                update("concurrency", parseInt(e.target.value) || 1)
              }
              className="input-field w-32"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-sm font-medium text-ink-secondary dark:text-ink-lightSecondary">
              日志级别
            </label>
            <div className="flex gap-2">
              {(["debug", "info", "warning", "error"] as const).map((level) => (
                <button
                  key={level}
                  onClick={() => update("logLevel", level)}
                  className={cn(
                    "rounded-lg px-4 py-2 text-sm font-medium transition-colors",
                    settings.logLevel === level
                      ? "bg-primary-gradient text-white shadow-primary"
                      : "border border-surface-border text-ink-secondary hover:border-primary hover:text-primary dark:border-dark-border dark:text-ink-lightSecondary"
                  )}
                >
                  {level.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 保存按钮 */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-primary"
        >
          {saving ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Save className="h-4 w-4" />
          )}
          保存设置
        </button>
      </div>
    </div>
  );
}

function DirField({
  label,
  value,
  onChange,
  testResult,
  testing,
  onTest,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  testResult: { path: string; accessible: boolean; fileCount?: number; error?: string } | null;
  testing: boolean;
  onTest: (path: string) => void;
}) {
  const showResult = testResult?.path === value;

  return (
    <div>
      <label className="mb-1.5 block text-sm font-medium text-ink-secondary dark:text-ink-lightSecondary">
        {label}
      </label>
      <div className="flex gap-2">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="input-field flex-1 font-mono"
        />
        <button
          onClick={() => onTest(value)}
          disabled={testing || !value}
          className="btn-secondary shrink-0"
        >
          {testing ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <TestTube className="h-4 w-4" />
          )}
          测试
        </button>
      </div>
      {showResult && (
        <div
          className={cn(
            "mt-2 flex items-center gap-1.5 text-xs",
            testResult.accessible
              ? "text-emerald-600 dark:text-emerald-400"
              : "text-red-500"
          )}
        >
          {testResult.accessible ? (
            <>
              <CheckCircle2 className="h-4 w-4" />
              目录可访问，包含 {testResult.fileCount} 个文件
            </>
          ) : (
            <>
              <XCircle className="h-4 w-4" />
              {testResult.error || "目录不可访问"}
            </>
          )}
        </div>
      )}
    </div>
  );
}
