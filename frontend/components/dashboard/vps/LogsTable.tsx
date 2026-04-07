"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Table } from "@/components/ui/Table";
import { Select } from "@/components/ui/Select";
import { MESSAGES } from "@/lib/constants/ui";
import { useServiceLogs } from "@/lib/hooks/useVps";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import type { ServiceLog } from "@/lib/api/vps";

const LEVEL_OPTIONS = [
  { value: "",      label: "Todos os níveis" },
  { value: "CRIT",  label: "Crítico" },
  { value: "ERROR", label: "Erro" },
  { value: "WARN",  label: "Atenção" },
  { value: "INFO",  label: "Info" },
];

function logLevelVariant(level: string): "critical" | "warning" | "info" | "neutral" {
  switch (level) {
    case "CRIT":  return "critical";
    case "ERROR": return "critical";
    case "WARN":  return "warning";
    case "INFO":  return "info";
    default:      return "neutral";
  }
}

function logLevelLabel(level: string) {
  switch (level) {
    case "CRIT":  return "CRÍTICO";
    case "ERROR": return "ERRO";
    case "WARN":  return "ATENÇÃO";
    case "INFO":  return "INFO";
    default:      return level;
  }
}

interface Props {
  instanceId?: string;
  instanceNames: Record<string, string>;
}

export function LogsTable({ instanceId, instanceNames }: Props) {
  const [level, setLevel] = useState("");

  const { data: logs, isLoading } = useServiceLogs({
    instance_id: instanceId || undefined,
    level: level || undefined,
    limit: 200,
  });

  // Extrai projeto do nome do container (ex: "mautic-br_php" → "mautic-br")
  function extractProject(containerName: string) {
    const parts = containerName.split("_");
    return parts.length > 1 ? parts.slice(0, -1).join("_") : containerName;
  }

  const columns = [
    {
      key: "time",
      header: "Horário",
      width: "140px",
      render: (row: ServiceLog) => (
        <span className="text-xs text-[var(--color-text-muted)] tabular-nums whitespace-nowrap">
          {format(new Date(row.captured_at), "dd/MM HH:mm:ss", { locale: ptBR })}
        </span>
      ),
    },
    {
      key: "level",
      header: "Nível",
      width: "90px",
      render: (row: ServiceLog) => (
        <Badge variant={logLevelVariant(row.log_level)}>
          {logLevelLabel(row.log_level)}
        </Badge>
      ),
    },
    {
      key: "vps",
      header: "VPS",
      render: (row: ServiceLog) => (
        <Badge variant="info">
          {instanceNames[row.instance_id] ?? row.instance_name ?? row.instance_id}
        </Badge>
      ),
    },
    {
      key: "project",
      header: "Projeto",
      render: (row: ServiceLog) => (
        <Badge variant="neutral">
          {extractProject(row.container_name)}
        </Badge>
      ),
    },
    {
      key: "container",
      header: "Container",
      render: (row: ServiceLog) => (
        <Badge variant="muted">
          <span className="font-mono">{row.container_name}</span>
        </Badge>
      ),
    },
    {
      key: "message",
      header: "Mensagem",
      render: (row: ServiceLog) => (
        <span className="text-xs text-[var(--color-text)] font-mono line-clamp-2">
          {row.message}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {/* Filtro de nível */}
      <div className="flex items-center gap-3">
        <Select
          value={level}
          onChange={(e) => setLevel(e.target.value)}
          options={LEVEL_OPTIONS}
          className="w-48"
        />
      </div>

      {isLoading ? (
        <p className="py-8 text-center text-sm text-[var(--color-text-muted)]">
          Carregando logs...
        </p>
      ) : (
        <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] overflow-hidden">
          <Table
            columns={columns}
            data={logs ?? []}
            keyExtractor={(row) => row.id}
            emptyMessage={MESSAGES.emptyStates.logs}
          />
        </div>
      )}
    </div>
  );
}
