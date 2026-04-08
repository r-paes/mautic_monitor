import { apiClient } from "./client";

export interface VpsServer {
  id: string;
  name: string;
  easypanel_url: string;
  active: boolean;
  instance_count: number;
}

export interface VpsServerCreate {
  name: string;
  easypanel_url: string;
  api_key: string;
}

export interface VpsServerUpdate {
  name?: string;
  easypanel_url?: string;
  api_key?: string;
  active?: boolean;
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
  cpu_count?: number;
  memory_total_mb?: number;
  disk_total_gb?: number;
}

export interface EasyPanelService {
  name: string;
  project: string;
  type: string;
  status: string;
  image: string;
}

export const vpsServersApi = {
  list: () =>
    apiClient.get<VpsServer[]>("/vps-servers/").then((r) => r.data),

  get: (id: string) =>
    apiClient.get<VpsServer>(`/vps-servers/${id}`).then((r) => r.data),

  create: (data: VpsServerCreate) =>
    apiClient.post<VpsServer>("/vps-servers/", data).then((r) => r.data),

  update: (id: string, data: VpsServerUpdate) =>
    apiClient.patch<VpsServer>(`/vps-servers/${id}`, data).then((r) => r.data),

  remove: (id: string) =>
    apiClient.delete(`/vps-servers/${id}`),

  testConnection: (id: string) =>
    apiClient.post<ConnectionTestResult>(`/vps-servers/${id}/test-connection`).then((r) => r.data),

  listServices: (id: string) =>
    apiClient.get<EasyPanelService[]>(`/vps-servers/${id}/services`).then((r) => r.data),
};
