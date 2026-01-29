/**
 * 认证模块：对接服务端 JWT 认证体系
 * - POST /api/auth/login：用户名密码登录，返回 access_token，refresh_token 通过 HttpOnly Cookie 下发
 * - POST /api/auth/refresh：用 Cookie 中的 refresh_token 换取新 access_token
 * - POST /api/auth/logout：登出并清除服务端 Cookie
 */

const KEY_ACCESS_TOKEN = "access_token";

export interface LoginResponse {
  code: number;
  msg: string;
  access_token: string;
  expires_in: number;
  user?: { id: number; name: string; icon?: string; admin?: number };
}

export function getAccessToken(): string | null {
  return localStorage.getItem(KEY_ACCESS_TOKEN);
}

export function setAccessToken(token: string | null): void {
  if (!token) {
    localStorage.removeItem(KEY_ACCESS_TOKEN);
    return;
  }
  localStorage.setItem(KEY_ACCESS_TOKEN, token);
}

/**
 * 登录。需在 getApiUrl() 已初始化的环境下调用，且请求会通过 apiClient 发出（withCredentials + 后续可带 token）。
 */
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
    setAccessToken(data.access_token);
  }
  return data;
}

/**
 * 刷新 access_token（依赖 Cookie 中的 refresh_token，需 withCredentials）。
 */
export async function refreshToken(baseUrl: string): Promise<{
  access_token: string;
  expires_in: number;
}> {
  const axios = (await import("axios")).default;
  const url = baseUrl.replace(/\/$/, "") + "/auth/refresh";
  const token = getAccessToken();
  const resp = await axios.post(
    url,
    {},
    {
      withCredentials: true,
      timeout: 10000,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    }
  );
  const data = resp.data as { code?: number; access_token?: string; expires_in?: number };
  if (data?.access_token) {
    setAccessToken(data.access_token);
  }
  return {
    access_token: data?.access_token ?? "",
    expires_in: data?.expires_in ?? 0,
  };
}

/**
 * 登出：清除服务端 Cookie 并清除本地 access_token。
 */
export async function logout(baseUrl: string): Promise<void> {
  const axios = (await import("axios")).default;
  const url = baseUrl.replace(/\/$/, "") + "/auth/logout";
  try {
    await axios.post(url, {}, { withCredentials: true, timeout: 5000 });
  } finally {
    setAccessToken(null);
  }
}
