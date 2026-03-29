"use client";

import { useState } from "react";
import { Download, RefreshCw, Eye } from "lucide-react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Table } from "@/components/ui/Table";
import { Badge, statusVariant } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { MESSAGES } from "@/lib/constants/ui";
import { useReportHistory, useGenerateReport } from "@/lib/hooks/useReports";
import { reportsApi } from "@/lib/api/reports";
import type { ReportHistory, ReportConfig } from "@/lib/api/reports";

function fmt(d: string) {
  return format(new Date(d), "dd/MM/yy HH:mm", { locale: ptBR });
}

function fmtPeriod(start: string, end: string) {
  return `${format(new Date(start), "dd/MM/yy")} — ${format(new Date(end), "dd/MM/yy")}`;
}

interface Props {
  configs: ReportConfig[];
  instanceNames: Record<string, string>;
}

export function ReportHistoryTable({ configs, instanceNames }: Props) {
  const [generating, setGenerating] = useState<string | null>(null);
  const [preview, setPreview] = useState<ReportHistory | null>(null);

  const { data: history, isLoading } = useReportHistory({ limit: 100 });
  const { mutate: generate, isPending } = useGenerateReport();

  const configMap = Object.fromEntries(configs.map((c) => [c.id, c]));

  function handleGenerate(configId: string) {
    setGenerating(configId);
    generate(
      { configId },
      { onSettled: () => setGenerating(null) }
    );
  }

  const columns = [
    {
      key: "generated_at",
      header: "Gerado em",
      width: "130px",
      render: (row: ReportHistory) => (
        <span className="text-xs text-[var(--color-text-muted)] tabular-nums whitespace-nowrap">
          {fmt(row.generated_at)}
        </span>
      ),
    },
    {
      key: "company",
      header: "Empresa",
      render: (row: ReportHistory) => {
        const cfg = configMap[row.report_config_id];
        return (
          <span className="text-sm font-medium text-[var(--color-text)]">
            {cfg?.company_name ?? "—"}
          </span>
        );
      },
    },
    {
      key: "instance",
      header: "Instância",
      render: (row: ReportHistory) => (
        <Badge variant="info">
          {row.instance_id ? (instanceNames[row.instance_id] ?? row.instance_id) : "—"}
        </Badge>
      ),
    },
    {
      key: "period",
      header: "Período",
      render: (row: ReportHistory) => (
        <span className="text-xs text-[var(--color-text-muted)] whitespace-nowrap">
          {fmtPeriod(row.period_start, row.period_end)}
        </span>
      ),
    },
    {
      key: "trigger",
      header: "Origem",
      render: (row: ReportHistory) => (
        <Badge variant={row.trigger === "manual" ? "info" : "neutral"}>
          {MESSAGES.status[row.trigger as keyof typeof MESSAGES.status] ?? row.trigger}
        </Badge>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (row: ReportHistory) => (
        <Badge variant={statusVariant(row.status)} dot>
          {MESSAGES.status[row.status as keyof typeof MESSAGES.status] ?? row.status}
        </Badge>
      ),
    },
    {
      key: "sent",
      header: "Enviado",
      align: "center" as const,
      render: (row: ReportHistory) => (
        <span className="text-xs">
          {row.sent_email && <span className="text-[var(--color-ok)]">Email</span>}
          {row.sent_email && row.sent_sms && " · "}
          {row.sent_sms && <span className="text-[var(--color-ok)]">SMS</span>}
          {!row.sent_email && !row.sent_sms && (
            <span className="text-[var(--color-text-muted)]">—</span>
          )}
        </span>
      ),
    },
    {
      key: "actions",
      header: "",
      align: "right" as const,
      render: (row: ReportHistory) => (
        <div className="flex items-center justify-end gap-1">
          {row.status === "success" && (
            <>
              <Button
                variant="ghost"
                size="sm"
                icon={<Eye size={13} />}
                onClick={() => setPreview(row)}
              />
              <a
                href={reportsApi.downloadUrl(row.id)}
                target="_blank"
                rel="noreferrer"
              >
                <Button variant="ghost" size="sm" icon={<Download size={13} />} />
              </a>
            </>
          )}
          <Button
            variant="ghost"
            size="sm"
            icon={<RefreshCw size={13} />}
            loading={isPending && generating === row.report_config_id}
            onClick={() => handleGenerate(row.report_config_id)}
          />
        </div>
      ),
    },
  ];

  return (
    <>
      {isLoading ? (
        <p className="py-8 text-center text-sm text-[var(--color-text-muted)]">
          Carregando histórico...
        </p>
      ) : (
        <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] overflow-hidden">
          <Table
            columns={columns}
            data={history ?? []}
            keyExtractor={(row) => row.id}
            emptyMessage={MESSAGES.emptyStates.reports}
          />
        </div>
      )}

      {/* Modal preview */}
      <Modal
        open={!!preview}
        onClose={() => setPreview(null)}
        title="Visualizar Relatório"
        size="lg"
      >
        {preview?.file_url ? (
          <iframe
            src={reportsApi.downloadUrl(preview.id)}
            className="w-full h-[60vh] rounded border border-[var(--color-border)]"
            title="Relatório"
          />
        ) : (
          <p className="text-sm text-[var(--color-text-muted)]">
            Arquivo não disponível.
          </p>
        )}
      </Modal>
    </>
  );
}
