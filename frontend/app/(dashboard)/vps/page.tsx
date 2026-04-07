"use client";

import { Suspense, useState } from "react";
import { RefreshCw, Plus } from "lucide-react";
import { Topnav } from "@/components/layout/Topnav";
import { Tabs } from "@/components/ui/Tabs";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageSpinner } from "@/components/ui/Spinner";
import { VpsResourceCards } from "@/components/dashboard/vps/VpsResourceCards";
import { VpsFormModal } from "@/components/dashboard/vps/VpsFormModal";
import { ContainersTable } from "@/components/dashboard/vps/ContainersTable";
import { LogsTable } from "@/components/dashboard/vps/LogsTable";
import { useVpsMetrics } from "@/lib/hooks/useVps";
import { useInstances } from "@/lib/hooks/useInstances";
import { useDashboard } from "@/lib/hooks/useMetrics";
import { useTabParam } from "@/lib/hooks/useTabParam";
import { MESSAGES, PAGE_TABS } from "@/lib/constants/ui";

function VpsContent() {
  const [activeTab, setTab] = useTabParam("resources");
  const [formOpen, setFormOpen] = useState(false);

  const { data: vpsMetrics, isLoading: loadingVps, refetch } = useVpsMetrics();
  const { data: instances, isLoading: loadingInstances } = useInstances();
  const { data: dashboard, isLoading: loadingDashboard } = useDashboard();

  const isLoading = loadingVps || loadingDashboard || loadingInstances;

  // Mapa instance_id → name para logs e containers
  const instanceNames: Record<string, string> = Object.fromEntries(
    (dashboard?.instances ?? []).map((i) => [i.id, i.name])
  );

  const topnavTabs = (
    <Tabs
      tabs={PAGE_TABS.vps as unknown as { key: string; label: string }[]}
      active={activeTab}
      onChange={setTab}
      variant="topnav"
    />
  );

  const topnavActions = (
    <div className="flex items-center gap-2">
      {activeTab === "resources" && (
        <Button
          variant="primary"
          size="md"
          icon={<Plus size={14} />}
          onClick={() => setFormOpen(true)}
        >
          <span className="hidden sm:inline">Nova VPS</span>
        </Button>
      )}
      <Button
        variant="secondary"
        size="md"
        icon={<RefreshCw size={14} />}
        onClick={() => refetch()}
        loading={isLoading}
      >
        <span className="hidden sm:inline">{MESSAGES.buttons.refresh}</span>
      </Button>
    </div>
  );

  return (
    <>
      <Topnav title="VPS & Logs" tabs={topnavTabs} actions={topnavActions} />

      <div className="px-4 md:px-6 py-5">
        {isLoading && !vpsMetrics ? (
          <PageSpinner />
        ) : (
          <>
            {activeTab === "resources" && (
              <VpsResourceCards
                metrics={vpsMetrics ?? []}
                instances={instances ?? []}
              />
            )}

            {activeTab === "containers" && (
              <Card padding="none">
                <ContainersTable instances={dashboard?.instances ?? []} />
              </Card>
            )}

            {activeTab === "logs" && (
              <LogsTable instanceNames={instanceNames} />
            )}
          </>
        )}
      </div>

      <VpsFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
      />
    </>
  );
}

export default function VpsPage() {
  return (
    <Suspense
      fallback={
        <>
          <Topnav title="VPS & Logs" />
          <div className="px-4 md:px-6 py-5"><PageSpinner /></div>
        </>
      }
    >
      <VpsContent />
    </Suspense>
  );
}
