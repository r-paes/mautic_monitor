"use client";

import { Users, Mail, MessageSquare, Zap, Target, GitBranch, Package } from "lucide-react";
import { StatCard } from "@/components/ui/Card";
import { PageSpinner } from "@/components/ui/Spinner";
import { AlertsPanel } from "@/components/dashboard/AlertsPanel";
import { VolumeChart } from "@/components/dashboard/VolumeChart";
import { useInstanceMetrics } from "@/lib/hooks/useMetrics";
import type { DateRange } from "@/components/ui/DateRangePicker";


function fmt(n: number | null | undefined) {
  if (n == null) return "—";
  return n.toLocaleString("pt-BR");
}

interface Props {
  instanceId: string;
  dateRange: DateRange;
}

export function InstanceView({ instanceId, dateRange }: Props) {
  const { data, isLoading } = useInstanceMetrics(instanceId, {
    start: dateRange.start.toISOString(),
    end: dateRange.end.toISOString(),
  });

  if (isLoading) return <PageSpinner />;
  if (!data) return (
    <p className="text-sm text-[var(--color-text-muted)]">
      Dados indisponíveis para esta instância.
    </p>
  );

  return (
    <div className="space-y-6">
      {/* ── Cards principais da instância ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          label="Contatos 24h"
          value={fmt(data.contacts_24h)}
          icon={<Users size={18} />}
        />
        <StatCard
          label="Emails Enviados"
          value={fmt(data.emails_sent_mautic)}
          delta={
            data.emails_sent_gateway != null
              ? `Gateway: ${fmt(data.emails_sent_gateway)}`
              : undefined
          }
          deltaOk
          icon={<Mail size={18} />}
        />
        <StatCard
          label="SMS Enviados"
          value={fmt(data.sms_sent_mautic)}
          delta={
            data.sms_sent_gateway != null
              ? `Gateway: ${fmt(data.sms_sent_gateway)}`
              : undefined
          }
          deltaOk
          icon={<MessageSquare size={18} />}
        />
        <StatCard
          label="Campanhas Ativas"
          value={fmt(data.active_campaigns)}
          icon={<Zap size={18} />}
        />
      </div>

      {/* ── Cards adicionais (anotações do dashboard) ── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          label="Eventos de Campanha"
          value="—"
          icon={<Target size={18} />}
        />
        <StatCard
          label="Segmentos Atualizados"
          value="—"
          icon={<GitBranch size={18} />}
        />
        <StatCard
          label="Depósitos Recebidos"
          value="—"
          icon={<Package size={18} />}
        />
        <StatCard
          label="Logins / Saques"
          value="—"
          icon={<Package size={18} />}
        />
      </div>

      {/* ── Alertas + Gráfico filtrado pela instância ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <AlertsPanel />
        <VolumeChart instanceId={instanceId} />
      </div>
    </div>
  );
}
