"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { authApi, type Me } from "@/lib/api/auth";
import { setAccessToken } from "@/lib/api/client";

interface AuthState {
  user: Me | null;
  loading: boolean;
  error: string | null;
}

export function useAuth() {
  const router = useRouter();
  const [state, setState] = useState<AuthState>({
    user: null,
    loading: true,
    error: null,
  });

  // Inicializa sessão via refresh cookie (HTTP-only, enviado automaticamente)
  useEffect(() => {
    authApi
      .refresh()
      .then(({ access_token }) => {
        setAccessToken(access_token);
        return authApi.me();
      })
      .then((user) => setState({ user, loading: false, error: null }))
      .catch(() => {
        setAccessToken(null);
        setState({ user: null, loading: false, error: null });
      });
  }, []);

  const login = useCallback(
    async (username: string, password: string) => {
      setState((s) => ({ ...s, loading: true, error: null }));
      try {
        const { access_token } = await authApi.login({ username, password });
        setAccessToken(access_token);
        const user = await authApi.me();
        setState({ user, loading: false, error: null });
        router.push("/dashboard");
      } catch {
        setState({ user: null, loading: false, error: "Credenciais inválidas." });
      }
    },
    [router]
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Ignora erro no logout — limpa sessão local de qualquer forma
    }
    setAccessToken(null);
    setState({ user: null, loading: false, error: null });
    router.push("/login");
  }, [router]);

  return { ...state, login, logout };
}
