"use client";

import { Suspense, useState } from "react";
import { RefreshCw } from "lucide-react";
import { startOfDay, format } from "date-fns";
import { Topnav } from "@/components/layout/Topnav";
import { Tabs } from "@/components/ui/Tabs";
import { Button } from "@/components/ui/Button";
import { DateRangePicker, type DateRange } from "@/components/ui/DateRangePicker";
import { PageSpinner } from "@/components/ui/Spinner";
import { SendpostCards, AvantCards, DeltaAlertCards } from "@/components/dashboard/gateways/GatewayStatCards";
import { useGatewayMetrics } from "@/lib/hooks/useMetrics";
import { useTabParam } from "@/lib/hooks/useTabParam";
import { MESSAGES, PAGE_TABS } from "@/lib/constants/ui";

const DEFAULT_RANGE: DateRange = {
  start: startOfDay(new Date()),
  end: new Date(),
};

function GatewaysContent({ dateRange, setDateRange }: { dateRange: DateRange; setDateRange: (r: DateRange) => void }) {
  const [activeTab, setTab] = useTabParam("sendpost");

  const params = {
    start: format(dateRange.start, "yyyy-MM-dd'T'HH:mm:ss"),
    end: format(dateRange.end, "yyyy-MM-dd'T'HH:mm:ss"),
  };

  const { data: metrics, isLoading, refetch } = useGatewayMetrics(params);

  const topnavTabs = (
    <Tabs
      tabs={PAGE_TABS.gateways as unknown as { key: string; label: string }[]}
      active={activeTab}
      onChange={setTab}
      variant="topnav"
    />
  );

  const topnavActions = (
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
  );

  return (
    <>
      <Topnav title="Gateways de Envio" tabs={topnavTabs} actions={topnavActions} />

      <div className="px-4 md:px-6 py-5">
        {isLoading && !metrics ? (
          <PageSpinner />
        ) : (
          <>
            {activeTab === "sendpost" && <SendpostCards metrics={metrics ?? []} />}
            {activeTab === "avant"    && <AvantCards    metrics={metrics ?? []} />}
            {activeTab === "delta"    && <DeltaAlertCards metrics={metrics ?? []} />}
          </>
        )}
      </div>
    </>
  );
}

export default function GatewaysPage() {
  const [dateRange, setDateRange] = useState<DateRange>(DEFAULT_RANGE);

  return (
    <Suspense
      fallback={
        <>
          <Topnav title="Gateways de Envio" />
          <div className="px-4 md:px-6 py-5"><PageSpinner /></div>
        </>
      }
    >
      <GatewaysContent dateRange={dateRange} setDateRange={setDateRange} />
    </Suspense>
  );
}
