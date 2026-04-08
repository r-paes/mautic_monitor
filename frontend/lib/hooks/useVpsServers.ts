import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  vpsServersApi,
  type VpsServerCreate,
  type VpsServerUpdate,
} from "@/lib/api/vps-servers";

export const VPS_SERVERS_KEY = ["vps-servers"] as const;

export function useVpsServers() {
  return useQuery({
    queryKey: VPS_SERVERS_KEY,
    queryFn: vpsServersApi.list,
  });
}

export function useVpsServer(id: string) {
  return useQuery({
    queryKey: [...VPS_SERVERS_KEY, id],
    queryFn: () => vpsServersApi.get(id),
    enabled: !!id,
  });
}

export function useCreateVpsServer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: VpsServerCreate) => vpsServersApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: VPS_SERVERS_KEY }),
  });
}

export function useUpdateVpsServer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: VpsServerUpdate }) =>
      vpsServersApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: VPS_SERVERS_KEY }),
  });
}

export function useDeleteVpsServer() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => vpsServersApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: VPS_SERVERS_KEY }),
  });
}

export function useTestVpsConnection() {
  return useMutation({
    mutationFn: (id: string) => vpsServersApi.testConnection(id),
  });
}

export function useVpsEasyPanelServices(vpsId: string | undefined) {
  return useQuery({
    queryKey: [...VPS_SERVERS_KEY, vpsId, "services"],
    queryFn: () => vpsServersApi.listServices(vpsId!),
    enabled: !!vpsId,
  });
}
