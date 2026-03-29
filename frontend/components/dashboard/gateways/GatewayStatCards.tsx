"use client";

import { Mail, CheckCircle, XCircle, AlertTriangle, MessageSquare, CreditCard } from "lucide-react";
import { StatCard } from "@/components/ui/Card";
import { Badge, statusVariant } from "@/components/ui/Badge";
import { MESSAGES } from "@/lib/constants/ui";
import type { GatewayMetric } from "@/lib/api/metrics";

function fmt(n: number | null | undefined) {
  if (n == null) return "—";
  return n.toLocaleString("pt-BR");
}

function fmtCredits(n: number | null | undefined) {
  if (n == null) return "—";
  return `R$ ${n.toLocaleString("pt-BR", { minimumFractionDigits: 2 })}`;
}

function deliveryRate(sent: number | null, delivered: number | null) {
  if (!sent || !delivered) return null;
  return `${((delivered / sent) * 100).toFixed(1)}% entrega`;
}

// ─── Sendpost (email) ────────────────────────────────────────────────────────

interface SendpostCardsProps {
  metrics: GatewayMetric[];
}

export function SendpostCards({ metrics }: SendpostCardsProps) {
  const sendpost = metrics.filter((m) => m.gateway_type === "sendpost");

  const totals = sendpost.reduce(
    (acc, m) => ({
      sent: acc.sent + (m.emails_sent ?? 0),
      delivered: acc.delivered + (m.emails_delivered ?? 0),
      bounced: acc.bounced + (m.emails_bounced ?? 0),
      spam: acc.spam + (m.emails_spam ?? 0),
    }),
    { sent: 0, delivered: 0, bounced: 0, spam: 0 }
  );

  if (sendpost.length === 0) {
    return (
      <p className="text-sm text-[var(--color-text-muted)] py-8 text-center">
        {MESSAGES.emptyStates.gateways}
      </p>
    );
  }

  return (
    <div className="space-y-6">
      {/* Totais consolidados */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          label="Emails Enviados"
          value={fmt(totals.sent)}
          delta={deliveryRate(totals.sent, totals.delivered) ?? undefined}
          deltaOk
          icon={<Mail size={18} />}
        />
        <StatCard
          label="Entregues"
          value={fmt(totals.delivered)}
          icon={<CheckCircle size={18} />}
        />
        <StatCard
          label="Bounces"
          value={fmt(totals.bounced)}
          deltaOk={totals.bounced === 0}
          delta={totals.bounced > 0 ? "Verificar lista" : "Dentro do limite"}
          icon={<XCircle size={18} />}
        />
        <StatCard
          label="Spam"
          value={fmt(totals.spam)}
          deltaOk={totals.spam === 0}
          delta={totals.spam > 0 ? "Atenção requerida" : "Sem ocorrências"}
          icon={<AlertTriangle size={18} />}
        />
      </div>

      {/* Breakdown por instância */}
      <BreakdownTable
        rows={sendpost.map((m) => ({
          type: m.gateway_type,
          status: m.status,
          cols: [
            { label: "Enviados",  value: fmt(m.emails_sent) },
            { label: "Entregues", value: fmt(m.emails_delivered) },
            { label: "Bounces",   value: fmt(m.emails_bounced) },
            { label: "Spam",      value: fmt(m.emails_spam) },
          ],
        }))}
      />
    </div>
  );
}

// ─── Avant SMS ───────────────────────────────────────────────────────────────

interface AvantCardsProps {
  metrics: GatewayMetric[];
}

export function AvantCards({ metrics }: AvantCardsProps) {
  const avant = metrics.filter((m) => m.gateway_type === "avant");

  const totals = avant.reduce(
    (acc, m) => ({
      sent: acc.sent + (m.sms_sent ?? 0),
      delivered: acc.delivered + (m.sms_delivered ?? 0),
      failed: acc.failed + (m.sms_failed ?? 0),
      balance: acc.balance + (m.balance_credits ?? 0),
    }),
    { sent: 0, delivered: 0, failed: 0, balance: 0 }
  );

  if (avant.length === 0) {
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
          label="Saldo (créditos)"
          value={fmtCredits(totals.balance)}
          deltaOk={totals.balance > 100}
          delta={totals.balance <= 100 ? "Saldo baixo" : "Saldo ok"}
          icon={<CreditCard size={18} />}
        />
      </div>

      <BreakdownTable
        rows={avant.map((m) => ({
          type: m.gateway_type,
          status: m.status,
          cols: [
            { label: "Enviados",  value: fmt(m.sms_sent) },
            { label: "Entregues", value: fmt(m.sms_delivered) },
            { label: "Falhas",    value: fmt(m.sms_failed) },
            { label: "Saldo",     value: fmtCredits(m.balance_credits) },
          ],
        }))}
      />
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
      failed: acc.failed + (m.emails_bounced ?? 0) + (m.sms_failed ?? 0),
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
          status: m.status,
          cols: [
            { label: "Email",    value: fmt(m.emails_sent) },
            { label: "SMS",      value: fmt(m.sms_sent) },
            { label: "Entregues", value: fmt((m.emails_delivered ?? 0) + (m.sms_delivered ?? 0)) },
            { label: "Falhas",   value: fmt((m.emails_bounced ?? 0) + (m.sms_failed ?? 0)) },
          ],
        }))}
      />
    </div>
  );
}

// ─── Tabela de breakdown compartilhada ───────────────────────────────────────

interface BreakdownRow {
  type: string;
  status: string;
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
            <th className="px-4 py-3 text-left text-[10px] font-semibold tracking-wider uppercase text-[var(--color-text-muted)]">
              Status
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
              <td className="px-4 py-3">
                <Badge variant={statusVariant(row.status)} dot>
                  {MESSAGES.status[row.status as keyof typeof MESSAGES.status] ?? row.status}
                </Badge>
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
