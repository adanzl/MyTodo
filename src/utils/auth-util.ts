/** 登录/续期/登出与 localStorage，refresh 存 A 时 XSS 可读（与 B 的 HttpOnly 不同） */
import EventBus, { C_EVENT } from "@/types/event-bus";

const KEY_ACCESS = "lx_access_token";
const KEY_EXPIRES_AT = "lx_access_token_expires_at";
const KEY_REFRESH = "lx_refresh_token";
const KEY_SAVE_USER = "lx_saveUser";
const KEY_BAUTH = "lx_bAuth";
const KEY_SESSION_REVISION = "lx_session_revision";
/** 网页主动注销时置位，原生侧不得再自动注入旧会话（与 LOGIN_CACHE_KEYS 分离）。 */
export const KEY_WEB_LOGOUT_SIGNAL = "lx_web_logout_signal";
const LOGIN_CACHE_KEYS = [
  KEY_ACCESS,
  KEY_EXPIRES_AT,
  KEY_REFRESH,
  KEY_SAVE_USER,
  KEY_BAUTH,
  KEY_SESSION_REVISION,
] as const;

/** 登录 / 注销时递增，用于丢弃过期的 refresh 结果（含同账号重新登录）。 */
export interface SessionScope {
  revision: string;
  userId: string | null;
}

function getSessionRevision(): string {
  return localStorage.getItem(KEY_SESSION_REVISION) ?? "";
}

function bumpSessionRevision(): void {
  localStorage.setItem(
    KEY_SESSION_REVISION,
    `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
  );
}

export function captureSessionScope(): SessionScope {
  return {
    revision: getSessionRevision(),
    userId: localStorage.getItem(KEY_SAVE_USER),
  };
}

export function sessionScopeMatches(scope: SessionScope): boolean {
  const cur = captureSessionScope();
  return cur.revision === scope.revision && cur.userId === scope.userId;
}

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
  localStorage.setItem(KEY_WEB_LOGOUT_SIGNAL, "1");
  EventBus.$emit(C_EVENT.LOGIN_CACHE_CLEARED);
}

/** 登录成功后一次性写入完整会话（无先清空再写入的空窗）。 */
export function applyLoginSession(userId: string, data: LoginResponse): void {
  if (!data.access_token) return;
  const expiresIn = data.expires_in ?? 86400;
  setTokenWithExpiry(data.access_token, expiresIn);
  localStorage.setItem(KEY_SAVE_USER, userId);
  localStorage.setItem(KEY_BAUTH, "true");
  if (data.refresh_token) {
    localStorage.setItem(KEY_REFRESH, data.refresh_token);
  } else {
    localStorage.removeItem(KEY_REFRESH);
  }
  bumpSessionRevision();
  localStorage.removeItem(KEY_WEB_LOGOUT_SIGNAL);
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
    const userId = data.user?.id?.toString();
    if (!userId) {
      throw new Error("登录响应缺少 user.id，无法保存会话");
    }
    applyLoginSession(userId, data);
  }
  return data;
}

export async function refreshToken(
  baseUrl: string,
  scopeAtStart?: SessionScope
): Promise<{
  access_token: string;
  expires_in: number;
}> {
  const scope = scopeAtStart ?? captureSessionScope();
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
    if (!sessionScopeMatches(scope)) {
      return { access_token: "", expires_in: 0 };
    }
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
