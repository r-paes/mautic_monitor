import { apiClient } from "./client";

export interface LoginPayload {
  username: string;
  password: string;
}

export interface TokenOut {
  access_token: string;
  token_type: string;
}

export interface Me {
  id: string;
  name: string;
  email: string;
  role: "admin" | "viewer";
  active: boolean;
}

export const authApi = {
  login: (payload: LoginPayload) =>
    apiClient
      .post<TokenOut>("/auth/login", new URLSearchParams({
        username: payload.username,
        password: payload.password,
      }), { headers: { "Content-Type": "application/x-www-form-urlencoded" } })
      .then((r) => r.data),

  /** Refresh token é enviado automaticamente via cookie HTTP-only */
  refresh: () =>
    apiClient
      .post<TokenOut>("/auth/refresh")
      .then((r) => r.data),

  logout: () =>
    apiClient.post("/auth/logout"),

  me: () =>
    apiClient.get<Me>("/auth/me").then((r) => r.data),
};
