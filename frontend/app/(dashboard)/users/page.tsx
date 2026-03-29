"use client";

import { Suspense, useState } from "react";
import { Plus, Pencil, Trash2 } from "lucide-react";
import { format } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Topnav } from "@/components/layout/Topnav";
import { Tabs } from "@/components/ui/Tabs";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { Table } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { PageSpinner } from "@/components/ui/Spinner";
import { useTabParam } from "@/lib/hooks/useTabParam";
import { MESSAGES, PAGE_TABS } from "@/lib/constants/ui";

// Dados de placeholder — serão substituídos pela API de usuários (Bloco H backend)
const MOCK_USERS = [
  { id: "1", name: "Ricardo Faria",  email: "ricardo@spacecrm.online", role: "admin",    alert_email: true,  alert_sms: true,  active: true },
  { id: "2", name: "Ana Costa",      email: "ana@spacecrm.online",     role: "operador", alert_email: true,  alert_sms: false, active: true },
  { id: "3", name: "Carlos Lima",    email: "carlos@spacecrm.online",  role: "operador", alert_email: true,  alert_sms: true,  active: true },
];

type MockUser = typeof MOCK_USERS[number];

function roleVariant(role: string): "info" | "neutral" {
  return role === "admin" ? "info" : "neutral";
}

function UsersContent() {
  const [activeTab, setTab] = useTabParam("list");

  const topnavTabs = (
    <Tabs
      tabs={PAGE_TABS.users as unknown as { key: string; label: string }[]}
      active={activeTab}
      onChange={setTab}
      variant="topnav"
    />
  );

  const topnavActions = activeTab === "list" ? (
    <Button variant="primary" size="md" icon={<Plus size={14} />}>
      <span className="hidden sm:inline">{MESSAGES.buttons.add} Usuário</span>
    </Button>
  ) : null;

  const columns = [
    {
      key: "name",
      header: "Nome",
      render: (row: MockUser) => (
        <span className="font-semibold text-[var(--color-text)]">{row.name}</span>
      ),
    },
    {
      key: "email",
      header: "Email",
      render: (row: MockUser) => (
        <span className="text-xs text-[var(--color-text-muted)]">{row.email}</span>
      ),
    },
    {
      key: "role",
      header: "Papel",
      render: (row: MockUser) => (
        <Badge variant={roleVariant(row.role)}>{row.role}</Badge>
      ),
    },
    {
      key: "alerts",
      header: "Alertas",
      render: (row: MockUser) => (
        <div className="flex gap-1">
          {row.alert_email && <Badge variant="neutral">Email</Badge>}
          {row.alert_sms   && <Badge variant="neutral">SMS</Badge>}
        </div>
      ),
    },
    {
      key: "status",
      header: "Status",
      render: (row: MockUser) => (
        <Badge variant={row.active ? "ok" : "neutral"} dot>
          {row.active ? "Ativo" : "Inativo"}
        </Badge>
      ),
    },
    {
      key: "actions",
      header: "",
      align: "right" as const,
      render: (_row: MockUser) => (
        <div className="flex items-center justify-end gap-1">
          <Button variant="ghost" size="sm" icon={<Pencil size={13} />}>
            <span className="hidden sm:inline">{MESSAGES.buttons.edit}</span>
          </Button>
          <Button
            variant="ghost"
            size="sm"
            icon={<Trash2 size={13} />}
            className="text-[var(--color-critical)] hover:text-[var(--color-critical)]"
          >
            <span className="hidden sm:inline">{MESSAGES.buttons.delete}</span>
          </Button>
        </div>
      ),
    },
  ];

  return (
    <>
      <Topnav
        title="Usuários"
        subtitle={`${MOCK_USERS.length} usuários cadastrados`}
        tabs={topnavTabs}
        actions={topnavActions}
      />

      <div className="px-4 md:px-6 py-5">
        {activeTab === "list" && (
          <Card padding="none">
            <div className="px-5 py-4 border-b border-[var(--color-border)]">
              <CardHeader
                title="Usuários"
                subtitle={`${MOCK_USERS.length} usuários cadastrados`}
              />
            </div>
            <Table
              columns={columns}
              data={MOCK_USERS}
              keyExtractor={(row) => row.id}
              emptyMessage={MESSAGES.emptyStates.users}
            />
          </Card>
        )}

        {activeTab === "permissions" && (
          <div className="py-10 text-center text-sm text-[var(--color-text-muted)]">
            Matriz de permissões por papel — em breve.
          </div>
        )}
      </div>
    </>
  );
}

export default function UsersPage() {
  return (
    <Suspense fallback={<><Topnav title="Usuários" /><div className="px-4 md:px-6 py-5"><PageSpinner /></div></>}>
      <UsersContent />
    </Suspense>
  );
}
