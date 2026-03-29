"use client";

import { useState } from "react";
import { Pencil, Trash2, Check, Minus } from "lucide-react";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { MESSAGES } from "@/lib/constants/ui";
import { useDeleteInstance } from "@/lib/hooks/useInstances";
import type { Instance } from "@/lib/api/instances";

interface Props {
  data: Instance[];
  isLoading?: boolean;
  onEdit: (instance: Instance) => void;
}

function StatusIcon({ ok }: { ok: boolean }) {
  if (ok) return <Check size={14} className="text-[var(--color-ok)]" />;
  return <Minus size={14} className="text-[var(--color-text-muted)]" />;
}

export function InstancesTable({ data, isLoading, onEdit }: Props) {
  const [deleting, setDeleting] = useState<Instance | null>(null);
  const { mutate: removeInstance, isPending } = useDeleteInstance();

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
      key: "status",
      header: "Status",
      render: (row: Instance) => (
        <Badge variant={row.active ? "ok" : "neutral"} dot>
          {row.active ? MESSAGES.status.online : "Inativa"}
        </Badge>
      ),
    },
    {
      key: "ssh",
      header: "SSH",
      align: "center" as const,
      render: (row: Instance) => <StatusIcon ok={!!row.ssh_host} />,
    },
    {
      key: "db",
      header: "DB",
      align: "center" as const,
      render: (row: Instance) => <StatusIcon ok={!!row.db_host} />,
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
