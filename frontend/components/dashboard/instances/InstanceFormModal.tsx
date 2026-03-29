"use client";

import { useState, useEffect } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { MESSAGES } from "@/lib/constants/ui";
import { useCreateInstance, useUpdateInstance } from "@/lib/hooks/useInstances";
import type { Instance } from "@/lib/api/instances";

interface Props {
  open: boolean;
  onClose: () => void;
  instance?: Instance | null;
}

interface FormState {
  name: string;
  url: string;
  api_user: string;
  api_password: string;
  active: boolean;
  // create-only
  db_host: string;
  db_port: string;
  db_name: string;
  db_user: string;
  db_password: string;
  ssh_host: string;
  ssh_port: string;
  ssh_user: string;
  ssh_key_path: string;
}

const EMPTY: FormState = {
  name: "",
  url: "",
  api_user: "",
  api_password: "",
  active: true,
  db_host: "",
  db_port: "3306",
  db_name: "",
  db_user: "",
  db_password: "",
  ssh_host: "",
  ssh_port: "22",
  ssh_user: "",
  ssh_key_path: "",
};

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

const inputCls =
  "w-full h-8 px-3 text-sm rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)] transition-colors";

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--color-text-muted)] pb-1 border-b border-[var(--color-border)] mb-3">
      {children}
    </p>
  );
}

export function InstanceFormModal({ open, onClose, instance }: Props) {
  const isEdit = !!instance;
  const [form, setForm] = useState<FormState>(EMPTY);

  const { mutate: create, isPending: creating } = useCreateInstance();
  const { mutate: update, isPending: updating } = useUpdateInstance();
  const isPending = creating || updating;

  useEffect(() => {
    if (open) {
      setForm(
        instance
          ? {
              ...EMPTY,
              name: instance.name,
              url: instance.url,
              api_user: instance.api_user,
              active: instance.active,
            }
          : EMPTY
      );
    }
  }, [open, instance]);

  function set(field: keyof FormState, value: string | boolean) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (isEdit && instance) {
      update(
        {
          id: instance.id,
          data: {
            name: form.name,
            url: form.url,
            api_user: form.api_user,
            ...(form.api_password ? { api_password: form.api_password } : {}),
            active: form.active,
          },
        },
        { onSuccess: onClose }
      );
    } else {
      create(
        {
          name: form.name,
          url: form.url,
          api_user: form.api_user,
          api_password: form.api_password,
          db_host: form.db_host || undefined,
          db_port: form.db_port ? Number(form.db_port) : undefined,
          db_name: form.db_name || undefined,
          db_user: form.db_user || undefined,
          db_password: form.db_password || undefined,
          ssh_host: form.ssh_host || undefined,
          ssh_port: form.ssh_port ? Number(form.ssh_port) : undefined,
          ssh_user: form.ssh_user || undefined,
          ssh_key_path: form.ssh_key_path || undefined,
        },
        { onSuccess: onClose }
      );
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={isEdit ? "Editar instância" : MESSAGES.buttons.newInstance}
      size="lg"
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
            form="instance-form"
          >
            {MESSAGES.buttons.save}
          </Button>
        </>
      }
    >
      <form id="instance-form" onSubmit={handleSubmit} className="space-y-5">
        {/* Acesso à API */}
        <div>
          <SectionTitle>Acesso à API</SectionTitle>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <Field label="Nome" required>
              <input
                className={inputCls}
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                placeholder="Produção BR"
                required
              />
            </Field>
            <Field label="URL da instância" required>
              <input
                className={inputCls}
                value={form.url}
                onChange={(e) => set("url", e.target.value)}
                placeholder={MESSAGES.placeholders.url}
                required
              />
            </Field>
            <Field label="Usuário da API" required>
              <input
                className={inputCls}
                value={form.api_user}
                onChange={(e) => set("api_user", e.target.value)}
                placeholder="api_user"
                required
              />
            </Field>
            <Field label={isEdit ? "Nova senha (deixe vazio para manter)" : "Senha da API"} required={!isEdit}>
              <input
                className={inputCls}
                type="password"
                value={form.api_password}
                onChange={(e) => set("api_password", e.target.value)}
                placeholder={MESSAGES.placeholders.password}
                required={!isEdit}
              />
            </Field>
          </div>
          {isEdit && (
            <div className="mt-3 flex items-center gap-2">
              <input
                id="active-toggle"
                type="checkbox"
                checked={form.active}
                onChange={(e) => set("active", e.target.checked)}
                className="h-4 w-4 accent-[var(--color-primary)]"
              />
              <label htmlFor="active-toggle" className="text-sm text-[var(--color-text)]">
                Instância ativa
              </label>
            </div>
          )}
        </div>

        {/* Banco de Dados — somente criação */}
        {!isEdit && (
          <div>
            <SectionTitle>Banco de Dados (MySQL)</SectionTitle>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Field label="Host">
                <input
                  className={inputCls}
                  value={form.db_host}
                  onChange={(e) => set("db_host", e.target.value)}
                  placeholder="db.exemplo.com"
                />
              </Field>
              <Field label="Porta">
                <input
                  className={inputCls}
                  type="number"
                  value={form.db_port}
                  onChange={(e) => set("db_port", e.target.value)}
                  placeholder="3306"
                />
              </Field>
              <Field label="Nome do banco">
                <input
                  className={inputCls}
                  value={form.db_name}
                  onChange={(e) => set("db_name", e.target.value)}
                  placeholder="mautic_db"
                />
              </Field>
              <Field label="Usuário">
                <input
                  className={inputCls}
                  value={form.db_user}
                  onChange={(e) => set("db_user", e.target.value)}
                  placeholder="db_user"
                />
              </Field>
              <Field label="Senha" className="sm:col-span-2">
                <input
                  className={inputCls}
                  type="password"
                  value={form.db_password}
                  onChange={(e) => set("db_password", e.target.value)}
                  placeholder={MESSAGES.placeholders.password}
                />
              </Field>
            </div>
          </div>
        )}

        {/* SSH — somente criação */}
        {!isEdit && (
          <div>
            <SectionTitle>Acesso SSH</SectionTitle>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Field label="Host SSH">
                <input
                  className={inputCls}
                  value={form.ssh_host}
                  onChange={(e) => set("ssh_host", e.target.value)}
                  placeholder="vps.exemplo.com"
                />
              </Field>
              <Field label="Porta SSH">
                <input
                  className={inputCls}
                  type="number"
                  value={form.ssh_port}
                  onChange={(e) => set("ssh_port", e.target.value)}
                  placeholder="22"
                />
              </Field>
              <Field label="Usuário SSH">
                <input
                  className={inputCls}
                  value={form.ssh_user}
                  onChange={(e) => set("ssh_user", e.target.value)}
                  placeholder="root"
                />
              </Field>
              <Field label="Caminho da chave SSH">
                <input
                  className={inputCls}
                  value={form.ssh_key_path}
                  onChange={(e) => set("ssh_key_path", e.target.value)}
                  placeholder="/root/.ssh/id_rsa"
                />
              </Field>
            </div>
          </div>
        )}
      </form>
    </Modal>
  );
}
