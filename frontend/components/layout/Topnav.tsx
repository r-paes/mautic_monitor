"use client";

import { Sun, Moon, Menu } from "lucide-react";
import { useTheme } from "@/components/layout/Providers";
import { useSidebar } from "@/lib/hooks/useSidebar";

interface TopnavProps {
  title: string;
  subtitle?: string;
  /** Tabs inline — visíveis apenas em desktop (md+). Mobile usa sub-itens da sidebar. */
  tabs?: React.ReactNode;
  /** Ações à direita (filtros, botões) */
  actions?: React.ReactNode;
}

export function Topnav({ title, subtitle, tabs, actions }: TopnavProps) {
  const { theme, toggle } = useTheme();
  const { toggle: toggleSidebar } = useSidebar();

  return (
    <header
      className="fixed top-0 right-0 z-20"
      style={{
        left: 0,
        background: "var(--color-topnav-bg)",
        borderBottom: "1px solid var(--color-nav-border)",
        height: "var(--topnav-height)",
      }}
    >
      <div className="sidebar-offset flex items-center h-full gap-3 px-4 md:px-6">
        {/* Hamburger — só mobile */}
        <button
          onClick={toggleSidebar}
          className="md:hidden shrink-0 p-1.5 rounded-md text-[var(--color-sidebar-muted)] hover:text-[var(--color-sidebar-text)] transition-colors"
          aria-label="Abrir menu"
        >
          <Menu size={20} />
        </button>

        {/* Título */}
        <div className="shrink-0">
          <h1 className="text-sm font-semibold text-[var(--color-sidebar-text)] leading-tight">
            {title}
          </h1>
          {subtitle && (
            <p className="hidden md:block text-[11px] text-[var(--color-sidebar-muted)] leading-tight">
              {subtitle}
            </p>
          )}
        </div>

        {/* Tabs inline — visíveis apenas em desktop; mobile usa sidebar sub-itens */}
        <div className="flex-1 flex items-center min-w-0">
          {tabs && (
            <div className="hidden md:flex items-center gap-1 px-2">
              {tabs}
            </div>
          )}
        </div>

        {/* Ações (filtros, botões) */}
        {actions && (
          <div className="flex items-center gap-2 shrink-0">{actions}</div>
        )}

        {/* Toggle tema */}
        <button
          onClick={toggle}
          className="shrink-0 flex items-center gap-1.5 px-2.5 py-1.5 rounded-[var(--radius-sm)] text-[var(--color-sidebar-muted)] hover:text-[var(--color-sidebar-text)] hover:bg-[var(--color-nav-active)] transition-colors text-xs font-medium"
          aria-label="Alternar tema"
        >
          {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
          <span className="hidden sm:inline">
            {theme === "dark" ? "Light" : "Dark"}
          </span>
        </button>
      </div>
    </header>
  );
}
