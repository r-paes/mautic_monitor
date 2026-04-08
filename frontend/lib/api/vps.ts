import { apiClient } from "./client";

export interface VpsMetric {
  time: string;
  vps_id: string;
  cpu_percent: number | null;
  memory_percent: number | null;
  memory_used_mb: number | null;
  memory_total_mb: number | null;
  disk_percent: number | null;
  disk_used_gb: number | null;
  disk_total_gb: number | null;
  load_avg_1m: number | null;
}

export interface ServiceLog {
  id: string;
  instance_id: string;
  vps_id: string;
  instance_name?: string;
  container_name: string;
  log_level: "critical" | "error" | "warning" | "info";
  message: string;
  pattern_matched: string | null;
  captured_at: string;
}

export interface ServiceStatusEntry {
  id: string;
  time: string;
  instance_id: string;
  vps_id: string;
  container_name: string;
  status: "running" | "stopped" | "restarting" | "error" | "unknown";
  restart_count: number | null;
  image: string | null;
}

export const vpsApi = {
  metrics: (params?: { vps_id?: string; hours?: number; limit?: number }) =>
    apiClient.get<VpsMetric[]>("/vps/metrics", { params }).then((r) => r.data),

  services: (params?: { vps_id?: string; instance_id?: string }) =>
    apiClient.get<ServiceStatusEntry[]>("/vps/services", { params }).then((r) => r.data),

  logs: (params?: {
    vps_id?: string;
    instance_id?: string;
    log_level?: string;
    limit?: number;
  }) =>
    apiClient.get<ServiceLog[]>("/vps/logs", { params }).then((r) => r.data),
};
