"use client";

import { Topnav } from "@/components/layout/Topnav";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Bell, Mail, MessageSquare } from "lucide-react";

const CHANNELS = [
  {
    Icon: Bell,
    title: "Push / In-app",
    description: "Notificações exibidas dentro do painel",
    enabled: true,
  },
  {
    Icon: Mail,
    title: "Email",
    description: "Alertas críticos enviados por email",
    enabled: false,
  },
  {
    Icon: MessageSquare,
    title: "SMS",
    description: "Alertas enviados via Avant SMS",
    enabled: false,
  },
];

export default function NotificationsPage() {
  return (
    <>
      <Topnav title="Notificações" />

      <div className="px-4 md:px-6 py-5 space-y-4">
        <Card>
          <CardHeader
            title="Canais de Notificação"
            subtitle="Configuração de canais de entrega de alertas"
          />
          <div className="space-y-3">
            {CHANNELS.map(({ Icon, title, description, enabled }) => (
              <div
                key={title}
                className="flex items-center gap-4 p-4 rounded-[var(--radius-md)] border border-[var(--color-border)] bg-[var(--color-surface-2)]"
              >
                <div className="p-2 rounded-[var(--radius-sm)] bg-[var(--color-surface)] text-[var(--color-primary)] shrink-0">
                  <Icon size={18} strokeWidth={1.75} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-[var(--color-text)]">{title}</p>
                  <p className="text-xs text-[var(--color-text-muted)]">{description}</p>
                </div>
                <Badge variant={enabled ? "ok" : "neutral"} dot>
                  {enabled ? "Ativo" : "Em breve"}
                </Badge>
              </div>
            ))}
          </div>
        </Card>

        <div className="py-6 text-center text-sm text-[var(--color-text-muted)]">
          Configurações avançadas de notificação — em breve.
        </div>
      </div>
    </>
  );
}
