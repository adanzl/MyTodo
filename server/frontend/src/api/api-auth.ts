import { api } from "./config";

export interface LoginResponse {
  code: number;
  msg: string;
  access_token: string;
  expires_in: number;
  user: { id: number; name: string; icon?: string };
}

const KEY_ACCESS_TOKEN = "access_token";
const KEY_ACCESS_TOKEN_EXPIRES_AT = "access_token_expires_at";

export function getAccessToken(): string | null {
  return localStorage.getItem(KEY_ACCESS_TOKEN);
}

/** 获取 token 过期时间戳（毫秒），未设置时返回 null */
export function getTokenExpiresAt(): number | null {
  const v = localStorage.getItem(KEY_ACCESS_TOKEN_EXPIRES_AT);
  return v ? parseInt(v, 10) : null;
}

export function setAccessToken(token: string | null): void {
  if (!token) {
    localStorage.removeItem(KEY_ACCESS_TOKEN);
    localStorage.removeItem(KEY_ACCESS_TOKEN_EXPIRES_AT);
    return;
  }
  localStorage.setItem(KEY_ACCESS_TOKEN, token);
}

/** 设置 token 及其过期时间（expires_in 为秒） */
export function setTokenWithExpiry(token: string, expiresInSeconds: number): void {
  localStorage.setItem(KEY_ACCESS_TOKEN, token);
  const expiresAt = Date.now() + expiresInSeconds * 1000;
  localStorage.setItem(KEY_ACCESS_TOKEN_EXPIRES_AT, String(expiresAt));
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const resp = await api.post<LoginResponse>("/auth/login", { username, password });
  const data = resp.data;
  if (data?.access_token) {
    const expiresIn = data.expires_in ?? 86400;
    setTokenWithExpiry(data.access_token, expiresIn);
  }
  return data;
}

export async function refreshToken(): Promise<{ access_token: string; expires_in: number }> {
  const resp = await api.post("/auth/refresh");
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
