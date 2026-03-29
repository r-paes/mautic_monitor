/**
 * ui.ts — Textos de interface: mensagens de erro, empty states e labels de botões.
 * Nenhum texto de UI deve aparecer hardcoded nos componentes.
 */

export const MESSAGES = {
  errors: {
    generic: "Ocorreu um erro inesperado. Tente novamente.",
    unauthorized: "Sessão expirada. Faça login novamente.",
    forbidden: "Você não tem permissão para realizar esta ação.",
    notFound: "Recurso não encontrado.",
    networkError: "Falha de conexão com o servidor.",
    timeout: "A requisição excedeu o tempo limite.",
    validation: "Verifique os campos e tente novamente.",
  },

  emptyStates: {
    dashboard: "Nenhuma instância configurada. Adicione uma instância para começar.",
    instances: "Nenhuma instância cadastrada.",
    alerts: "Nenhum alerta ativo no momento.",
    alertsHistory: "Nenhum alerta no histórico.",
    reports: "Nenhum relatório gerado ainda.",
    reportConfigs: "Nenhuma configuração de relatório cadastrada.",
    gateways: "Nenhum dado de gateway disponível.",
    vps: "Nenhuma VPS monitorada.",
    logs: "Nenhum log de serviço disponível.",
    users: "Nenhum usuário cadastrado.",
  },

  buttons: {
    save: "Salvar",
    cancel: "Cancelar",
    delete: "Excluir",
    confirm: "Confirmar",
    close: "Fechar",
    add: "Adicionar",
    edit: "Editar",
    refresh: "Atualizar",
    newInstance: "Nova Instância",
    generate: "Gerar Relatório",
    send: "Enviar Relatório",
    preview: "Visualizar",
    download: "Baixar",
    filter: "Filtrar",
    clearFilters: "Limpar Filtros",
    login: "Entrar",
    logout: "Sair",
    viewAll: "Ver todos",
    acknowledge: "Reconhecer",
  },

  status: {
    online: "Online",
    degraded: "Degradado",
    down: "Offline",
    ok: "OK",
    warning: "Atenção",
    critical: "Crítico",
    pending: "Pendente",
    generating: "Gerando",
    success: "Sucesso",
    error: "Erro",
    scheduled: "Agendado",
    manual: "Manual",
  },

  placeholders: {
    searchInstances: "Buscar instâncias...",
    searchAlerts: "Buscar alertas...",
    email: "email@exemplo.com",
    phone: "+55 11 99999-9999",
    url: "https://mautic.exemplo.com",
    password: "••••••••",
  },

  confirmations: {
    deleteInstance: "Tem certeza que deseja remover esta instância? Esta ação não pode ser desfeita.",
    deleteReportConfig: "Tem certeza que deseja remover esta configuração de relatório?",
    deleteUser: "Tem certeza que deseja remover este usuário?",
    deleteAlert: "Tem certeza que deseja remover este alerta?",
  },
} as const;

/** Tabs por página */
export const PAGE_TABS = {
  instances: [
    { key: "overview", label: "Visão Geral" },
    { key: "config",   label: "Configurações" },
    { key: "history",  label: "Histórico" },
  ],
  gateways: [
    { key: "sendpost", label: "Sendpost" },
    { key: "avant",    label: "Avant SMS" },
    { key: "delta",    label: "Delta Alerts" },
  ],
  vps: [
    { key: "resources",   label: "Recursos" },
    { key: "containers",  label: "Containers" },
    { key: "logs",        label: "Logs de Erros" },
  ],
  alerts: [
    { key: "active",   label: "Ativos" },
    { key: "history",  label: "Histórico" },
    { key: "rules",    label: "Regras" },
  ],
  reports: [
    { key: "envios", label: "Envios por Empresa" },
  ],
  users: [
    { key: "list",        label: "Lista" },
    { key: "permissions", label: "Permissões" },
  ],
  settings: [
    { key: "thresholds",    label: "Thresholds" },
    { key: "general",       label: "Geral" },
    { key: "notifications", label: "Notificações" },
  ],
} as const;

/** Rótulos de seções da sidebar */
export const NAV_LABELS = {
  monitoring: "Monitoramento",
  alerts_section: "Alertas e Notificações",
  reports_section: "Relatórios",
  system: "Sistema",
  dashboard: "Dashboard",
  instances: "Instâncias",
  gateways: "Gateways",
  vps: "VPS & Logs",
  alerts: "Alertas",
  notifications: "Notificações",
  reports_recentes: "Recentes",
  reports_agendamentos: "Agendamentos",
  users: "Usuários",
  settings: "Configurações",
  logout: "Sair",
} as const;
