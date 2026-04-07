"use client";

import { useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { MESSAGES } from "@/lib/constants/ui";
import { useCostCenters, useCreateCostCenter, useDeleteCostCenter } from "@/lib/hooks/useGatewayConfig";

const inputCls =
  "w-full h-8 px-3 text-sm rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)] transition-colors";

export function CostCenterManager() {
  const { data: costCenters, isLoading } = useCostCenters();
  const { mutate: create, isPending: creating } = useCreateCostCenter();
  const { mutate: remove, isPending: deleting } = useDeleteCostCenter();

  const [code, setCode] = useState("");
  const [clientName, setClientName] = useState("");

  function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!code.trim() || !clientName.trim()) return;
    create(
      { code: code.trim(), client_name: clientName.trim() },
      {
        onSuccess: () => {
          setCode("");
          setClientName("");
        },
      }
    );
  }

  if (isLoading) {
    return (
      <Card>
        <div className="py-8 text-center text-sm text-[var(--color-text-muted)]">
          Carregando cost centers...
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader
        title="Avant SMS — Cost Centers"
        subtitle="Correlação entre costCenterCode e nome do cliente"
      />

      {/* Lista existente */}
      {costCenters && costCenters.length > 0 ? (
        <div className="mt-3 space-y-1">
          {costCenters.map((cc) => (
            <div
              key={cc.code}
              className="flex items-center justify-between py-2 px-3 rounded-[var(--radius-sm)] hover:bg-[var(--color-surface-2)] transition-colors"
            >
              <div className="flex items-center gap-3 min-w-0">
                <Badge variant="info" dot={false}>
                  {cc.code}
                </Badge>
                <span className="text-sm text-[var(--color-text)] truncate">
                  {cc.client_name}
                </span>
              </div>
              <button
                type="button"
                onClick={() => remove(cc.code)}
                disabled={deleting}
                className="p-1 text-[var(--color-text-muted)] hover:text-[var(--color-critical)] transition-colors shrink-0"
                title="Remover"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      ) : (
        <p className="mt-3 text-sm text-[var(--color-text-muted)]">
          Nenhum cost center cadastrado.
        </p>
      )}

      {/* Formulário de adição */}
      <form onSubmit={handleAdd} className="mt-4 flex items-end gap-2">
        <div className="flex-1 min-w-0">
          <label className="text-xs font-medium text-[var(--color-text-muted)] mb-1 block">
            Codigo
          </label>
          <input
            className={inputCls}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="CLI001"
          />
        </div>
        <div className="flex-[2] min-w-0">
          <label className="text-xs font-medium text-[var(--color-text-muted)] mb-1 block">
            Nome do Cliente
          </label>
          <input
            className={inputCls}
            value={clientName}
            onChange={(e) => setClientName(e.target.value)}
            placeholder="Empresa XYZ"
          />
        </div>
        <Button
          variant="primary"
          size="md"
          type="submit"
          loading={creating}
          icon={<Plus size={14} />}
        >
          {MESSAGES.buttons.add}
        </Button>
      </form>
    </Card>
  );
}
