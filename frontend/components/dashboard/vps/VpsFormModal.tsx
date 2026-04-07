"use client";

import { useState, useEffect } from "react";
import { CheckCircle2, XCircle, Copy, Check, RefreshCw, Wifi } from "lucide-react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { MESSAGES } from "@/lib/constants/ui";
import {
  useCreateInstance,
  useUpdateInstance,
  useGenerateSshKey,
  useTestSsh,
} from "@/lib/hooks/useInstances";
import type { Instance } from "@/lib/api/instances";

interface Props {
  open: boolean;
  onClose: () => void;
  vps?: Instance | null;
}

interface FormState {
  name: string;
  ssh_host: string;
  ssh_port: string;
  ssh_user: string;
}

const EMPTY: FormState = {
  name: "",
  ssh_host: "",
  ssh_port: "22",
  ssh_user: "root",
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

// ─── Passo 1: Informações da VPS ─────────────────────────────────────────────

interface Step1Props {
  form: FormState;
  set: (k: keyof FormState, v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  isPending: boolean;
  onClose: () => void;
}

function Step1({ form, set, onSubmit, isPending, onClose }: Step1Props) {
  return (
    <>
      <form id="vps-step1" onSubmit={onSubmit} className="space-y-4">
        <Field label="Nome da VPS" required>
          <input
            className={inputCls}
            value={form.name}
            onChange={(e) => set("name", e.target.value)}
            placeholder="VPS Produção"
            required
          />
        </Field>

        <div className="grid grid-cols-3 gap-3">
          <div className="col-span-2">
            <Field label="Host / IP" required>
              <input
                className={inputCls}
                value={form.ssh_host}
                onChange={(e) => set("ssh_host", e.target.value)}
                placeholder="vps.exemplo.com"
                required
              />
            </Field>
          </div>
          <Field label="Porta SSH">
            <input
              className={inputCls}
              type="number"
              value={form.ssh_port}
              onChange={(e) => set("ssh_port", e.target.value)}
              placeholder="22"
            />
          </Field>
        </div>

        <Field label="Usuário SSH">
          <input
            className={inputCls}
            value={form.ssh_user}
            onChange={(e) => set("ssh_user", e.target.value)}
            placeholder="root"
          />
        </Field>
      </form>

      <div className="flex justify-end gap-2 mt-6">
        <Button variant="ghost" size="sm" onClick={onClose} disabled={isPending}>
          {MESSAGES.buttons.cancel}
        </Button>
        <Button
          variant="primary"
          size="sm"
          loading={isPending}
          type="submit"
          form="vps-step1"
        >
          Gerar chave SSH →
        </Button>
      </div>
    </>
  );
}

// ─── Passo 2: Chave pública + teste de conexão ────────────────────────────────

interface Step2Props {
  instanceId: string;
  publicKey: string;
  onClose: () => void;
  onRegenerateKey: () => void;
  isRegenerating: boolean;
}

function Step2({ instanceId, publicKey, onClose, onRegenerateKey, isRegenerating }: Step2Props) {
  const [copied, setCopied] = useState(false);
  const { mutate: testSsh, isPending: testing, data: testResult } = useTestSsh();

  function handleCopy() {
    navigator.clipboard.writeText(publicKey).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  return (
    <div className="space-y-5">
      {/* Instrução */}
      <div className="rounded-[var(--radius-md)] bg-[var(--color-surface-2)] border border-[var(--color-border)] p-4 space-y-2">
        <p className="text-sm font-semibold text-[var(--color-text)]">
          Adicione a chave pública na VPS
        </p>
        <p className="text-xs text-[var(--color-text-muted)] leading-relaxed">
          Copie a chave abaixo e execute este comando na sua VPS como <code className="font-mono bg-[var(--color-surface)] px-1 rounded">root</code>:
        </p>
        <pre className="text-[11px] font-mono bg-[var(--color-surface)] rounded p-2 text-[var(--color-text-muted)] overflow-x-auto">
          echo &apos;CHAVE_PÚBLICA&apos; &gt;&gt; ~/.ssh/authorized_keys
        </pre>
      </div>

      {/* Chave pública */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-xs font-medium text-[var(--color-text-muted)]">
            Chave pública RSA
          </label>
          <div className="flex gap-2">
            <button
              onClick={onRegenerateKey}
              disabled={isRegenerating}
              className="text-[11px] text-[var(--color-text-muted)] hover:text-[var(--color-primary)] flex items-center gap-1 transition-colors"
            >
              <RefreshCw size={11} className={isRegenerating ? "animate-spin" : ""} />
              Regenerar
            </button>
            <button
              onClick={handleCopy}
              className="text-[11px] text-[var(--color-primary)] hover:opacity-80 flex items-center gap-1 transition-colors"
            >
              {copied ? <Check size={11} /> : <Copy size={11} />}
              {copied ? "Copiado!" : "Copiar"}
            </button>
          </div>
        </div>
        <textarea
          readOnly
          value={publicKey}
          rows={3}
          className="w-full px-3 py-2 text-[11px] font-mono rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-surface-2)] text-[var(--color-text-muted)] resize-none focus:outline-none"
        />
      </div>

      {/* Resultado do teste */}
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
          <p className="text-sm text-[var(--color-text)]">{testResult.message}</p>
        </div>
      )}

      {/* Ações */}
      <div className="flex items-center justify-between gap-2 pt-1">
        <Button
          variant="secondary"
          size="sm"
          icon={<Wifi size={13} />}
          loading={testing}
          onClick={() => testSsh(instanceId)}
        >
          Testar conexão
        </Button>
        <Button variant="primary" size="sm" onClick={onClose}>
          {testResult?.success ? "Concluir" : "Fechar"}
        </Button>
      </div>
    </div>
  );
}

// ─── Modal principal ──────────────────────────────────────────────────────────

export function VpsFormModal({ open, onClose, vps }: Props) {
  const isEdit = !!vps;
  const [step, setStep] = useState<1 | 2>(1);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [createdId, setCreatedId] = useState<string>("");
  const [publicKey, setPublicKey] = useState<string>("");

  const { mutate: create, isPending: creating } = useCreateInstance();
  const { mutate: update, isPending: updating } = useUpdateInstance();
  const { mutate: generateKey, isPending: generatingKey } = useGenerateSshKey();

  useEffect(() => {
    if (open) {
      if (isEdit && vps) {
        setForm({
          name: vps.name,
          ssh_host: vps.ssh_host ?? "",
          ssh_port: String(vps.ssh_port ?? 22),
          ssh_user: vps.ssh_user ?? "root",
        });
        // Se já tem chave pública, vai direto para o passo 2 de gestão
        if (vps.ssh_public_key) {
          setCreatedId(vps.id);
          setPublicKey(vps.ssh_public_key);
          setStep(2);
        } else {
          setStep(1);
        }
      } else {
        setForm(EMPTY);
        setStep(1);
        setCreatedId("");
        setPublicKey("");
      }
    }
  }, [open, vps, isEdit]);

  function set(field: keyof FormState, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function handleStep1Submit(e: React.FormEvent) {
    e.preventDefault();

    const onInstanceReady = (id: string) => {
      generateKey(id, {
        onSuccess: (data) => {
          setCreatedId(id);
          setPublicKey(data.public_key);
          setStep(2);
        },
      });
    };

    if (isEdit && vps) {
      update(
        {
          id: vps.id,
          data: {
            name: form.name,
            ssh_host: form.ssh_host || undefined,
            ssh_port: form.ssh_port ? Number(form.ssh_port) : undefined,
            ssh_user: form.ssh_user || undefined,
          },
        },
        { onSuccess: () => onInstanceReady(vps.id) }
      );
    } else {
      create(
        {
          name: form.name,
          url: `ssh://${form.ssh_host}`,
          api_user: "vps",
          api_password: "vps",
          ssh_host: form.ssh_host || undefined,
          ssh_port: form.ssh_port ? Number(form.ssh_port) : undefined,
          ssh_user: form.ssh_user || undefined,
        },
        {
          onSuccess: (created) => onInstanceReady(created.id),
        }
      );
    }
  }

  const title = isEdit
    ? step === 1
      ? "Editar VPS"
      : `Chave SSH — ${vps?.name}`
    : step === 1
    ? "Nova VPS"
    : "Configurar acesso SSH";

  return (
    <Modal open={open} onClose={onClose} title={title} size="md">
      {/* Indicador de passo */}
      <div className="flex items-center gap-2 mb-5">
        <div className={`flex items-center gap-1.5 text-xs font-medium ${step === 1 ? "text-[var(--color-primary)]" : "text-[var(--color-text-muted)]"}`}>
          <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${step === 1 ? "bg-[var(--color-primary)] text-white" : "bg-[var(--color-ok)] text-white"}`}>
            {step > 1 ? "✓" : "1"}
          </span>
          Informações
        </div>
        <div className="flex-1 h-px bg-[var(--color-border)]" />
        <div className={`flex items-center gap-1.5 text-xs font-medium ${step === 2 ? "text-[var(--color-primary)]" : "text-[var(--color-text-muted)]"}`}>
          <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${step === 2 ? "bg-[var(--color-primary)] text-white" : "bg-[var(--color-surface-2)] text-[var(--color-text-muted)]"}`}>
            2
          </span>
          Chave SSH
        </div>
      </div>

      {step === 1 && (
        <Step1
          form={form}
          set={set}
          onSubmit={handleStep1Submit}
          isPending={creating || updating || generatingKey}
          onClose={onClose}
        />
      )}

      {step === 2 && (
        <Step2
          instanceId={createdId}
          publicKey={publicKey}
          onClose={onClose}
          onRegenerateKey={() =>
            generateKey(createdId, {
              onSuccess: (data) => setPublicKey(data.public_key),
            })
          }
          isRegenerating={generatingKey}
        />
      )}
    </Modal>
  );
}
