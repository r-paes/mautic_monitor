import { apiClient } from "./client";

export interface GatewayConfigField {
  key: string;
  label: string;
  gateway: string;
  sensitive: boolean;
  configured: boolean;
  value: string | null;
}

export interface GatewayConfigOut {
  fields: GatewayConfigField[];
}

export interface GatewayConfigPatch {
  values: Record<string, string>;
}

// ─── Avant Cost Centers ──────────────────────────────────────────────────────

export interface CostCenter {
  code: string;
  client_name: string;
  active: boolean;
}

export interface CostCenterIn {
  code: string;
  client_name: string;
}

export interface CostCenterStats {
  cost_center_code: string;
  client_name: string;
  sms_sent: number;
  sms_delivered: number;
  sms_failed: number;
}

export interface AvantStatsOut {
  balance: number | null;
  by_client: CostCenterStats[];
}

// ─── API ─────────────────────────────────────────────────────────────────────

export const gatewaysApi = {
  getConfig: () =>
    apiClient.get<GatewayConfigOut>("/gateways/config").then((r) => r.data),

  updateConfig: (data: GatewayConfigPatch) =>
    apiClient.patch("/gateways/config", data),

  // Avant SMS
  getAvantStats: () =>
    apiClient.get<AvantStatsOut>("/gateways/avant/stats").then((r) => r.data),

  getCostCenters: () =>
    apiClient.get<CostCenter[]>("/gateways/avant/cost-centers").then((r) => r.data),

  createCostCenter: (data: CostCenterIn) =>
    apiClient.post<CostCenter>("/gateways/avant/cost-centers", data).then((r) => r.data),

  deleteCostCenter: (code: string) =>
    apiClient.delete(`/gateways/avant/cost-centers/${encodeURIComponent(code)}`),
};
