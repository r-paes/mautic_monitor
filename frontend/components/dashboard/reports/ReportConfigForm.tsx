"use client";

import { useState, useEffect } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { MESSAGES } from "@/lib/constants/ui";
import { useCreateReportConfig, useUpdateReportConfig } from "@/lib/hooks/useReports";
import type { ReportConfig } from "@/lib/api/reports";
import type { Instance } from "@/lib/api/instances";

interface Props {
  open: boolean;
  onClose: () => void;
  config?: ReportConfig | null;
  instances: Instance[];
}

interface FormState {
  instance_id: string;
  company_name: string;
  mautic_company_id: string;
  report_email: string;
  report_phone: string;
  send_email: boolean;
  send_sms: boolean;
  active: boolean;
}

const EMPTY: FormState = {
  instance_id: "",
  company_name: "",
  mautic_company_id: "",
  report_email: "",
  report_phone: "",
  send_email: true,
  send_sms: false,
  active: true,
};

const inputCls =
  "w-full h-8 px-3 text-sm rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)] transition-colors";

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
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

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 accent-[var(--color-primary)]"
      />
      <span className="text-sm text-[var(--color-text)]">{label}</span>
    </label>
  );
}

export function ReportConfigForm({ open, onClose, config, instances }: Props) {
  const isEdit = !!config;
  const [form, setForm] = useState<FormState>(EMPTY);

  const { mutate: create, isPending: creating } = useCreateReportConfig();
  const { mutate: update, isPending: updating } = useUpdateReportConfig();
  const isPending = creating || updating;

  useEffect(() => {
    if (open) {
      setForm(
        config
          ? {
              instance_id: config.instance_id,
              company_name: config.company_name,
              mautic_company_id: config.mautic_company_id?.toString() ?? "",
              report_email: config.report_email,
              report_phone: config.report_phone ?? "",
              send_email: config.send_email,
              send_sms: config.send_sms,
              active: config.active,
            }
          : EMPTY
      );
    }
  }, [open, config]);

  function set<K extends keyof FormState>(field: K, value: FormState[K]) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload = {
      instance_id: form.instance_id,
      company_name: form.company_name,
      mautic_company_id: form.mautic_company_id ? Number(form.mautic_company_id) : undefined,
      report_email: form.report_email,
      report_phone: form.report_phone || undefined,
      send_email: form.send_email,
      send_sms: form.send_sms,
      active: form.active,
    };

    if (isEdit && config) {
      update({ id: config.id, data: payload }, { onSuccess: onClose });
    } else {
      create(payload, { onSuccess: onClose });
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? "Editar configuração" : "Nova configuração de relatório"}
      size="md"
      footer={
        <>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isPending}>
            {MESSAGES.buttons.cancel}
          </Button>
          <Button variant="primary" size="sm" loading={isPending} type="submit" form="report-config-form">
            {MESSAGES.buttons.save}
          </Button>
        </>
      }
    >
      <form id="report-config-form" onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <Field label="Instância" required>
            <select
              className={inputCls}
              value={form.instance_id}
              onChange={(e) => set("instance_id", e.target.value)}
              required
              disabled={isEdit}
            >
              <option value="">Selecione...</option>
              {instances.map((i) => (
                <option key={i.id} value={i.id}>{i.name}</option>
              ))}
            </select>
          </Field>

          <Field label="Empresa" required>
            <input
              className={inputCls}
              value={form.company_name}
              onChange={(e) => set("company_name", e.target.value)}
              placeholder="Nome da empresa"
              required
            />
          </Field>

          <Field label="ID Empresa no Mautic">
            <input
              className={inputCls}
              type="number"
              value={form.mautic_company_id}
              onChange={(e) => set("mautic_company_id", e.target.value)}
              placeholder="Ex: 42"
            />
          </Field>

          <Field label="Email de destino" required>
            <input
              className={inputCls}
              type="email"
              value={form.report_email}
              onChange={(e) => set("report_email", e.target.value)}
              placeholder={MESSAGES.placeholders.email}
              required
            />
          </Field>

          <Field label="Telefone (SMS)">
            <input
              className={inputCls}
              value={form.report_phone}
              onChange={(e) => set("report_phone", e.target.value)}
              placeholder={MESSAGES.placeholders.phone}
            />
          </Field>
        </div>

        <div className="flex flex-wrap gap-4 pt-1">
          <Toggle label="Enviar por Email" checked={form.send_email} onChange={(v) => set("send_email", v)} />
          <Toggle label="Enviar por SMS" checked={form.send_sms} onChange={(v) => set("send_sms", v)} />
          <Toggle label="Configuração ativa" checked={form.active} onChange={(v) => set("active", v)} />
        </div>
      </form>
    </Modal>
  );
}
