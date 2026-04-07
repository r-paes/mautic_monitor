import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { instancesApi, type InstanceCreate, type InstanceUpdate } from "@/lib/api/instances";

export const INSTANCES_KEY = ["instances"] as const;

export function useInstances() {
  return useQuery({
    queryKey: INSTANCES_KEY,
    queryFn: instancesApi.list,
  });
}

export function useInstance(id: string) {
  return useQuery({
    queryKey: [...INSTANCES_KEY, id],
    queryFn: () => instancesApi.get(id),
    enabled: !!id,
  });
}

export function useCreateInstance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: InstanceCreate) => instancesApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: INSTANCES_KEY }),
  });
}

export function useUpdateInstance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: InstanceUpdate }) =>
      instancesApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: INSTANCES_KEY }),
  });
}

export function useDeleteInstance() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => instancesApi.remove(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: INSTANCES_KEY }),
  });
}

export function useGenerateSshKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => instancesApi.generateSshKey(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: INSTANCES_KEY }),
  });
}

export function useTestSsh() {
  return useMutation({
    mutationFn: (id: string) => instancesApi.testSsh(id),
  });
}
