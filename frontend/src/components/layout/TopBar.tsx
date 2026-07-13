import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Sun, Moon, RefreshCw, Menu } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import { useStore } from "@/store/useStore";
import { cn } from "@/lib/utils";

interface TopBarProps {
  title: string;
  onRefresh?: () => void;
}

export default function TopBar({ title, onRefresh }: TopBarProps) {
  const { theme, toggleTheme, isDark } = useTheme();
  const { toggleMobileNav } = useStore();
  const navigate = useNavigate();
  const [searchValue, setSearchValue] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchValue.trim()) {
      navigate(`/library?q=${encodeURIComponent(searchValue.trim())}`);
    }
  };

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-surface-border bg-surface-card/80 px-3 backdrop-blur-lg dark:border-dark-border dark:bg-dark-card/80 sm:gap-4 sm:px-6">
      {/* 汉堡菜单：仅移动端显示 */}
      <button
        onClick={toggleMobileNav}
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-ink-secondary transition-colors hover:bg-surface-hover hover:text-primary dark:text-ink-lightSecondary dark:hover:bg-dark-hover dark:hover:text-primary md:hidden"
        title="打开菜单"
        aria-label="打开菜单"
      >
        <Menu className="h-5 w-5" />
      </button>

      <h2 className="shrink-0 text-lg font-semibold text-ink-primary dark:text-ink-light">
        {title}
      </h2>

      {/* 搜索栏：小屏隐藏，使用音乐库页内的搜索 */}
      <form onSubmit={handleSearch} className="relative ml-auto hidden w-96 max-w-[40%] sm:block">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted dark:text-ink-lightMuted" />
        <input
          type="text"
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
          placeholder="搜索歌曲、艺术家、专辑..."
          className="w-full rounded-pill border border-surface-border bg-surface-light py-2 pl-10 pr-4 text-sm text-ink-primary outline-none transition-all focus:border-primary focus:ring-2 focus:ring-primary/20 dark:border-dark-border dark:bg-dark-hover dark:text-ink-light dark:placeholder:text-ink-lightMuted"
        />
      </form>

      <div className={cn("flex items-center gap-2", "ml-auto sm:ml-0")}>
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="flex h-9 w-9 items-center justify-center rounded-full text-ink-secondary transition-colors hover:bg-surface-hover hover:text-primary dark:text-ink-lightSecondary dark:hover:bg-dark-hover dark:hover:text-primary"
            title="刷新"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        )}

        {/* 主题切换 */}
        <button
          onClick={toggleTheme}
          className={cn(
            "flex h-9 w-9 items-center justify-center rounded-full transition-colors",
            isDark
              ? "text-ink-lightSecondary hover:bg-dark-hover hover:text-primary"
              : "text-ink-secondary hover:bg-surface-hover hover:text-primary"
          )}
          title={isDark ? "切换到浅色模式" : "切换到深色模式"}
        >
          {theme === "dark" ? (
            <Sun className="h-4 w-4" />
          ) : (
            <Moon className="h-4 w-4" />
          )}
        </button>
      </div>
    </header>
  );
}
