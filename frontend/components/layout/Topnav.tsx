"use client";

import { Bell, Sun, Moon, Menu } from "lucide-react";
import { useTheme } from "@/components/layout/Providers";
import { useSidebar } from "@/lib/hooks/useSidebar";

interface TopnavProps {
  title: string;
  subtitle?: string;
  /** Tabs inline — aparecem na mesma linha do título, no centro */
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
      <div
        className="flex items-center h-full gap-3 px-4 md:px-6"
        style={{ marginLeft: "var(--sidebar-width)" }}
      >
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

        {/* Tabs inline — ocupa o espaço central, scrollável em mobile */}
        {tabs && (
          <div className="flex-1 flex items-center overflow-x-auto min-w-0 scrollbar-none px-2">
            {tabs}
          </div>
        )}

        {/* Espaço vazio quando não há tabs */}
        {!tabs && <div className="flex-1" />}

        {/* Ações (filtros, botões) */}
        {actions && (
          <div className="flex items-center gap-2 shrink-0">{actions}</div>
        )}

        {/* Notificações */}
        <button
          className="shrink-0 p-1.5 rounded-md text-[var(--color-sidebar-muted)] hover:text-[var(--color-sidebar-text)] transition-colors"
          aria-label="Notificações"
        >
          <Bell size={18} strokeWidth={1.75} />
        </button>

        {/* Toggle tema */}
        <button
          onClick={toggle}
          className="shrink-0 p-1.5 rounded-md text-[var(--color-sidebar-muted)] hover:text-[var(--color-sidebar-text)] transition-colors"
          aria-label="Alternar tema"
        >
          {theme === "dark" ? <Sun size={16} /> : <Moon size={16} />}
        </button>
      </div>
    </header>
  );
}
