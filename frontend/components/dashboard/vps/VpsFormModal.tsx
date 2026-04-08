"use client";

import { useState, useEffect } from "react";
import { CheckCircle2, XCircle, Wifi } from "lucide-react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { MESSAGES } from "@/lib/constants/ui";
import {
  useCreateVpsServer,
  useUpdateVpsServer,
  useTestVpsConnection,
} from "@/lib/hooks/useVpsServers";
import type { VpsServer } from "@/lib/api/vps-servers";

interface Props {
  open: boolean;
  onClose: () => void;
  vps?: VpsServer | null;
}

interface FormState {
  name: string;
  easypanel_url: string;
  api_key: string;
}

const EMPTY: FormState = {
  name: "",
  easypanel_url: "",
  api_key: "",
};

const inputCls =
  "w-full h-8 px-3 text-sm rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)] transition-colors";

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1">
        {label}
        {required && <span className="text-[var(--color-critical)] ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}

export function VpsFormModal({ open, onClose, vps }: Props) {
  const isEdit = !!vps;
  const [form, setForm] = useState<FormState>(EMPTY);

  const { mutate: create, isPending: creating } = useCreateVpsServer();
  const { mutate: update, isPending: updating } = useUpdateVpsServer();
  const { mutate: testConn, isPending: testing, data: testResult, reset: resetTest } = useTestVpsConnection();
  const isPending = creating || updating;

  useEffect(() => {
    if (open) {
      resetTest();
      if (isEdit && vps) {
        setForm({
          name: vps.name,
          easypanel_url: vps.easypanel_url,
          api_key: "",
        });
      } else {
        setForm(EMPTY);
      }
    }
  }, [open, vps, isEdit, resetTest]);

  function set(field: keyof FormState, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (isEdit && vps) {
      update(
        {
          id: vps.id,
          data: {
            name: form.name,
            easypanel_url: form.easypanel_url,
            ...(form.api_key ? { api_key: form.api_key } : {}),
          },
        },
        { onSuccess: onClose }
      );
    } else {
      create(
        {
          name: form.name,
          easypanel_url: form.easypanel_url,
          api_key: form.api_key,
        },
        {
          onSuccess: (created) => {
            testConn(created.id);
            onClose();
          },
        }
      );
    }
  }

  function handleTestConnection() {
    if (isEdit && vps) {
      // Se editou a api_key, salva primeiro e depois testa
      if (form.api_key) {
        update(
          {
            id: vps.id,
            data: {
              name: form.name,
              easypanel_url: form.easypanel_url,
              api_key: form.api_key,
            },
          },
          { onSuccess: () => testConn(vps.id) }
        );
      } else {
        testConn(vps.id);
      }
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? "Editar VPS" : "Nova VPS"}
      size="md"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isPending}>
            {MESSAGES.buttons.cancel}
          </Button>
          <Button
            variant="primary"
            size="sm"
            loading={isPending}
            onClick={handleSubmit as never}
            type="submit"
            form="vps-form"
          >
            {MESSAGES.buttons.save}
          </Button>
        </>
      }
    >
      <form id="vps-form" onSubmit={handleSubmit} className="space-y-4">
        <Field label="Nome da VPS" required>
          <input
            className={inputCls}
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
            placeholder="VPS Produção"
            required
          />
        </Field>

        <Field label="URL do EasyPanel" required>
          <input
            className={inputCls}
            value={form.easypanel_url}
            onChange={(e) => set("easypanel_url", e.target.value)}
            placeholder="https://easy.exemplo.com"
            required
          />
        </Field>

        <Field label={isEdit ? "API Key (deixe vazio para manter)" : "API Key"} required={!isEdit}>
          <input
            className={inputCls}
            type="password"
            value={form.api_key}
            onChange={(e) => set("api_key", e.target.value)}
            placeholder="Cole a API Key do EasyPanel"
            required={!isEdit}
          />
        </Field>

        {/* Testar conexão (só em edição) */}
        {isEdit && (
          <div className="pt-2 space-y-3">
            <Button
              variant="secondary"
              size="sm"
              icon={<Wifi size={13} />}
              loading={testing}
              onClick={handleTestConnection}
              type="button"
            >
              Testar conexão
            </Button>

            {testResult && (
              <div
                className={`flex items-start gap-3 rounded-[var(--radius-md)] border p-3 ${
                  testResult.success
                    ? "border-[var(--color-ok)] bg-[var(--color-ok)]/10"
                    : "border-[var(--color-critical)] bg-[var(--color-critical)]/10"
                }`}
              >
                {testResult.success ? (
                  <CheckCircle2 size={16} className="text-[var(--color-ok)] mt-0.5 shrink-0" />
                ) : (
                  <XCircle size={16} className="text-[var(--color-critical)] mt-0.5 shrink-0" />
                )}
                <div>
                  <p className="text-sm text-[var(--color-text)]">{testResult.message}</p>
                  {testResult.success && testResult.cpu_count && (
                    <p className="text-xs text-[var(--color-text-muted)] mt-1">
                      {testResult.cpu_count} CPUs · {testResult.memory_total_mb?.toFixed(0)} MB RAM · {testResult.disk_total_gb?.toFixed(0)} GB Disco
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </form>
    </Modal>
  );
}
