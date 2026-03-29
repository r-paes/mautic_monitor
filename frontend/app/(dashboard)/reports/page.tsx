"use client";

import { Suspense, useState } from "react";
import { Plus } from "lucide-react";
import { Topnav } from "@/components/layout/Topnav";
import { Tabs } from "@/components/ui/Tabs";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { PageSpinner } from "@/components/ui/Spinner";
import { ReportHistoryTable } from "@/components/dashboard/reports/ReportHistoryTable";
import { ReportConfigsTable } from "@/components/dashboard/reports/ReportConfigsTable";
import { ReportConfigForm } from "@/components/dashboard/reports/ReportConfigForm";
import { useReportConfigs } from "@/lib/hooks/useReports";
import { useInstances } from "@/lib/hooks/useInstances";
import { useDashboard } from "@/lib/hooks/useMetrics";
import { useTabParam } from "@/lib/hooks/useTabParam";
import { MESSAGES, PAGE_TABS } from "@/lib/constants/ui";
import type { ReportConfig } from "@/lib/api/reports";

function ReportsContent() {
  const [activeTab, setTab] = useTabParam("envios");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<ReportConfig | null>(null);

  const { data: configs, isLoading: loadingConfigs } = useReportConfigs();
  const { data: instances } = useInstances();
  const { data: dashboard } = useDashboard();

  const instanceNames: Record<string, string> = Object.fromEntries(
    (dashboard?.instances ?? []).map((i) => [i.id, i.name])
  );

  const topnavTabs = (
    <Tabs
      tabs={PAGE_TABS.reports as unknown as { key: string; label: string }[]}
      active={activeTab}
      onChange={setTab}
      variant="topnav"
    />
  );

  const topnavActions = activeTab === "agendamentos" ? (
    <Button
      variant="primary"
      size="md"
      icon={<Plus size={14} />}
      onClick={() => { setEditing(null); setFormOpen(true); }}
    >
      <span className="hidden sm:inline">Nova Configuração</span>
    </Button>
  ) : null;

  return (
    <>
      <Topnav title="Relatórios" tabs={topnavTabs} actions={topnavActions} />

      <div className="px-4 md:px-6 py-5">
        {/* Envios por Empresa — histórico de relatórios gerados */}
        {activeTab === "envios" && (
          loadingConfigs ? (
            <PageSpinner />
          ) : (
            <div className="space-y-4">
              <Card padding="none">
                <div className="px-5 py-4 border-b border-[var(--color-border)]">
                  <CardHeader
                    title="Histórico de Envios"
                    subtitle="Relatórios gerados por empresa e instância"
                  />
                </div>
                <ReportHistoryTable
                  configs={configs ?? []}
                  instanceNames={instanceNames}
                />
              </Card>
            </div>
          )
        )}

        {/* Agendamentos — configurações de relatório */}
        {activeTab === "agendamentos" && (
          loadingConfigs ? (
            <PageSpinner />
          ) : (
            <Card padding="none">
              <div className="px-5 py-4 border-b border-[var(--color-border)]">
                <CardHeader
                  title="Configurações de Relatório"
                  subtitle={`${configs?.length ?? 0} configuração${(configs?.length ?? 0) !== 1 ? "s" : ""} cadastrada${(configs?.length ?? 0) !== 1 ? "s" : ""}`}
                  actions={
                    <Button
                      variant="primary"
                      size="sm"
                      icon={<Plus size={13} />}
                      onClick={() => { setEditing(null); setFormOpen(true); }}
                    >
                      <span className="hidden sm:inline">Nova Configuração</span>
                    </Button>
                  }
                />
              </div>
              <ReportConfigsTable
                configs={configs ?? []}
                instanceNames={instanceNames}
                onEdit={(c) => { setEditing(c); setFormOpen(true); }}
              />
            </Card>
          )
        )}
      </div>

      <ReportConfigForm
        open={formOpen}
        onClose={() => setFormOpen(false)}
        config={editing}
        instances={instances ?? []}
      />
    </>
  );
}

export default function ReportsPage() {
  return (
    <Suspense
      fallback={
        <>
          <Topnav title="Relatórios" />
          <div className="px-4 md:px-6 py-5"><PageSpinner /></div>
        </>
      }
    >
      <ReportsContent />
    </Suspense>
  );
}
