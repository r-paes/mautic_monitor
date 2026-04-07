import { apiClient } from "./client";

export interface HealthMetric {
  time: string;
  instance_id: string;
  new_contacts: number | null;
  active_campaigns: number | null;
  api_response_ms: number | null;
  emails_queued: number | null;
  emails_sent_mautic: number | null;
  sms_sent_mautic: number | null;
  db_response_ms: number | null;
  status: string;
}

export interface GatewayMetric {
  time: string;
  gateway_type: string;
  // Sub-account (Sendpost)
  subaccount_id: number | null;
  subaccount_name: string | null;
  // Email (Sendpost)
  emails_sent: number | null;
  emails_delivered: number | null;
  emails_dropped: number | null;
  emails_hard_bounced: number | null;
  emails_soft_bounced: number | null;
  emails_opened: number | null;
  emails_clicked: number | null;
  emails_unsubscribed: number | null;
  emails_spam: number | null;
  open_rate: number | null;
  click_rate: number | null;
  // SMS (Avant)
  sms_sent: number | null;
  sms_delivered: number | null;
  sms_failed: number | null;
  // Saldo
  balance_credits: number | null;
}

export interface DashboardSummary {
  total_contacts_24h: number;
  total_emails_sent: number;
  total_sms_sent: number;
  active_alerts: number;
  critical_alerts: number;
  instances: InstanceSummary[];
}

export interface InstanceSummary {
  id: string;
  name: string;
  url: string;
  status: string;
  contacts_24h: number | null;
  active_campaigns: number | null;
  api_response_ms: number | null;
  emails_sent_mautic: number | null;
  emails_sent_gateway: number | null;
  sms_sent_mautic: number | null;
  sms_sent_gateway: number | null;
  containers: ContainerStatus[];
}

export interface ContainerStatus {
  name: string;
  status: string;
  restart_count: number | null;
}

// Resposta do endpoint on-demand /gateways/sendpost/stats
export interface SendpostSubAccountStats {
  subaccount_id: number | null;
  subaccount_name: string;
  emails_sent: number;
  emails_delivered: number;
  emails_dropped: number;
  emails_hard_bounced: number;
  emails_soft_bounced: number;
  emails_opened: number;
  emails_clicked: number;
  emails_unsubscribed: number;
  emails_spam: number;
  open_rate: number;
  click_rate: number;
}

export interface SendpostStatsResponse {
  period: { start: string; end: string };
  subaccounts: SendpostSubAccountStats[];
  totals: Omit<SendpostSubAccountStats, "subaccount_id" | "subaccount_name">;
}

export const metricsApi = {
  dashboard: (params?: { start?: string; end?: string }) =>
    apiClient.get<DashboardSummary>("/metrics/dashboard", { params }).then((r) => r.data),

  instance: (id: string, params?: { start?: string; end?: string }) =>
    apiClient.get<InstanceSummary>(`/metrics/instances/${id}`, { params }).then((r) => r.data),

  gateways: (params?: { start?: string; end?: string }) =>
    apiClient.get<GatewayMetric[]>("/metrics/gateways", { params }).then((r) => r.data),

  sendpostStats: (params: { start: string; end: string }) =>
    apiClient.get<SendpostStatsResponse>("/gateways/sendpost/stats", { params }).then((r) => r.data),

  emailTimeseries: (params?: { instance_id?: string; hours?: number }) =>
    apiClient.get<{ time: string; count: number; type: "email" | "sms" }[]>(
      "/metrics/timeseries/emails", { params }
    ).then((r) => r.data),
};
