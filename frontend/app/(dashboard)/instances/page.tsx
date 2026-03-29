"use client";

import { Suspense, useState } from "react";
import { Plus } from "lucide-react";
import { Topnav } from "@/components/layout/Topnav";
import { Tabs } from "@/components/ui/Tabs";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { PageSpinner } from "@/components/ui/Spinner";
import { InstancesTable } from "@/components/dashboard/instances/InstancesTable";
import { InstanceFormModal } from "@/components/dashboard/instances/InstanceFormModal";
import { useInstances } from "@/lib/hooks/useInstances";
import { useTabParam } from "@/lib/hooks/useTabParam";
import { MESSAGES, PAGE_TABS } from "@/lib/constants/ui";
import type { Instance } from "@/lib/api/instances";

function InstancesContent() {
  const [activeTab, setTab] = useTabParam("overview");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Instance | null>(null);

  const { data: instances, isLoading } = useInstances();

  const subtitle = instances
    ? `${instances.length} instância${instances.length !== 1 ? "s" : ""} configurada${instances.length !== 1 ? "s" : ""}`
    : undefined;

  const topnavTabs = (
    <Tabs
      tabs={PAGE_TABS.instances as unknown as { key: string; label: string }[]}
      active={activeTab}
      onChange={setTab}
      variant="topnav"
    />
  );

  const topnavActions = (
    <Button
      variant="primary"
      size="md"
      icon={<Plus size={14} />}
      onClick={() => { setEditing(null); setFormOpen(true); }}
    >
      <span className="hidden sm:inline">{MESSAGES.buttons.newInstance}</span>
    </Button>
  );

  return (
    <>
      <Topnav
        title="Instâncias Mautic"
        subtitle={subtitle}
        tabs={topnavTabs}
        actions={topnavActions}
      />

      <div className="px-4 md:px-6 py-5">
        {activeTab === "overview" && (
          isLoading ? (
            <PageSpinner />
          ) : (
            <Card padding="none">
              <div className="px-5 py-4 border-b border-[var(--color-border)]">
                <CardHeader title="Instâncias Configuradas" subtitle={subtitle} />
              </div>
              <InstancesTable
                data={instances ?? []}
                isLoading={isLoading}
                onEdit={(instance) => { setEditing(instance); setFormOpen(true); }}
              />
            </Card>
          )
        )}

        {activeTab === "config" && (
          <div className="py-10 text-center text-sm text-[var(--color-text-muted)]">
            Configurações globais de monitoramento — em breve.
          </div>
        )}

        {activeTab === "history" && (
          <div className="py-10 text-center text-sm text-[var(--color-text-muted)]">
            Histórico de conexões e coletas — em breve.
          </div>
        )}
      </div>

      <InstanceFormModal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        instance={editing}
      />
    </>
  );
}

export default function InstancesPage() {
  return (
    <Suspense
      fallback={
        <>
          <Topnav title="Instâncias Mautic" />
          <div className="px-4 md:px-6 py-5"><PageSpinner /></div>
        </>
      }
    >
      <InstancesContent />
    </Suspense>
  );
}
