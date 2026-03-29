"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clsx } from "clsx";
import {
  LayoutDashboard,
  Server,
  Radio,
  Monitor,
  Bell,
  BellRing,
  FileText,
  CalendarClock,
  Users,
  Settings,
  LogOut,
  X,
} from "lucide-react";
import { APP_LOGO_PATH, APP_NAME } from "@/lib/constants/app";
import { NAV_LABELS } from "@/lib/constants/ui";
import { useAuth } from "@/lib/hooks/useAuth";
import { useSidebar } from "@/lib/hooks/useSidebar";

const NAV_MONITORING = [
  { href: "/dashboard",  label: NAV_LABELS.dashboard,  Icon: LayoutDashboard },
  { href: "/instances",  label: NAV_LABELS.instances,  Icon: Server },
  { href: "/gateways",   label: NAV_LABELS.gateways,   Icon: Radio },
  { href: "/vps",        label: NAV_LABELS.vps,        Icon: Monitor },
];

const NAV_ALERTS = [
  { href: "/alerts",         label: NAV_LABELS.alerts,         Icon: Bell },
  { href: "/notifications",  label: NAV_LABELS.notifications,  Icon: BellRing },
];

const NAV_REPORTS = [
  { href: "/reports",                label: NAV_LABELS.reports_recentes,     Icon: FileText },
  { href: "/reports/agendamentos",   label: NAV_LABELS.reports_agendamentos, Icon: CalendarClock },
];

const NAV_SYSTEM = [
  { href: "/users",    label: NAV_LABELS.users,    Icon: Users },
  { href: "/settings", label: NAV_LABELS.settings, Icon: Settings },
];

function NavItem({
  href,
  label,
  Icon,
  onClick,
}: {
  href: string;
  label: string;
  Icon: React.ElementType;
  onClick?: () => void;
}) {
  const pathname = usePathname();
  const active = pathname === href || pathname.startsWith(href + "/");

  return (
    <Link
      href={href}
      onClick={onClick}
      className={clsx(
        "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
        active
          ? "bg-[var(--color-nav-active)] text-[var(--color-sidebar-text)]"
          : "text-[var(--color-sidebar-muted)] hover:bg-[var(--color-nav-active)] hover:text-[var(--color-sidebar-text)]"
      )}
    >
      <Icon size={16} strokeWidth={1.75} className="shrink-0" />
      <span className="flex-1 truncate">{label}</span>
    </Link>
  );
}

function SectionLabel({ label }: { label: string }) {
  return (
    <p className="px-3 mb-2 text-[10px] font-semibold tracking-widest uppercase text-[var(--color-sidebar-muted)]">
      {label}
    </p>
  );
}

export function Sidebar() {
  const { user, logout } = useAuth();
  const { open, close } = useSidebar();

  const initials = user?.name
    ? user.name.split(" ").map((n: string) => n[0]).join("").slice(0, 2).toUpperCase()
    : "??";

  return (
    <>
      {/* Overlay mobile */}
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/50 md:hidden"
          onClick={close}
        />
      )}

      {/* Sidebar */}
      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-40 flex flex-col transition-transform duration-300",
          open ? "translate-x-0" : "-translate-x-full",
          "md:translate-x-0"
        )}
        style={{
          width: "var(--sidebar-width)",
          background: "var(--color-sidebar-bg)",
          borderRight: "1px solid var(--color-nav-border)",
        }}
      >
        {/* Logo + fechar (mobile) */}
        <div className="flex items-center justify-between px-4 py-4 border-b border-[var(--color-nav-border)]">
          <img
            src={APP_LOGO_PATH}
            alt={APP_NAME}
            className="h-8 w-auto object-contain"
          />
          <button
            onClick={close}
            className="md:hidden p-1 rounded-md text-[var(--color-sidebar-muted)] hover:text-[var(--color-sidebar-text)]"
          >
            <X size={18} />
          </button>
        </div>

        {/* Nav principal */}
        <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-4">
          {/* ALERTAS E NOTIFICAÇÕES — primeira seção */}
          <div className="space-y-0.5">
            <SectionLabel label={NAV_LABELS.alerts_section} />
            {NAV_ALERTS.map(({ href, label, Icon }) => (
              <NavItem key={href} href={href} label={label} Icon={Icon} onClick={close} />
            ))}
          </div>

          {/* MONITORAMENTO */}
          <div className="space-y-0.5">
            <SectionLabel label={NAV_LABELS.monitoring} />
            {NAV_MONITORING.map(({ href, label, Icon }) => (
              <NavItem key={href} href={href} label={label} Icon={Icon} onClick={close} />
            ))}
          </div>

          {/* RELATÓRIOS */}
          <div className="space-y-0.5">
            <SectionLabel label={NAV_LABELS.reports_section} />
            {NAV_REPORTS.map(({ href, label, Icon }) => (
              <NavItem key={href} href={href} label={label} Icon={Icon} onClick={close} />
            ))}
          </div>
        </nav>

        {/* Nav sistema */}
        <div className="px-3 pb-2 border-t border-[var(--color-nav-border)] pt-3 space-y-0.5">
          <SectionLabel label={NAV_LABELS.system} />
          {NAV_SYSTEM.map(({ href, label, Icon }) => (
            <NavItem key={href} href={href} label={label} Icon={Icon} onClick={close} />
          ))}
          <button
            onClick={() => { close(); logout(); }}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium text-[var(--color-critical)] hover:bg-[var(--color-nav-active)] transition-colors"
          >
            <LogOut size={16} strokeWidth={1.75} />
            {NAV_LABELS.logout}
          </button>
        </div>

        {/* Avatar */}
        <div className="px-3 py-3 border-t border-[var(--color-nav-border)] flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-[var(--color-primary)] flex items-center justify-center text-white text-xs font-bold shrink-0">
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-medium text-[var(--color-sidebar-text)] truncate">
              {user?.name ?? "—"}
            </p>
            <p className="text-[10px] text-[var(--color-sidebar-muted)] truncate">
              {user?.email ?? "—"}
            </p>
          </div>
        </div>
      </aside>
    </>
  );
}
