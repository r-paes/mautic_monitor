"use client";

import { Suspense } from "react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Topnav } from "@/components/layout/Topnav";
import { Tabs } from "@/components/ui/Tabs";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Table } from "@/components/ui/Table";
import { PageSpinner } from "@/components/ui/Spinner";
import { useAlerts, useAcknowledgeAlert } from "@/lib/hooks/useAlerts";
import { useTabParam } from "@/lib/hooks/useTabParam";
import { MESSAGES, PAGE_TABS } from "@/lib/constants/ui";
import type { Alert } from "@/lib/api/alerts";

function severityVariant(s: string): "critical" | "warning" {
  return s === "critical" ? "critical" : "warning";
}

function AlertsTable({ acknowledged }: { acknowledged: boolean }) {
  const { data: alerts, isLoading } = useAlerts({ acknowledged, limit: 200 });
  const { mutate: ack, isPending } = useAcknowledgeAlert();

  const columns = [
    {
      key: "time",
      header: "Horário",
      width: "130px",
      render: (row: Alert) => (
        <span className="text-xs text-[var(--color-text-muted)] tabular-nums whitespace-nowrap">
          {format(new Date(row.created_at), "dd/MM HH:mm", { locale: ptBR })}
        </span>
      ),
    },
    {
      key: "severity",
      header: "Severidade",
      render: (row: Alert) => (
        <Badge variant={severityVariant(row.severity)} dot>
          {row.severity === "critical" ? MESSAGES.status.critical : MESSAGES.status.warning}
        </Badge>
      ),
    },
    {
      key: "instance",
      header: "Instância",
      render: (row: Alert) => (
        <Badge variant="info">{row.instance_name ?? row.instance_id}</Badge>
      ),
    },
    {
      key: "type",
      header: "Tipo",
      render: (row: Alert) => (
        <span className="text-xs font-mono text-[var(--color-text-muted)]">{row.type}</span>
      ),
    },
    {
      key: "message",
      header: "Mensagem",
      render: (row: Alert) => (
        <span className="text-sm text-[var(--color-text)]">{row.message}</span>
      ),
    },
    ...(!acknowledged
      ? [{
          key: "ack",
          header: "",
          align: "right" as const,
          render: (row: Alert) => (
            <Button
              variant="ghost"
              size="sm"
              loading={isPending}
              onClick={() => ack(row.id)}
            >
              {MESSAGES.buttons.acknowledge}
            </Button>
          ),
        }]
      : [{
          key: "acked_at",
          header: "Reconhecido em",
          align: "right" as const,
          render: (row: Alert) => (
            <span className="text-xs text-[var(--color-text-muted)] tabular-nums">
              {row.acknowledged_at
                ? format(new Date(row.acknowledged_at), "dd/MM HH:mm", { locale: ptBR })
                : "—"}
            </span>
          ),
        }]
    ),
  ];

  if (isLoading) return <PageSpinner />;

  return (
    <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] overflow-hidden">
      <Table
        columns={columns}
        data={alerts ?? []}
        keyExtractor={(row) => row.id}
        emptyMessage={acknowledged ? MESSAGES.emptyStates.alertsHistory : MESSAGES.emptyStates.alerts}
      />
    </div>
  );
}

function AlertsContent() {
  const [activeTab, setTab] = useTabParam("active");

  const { data: activeAlerts } = useAlerts({ acknowledged: false });
  const criticalCount = activeAlerts?.filter((a) => a.severity === "critical").length ?? 0;

  const tabs = PAGE_TABS.alerts.map((t) =>
    t.key === "active" && (activeAlerts?.length ?? 0) > 0
      ? { ...t, count: activeAlerts!.length }
      : t
  );

  const topnavTabs = (
    <Tabs
      tabs={tabs as unknown as { key: string; label: string; count?: number }[]}
      active={activeTab}
      onChange={setTab}
      variant="topnav"
    />
  );

  return (
    <>
      <Topnav
        title="Alertas"
        subtitle={criticalCount > 0 ? `${criticalCount} alerta${criticalCount > 1 ? "s" : ""} crítico${criticalCount > 1 ? "s" : ""}` : undefined}
        tabs={topnavTabs}
      />

      <div className="px-4 md:px-6 py-5 space-y-4">
        {activeTab === "active" && (
          <Card padding="none">
            <div className="px-5 py-4 border-b border-[var(--color-border)]">
              <CardHeader title="Alertas Ativos" subtitle="Alertas não reconhecidos" />
            </div>
            <AlertsTable acknowledged={false} />
          </Card>
        )}

        {activeTab === "history" && (
          <Card padding="none">
            <div className="px-5 py-4 border-b border-[var(--color-border)]">
              <CardHeader title="Histórico de Alertas" subtitle="Alertas já reconhecidos" />
            </div>
            <AlertsTable acknowledged={true} />
          </Card>
        )}

        {activeTab === "rules" && (
          <div className="py-10 text-center text-sm text-[var(--color-text-muted)]">
            Configuração de regras de alerta — em breve.
          </div>
        )}
      </div>
    </>
  );
}

export default function AlertsPage() {
  return (
    <Suspense fallback={<><Topnav title="Alertas" /><div className="px-4 md:px-6 py-5"><PageSpinner /></div></>}>
      <AlertsContent />
    </Suspense>
  );
}
