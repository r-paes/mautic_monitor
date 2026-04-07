"use client";

import { useState } from "react";
import { Cpu, MemoryStick, HardDrive, Pencil, Trash2, Terminal } from "lucide-react";
import { Card, StatCard } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ConfirmModal } from "@/components/ui/ConfirmModal";
import { MESSAGES } from "@/lib/constants/ui";
import { useDeleteInstance } from "@/lib/hooks/useInstances";
import { VpsFormModal } from "./VpsFormModal";
import type { VpsMetric } from "@/lib/api/vps";
import type { Instance } from "@/lib/api/instances";

function fmt(n: number | null | undefined, unit = "") {
  if (n == null) return "—";
  return `${n.toFixed(1)}${unit}`;
}

function usageVariant(pct: number | null): "ok" | "warning" | "critical" {
  if (pct == null) return "ok";
  if (pct >= 90) return "critical";
  if (pct >= 75) return "warning";
  return "ok";
}

function UsageBar({ pct }: { pct: number | null }) {
  const value = pct ?? 0;
  const variant = usageVariant(pct);
  const color =
    variant === "critical"
      ? "var(--color-critical)"
      : variant === "warning"
      ? "var(--color-warning)"
      : "var(--color-ok)";

  return (
    <div className="mt-2">
      <div className="flex justify-between items-center mb-1">
        <span className="text-[10px] text-[var(--color-text-muted)]">Uso</span>
        <span className="text-[10px] font-semibold" style={{ color }}>
          {pct != null ? `${value.toFixed(0)}%` : "—"}
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-[var(--color-surface-2)] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${Math.min(value, 100)}%`, background: color }}
        />
      </div>
    </div>
  );
}

interface VpsCardProps {
  metric: VpsMetric | null;
  instance: Instance;
  onEdit: (i: Instance) => void;
  onDelete: (i: Instance) => void;
}

function VpsCard({ metric, instance, onEdit, onDelete }: VpsCardProps) {
  const overallStatus =
    metric == null
      ? "warning"
      : usageVariant(metric.cpu_percent) === "critical" ||
        usageVariant(metric.memory_percent) === "critical" ||
        usageVariant(metric.disk_percent) === "critical"
      ? "critical"
      : usageVariant(metric.cpu_percent) === "warning" ||
        usageVariant(metric.memory_percent) === "warning" ||
        usageVariant(metric.disk_percent) === "warning"
      ? "warning"
      : "ok";

  const statusLabel =
    metric == null ? "Sem dados" : MESSAGES.status[overallStatus];

  return (
    <Card padding="none" className="overflow-hidden">
      {/* Header */}
      <div className="px-5 pt-4 pb-3 border-b border-[var(--color-border)]">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="text-sm font-semibold text-[var(--color-text)] truncate">
                {instance.name}
              </p>
              {instance.ssh_host ? (
                <Badge variant="info">
                  <Terminal size={10} className="mr-1" />
                  SSH
                </Badge>
              ) : (
                <Badge variant="warning">Sem SSH</Badge>
              )}
            </div>
            {instance.ssh_host && (
              <p className="text-[11px] text-[var(--color-text-muted)] mt-0.5 font-mono">
                {instance.ssh_user ?? "root"}@{instance.ssh_host}:{instance.ssh_port ?? 22}
                {metric && ` · load: ${fmt(metric.load_avg_1m)}`}
              </p>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <Badge variant={overallStatus} dot>{statusLabel}</Badge>
            <button
              onClick={() => onEdit(instance)}
              className="p-1 rounded text-[var(--color-text-muted)] hover:text-[var(--color-primary)] hover:bg-[var(--color-nav-active)] transition-colors"
              title="Editar VPS"
            >
              <Pencil size={13} />
            </button>
            <button
              onClick={() => onDelete(instance)}
              className="p-1 rounded text-[var(--color-text-muted)] hover:text-[var(--color-critical)] hover:bg-[var(--color-nav-active)] transition-colors"
              title="Remover VPS"
            >
              <Trash2 size={13} />
            </button>
          </div>
        </div>
      </div>

      {/* Métricas ou empty state */}
      {metric ? (
        <div className="grid grid-cols-1 sm:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x divide-[var(--color-border)]">
          {/* CPU */}
          <div className="px-5 py-4">
            <div className="flex items-center gap-2 mb-1">
              <Cpu size={14} className="text-[var(--color-primary)] shrink-0" />
              <span className="text-xs font-medium text-[var(--color-text-muted)]">CPU</span>
            </div>
            <p className="text-xl font-bold text-[var(--color-text)] tabular-nums">
              {fmt(metric.cpu_percent, "%")}
            </p>
            <UsageBar pct={metric.cpu_percent} />
          </div>

          {/* Memória */}
          <div className="px-5 py-4">
            <div className="flex items-center gap-2 mb-1">
              <MemoryStick size={14} className="text-[var(--color-primary)] shrink-0" />
              <span className="text-xs font-medium text-[var(--color-text-muted)]">Memória</span>
            </div>
            <p className="text-xl font-bold text-[var(--color-text)] tabular-nums">
              {fmt(metric.memory_percent, "%")}
            </p>
            <p className="text-[10px] text-[var(--color-text-muted)] mt-0.5">
              {metric.memory_used_mb != null && metric.memory_total_mb != null
                ? `${(metric.memory_used_mb / 1024).toFixed(1)} / ${(metric.memory_total_mb / 1024).toFixed(1)} GB`
                : "—"}
            </p>
            <UsageBar pct={metric.memory_percent} />
          </div>

          {/* Disco */}
          <div className="px-5 py-4">
            <div className="flex items-center gap-2 mb-1">
              <HardDrive size={14} className="text-[var(--color-primary)] shrink-0" />
              <span className="text-xs font-medium text-[var(--color-text-muted)]">Disco</span>
            </div>
            <p className="text-xl font-bold text-[var(--color-text)] tabular-nums">
              {fmt(metric.disk_percent, "%")}
            </p>
            <p className="text-[10px] text-[var(--color-text-muted)] mt-0.5">
              {metric.disk_used_gb != null && metric.disk_total_gb != null
                ? `${metric.disk_used_gb.toFixed(0)} / ${metric.disk_total_gb.toFixed(0)} GB`
                : "—"}
            </p>
            <UsageBar pct={metric.disk_percent} />
          </div>
        </div>
      ) : (
        <div className="px-5 py-6 text-sm text-[var(--color-text-muted)]">
          {instance.ssh_host
            ? "Aguardando primeira coleta via SSH..."
            : "Configure o acesso SSH para monitorar esta VPS."}
        </div>
      )}
    </Card>
  );
}

interface Props {
  metrics: VpsMetric[];
  instances: Instance[];
}

export function VpsResourceCards({ metrics, instances }: Props) {
  const [editTarget, setEditTarget] = useState<Instance | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Instance | null>(null);
  const { mutate: remove, isPending: deleting } = useDeleteInstance();

  // Índice métrica mais recente por instance_id
  const metricByInstance = metrics.reduce<Record<string, VpsMetric>>((acc, m) => {
    if (!acc[m.instance_id]) acc[m.instance_id] = m;
    return acc;
  }, {});

  if (!instances.length) {
    return (
      <p className="py-10 text-center text-sm text-[var(--color-text-muted)]">
        {MESSAGES.emptyStates.vps}
      </p>
    );
  }

  const metricsWithData = metrics.filter((m) => m.cpu_percent != null);
  const totals = metricsWithData.reduce(
    (acc, m) => ({
      cpu: acc.cpu + (m.cpu_percent ?? 0),
      mem: acc.mem + (m.memory_percent ?? 0),
      disk: acc.disk + (m.disk_percent ?? 0),
      count: acc.count + 1,
    }),
    { cpu: 0, mem: 0, disk: 0, count: 0 }
  );
  const avg = (v: number) =>
    totals.count ? (v / totals.count).toFixed(1) + "%" : "—";

  return (
    <div className="space-y-6">
      {/* Resumo global */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard label="CPU Médio"    value={avg(totals.cpu)}  icon={<Cpu size={18} />} />
        <StatCard label="Memória Média" value={avg(totals.mem)}  icon={<MemoryStick size={18} />} />
        <StatCard label="Disco Médio"  value={avg(totals.disk)} icon={<HardDrive size={18} />} />
      </div>

      {/* Cards por VPS */}
      <div className="space-y-4">
        {instances.map((inst) => (
          <VpsCard
            key={inst.id}
            instance={inst}
            metric={metricByInstance[inst.id] ?? null}
            onEdit={setEditTarget}
            onDelete={setDeleteTarget}
          />
        ))}
      </div>

      <VpsFormModal
        open={!!editTarget}
        onClose={() => setEditTarget(null)}
        vps={editTarget}
      />

      <ConfirmModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => {
          if (deleteTarget) {
            remove(deleteTarget.id, { onSuccess: () => setDeleteTarget(null) });
          }
        }}
        title="Remover VPS"
        description={`Tem certeza que deseja remover "${deleteTarget?.name}"? Todos os dados de monitoramento serão excluídos.`}
        confirmLabel={MESSAGES.buttons.delete}
        confirmVariant="danger"
        loading={deleting}
      />
    </div>
  );
}
