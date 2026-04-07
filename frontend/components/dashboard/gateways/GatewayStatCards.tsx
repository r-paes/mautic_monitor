"use client";

import {
  Send, CheckCircle, XCircle, AlertTriangle, Ban,
  Eye, MousePointerClick, ShieldAlert,
  MessageSquare, CreditCard,
} from "lucide-react";
// Send=Processed, CheckCircle=Delivered, Ban=Dropped, XCircle=Bounce,
// Eye=Opened, MousePointerClick=Clicked, ShieldAlert=Spam
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

/** Calcula percentual a/b, retorna string "X.Y%" ou null */
function pct(a: number | null | undefined, b: number | null | undefined): string | null {
  if (!a || !b) return null;
  return `${((a / b) * 100).toFixed(1)}%`;
}

/** Valor absoluto + percentual na mesma célula: "1.234 (5.6%)" */
function fmtPct(value: number, base: number): string {
  const abs = fmt(value);
  if (!base) return abs;
  return `${abs} (${((value / base) * 100).toFixed(1)}%)`;
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

  const t = data.totals;
  const processed = t.emails_sent ?? 0;
  const delivered = t.emails_delivered ?? 0;
  const bounce = (t.emails_hard_bounced ?? 0) + (t.emails_soft_bounced ?? 0);

  return (
    <div className="space-y-6">
      {/* Cards — 7 métricas com percentuais */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          label="Processed"
          value={fmt(processed)}
          icon={<Send size={18} />}
        />
        <StatCard
          label="Delivered"
          value={fmt(delivered)}
          delta={pct(delivered, processed) ?? undefined}
          deltaOk
          icon={<CheckCircle size={18} />}
        />
        <StatCard
          label="Dropped"
          value={fmt(t.emails_dropped)}
          delta={pct(t.emails_dropped, delivered) ?? undefined}
          deltaOk={(t.emails_dropped ?? 0) === 0}
          icon={<Ban size={18} />}
        />
        <StatCard
          label="Bounce"
          value={fmt(bounce)}
          delta={pct(bounce, delivered) ?? undefined}
          deltaOk={bounce === 0}
          icon={<XCircle size={18} />}
        />
        <StatCard
          label="Opened"
          value={fmt(t.emails_opened)}
          delta={pct(t.emails_opened, delivered) ?? undefined}
          deltaOk
          icon={<Eye size={18} />}
        />
        <StatCard
          label="Clicked"
          value={fmt(t.emails_clicked)}
          delta={
            delivered
              ? `${pct(t.emails_clicked, delivered)} del · ${pct(t.emails_clicked, t.emails_opened)} open`
              : undefined
          }
          deltaOk
          icon={<MousePointerClick size={18} />}
        />
        <StatCard
          label="Spam"
          value={fmt(t.emails_spam)}
          delta={pct(t.emails_spam, delivered) ?? undefined}
          deltaOk={(t.emails_spam ?? 0) === 0}
          icon={<ShieldAlert size={18} />}
        />
      </div>

      {/* Tabela por sub-account — dados diretos da API Sendpost */}
      <SendpostSubAccountTable rows={data.subaccounts} />
    </div>
  );
}

const SENDPOST_COLS = [
  "Processed", "Delivered", "Dropped", "Bounce",
  "Opened", "Clicked", "Unsubscribed", "Spam",
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
          {rows.map((r) => {
            const proc = r.emails_sent ?? 0;
            const del = r.emails_delivered ?? 0;
            const bnc = (r.emails_hard_bounced ?? 0) + (r.emails_soft_bounced ?? 0);
            return (
              <tr
                key={r.subaccount_name}
                className="border-b border-[var(--color-border)] last:border-0 hover:bg-[var(--color-surface-2)] transition-colors"
              >
                <td className="px-4 py-3 font-medium text-[var(--color-text)]">{r.subaccount_name}</td>
                <td className="px-4 py-3 text-right tabular-nums text-[var(--color-text)]">
                  {fmt(proc)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-[var(--color-text)]">
                  {fmtPct(del, proc)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-[var(--color-text)]">
                  {fmtPct(r.emails_dropped ?? 0, del)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-[var(--color-text)]">
                  <span className={bnc > 0 ? "text-[var(--color-error)]" : ""}>
                    {fmtPct(bnc, del)}
                  </span>
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-[var(--color-text)]">
                  {fmtPct(r.emails_opened ?? 0, del)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-[var(--color-text)]">
                  {fmtPct(r.emails_clicked ?? 0, del)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-[var(--color-text)]">
                  {fmt(r.emails_unsubscribed)}
                </td>
                <td className="px-4 py-3 text-right tabular-nums text-[var(--color-text)]">
                  <span className={(r.emails_spam ?? 0) > 0 ? "text-[var(--color-error)]" : ""}>
                    {fmtPct(r.emails_spam ?? 0, del)}
                  </span>
                </td>
              </tr>
            );
          })}
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
