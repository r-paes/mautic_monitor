"use client";

import {
  Send, CheckCircle, XCircle, AlertTriangle, Ban,
  Eye, MousePointerClick, ShieldAlert,
  MessageSquare, CreditCard,
} from "lucide-react";
import { StatCard } from "@/components/ui/Card";
import { PageSpinner } from "@/components/ui/Spinner";
import { MESSAGES } from "@/lib/constants/ui";
import { useAvantStats } from "@/lib/hooks/useGatewayConfig";
import { useSendpostStats } from "@/lib/hooks/useMetrics";
import type { GatewayMetric, SendpostSubAccountStats } from "@/lib/api/metrics";

function fmt(n: number | null | undefined) {
  if (n == null) return "—";
  return n.toLocaleString("pt-BR");
}

function deliveryRate(sent: number | null, delivered: number | null) {
  if (!sent || !delivered) return null;
  return `${((delivered / sent) * 100).toFixed(1)}% entrega`;
}

// ─── Sendpost (email) — dados on-demand da API Sendpost ─────────────────────

interface SendpostCardsProps {
  params: { start: string; end: string };
}

export function SendpostCards({ params }: SendpostCardsProps) {
  const { data, isLoading, error } = useSendpostStats(params);

  if (isLoading) {
    return <PageSpinner />;
  }

  if (error || !data || data.subaccounts.length === 0) {
    return (
      <p className="text-sm text-[var(--color-text-muted)] py-8 text-center">
        {MESSAGES.emptyStates.gateways}
      </p>
    );
  }

  const totals = data.totals;

  return (
    <div className="space-y-6">
      {/* Cards — 8 métricas principais */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          label="Processed"
          value={fmt(totals.emails_sent)}
          delta={deliveryRate(totals.emails_sent, totals.emails_delivered) ?? undefined}
          deltaOk
          icon={<Send size={18} />}
        />
        <StatCard
          label="Delivered"
          value={fmt(totals.emails_delivered)}
          icon={<CheckCircle size={18} />}
        />
        <StatCard
          label="Dropped"
          value={fmt(totals.emails_dropped)}
          deltaOk={(totals.emails_dropped ?? 0) === 0}
          delta={(totals.emails_dropped ?? 0) > 0 ? "Verificar" : "OK"}
          icon={<Ban size={18} />}
        />
        <StatCard
          label="Hard Bounce"
          value={fmt(totals.emails_hard_bounced)}
          deltaOk={(totals.emails_hard_bounced ?? 0) === 0}
          delta={(totals.emails_hard_bounced ?? 0) > 0 ? "Verificar lista" : "OK"}
          icon={<XCircle size={18} />}
        />
        <StatCard
          label="Soft Bounce"
          value={fmt(totals.emails_soft_bounced)}
          deltaOk={(totals.emails_soft_bounced ?? 0) === 0}
          delta={(totals.emails_soft_bounced ?? 0) > 0 ? "Temporário" : "OK"}
          icon={<AlertTriangle size={18} />}
        />
        <StatCard
          label="Opened"
          value={fmt(totals.emails_opened)}
          delta={totals.emails_delivered ? `${((totals.emails_opened / totals.emails_delivered) * 100).toFixed(1)}%` : undefined}
          deltaOk
          icon={<Eye size={18} />}
        />
        <StatCard
          label="Clicked"
          value={fmt(totals.emails_clicked)}
          delta={totals.emails_delivered ? `${((totals.emails_clicked / totals.emails_delivered) * 100).toFixed(1)}%` : undefined}
          deltaOk
          icon={<MousePointerClick size={18} />}
        />
        <StatCard
          label="Spam"
          value={fmt(totals.emails_spam)}
          deltaOk={(totals.emails_spam ?? 0) === 0}
          delta={(totals.emails_spam ?? 0) > 0 ? "Atenção requerida" : "Sem ocorrências"}
          icon={<ShieldAlert size={18} />}
        />
      </div>

      {/* Tabela por sub-account — dados diretos da API Sendpost */}
      <SendpostSubAccountTable rows={data.subaccounts} />
    </div>
  );
}

const SENDPOST_COLS = [
  "Processed", "Delivered", "Dropped", "Hard Bounce",
  "Soft Bounce", "Opened", "Clicked", "Unsubscribed", "Spam",
] as const;

function SendpostSubAccountTable({ rows }: { rows: SendpostSubAccountStats[] }) {
  return (
    <div className="w-full overflow-x-auto rounded-[var(--radius-md)] border border-[var(--color-border)]">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--color-border)]">
            <th className="px-4 py-3 text-left text-[10px] font-semibold tracking-wider uppercase text-[var(--color-text-muted)]">
              Sub-account
            </th>
            {SENDPOST_COLS.map((h) => (
              <th
                key={h}
                className="px-4 py-3 text-right text-[10px] font-semibold tracking-wider uppercase text-[var(--color-text-muted)]"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr
              key={r.subaccount_name}
              className="border-b border-[var(--color-border)] last:border-0 hover:bg-[var(--color-surface-2)] transition-colors"
            >
              <td className="px-4 py-3 font-medium text-[var(--color-text)]">{r.subaccount_name}</td>
              <td className="px-4 py-3 text-right tabular-nums text-[var(--color-text)]">{fmt(r.emails_sent)}</td>
              <td className="px-4 py-3 text-right tabular-nums text-[var(--color-text)]">{fmt(r.emails_delivered)}</td>
              <td className="px-4 py-3 text-right tabular-nums text-[var(--color-text)]">{fmt(r.emails_dropped)}</td>
              <td className="px-4 py-3 text-right tabular-nums text-[var(--color-text)]">
                <span className={r.emails_hard_bounced > 0 ? "text-[var(--color-error)]" : ""}>{fmt(r.emails_hard_bounced)}</span>
              </td>
              <td className="px-4 py-3 text-right tabular-nums text-[var(--color-text)]">
                <span className={r.emails_soft_bounced > 0 ? "text-[var(--color-warning)]" : ""}>{fmt(r.emails_soft_bounced)}</span>
              </td>
              <td className="px-4 py-3 text-right tabular-nums text-[var(--color-text)]">{fmt(r.emails_opened)}</td>
              <td className="px-4 py-3 text-right tabular-nums text-[var(--color-text)]">{fmt(r.emails_clicked)}</td>
              <td className="px-4 py-3 text-right tabular-nums text-[var(--color-text)]">{fmt(r.emails_unsubscribed)}</td>
              <td className="px-4 py-3 text-right tabular-nums text-[var(--color-text)]">
                <span className={r.emails_spam > 0 ? "text-[var(--color-error)]" : ""}>{fmt(r.emails_spam)}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── Avant SMS ───────────────────────────────────────────────────────────────

interface AvantCardsProps {
  metrics: GatewayMetric[];
}

export function AvantCards({ metrics }: AvantCardsProps) {
  const { data: avantStats, isLoading: statsLoading } = useAvantStats();

  // Stat cards globais — dados do endpoint /gateways/avant/stats
  const balance = avantStats?.balance ?? null;
  const byClient = avantStats?.by_client ?? [];

  const clientTotals = byClient.reduce(
    (acc, c) => ({
      sent: acc.sent + c.sms_sent,
      delivered: acc.delivered + c.sms_delivered,
      failed: acc.failed + c.sms_failed,
    }),
    { sent: 0, delivered: 0, failed: 0 }
  );

  // Fallback: se não há dados do endpoint de stats, usa métricas do GatewayMetric
  const avant = metrics.filter((m) => m.gateway_type === "avant");
  const metricTotals = avant.reduce(
    (acc, m) => ({
      sent: acc.sent + (m.sms_sent ?? 0),
      delivered: acc.delivered + (m.sms_delivered ?? 0),
      failed: acc.failed + (m.sms_failed ?? 0),
      balance: m.balance_credits ?? acc.balance,
    }),
    { sent: 0, delivered: 0, failed: 0, balance: null as number | null }
  );

  const totals = byClient.length > 0 ? clientTotals : metricTotals;
  const displayBalance = balance ?? metricTotals.balance;

  if (avant.length === 0 && !statsLoading && byClient.length === 0) {
    return (
      <p className="text-sm text-[var(--color-text-muted)] py-8 text-center">
        {MESSAGES.emptyStates.gateways}
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          label="SMS Enviados"
          value={fmt(totals.sent)}
          delta={deliveryRate(totals.sent, totals.delivered) ?? undefined}
          deltaOk
          icon={<MessageSquare size={18} />}
        />
        <StatCard
          label="Entregues"
          value={fmt(totals.delivered)}
          icon={<CheckCircle size={18} />}
        />
        <StatCard
          label="Falhas"
          value={fmt(totals.failed)}
          deltaOk={totals.failed === 0}
          delta={totals.failed > 0 ? "Verificar gateway" : "Sem falhas"}
          icon={<XCircle size={18} />}
        />
        <StatCard
          label="Saldo (creditos)"
          value={fmt(displayBalance)}
          deltaOk={displayBalance != null && displayBalance > 1000}
          delta={
            displayBalance == null
              ? undefined
              : displayBalance <= 1000
              ? "Saldo baixo"
              : "Saldo ok"
          }
          icon={<CreditCard size={18} />}
        />
      </div>

      {/* Tabela por cliente (costCenterCode) */}
      {byClient.length > 0 && (
        <div className="w-full overflow-x-auto rounded-[var(--radius-md)] border border-[var(--color-border)]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)]">
                <th className="px-4 py-3 text-left text-[10px] font-semibold tracking-wider uppercase text-[var(--color-text-muted)]">
                  Cliente
                </th>
                <th className="px-4 py-3 text-left text-[10px] font-semibold tracking-wider uppercase text-[var(--color-text-muted)]">
                  Cost Center
                </th>
                <th className="px-4 py-3 text-right text-[10px] font-semibold tracking-wider uppercase text-[var(--color-text-muted)]">
                  Enviados
                </th>
                <th className="px-4 py-3 text-right text-[10px] font-semibold tracking-wider uppercase text-[var(--color-text-muted)]">
                  Entregues
                </th>
                <th className="px-4 py-3 text-right text-[10px] font-semibold tracking-wider uppercase text-[var(--color-text-muted)]">
                  Falhas
                </th>
                <th className="px-4 py-3 text-right text-[10px] font-semibold tracking-wider uppercase text-[var(--color-text-muted)]">
                  Taxa
                </th>
              </tr>
            </thead>
            <tbody>
              {byClient.map((c) => {
                const rate =
                  c.sms_sent > 0
                    ? ((c.sms_delivered / c.sms_sent) * 100).toFixed(1) + "%"
                    : "—";
                return (
                  <tr
                    key={c.cost_center_code}
                    className="border-b border-[var(--color-border)] last:border-0 hover:bg-[var(--color-surface-2)] transition-colors"
                  >
                    <td className="px-4 py-3 font-medium text-[var(--color-text)]">
                      {c.client_name}
                    </td>
                    <td className="px-4 py-3 text-[var(--color-text-muted)] text-xs font-mono">
                      {c.cost_center_code}
                    </td>
                    <td className="px-4 py-3 text-right font-semibold tabular-nums text-[var(--color-text)]">
                      {fmt(c.sms_sent)}
                    </td>
                    <td className="px-4 py-3 text-right font-semibold tabular-nums text-[var(--color-text)]">
                      {fmt(c.sms_delivered)}
                    </td>
                    <td className="px-4 py-3 text-right font-semibold tabular-nums text-[var(--color-text)]">
                      <span className={c.sms_failed > 0 ? "text-[var(--color-warning)]" : ""}>
                        {fmt(c.sms_failed)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right font-semibold tabular-nums text-[var(--color-text)]">
                      {rate}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── Delta Alerts ────────────────────────────────────────────────────────────

interface DeltaCardsProps {
  metrics: GatewayMetric[];
}

export function DeltaAlertCards({ metrics }: DeltaCardsProps) {
  const delta = metrics.filter((m) => m.gateway_type === "delta");

  if (delta.length === 0) {
    return (
      <p className="text-sm text-[var(--color-text-muted)] py-8 text-center">
        {MESSAGES.emptyStates.gateways}
      </p>
    );
  }

  const totals = delta.reduce(
    (acc, m) => ({
      sent: acc.sent + (m.emails_sent ?? 0) + (m.sms_sent ?? 0),
      delivered: acc.delivered + (m.emails_delivered ?? 0) + (m.sms_delivered ?? 0),
      failed: acc.failed + (m.emails_hard_bounced ?? 0) + (m.emails_soft_bounced ?? 0) + (m.sms_failed ?? 0),
    }),
    { sent: 0, delivered: 0, failed: 0 }
  );

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
        <StatCard
          label="Alertas Disparados"
          value={fmt(totals.sent)}
          icon={<AlertTriangle size={18} />}
        />
        <StatCard
          label="Entregues"
          value={fmt(totals.delivered)}
          delta={deliveryRate(totals.sent, totals.delivered) ?? undefined}
          deltaOk
          icon={<CheckCircle size={18} />}
        />
        <StatCard
          label="Falhas de Entrega"
          value={fmt(totals.failed)}
          deltaOk={totals.failed === 0}
          delta={totals.failed > 0 ? "Verificar configuração" : "Sem falhas"}
          icon={<XCircle size={18} />}
        />
      </div>

      <BreakdownTable
        rows={delta.map((m) => ({
          type: m.gateway_type,
          cols: [
            { label: "Email",    value: fmt(m.emails_sent) },
            { label: "SMS",      value: fmt(m.sms_sent) },
            { label: "Entregues", value: fmt((m.emails_delivered ?? 0) + (m.sms_delivered ?? 0)) },
            { label: "Falhas",   value: fmt((m.emails_hard_bounced ?? 0) + (m.emails_soft_bounced ?? 0) + (m.sms_failed ?? 0)) },
          ],
        }))}
      />
    </div>
  );
}

// ─── Tabela de breakdown compartilhada ───────────────────────────────────────

interface BreakdownRow {
  type: string;
  cols: { label: string; value: string }[];
}

function BreakdownTable({ rows }: { rows: BreakdownRow[] }) {
  if (!rows.length) return null;
  const headers = rows[0].cols.map((c) => c.label);

  return (
    <div className="w-full overflow-x-auto rounded-[var(--radius-md)] border border-[var(--color-border)]">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--color-border)]">
            <th className="px-4 py-3 text-left text-[10px] font-semibold tracking-wider uppercase text-[var(--color-text-muted)]">
              Gateway
            </th>
            {headers.map((h) => (
              <th
                key={h}
                className="px-4 py-3 text-right text-[10px] font-semibold tracking-wider uppercase text-[var(--color-text-muted)]"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              className="border-b border-[var(--color-border)] last:border-0 hover:bg-[var(--color-surface-2)] transition-colors"
            >
              <td className="px-4 py-3 font-medium text-[var(--color-text)] capitalize">
                {row.type}
              </td>
              {row.cols.map((col) => (
                <td
                  key={col.label}
                  className="px-4 py-3 text-right font-semibold tabular-nums text-[var(--color-text)]"
                >
                  {col.value}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
