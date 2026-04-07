"use client";

import { useState, useEffect } from "react";
import { CheckCircle2, Eye, EyeOff } from "lucide-react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { MESSAGES } from "@/lib/constants/ui";
import { useGatewayConfig, useSaveGatewayConfig } from "@/lib/hooks/useGatewayConfig";
import type { GatewayConfigField } from "@/lib/api/gateways";

const inputCls =
  "w-full h-8 px-3 text-sm rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:border-[var(--color-primary)] transition-colors";

interface FieldRowProps {
  field: GatewayConfigField;
  value: string;
  onChange: (v: string) => void;
}

function FieldRow({ field, value, onChange }: FieldRowProps) {
  const [show, setShow] = useState(false);

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <label className="text-xs font-medium text-[var(--color-text-muted)]">
          {field.label}
        </label>
        <Badge variant={field.configured ? "ok" : "warning"} dot>
          {field.configured ? "Configurado" : "Não configurado"}
        </Badge>
      </div>
      <div className="relative">
        <input
          className={inputCls}
          type={field.sensitive && !show ? "password" : "text"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={
            field.sensitive
              ? field.configured
                ? "••••••••  (deixe vazio para manter)"
                : "Informe o valor"
              : field.value ?? "Informe o valor"
          }
          style={field.sensitive ? { paddingRight: "2.5rem" } : undefined}
        />
        {field.sensitive && (
          <button
            type="button"
            onClick={() => setShow((s) => !s)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--color-text-muted)] hover:text-[var(--color-text)] transition-colors"
          >
            {show ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
        )}
      </div>
    </div>
  );
}

interface GatewayCredentialsFormProps {
  gateway: "sendpost" | "avant";
  title: string;
  subtitle: string;
}

export function GatewayCredentialsForm({ gateway, title, subtitle }: GatewayCredentialsFormProps) {
  const { data: config, isLoading } = useGatewayConfig();
  const { mutate: save, isPending: saving, isSuccess } = useSaveGatewayConfig();

  const fields = (config?.fields ?? []).filter((f) => f.gateway === gateway);
  const [values, setValues] = useState<Record<string, string>>({});

  useEffect(() => {
    if (fields.length) {
      const initial: Record<string, string> = {};
      fields.forEach((f) => {
        initial[f.key] = f.sensitive ? "" : (f.value ?? "");
      });
      setValues(initial);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config]);

  function handleSave(e: React.FormEvent) {
    e.preventDefault();
    // Remove entradas vazias — não sobrescreve valores existentes com vazio
    const payload: Record<string, string> = {};
    Object.entries(values).forEach(([k, v]) => {
      if (v.trim()) payload[k] = v.trim();
    });
    if (Object.keys(payload).length > 0) {
      save({ values: payload });
    }
  }

  if (isLoading) {
    return (
      <Card>
        <div className="py-8 text-center text-sm text-[var(--color-text-muted)]">
          Carregando configurações...
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader title={title} subtitle={subtitle} />
      <form onSubmit={handleSave} className="space-y-4 mt-2">
        {fields.map((field) => (
          <FieldRow
            key={field.key}
            field={field}
            value={values[field.key] ?? ""}
            onChange={(v) => setValues((prev) => ({ ...prev, [field.key]: v }))}
          />
        ))}

        {isSuccess && (
          <div className="flex items-center gap-2 text-sm text-[var(--color-ok)]">
            <CheckCircle2 size={14} />
            Credenciais salvas com sucesso.
          </div>
        )}

        <div className="flex justify-end pt-1">
          <Button variant="primary" size="md" type="submit" loading={saving}>
            {MESSAGES.buttons.save}
          </Button>
        </div>
      </form>
    </Card>
  );
}
