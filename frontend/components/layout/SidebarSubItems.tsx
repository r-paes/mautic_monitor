"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { clsx } from "clsx";

interface SubTab {
  key: string;
  label: string;
}

interface Props {
  href: string;
  subItems: readonly SubTab[];
  onClick?: () => void;
}

function SubItemsInner({ href, subItems, onClick }: Props) {
  const searchParams = useSearchParams();
  const activeTab = searchParams.get("tab") ?? subItems[0]?.key;

  return (
    <div className="mt-0.5 ml-3 pl-3 border-l border-[var(--color-nav-border)] space-y-0.5 pb-1">
      {subItems.map((tab) => (
        <Link
          key={tab.key}
          href={`${href}?tab=${tab.key}`}
          onClick={onClick}
          className={clsx(
            "flex items-center px-2 py-1.5 rounded-[var(--radius-sm)] text-xs transition-colors",
            tab.key === activeTab
              ? "bg-[var(--color-nav-active)] text-[var(--color-primary)] font-semibold"
              : "text-[var(--color-sidebar-muted)] hover:bg-[var(--color-nav-active)] hover:text-[var(--color-sidebar-text)]"
          )}
        >
          {tab.label}
        </Link>
      ))}
    </div>
  );
}

export function SidebarSubItems({ href, subItems, onClick }: Props) {
  return (
    <Suspense
      fallback={
        <div className="mt-0.5 ml-3 pl-3 border-l border-[var(--color-nav-border)] space-y-0.5 pb-1">
          {subItems.map((tab) => (
            <div
              key={tab.key}
              className="h-7 rounded-[var(--radius-sm)] bg-[var(--color-nav-active)] opacity-20 animate-pulse"
            />
          ))}
        </div>
      }
    >
      <SubItemsInner href={href} subItems={subItems} onClick={onClick} />
    </Suspense>
  );
}
