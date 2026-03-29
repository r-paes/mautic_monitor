"use client";

import { clsx } from "clsx";

interface Tab {
  key: string;
  label: string;
  count?: number;
}

interface TabsProps {
  tabs: Tab[];
  active: string;
  onChange: (key: string) => void;
  /** "topnav" renderiza no estilo dos tabs do topo (fundo escuro), "page" renderiza com estilo claro */
  variant?: "topnav" | "page";
}

export function Tabs({ tabs, active, onChange, variant = "page" }: TabsProps) {
  if (variant === "topnav") {
    return (
      <>
        {/* Mobile: select nativo — sem rolagem horizontal */}
        <select
          className="md:hidden h-8 px-2 text-sm rounded-[var(--radius-sm)] border border-[var(--color-nav-border)] bg-[var(--color-nav-active)] text-[var(--color-sidebar-text)] focus:outline-none focus:border-[var(--color-primary)]"
          value={active}
          onChange={(e) => onChange(e.target.value)}
        >
          {tabs.map((tab) => (
            <option key={tab.key} value={tab.key}>
              {tab.label}
            </option>
          ))}
        </select>

        {/* Desktop: botões inline */}
        <div className="hidden md:flex items-center gap-1">
          {tabs.map((tab) => {
            const isActive = tab.key === active;
            return (
              <button
                key={tab.key}
                onClick={() => onChange(tab.key)}
                className={clsx(
                  "px-3.5 py-1.5 rounded-[var(--radius-sm)] text-sm whitespace-nowrap transition-colors",
                  isActive
                    ? "bg-[var(--color-nav-active)] text-[var(--color-primary)] font-semibold"
                    : "text-[var(--color-sidebar-muted)] font-medium hover:bg-[var(--color-nav-active)] hover:text-[var(--color-sidebar-text)]"
                )}
              >
                {tab.label}
                {tab.count != null && (
                  <span className="ml-1.5 opacity-70">{tab.count}</span>
                )}
              </button>
            );
          })}
        </div>
      </>
    );
  }

  return (
    <div className="flex items-center gap-1">
      {tabs.map((tab) => {
        const isActive = tab.key === active;
        return (
          <button
            key={tab.key}
            onClick={() => onChange(tab.key)}
            className={clsx(
              "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
              isActive
                ? "border-[var(--color-primary)] text-[var(--color-primary)]"
                : "border-transparent text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
            )}
          >
            {tab.label}
            {tab.count != null && (
              <span
                className={clsx(
                  "ml-2 px-1.5 py-0.5 text-[10px] rounded-full font-bold",
                  isActive
                    ? "bg-[var(--color-primary)] text-white"
                    : "bg-[var(--color-surface-2)] text-[var(--color-text-muted)]"
                )}
              >
                {tab.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
