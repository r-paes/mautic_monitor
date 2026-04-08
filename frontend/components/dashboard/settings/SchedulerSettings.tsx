"use client";

import { useState } from "react";
import { Clock, Check } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { PageSpinner } from "@/components/ui/Spinner";
import { useSchedulerConfigs, useUpdateSchedulerConfig } from "@/lib/hooks/useSchedulerConfig";

const CONFIG_ICONS: Record<string, string> = {
  mautic_api_interval: "API Mautic",
  mautic_db_interval: "DB Mautic",
  vps_interval: "VPS (EasyPanel)",
  gateway_interval: "Gateways",
  alert_engine_interval: "Motor de Alertas",
};

const inputCls =
  "w-20 h-8 px-2 text-sm text-center rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-surface)] text-[var(--color-text)] focus:outline-none focus:border-[var(--color-primary)] transition-colors tabular-nums";

export function SchedulerSettings() {
  const { data: configs, isLoading } = useSchedulerConfigs();
  const { mutate: updateConfig, isPending } = useUpdateSchedulerConfig();
  const [editing, setEditing] = useState<Record<string, number>>({});
  const [saved, setSaved] = useState<string | null>(null);

  if (isLoading) return <PageSpinner />;

  function handleSave(key: string) {
    const value = editing[key];
    if (value == null || value < 1) return;
    updateConfig(
      { key, data: { interval_minutes: value } },
      {
        onSuccess: () => {
          setSaved(key);
          setTimeout(() => setSaved(null), 2000);
          setEditing((prev) => {
            const next = { ...prev };
            delete next[key];
            return next;
          });
        },
      }
    );
  }

  return (
    <Card padding="none">
      <div className="px-5 py-4 border-b border-[var(--color-border)]">
        <div className="flex items-center gap-2">
          <Clock size={16} className="text-[var(--color-primary)]" />
          <div>
            <p className="text-sm font-semibold text-[var(--color-text)]">
              Intervalos de Coleta
            </p>
            <p className="text-xs text-[var(--color-text-muted)]">
              Defina a frequência de cada tipo de monitoramento (em minutos)
            </p>
          </div>
        </div>
      </div>

      <div className="divide-y divide-[var(--color-border)]">
        {(configs ?? []).map((cfg) => {
          const isEditing = cfg.config_key in editing;
          const currentValue = isEditing ? editing[cfg.config_key] : cfg.interval_minutes;
          const justSaved = saved === cfg.config_key;

          return (
            <div
              key={cfg.config_key}
              className="flex items-center justify-between px-5 py-3"
            >
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-[var(--color-text)]">
                  {CONFIG_ICONS[cfg.config_key] ?? cfg.config_key}
                </p>
                <p className="text-xs text-[var(--color-text-muted)]">
                  {cfg.description}
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <input
                  type="number"
                  min={1}
                  max={1440}
                  className={inputCls}
                  value={currentValue}
                  onChange={(e) =>
                    setEditing((prev) => ({
                      ...prev,
                      [cfg.config_key]: Number(e.target.value),
                    }))
                  }
                />
                <span className="text-xs text-[var(--color-text-muted)]">min</span>

                {isEditing && (
                  <Button
                    variant="primary"
                    size="sm"
                    loading={isPending}
                    onClick={() => handleSave(cfg.config_key)}
                  >
                    Salvar
                  </Button>
                )}

                {justSaved && (
                  <Badge variant="ok">
                    <Check size={10} className="mr-1" />
                    Salvo
                  </Badge>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="px-5 py-3 bg-[var(--color-surface-2)] border-t border-[var(--color-border)]">
        <p className="text-[11px] text-[var(--color-text-muted)]">
          Alterações nos intervalos serão aplicadas após reinício do backend.
        </p>
      </div>
    </Card>
  );
}
