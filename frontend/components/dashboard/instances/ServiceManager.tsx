"use client";

import { useState } from "react";
import { Plus, Trash2, Database, Clock, Globe } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ConfirmModal } from "@/components/ui/ConfirmModal";
import { MESSAGES } from "@/lib/constants/ui";
import { useCreateService, useDeleteService } from "@/lib/hooks/useInstances";
import type { InstanceService } from "@/lib/api/instances";

const SERVICE_TYPES = [
  { value: "database", label: "Database", Icon: Database },
  { value: "crons",    label: "Crons",    Icon: Clock },
  { value: "web",      label: "Web",      Icon: Globe },
] as const;

function serviceIcon(type: string) {
  const found = SERVICE_TYPES.find((t) => t.value === type);
  if (!found) return null;
  const Icon = found.Icon;
  return <Icon size={13} className="text-[var(--color-primary)] shrink-0" />;
}

function serviceLabel(type: string) {
  return SERVICE_TYPES.find((t) => t.value === type)?.label ?? type;
}

const inputCls =
  "w-full h-8 px-3 text-sm rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)] transition-colors";

const selectCls =
  "h-8 px-3 text-sm rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-primary)] transition-colors";

interface Props {
  instanceId: string;
  services: InstanceService[];
}

export function ServiceManager({ instanceId, services }: Props) {
  const [showForm, setShowForm] = useState(false);
  const [newType, setNewType] = useState("database");
  const [newContainer, setNewContainer] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<InstanceService | null>(null);

  const { mutate: createService, isPending: creating } = useCreateService();
  const { mutate: deleteService, isPending: deleting } = useDeleteService();

  // Tipos já usados
  const usedTypes = new Set(services.map((s) => s.service_type));
  const availableTypes = SERVICE_TYPES.filter((t) => !usedTypes.has(t.value));

  function handleAdd(e?: React.FormEvent | React.MouseEvent) {
    e?.preventDefault();
    if (!newContainer.trim()) return;
    createService(
      { instanceId, data: { service_type: newType, container_name: newContainer.trim() } },
      {
        onSuccess: () => {
          setNewContainer("");
          setShowForm(false);
          // Reset type to next available
          const nextAvailable = SERVICE_TYPES.find((t) => !usedTypes.has(t.value) && t.value !== newType);
          if (nextAvailable) setNewType(nextAvailable.value);
        },
      }
    );
  }

  function handleDelete() {
    if (!deleteTarget) return;
    deleteService(
      { instanceId, serviceId: deleteTarget.id },
      { onSuccess: () => setDeleteTarget(null) }
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--color-text-muted)]">
          Serviços Monitorados (Containers)
        </p>
        {availableTypes.length > 0 && !showForm && (
          <Button
            variant="ghost"
            size="sm"
            icon={<Plus size={13} />}
            onClick={() => {
              setNewType(availableTypes[0].value);
              setShowForm(true);
            }}
          >
            Adicionar
          </Button>
        )}
      </div>

      {/* Lista de serviços existentes */}
      {services.length > 0 ? (
        <div className="divide-y divide-[var(--color-border)] rounded-[var(--radius-sm)] border border-[var(--color-border)] overflow-hidden">
          {services.map((svc) => (
            <div
              key={svc.id}
              className="flex items-center justify-between px-4 py-2.5 bg-[var(--color-surface)]"
            >
              <div className="flex items-center gap-3">
                {serviceIcon(svc.service_type)}
                <div>
                  <span className="text-sm font-medium text-[var(--color-text)]">
                    {serviceLabel(svc.service_type)}
                  </span>
                  <span className="ml-2 text-xs font-mono text-[var(--color-text-muted)]">
                    {svc.container_name}
                  </span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={svc.active ? "ok" : "neutral"} dot>
                  {svc.active ? "Ativo" : "Inativo"}
                </Badge>
                <button
                  onClick={() => setDeleteTarget(svc)}
                  className="p-1 rounded text-[var(--color-text-muted)] hover:text-[var(--color-critical)] hover:bg-[var(--color-nav-active)] transition-colors"
                  title="Remover serviço"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-[var(--color-text-muted)] py-2">
          Nenhum serviço configurado. Adicione os containers Docker que compõem esta instância.
        </p>
      )}

      {/* Formulário para adicionar novo serviço (usa div para não conflitar com form pai) */}
      {showForm && (
        <div className="flex items-end gap-2 p-3 rounded-[var(--radius-sm)] border border-dashed border-[var(--color-border)] bg-[var(--color-surface-2)]">
          <div className="w-36">
            <label className="block text-[10px] font-medium text-[var(--color-text-muted)] mb-1">
              Tipo
            </label>
            <select
              className={selectCls}
              value={newType}
              onChange={(e) => setNewType(e.target.value)}
            >
              {availableTypes.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-[10px] font-medium text-[var(--color-text-muted)] mb-1">
              Nome do Container
            </label>
            <input
              className={inputCls}
              value={newContainer}
              onChange={(e) => setNewContainer(e.target.value)}
              placeholder="projeto_database"
              autoFocus
            />
          </div>
          <Button
            variant="primary"
            size="sm"
            loading={creating}
            onClick={(e: React.MouseEvent) => {
              e.preventDefault();
              handleAdd(e);
            }}
          >
            Adicionar
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setShowForm(false)}>
            Cancelar
          </Button>
        </div>
      )}

      {/* Info: máximo 3 serviços */}
      {services.length >= 3 && !showForm && (
        <p className="text-[11px] text-[var(--color-text-muted)]">
          Todos os 3 tipos de serviço estão configurados.
        </p>
      )}

      <ConfirmModal
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onConfirm={handleDelete}
        title="Remover serviço"
        description={`Remover o serviço "${deleteTarget ? serviceLabel(deleteTarget.service_type) : ""}" (${deleteTarget?.container_name})? O monitoramento deste container será interrompido.`}
        confirmLabel={MESSAGES.buttons.delete}
        confirmVariant="danger"
        loading={deleting}
      />
    </div>
  );
}
