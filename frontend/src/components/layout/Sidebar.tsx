import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Library,
  Wand2,
  Copy,
  Settings,
  Music4,
  ChevronLeft,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useStore } from "@/store/useStore";

const navItems = [
  { to: "/dashboard", icon: LayoutDashboard, label: "总览" },
  { to: "/library", icon: Library, label: "音乐库" },
  { to: "/organize", icon: Wand2, label: "整理中心" },
  { to: "/duplicates", icon: Copy, label: "去重管理" },
  { to: "/settings", icon: Settings, label: "系统设置" },
];

export default function Sidebar() {
  const { sidebarCollapsed, toggleSidebar } = useStore();

  return (
    <aside
      className={cn(
        "flex flex-col border-r border-surface-border bg-surface-card transition-all duration-300 dark:border-dark-border dark:bg-dark-card",
        sidebarCollapsed ? "w-[68px]" : "w-[220px]"
      )}
    >
      {/* Logo 区域 */}
      <div className="flex h-16 items-center gap-3 border-b border-surface-border px-4 dark:border-dark-border">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary-gradient shadow-primary">
          <Music4 className="h-5 w-5 text-white" />
        </div>
        {!sidebarCollapsed && (
          <div className="overflow-hidden">
            <h1 className="text-lg font-bold leading-tight text-ink-primary dark:text-ink-light">
              MelodyBox
            </h1>
            <p className="text-xs text-ink-muted dark:text-ink-lightMuted">
              音律盒子
            </p>
          </div>
        )}
      </div>

      {/* 导航菜单 */}
      <nav className="flex-1 space-y-1 p-3">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200",
                  isActive
                    ? "bg-primary-gradient text-white shadow-primary"
                    : "text-ink-secondary hover:bg-surface-hover hover:text-primary dark:text-ink-lightSecondary dark:hover:bg-dark-hover dark:hover:text-primary"
                )
              }
              title={sidebarCollapsed ? item.label : undefined}
            >
              <Icon className="h-5 w-5 shrink-0" />
              {!sidebarCollapsed && <span>{item.label}</span>}
            </NavLink>
          );
        })}
      </nav>

      {/* 折叠按钮 */}
      <button
        onClick={toggleSidebar}
        className="flex h-12 items-center justify-center border-t border-surface-border text-ink-muted transition-colors hover:text-primary dark:border-dark-border dark:text-ink-lightMuted dark:hover:text-primary"
      >
        <ChevronLeft
          className={cn(
            "h-5 w-5 transition-transform duration-300",
            sidebarCollapsed && "rotate-180"
          )}
        />
      </button>
    </aside>
  );
}
