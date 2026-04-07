import { apiClient } from "./client";

export interface Instance {
  id: string;
  name: string;
  url: string;
  api_user: string;
  db_host: string | null;
  ssh_host: string | null;
  ssh_port: number;
  ssh_user: string | null;
  ssh_key_path: string | null;
  ssh_public_key: string | null;
  active: boolean;
}

export interface SshKeyOut {
  public_key: string;
}

export interface SshTestResult {
  success: boolean;
  message: string;
}

export interface InstanceCreate {
  name: string;
  url: string;
  api_user: string;
  api_password: string;
  db_host?: string;
  db_port?: number;
  db_name?: string;
  db_user?: string;
  db_password?: string;
  ssh_host?: string;
  ssh_port?: number;
  ssh_user?: string;
  ssh_key_path?: string;
}

export interface InstanceUpdate {
  name?: string;
  url?: string;
  api_user?: string;
  api_password?: string;
  active?: boolean;
  ssh_host?: string;
  ssh_port?: number;
  ssh_user?: string;
  ssh_key_path?: string;
}

export const instancesApi = {
  list: () =>
    apiClient.get<Instance[]>("/instances/").then((r) => r.data),

  get: (id: string) =>
    apiClient.get<Instance>(`/instances/${id}`).then((r) => r.data),

  create: (data: InstanceCreate) =>
    apiClient.post<Instance>("/instances/", data).then((r) => r.data),

  update: (id: string, data: InstanceUpdate) =>
    apiClient.patch<Instance>(`/instances/${id}`, data).then((r) => r.data),

  remove: (id: string) =>
    apiClient.delete(`/instances/${id}`),

  generateSshKey: (id: string) =>
    apiClient.post<SshKeyOut>(`/instances/${id}/generate-ssh-key`).then((r) => r.data),

  testSsh: (id: string) =>
    apiClient.post<SshTestResult>(`/instances/${id}/test-ssh`).then((r) => r.data),
};
