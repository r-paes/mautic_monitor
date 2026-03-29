"use client";

import { Suspense } from "react";
import { useInstances } from "@/lib/hooks/useInstances";
import { SidebarSubItems } from "@/components/layout/SidebarSubItems";

function DashboardSubItemsInner({ onClick }: { onClick?: () => void }) {
  const { data: instances } = useInstances();

  const subItems = [
    { key: "global", label: "Global" },
    ...(instances ?? []).map((i) => ({ key: i.id, label: i.name })),
  ] as const satisfies readonly { key: string; label: string }[];

  return <SidebarSubItems href="/dashboard" subItems={subItems} onClick={onClick} />;
}

export function DashboardSubItems({ onClick }: { onClick?: () => void }) {
  return (
    <Suspense fallback={
      <div className="mt-0.5 ml-3 pl-3 border-l border-[var(--color-nav-border)] pb-1">
        <div className="h-6 rounded bg-[var(--color-nav-active)] opacity-20 animate-pulse" />
      </div>
    }>
      <DashboardSubItemsInner onClick={onClick} />
    </Suspense>
  );
}
