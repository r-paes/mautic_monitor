/**
 * app.ts — Identidade e endpoints globais da aplicação.
 * Todos os valores sensíveis à URL ou ambiente vêm de variáveis NEXT_PUBLIC_*.
 */

export const APP_NAME = process.env.NEXT_PUBLIC_APP_NAME ?? "SpaceCRM Monitor";
export const APP_TAGLINE = "Painel de controle multi-instâncias Mautic";
export const APP_LOGO_PATH = "logo-space.webp";

export const APP_BASE_URL =
  process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const API_V1_PREFIX = "/api/v1";

/** URL completa para chamadas à API FastAPI */
export const API_URL = `${API_BASE_URL}${API_V1_PREFIX}`;

export const APP_ENV =
  (process.env.NEXT_PUBLIC_APP_ENV as "development" | "production") ??
  "development";

export const IS_PRODUCTION = APP_ENV === "production";
