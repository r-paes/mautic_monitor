import { useQuery } from "@tanstack/react-query";
import { vpsApi } from "@/lib/api/vps";
import { DASHBOARD_REFRESH_INTERVAL_MS } from "@/lib/constants/behavior";

export function useVpsMetrics(params?: { vps_id?: string; hours?: number; limit?: number }) {
  return useQuery({
    queryKey: ["vps-metrics", params],
    queryFn: () => vpsApi.metrics(params),
    refetchInterval: DASHBOARD_REFRESH_INTERVAL_MS,
  });
}

export function useServiceStatus(params?: { vps_id?: string; instance_id?: string }) {
  return useQuery({
    queryKey: ["service-status", params],
    queryFn: () => vpsApi.services(params),
    refetchInterval: DASHBOARD_REFRESH_INTERVAL_MS,
  });
}

export function useServiceLogs(params?: {
  vps_id?: string;
  instance_id?: string;
  log_level?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: ["service-logs", params],
    queryFn: () => vpsApi.logs(params),
    refetchInterval: 60_000,
  });
}
