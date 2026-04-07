import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { gatewaysApi, type GatewayConfigPatch, type CostCenterIn } from "@/lib/api/gateways";

export const GATEWAY_CONFIG_KEY = ["gateway-config"] as const;
export const AVANT_STATS_KEY = ["avant-stats"] as const;
export const COST_CENTERS_KEY = ["cost-centers"] as const;

export function useGatewayConfig() {
  return useQuery({
    queryKey: GATEWAY_CONFIG_KEY,
    queryFn: gatewaysApi.getConfig,
  });
}

export function useSaveGatewayConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: GatewayConfigPatch) => gatewaysApi.updateConfig(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: GATEWAY_CONFIG_KEY }),
  });
}

// ─── Avant SMS Stats ────────────────────────────────────────────────────────

export function useAvantStats() {
  return useQuery({
    queryKey: AVANT_STATS_KEY,
    queryFn: gatewaysApi.getAvantStats,
  });
}

// ─── Cost Centers ───────────────────────────────────────────────────────────

export function useCostCenters() {
  return useQuery({
    queryKey: COST_CENTERS_KEY,
    queryFn: gatewaysApi.getCostCenters,
  });
}

export function useCreateCostCenter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: CostCenterIn) => gatewaysApi.createCostCenter(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: COST_CENTERS_KEY }),
  });
}

export function useDeleteCostCenter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (code: string) => gatewaysApi.deleteCostCenter(code),
    onSuccess: () => qc.invalidateQueries({ queryKey: COST_CENTERS_KEY }),
  });
}
