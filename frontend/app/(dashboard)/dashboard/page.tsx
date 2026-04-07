"use client";

import { useState } from "react";
import { RefreshCw } from "lucide-react";
import { startOfDay } from "date-fns";
import { Topnav } from "@/components/layout/Topnav";
import { Tabs } from "@/components/ui/Tabs";
import { Button } from "@/components/ui/Button";
import { DateRangePicker, type DateRange } from "@/components/ui/DateRangePicker";
import { GlobalView } from "@/components/dashboard/GlobalView";
import { InstanceView } from "@/components/dashboard/InstanceView";
import { useDashboard } from "@/lib/hooks/useMetrics";
import { useInstances } from "@/lib/hooks/useInstances";
import { PageSpinner } from "@/components/ui/Spinner";
import { MESSAGES } from "@/lib/constants/ui";

const DEFAULT_RANGE: DateRange = {
  start: startOfDay(new Date()),
  end: new Date(),
};

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState("global");
  const [dateRange, setDateRange] = useState<DateRange>(DEFAULT_RANGE);
  const [refreshKey, setRefreshKey] = useState(0);

  const params = {
    start: dateRange.start.toISOString(),
    end: dateRange.end.toISOString(),
  };

  const { data: dashboard, isLoading: loadingDashboard, refetch } = useDashboard(params);
  const { data: instances } = useInstances();

  function handleRefresh() {
    setRefreshKey((k) => k + 1);
    refetch();
  }

  // Monta as tabs dinamicamente: Global + uma por instância
  const tabs = [
    { key: "global", label: "Global" },
    ...(instances ?? []).map((i) => ({ key: i.id, label: i.name })),
  ];

  const activeInstance = instances?.find((i) => i.id === activeTab);

  const topnavActions = (
    <div className="flex items-center gap-2">
      <DateRangePicker value={dateRange} onChange={setDateRange} />
      <Button
        variant="primary"
        size="md"
        icon={<RefreshCw size={14} />}
        onClick={handleRefresh}
        loading={loadingDashboard}
      >
        <span className="hidden sm:inline">{MESSAGES.buttons.refresh}</span>
      </Button>
    </div>
  );

  const topnavTabs = (
    <Tabs
      tabs={tabs}
      active={activeTab}
      onChange={setActiveTab}
      variant="topnav"
    />
  );

  return (
    <>
      <Topnav
        title="Dashboard"
        subtitle={
          dashboard
            ? `Atualizado agora · ${dashboard.instances.length} instância${dashboard.instances.length !== 1 ? "s" : ""} monitorada${dashboard.instances.length !== 1 ? "s" : ""}`
            : undefined
        }
        actions={topnavActions}
        tabs={topnavTabs}
      />

      {/* O layout já compensa var(--topnav-height); só adiciona padding interno */}
      <div className="px-4 md:px-6 py-5">
        {loadingDashboard && !dashboard ? (
          <PageSpinner />
        ) : !dashboard ? (
          <p className="text-sm text-[var(--color-text-muted)]">
            {MESSAGES.emptyStates.dashboard}
          </p>
        ) : activeTab === "global" ? (
          <GlobalView
            key={`global-${refreshKey}`}
            data={dashboard}
            isLoading={loadingDashboard}
          />
        ) : activeInstance ? (
          <InstanceView
            key={`${activeTab}-${refreshKey}`}
            instanceId={activeTab}
            dateRange={dateRange}
          />
        ) : null}
      </div>
    </>
  );
}
