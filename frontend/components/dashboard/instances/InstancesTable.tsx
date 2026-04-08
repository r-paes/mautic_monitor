"use client";

import { useState } from "react";
import { Pencil, Trash2, Minus, Server } from "lucide-react";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { MESSAGES } from "@/lib/constants/ui";
import { useDeleteInstance } from "@/lib/hooks/useInstances";
import { useServiceStatus } from "@/lib/hooks/useVps";
import type { Instance, InstanceService } from "@/lib/api/instances";
import type { ServiceStatusEntry } from "@/lib/api/vps";

interface Props {
  data: Instance[];
  isLoading?: boolean;
  onEdit: (instance: Instance) => void;
}

type ContainerStatusVariant = "ok" | "critical" | "warning" | "neutral";

function containerStatusVariant(status?: string): ContainerStatusVariant {
  switch (status) {
    case "running":    return "ok";
    case "stopped":
    case "error":      return "critical";
    case "restarting": return "warning";
    default:           return "neutral";
  }
}

function containerStatusLabel(status?: string): string {
  switch (status) {
    case "running":    return "OK";
    case "stopped":    return "Parado";
    case "error":      return "Erro";
    case "restarting": return "Reiniciando";
    default:           return "—";
  }
}

function ServiceCell({
  serviceType,
  services,
  serviceStatuses,
  instanceId,
}: {
  serviceType: "web" | "database" | "crons";
  services: InstanceService[];
  serviceStatuses: ServiceStatusEntry[];
  instanceId: string;
}) {
  const svc = services.find((s) => s.service_type === serviceType);
  if (!svc) {
    return <Minus size={14} className="text-[var(--color-text-muted)]" />;
  }

  // Busca status mais recente deste container para esta instância
  const status = serviceStatuses.find(
    (ss) => ss.instance_id === instanceId && ss.container_name === svc.container_name
  );

  const variant = containerStatusVariant(status?.status);
  const label = containerStatusLabel(status?.status);

  return (
    <Badge variant={variant} dot>
      {label}
    </Badge>
  );
}

export function InstancesTable({ data, isLoading, onEdit }: Props) {
  const [deleting, setDeleting] = useState<Instance | null>(null);
  const { mutate: removeInstance, isPending } = useDeleteInstance();
  const { data: serviceStatuses } = useServiceStatus();

  function handleConfirmDelete() {
    if (!deleting) return;
    removeInstance(deleting.id, { onSuccess: () => setDeleting(null) });
  }

  const columns = [
    {
      key: "name",
      header: "Nome",
      render: (row: Instance) => (
        <span className="font-semibold text-[var(--color-text)]">{row.name}</span>
      ),
    },
    {
      key: "url",
      header: "URL",
      render: (row: Instance) => (
        <span className="text-xs text-[var(--color-text-muted)]">{row.url}</span>
      ),
    },
    {
      key: "vps",
      header: "VPS",
      render: (row: Instance) =>
        row.vps_name ? (
          <Badge variant="info">
            <Server size={10} className="mr-1" />
            {row.vps_name}
          </Badge>
        ) : (
          <Minus size={14} className="text-[var(--color-text-muted)]" />
        ),
    },
    {
      key: "web",
      header: "Web",
      align: "center" as const,
      render: (row: Instance) => (
        <ServiceCell
          serviceType="web"
          services={row.services ?? []}
          serviceStatuses={serviceStatuses ?? []}
          instanceId={row.id}
        />
      ),
    },
    {
      key: "db",
      header: "DB",
      align: "center" as const,
      render: (row: Instance) => (
        <ServiceCell
          serviceType="database"
          services={row.services ?? []}
          serviceStatuses={serviceStatuses ?? []}
          instanceId={row.id}
        />
      ),
    },
    {
      key: "crons",
      header: "Crons",
      align: "center" as const,
      render: (row: Instance) => (
        <ServiceCell
          serviceType="crons"
          services={row.services ?? []}
          serviceStatuses={serviceStatuses ?? []}
          instanceId={row.id}
        />
      ),
    },
    {
      key: "actions",
      header: "Ações",
      align: "right" as const,
      render: (row: Instance) => (
        <div className="flex items-center justify-end gap-1">
          <Button
            variant="ghost"
            size="sm"
            icon={<Pencil size={13} />}
            onClick={() => onEdit(row)}
          >
            <span className="hidden sm:inline">{MESSAGES.buttons.edit}</span>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            icon={<Trash2 size={13} />}
            onClick={() => setDeleting(row)}
            className="text-[var(--color-critical)] hover:text-[var(--color-critical)]"
          >
            <span className="hidden sm:inline">{MESSAGES.buttons.delete}</span>
          </Button>
        </div>
      ),
    },
  ];

  if (isLoading) {
    return (
      <div className="py-10 text-center text-sm text-[var(--color-text-muted)]">
        Carregando instâncias...
      </div>
    );
  }

  return (
    <>
      <Table
        columns={columns}
        data={data}
        keyExtractor={(row) => row.id}
        emptyMessage={MESSAGES.emptyStates.instances}
      />

      <Modal
        open={!!deleting}
        onClose={() => setDeleting(null)}
        title="Remover instância"
        size="sm"
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setDeleting(null)}>
              {MESSAGES.buttons.cancel}
            </Button>
            <Button
              variant="danger"
              size="sm"
              loading={isPending}
              onClick={handleConfirmDelete}
            >
              {MESSAGES.buttons.delete}
            </Button>
          </>
        }
      >
        <p className="text-sm text-[var(--color-text)]">
          {MESSAGES.confirmations.deleteInstance}
        </p>
        {deleting && (
          <p className="mt-2 text-xs text-[var(--color-text-muted)]">
            Instância: <strong className="text-[var(--color-text)]">{deleting.name}</strong>
          </p>
        )}
      </Modal>
    </>
  );
}
