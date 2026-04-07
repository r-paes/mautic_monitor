"use client";

import { Suspense, useState } from "react";
import { RefreshCw } from "lucide-react";
import { startOfDay } from "date-fns";
import { Topnav } from "@/components/layout/Topnav";
import { Tabs } from "@/components/ui/Tabs";
import { Button } from "@/components/ui/Button";
import { DateRangePicker, type DateRange } from "@/components/ui/DateRangePicker";
import { PageSpinner } from "@/components/ui/Spinner";
import { SendpostCards, AvantCards, DeltaAlertCards } from "@/components/dashboard/gateways/GatewayStatCards";
import { GatewayCredentialsForm } from "@/components/dashboard/gateways/GatewayCredentialsForm";
import { CostCenterManager } from "@/components/dashboard/gateways/CostCenterManager";
import { useGatewayMetrics } from "@/lib/hooks/useMetrics";
import { useTabParam } from "@/lib/hooks/useTabParam";
import { MESSAGES, PAGE_TABS } from "@/lib/constants/ui";

function GatewaysContent() {
  const [activeTab, setTab] = useTabParam("sendpost");
  const [dateRange, setDateRange] = useState<DateRange>({
    start: startOfDay(new Date()),
    end: new Date(),
  });

  const params = {
    start: dateRange.start.toISOString(),
    end: dateRange.end.toISOString(),
  };

  const { data: metrics, isLoading, refetch } = useGatewayMetrics(params);

  const isConfigTab = activeTab === "config";

  const topnavTabs = (
    <Tabs
      tabs={PAGE_TABS.gateways as unknown as { key: string; label: string }[]}
      active={activeTab}
      onChange={setTab}
      variant="topnav"
    />
  );

  const topnavActions = !isConfigTab ? (
    <div className="flex items-center gap-2">
      <DateRangePicker value={dateRange} onChange={setDateRange} />
      <Button
        variant="primary"
        size="md"
        icon={<RefreshCw size={14} />}
        onClick={() => refetch()}
        loading={isLoading}
      >
        <span className="hidden sm:inline">{MESSAGES.buttons.refresh}</span>
      </Button>
    </div>
  ) : null;

  return (
    <>
      <Topnav title="Gateways" tabs={topnavTabs} actions={topnavActions} />

      <div className="px-4 md:px-6 py-5">
        {isConfigTab ? (
          <div className="space-y-5 max-w-xl">
            <GatewayCredentialsForm
              gateway="sendpost"
              title="Sendpost — Credenciais"
              subtitle="Account API Key para coleta de métricas de todas as sub-accounts"
            />
            <GatewayCredentialsForm
              gateway="avant"
              title="Avant SMS — Credenciais"
              subtitle="Token de autenticação e URL da API"
            />
            <CostCenterManager />
          </div>
        ) : isLoading && !metrics ? (
          <PageSpinner />
        ) : (
          <>
            {activeTab === "sendpost" && <SendpostCards params={params} />}
            {activeTab === "avant"    && <AvantCards    metrics={metrics ?? []} />}
            {activeTab === "delta"    && <DeltaAlertCards metrics={metrics ?? []} />}
          </>
        )}
      </div>
    </>
  );
}

export default function GatewaysPage() {
  return (
    <Suspense
      fallback={
        <>
          <Topnav title="Gateways" />
          <div className="px-4 md:px-6 py-5"><PageSpinner /></div>
        </>
      }
    >
      <GatewaysContent />
    </Suspense>
  );
}
