import { useQuery } from "@tanstack/react-query";
import { metricsApi } from "@/lib/api/metrics";
import { DASHBOARD_REFRESH_INTERVAL_MS } from "@/lib/constants/behavior";

export function useDashboard(params?: { start?: string; end?: string }) {
  return useQuery({
    queryKey: ["dashboard", params],
    queryFn: () => metricsApi.dashboard(params),
    refetchInterval: DASHBOARD_REFRESH_INTERVAL_MS,
  });
}

export function useInstanceMetrics(id: string, params?: { start?: string; end?: string }) {
  return useQuery({
    queryKey: ["instance-metrics", id, params],
    queryFn: () => metricsApi.instance(id, params),
    enabled: !!id,
    refetchInterval: DASHBOARD_REFRESH_INTERVAL_MS,
  });
}

export function useGatewayMetrics(params?: { start?: string; end?: string }) {
  return useQuery({
    queryKey: ["gateways", params],
    queryFn: () => metricsApi.gateways(params),
    refetchInterval: DASHBOARD_REFRESH_INTERVAL_MS,
  });
}

export function useSendpostStats(params: { start: string; end: string }) {
  return useQuery({
    queryKey: ["sendpost-stats", params],
    queryFn: () => metricsApi.sendpostStats(params),
    staleTime: 60_000, // 1 min — evita re-fetch excessivo à API Sendpost
  });
}

export function useEmailTimeseries(params?: { instance_id?: string; hours?: number }) {
  return useQuery({
    queryKey: ["timeseries-emails", params],
    queryFn: () => metricsApi.emailTimeseries(params),
    refetchInterval: DASHBOARD_REFRESH_INTERVAL_MS,
  });
}
