"use client";

import { useState } from "react";
import { Pencil, Trash2, Play } from "lucide-react";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { MESSAGES } from "@/lib/constants/ui";
import { useDeleteReportConfig, useGenerateReport } from "@/lib/hooks/useReports";
import type { ReportConfig } from "@/lib/api/reports";

interface Props {
  configs: ReportConfig[];
  instanceNames: Record<string, string>;
  onEdit: (config: ReportConfig) => void;
}

export function ReportConfigsTable({ configs, instanceNames, onEdit }: Props) {
  const [deleting, setDeleting] = useState<ReportConfig | null>(null);
  const [generating, setGenerating] = useState<string | null>(null);

  const { mutate: remove, isPending: removing } = useDeleteReportConfig();
  const { mutate: generate, isPending: generating_ } = useGenerateReport();

  function handleGenerate(config: ReportConfig) {
    setGenerating(config.id);
    generate({ configId: config.id }, { onSettled: () => setGenerating(null) });
  }

  const columns = [
    {
      key: "company",
      header: "Empresa",
      render: (row: ReportConfig) => (
        <span className="font-semibold text-[var(--color-text)]">{row.company_name}</span>
      ),
    },
    {
      key: "instance",
      header: "Instância",
      render: (row: ReportConfig) => (
        <Badge variant="info">
          {instanceNames[row.instance_id] ?? row.instance_id}
        </Badge>
      ),
    },
    {
      key: "email",
      header: "Email",
      render: (row: ReportConfig) => (
        <span className="text-xs text-[var(--color-text-muted)]">{row.report_email}</span>
      ),
    },
    {
      key: "channels",
      header: "Canais",
      render: (row: ReportConfig) => (
        <div className="flex gap-1">
          {row.send_email && <Badge variant="neutral">Email</Badge>}
          {row.send_sms && <Badge variant="neutral">SMS</Badge>}
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (row: ReportConfig) => (
        <Badge variant={row.active ? "ok" : "neutral"} dot>
          {row.active ? "Ativa" : "Inativa"}
        </Badge>
      ),
    },
    {
      key: "actions",
      header: "",
      align: "right" as const,
      render: (row: ReportConfig) => (
        <div className="flex items-center justify-end gap-1">
          <Button
            variant="ghost"
            size="sm"
            icon={<Play size={13} />}
            loading={generating_ && generating === row.id}
            onClick={() => handleGenerate(row)}
            title={MESSAGES.buttons.generate}
          />
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

  return (
    <>
      <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] overflow-hidden">
        <Table
          columns={columns}
          data={configs}
          keyExtractor={(row) => row.id}
          emptyMessage={MESSAGES.emptyStates.reportConfigs}
        />
      </div>

      <Modal
        open={!!deleting}
        onClose={() => setDeleting(null)}
        title="Remover configuração"
        size="sm"
        footer={
          <>
            <Button variant="ghost" size="sm" onClick={() => setDeleting(null)}>
              {MESSAGES.buttons.cancel}
            </Button>
            <Button
              variant="danger"
              size="sm"
              loading={removing}
              onClick={() => deleting && remove(deleting.id, { onSuccess: () => setDeleting(null) })}
            >
              {MESSAGES.buttons.delete}
            </Button>
          </>
        }
      >
        <p className="text-sm text-[var(--color-text)]">
          {MESSAGES.confirmations.deleteReportConfig}
        </p>
        {deleting && (
          <p className="mt-2 text-xs text-[var(--color-text-muted)]">
            Empresa: <strong className="text-[var(--color-text)]">{deleting.company_name}</strong>
          </p>
        )}
      </Modal>
    </>
  );
}
