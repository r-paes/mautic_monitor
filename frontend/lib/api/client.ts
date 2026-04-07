/**
 * client.ts — Instância Axios compartilhada com interceptors JWT.
 *
 * - Injeta Authorization header em cada requisição
 * - Tenta refresh automático do token ao receber 401
 * - Refresh token é armazenado em cookie HTTP-only (setado pelo backend)
 * - Access token é armazenado apenas em memória (não em localStorage)
 */

import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { API_URL } from "@/lib/constants/app";
import { REQUEST_TIMEOUT_MS } from "@/lib/constants/behavior";

// Access token armazenado apenas em memória — nunca em localStorage
let _accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  _accessToken = token;
}

export function getAccessToken() {
  return _accessToken;
}

export const apiClient = axios.create({
  baseURL: API_URL,
  timeout: REQUEST_TIMEOUT_MS,
  headers: { "Content-Type": "application/json" },
  withCredentials: true, // envia cookies HTTP-only (refresh_token) automaticamente
});

// ── Request interceptor — injeta Bearer token ──────────────────────────────
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  if (_accessToken) {
    config.headers.Authorization = `Bearer ${_accessToken}`;
  }
  return config;
});

// ── Response interceptor — refresh automático em 401 ──────────────────────
let _isRefreshing = false;
let _refreshQueue: Array<(token: string) => void> = [];

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error);
    }

    // Não tentar refresh se a request que falhou já é o refresh
    if (original.url?.includes("/auth/refresh")) {
      return Promise.reject(error);
    }

    if (_isRefreshing) {
      // Aguarda o refresh em andamento
      return new Promise((resolve) => {
        _refreshQueue.push((token) => {
          original.headers.Authorization = `Bearer ${token}`;
          resolve(apiClient(original));
        });
      });
    }

    original._retry = true;
    _isRefreshing = true;

    try {
      // Refresh token é enviado automaticamente via cookie HTTP-only
      const { data } = await axios.post(
        `${API_URL}/auth/refresh`,
        null,
        { withCredentials: true }
      );

      setAccessToken(data.access_token);

      _refreshQueue.forEach((cb) => cb(data.access_token));
      _refreshQueue = [];

      original.headers.Authorization = `Bearer ${data.access_token}`;
      return apiClient(original);
    } catch {
      // Refresh falhou — limpa sessão e redireciona
      setAccessToken(null);
      window.location.href = "/login";
      return Promise.reject(error);
    } finally {
      _isRefreshing = false;
    }
  }
);
