import { api } from "./config";

/** 与 api 层解耦：token 彻底失效时由根组件注册，避免 config ↔ store 循环依赖。 */
type OnAuthSessionExpired = () => void;
let onAuthSessionExpired: OnAuthSessionExpired | null = null;

export function setAuthSessionExpiredHandler(fn: OnAuthSessionExpired): void {
  onAuthSessionExpired = fn;
}

export function notifyAuthSessionExpired(): void {
  onAuthSessionExpired?.();
}

export interface LoginResponse {
  code: number;
  msg: string;
  access_token: string;
  refresh_token?: string;
  expires_in: number;
  user: { id: number; name: string; icon?: string };
}

const STORAGE_KEY_ACCESS = "access_token";
const STORAGE_KEY_ACCESS_EXPIRES_AT = "access_token_expires_at";
const STORAGE_KEY_REFRESH = "refresh_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(STORAGE_KEY_ACCESS);
}

export function getTokenExpiresAt(): number | null {
  const v = localStorage.getItem(STORAGE_KEY_ACCESS_EXPIRES_AT);
  return v ? parseInt(v, 10) : null;
}

export function setAccessToken(token: string | null): void {
  if (!token) {
    localStorage.removeItem(STORAGE_KEY_ACCESS);
    localStorage.removeItem(STORAGE_KEY_ACCESS_EXPIRES_AT);
    localStorage.removeItem(STORAGE_KEY_REFRESH);
    return;
  }
  localStorage.setItem(STORAGE_KEY_ACCESS, token);
}

export function setTokenWithExpiry(token: string, expiresInSeconds: number): void {
  localStorage.setItem(STORAGE_KEY_ACCESS, token);
  const expiresAt = Date.now() + expiresInSeconds * 1000;
  localStorage.setItem(STORAGE_KEY_ACCESS_EXPIRES_AT, String(expiresAt));
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const resp = await api.post<LoginResponse>("/auth/login", { username, password });
  const data = resp.data;
  if (data?.access_token) {
    const expiresIn = data.expires_in ?? 86400;
    setTokenWithExpiry(data.access_token, expiresIn);
  }
  if (data?.refresh_token) {
    localStorage.setItem(STORAGE_KEY_REFRESH, data.refresh_token);
  }
  return data;
}

export async function refreshToken(): Promise<{ access_token: string; expires_in: number }> {
  const r = localStorage.getItem(STORAGE_KEY_REFRESH);
  const resp = await api.post("/auth/refresh", r ? { refresh_token: r } : {});
  const data = resp.data;
  if (data?.access_token) {
    const expiresIn = data.expires_in ?? 86400;
    setTokenWithExpiry(data.access_token, expiresIn);
  }
  return data;
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout");
  setAccessToken(null);
}
