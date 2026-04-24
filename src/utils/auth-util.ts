/** 登录/续期/登出与 localStorage，refresh 存 A 时 XSS 可读（与 B 的 HttpOnly 不同） */
import EventBus, { C_EVENT } from "@/types/event-bus";

const KEY_ACCESS = "access_token";
const KEY_EXPIRES_AT = "access_token_expires_at";
const KEY_REFRESH = "refresh_token";
const LOGIN_CACHE_KEYS = [KEY_ACCESS, KEY_EXPIRES_AT, KEY_REFRESH, "saveUser", "bAuth"] as const;

export interface LoginResponse {
  code: number;
  msg: string;
  access_token: string;
  refresh_token?: string;
  expires_in: number;
  user?: { id: number; name: string; icon?: string; admin?: number };
}

export function getAccessToken(): string | null {
  return localStorage.getItem(KEY_ACCESS);
}

export function getTokenExpiresAt(): number | null {
  const v = localStorage.getItem(KEY_EXPIRES_AT);
  return v ? parseInt(v, 10) : null;
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(KEY_REFRESH);
}

export function setAccessToken(token: string | null): void {
  if (!token) {
    localStorage.removeItem(KEY_ACCESS);
    localStorage.removeItem(KEY_EXPIRES_AT);
    return;
  }
  localStorage.setItem(KEY_ACCESS, token);
}

export function setTokenWithExpiry(token: string, expiresInSeconds: number): void {
  localStorage.setItem(KEY_ACCESS, token);
  const expiresAt = Date.now() + expiresInSeconds * 1000;
  localStorage.setItem(KEY_EXPIRES_AT, String(expiresAt));
}

export function clearLoginCache(): void {
  for (const key of LOGIN_CACHE_KEYS) {
    localStorage.removeItem(key);
  }
  EventBus.$emit(C_EVENT.LOGIN_CACHE_CLEARED);
}

export async function login(
  baseUrl: string,
  username: string,
  password: string
): Promise<LoginResponse> {
  const axios = (await import("axios")).default;
  const url = baseUrl.replace(/\/$/, "") + "/auth/login";
  const resp = await axios.post<LoginResponse>(url, { username, password }, {
    withCredentials: true,
    timeout: 15000,
  });
  const data = resp.data;
  if (data?.access_token) {
    const expiresIn = data.expires_in ?? 86400;
    setTokenWithExpiry(data.access_token, expiresIn);
  }
  if (data?.refresh_token) {
    localStorage.setItem(KEY_REFRESH, data.refresh_token);
  }
  return data;
}

export async function refreshToken(baseUrl: string): Promise<{
  access_token: string;
  expires_in: number;
}> {
  const axios = (await import("axios")).default;
  const url = baseUrl.replace(/\/$/, "") + "/auth/refresh";
  const token = getAccessToken();
  const r = getRefreshToken();
  const resp = await axios.post(
    url,
    r ? { refresh_token: r } : {},
    {
      withCredentials: true,
      timeout: 10000,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    }
  );
  const data = resp.data as { code?: number; access_token?: string; expires_in?: number };
  if (data?.access_token) {
    const expiresIn = data.expires_in ?? 86400;
    setTokenWithExpiry(data.access_token, expiresIn);
  }
  return {
    access_token: data?.access_token ?? "",
    expires_in: data?.expires_in ?? 0,
  };
}

export async function logout(baseUrl: string): Promise<void> {
  const axios = (await import("axios")).default;
  const url = baseUrl.replace(/\/$/, "") + "/auth/logout";
  try {
    await axios.post(url, {}, { withCredentials: true, timeout: 5000 });
  } finally {
    clearLoginCache();
  }
}
