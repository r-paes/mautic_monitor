"use client";

import { Suspense, useState } from "react";
import { Topnav } from "@/components/layout/Topnav";
import { Tabs } from "@/components/ui/Tabs";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { PageSpinner } from "@/components/ui/Spinner";
import { useTabParam } from "@/lib/hooks/useTabParam";
import { MESSAGES, PAGE_TABS } from "@/lib/constants/ui";

// Thresholds padrão — virão da API futuramente
const DEFAULT_THRESHOLDS = [
  { key: "cpu_warning",     label: "CPU — Atenção (%)",       value: "75" },
  { key: "cpu_critical",    label: "CPU — Crítico (%)",       value: "90" },
  { key: "mem_warning",     label: "Memória — Atenção (%)",   value: "75" },
  { key: "mem_critical",    label: "Memória — Crítico (%)",   value: "90" },
  { key: "disk_warning",    label: "Disco — Atenção (%)",     value: "70" },
  { key: "disk_critical",   label: "Disco — Crítico (%)",     value: "85" },
  { key: "api_resp_warn",   label: "API Response — Atenção (ms)", value: "2000" },
  { key: "api_resp_crit",   label: "API Response — Crítico (ms)", value: "5000" },
];

const inputCls =
  "w-full h-8 px-3 text-sm rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-primary)] transition-colors";

function SettingsContent() {
  const [activeTab, setTab] = useTabParam("thresholds");
  const [thresholds, setThresholds] = useState(
    Object.fromEntries(DEFAULT_THRESHOLDS.map((t) => [t.key, t.value]))
  );

  const topnavTabs = (
    <Tabs
      tabs={PAGE_TABS.settings as unknown as { key: string; label: string }[]}
      active={activeTab}
      onChange={setTab}
      variant="topnav"
    />
  );

  return (
    <>
      <Topnav title="Configurações" tabs={topnavTabs} />

      <div className="px-4 md:px-6 py-5 space-y-4 max-w-2xl">
        {activeTab === "thresholds" && (
          <Card>
            <CardHeader
              title="Thresholds de Alerta"
              subtitle="Limites para geração automática de alertas de severidade"
            />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {DEFAULT_THRESHOLDS.map((t) => (
                <div key={t.key}>
                  <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1">
                    {t.label}
                  </label>
                  <input
                    type="number"
                    className={inputCls}
                    value={thresholds[t.key]}
                    onChange={(e) =>
                      setThresholds((prev) => ({ ...prev, [t.key]: e.target.value }))
                    }
                  />
                </div>
              ))}
            </div>
            <div className="flex justify-end mt-6">
              <Button variant="primary" size="md">
                {MESSAGES.buttons.save}
              </Button>
            </div>
          </Card>
        )}

        {activeTab === "general" && (
          <Card>
            <CardHeader
              title="Configurações Gerais"
              subtitle="Fuso horário, idioma e comportamento geral"
            />
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1">
                  Fuso horário
                </label>
                <select className={inputCls} defaultValue="America/Sao_Paulo">
                  <option value="America/Sao_Paulo">America/São_Paulo (BRT)</option>
                  <option value="UTC">UTC</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-[var(--color-text-muted)] mb-1">
                  Intervalo de atualização automática (segundos)
                </label>
                <input type="number" className={inputCls} defaultValue="60" />
              </div>
            </div>
            <div className="flex justify-end mt-6">
              <Button variant="primary" size="md">
                {MESSAGES.buttons.save}
              </Button>
            </div>
          </Card>
        )}

        {activeTab === "notifications" && (
          <div className="py-10 text-center text-sm text-[var(--color-text-muted)]">
            Configuração de templates e horários de notificação — em breve.
          </div>
        )}
      </div>
    </>
  );
}

export default function SettingsPage() {
  return (
    <Suspense fallback={<><Topnav title="Configurações" /><div className="px-4 md:px-6 py-5"><PageSpinner /></div></>}>
      <SettingsContent />
    </Suspense>
  );
}
