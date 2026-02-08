import EventBus, { C_EVENT } from "@/types/EventBus";
import { clearLoginCache, getAccessToken, getTokenExpiresAt, refreshToken } from "@/utils/Auth";
import axios, { type AxiosRequestConfig, type InternalAxiosRequestConfig } from "axios";

const REMOTE_URL = "https://leo-zhao.natapp4.cc/api";
const LOCAL_IP = "192.168.50.171";
const LOCAL_PORTS = { http: 8848, https: 8843 };
let API_URL = "";
let localIpAvailable: boolean | null = null;

export const apiClient = axios.create({
  timeout: 30000,
  withCredentials: true,
});

// token 即将过期时提前续期的缓冲时间（秒），1 小时
const TOKEN_REFRESH_BUFFER_SEC = 3600;

// 请求拦截器：每次请求都从 localStorage 读取 token 并写入 headers
// 若 token 即将过期则主动续期，实现「有请求就自动续期」
apiClient.interceptors.request.use(
  async (cfg: InternalAxiosRequestConfig) => {
    // 跳过 auth 相关接口，避免循环
    const url = String(cfg.url || "");
    if (url.includes("/auth/login") || url.includes("/auth/refresh")) {
      const token = getAccessToken();
      if (token) {
        (cfg.headers = cfg.headers ?? ({} as typeof cfg.headers))["Authorization"] = `Bearer ${token}`;
      }
      return cfg;
    }

    const token = getAccessToken();
    const expiresAt = getTokenExpiresAt();
    const now = Date.now();
    const needRefresh =
      token &&
      expiresAt &&
      expiresAt - now < TOKEN_REFRESH_BUFFER_SEC * 1000;
    if (needRefresh) {
      try {
        await ensureRefreshed();
      } catch {
        // 续期失败，继续使用当前 token，401 时由响应拦截器处理
      }
    }

    const finalToken = getAccessToken();
    if (finalToken) {
      (cfg.headers = cfg.headers ?? ({} as typeof cfg.headers))["Authorization"] = `Bearer ${finalToken}`;
    }
    return cfg;
  },
  (err) => Promise.reject(err)
);

let isRefreshing = false;
let refreshWaiters: Array<(token: string | null) => void> = [];
let proactiveRefreshTimer: ReturnType<typeof setTimeout> | null = null;

/** 提前刷新缓冲时间（秒），在 token 过期前多久触发 proactive refresh */
const REFRESH_BUFFER_SEC = 300;

function clearProactiveRefreshTimer(): void {
  if (proactiveRefreshTimer != null) {
    clearTimeout(proactiveRefreshTimer);
    proactiveRefreshTimer = null;
  }
}

/**
 * 根据 expires_in 安排 proactive refresh，在 token 过期前刷新。
 * 刷新时机：取「80% 过期时间」与「过期前 5 分钟」中较早者。
 */
export function scheduleProactiveRefresh(expiresInSeconds: number): void {
  clearProactiveRefreshTimer();
  if (expiresInSeconds <= 0) return;
  const delayMs =
    Math.min(expiresInSeconds * 0.8, Math.max(0, expiresInSeconds - REFRESH_BUFFER_SEC)) * 1000;
  proactiveRefreshTimer = setTimeout(async () => {
    proactiveRefreshTimer = null;
    try {
      const data = await refreshToken(API_URL);
      if (data?.access_token) {
        scheduleProactiveRefresh(data.expires_in);
      }
    } catch {
      // 静默失败，下次请求 401 时会走 ensureRefreshed
    }
  }, delayMs);
}

EventBus.$on(C_EVENT.LOGIN_CACHE_CLEARED, clearProactiveRefreshTimer);

async function ensureRefreshed(): Promise<string | null> {
  if (isRefreshing) {
    return new Promise((resolve) => {
      refreshWaiters.push(resolve);
    });
  }
  isRefreshing = true;
  try {
    const data = await refreshToken(API_URL);
    const token = data?.access_token || getAccessToken();
    refreshWaiters.forEach((cb) => cb(token));
    refreshWaiters = [];
    if (data?.expires_in) scheduleProactiveRefresh(data.expires_in);
    return token;
  } catch (e: any) {
    clearProactiveRefreshTimer();
    if (e?.response?.status === 401) {
      clearLoginCache();
    }
    refreshWaiters.forEach((cb) => cb(null));
    refreshWaiters = [];
    throw e;
  } finally {
    isRefreshing = false;
  }
}

apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    const cfg = error.config as (AxiosRequestConfig & { _retry?: boolean }) | undefined;
    if (error.response?.status === 401 && cfg && !cfg._retry) {
      cfg._retry = true;
      try {
        const newToken = await ensureRefreshed();
        if (newToken) {
          (cfg.headers = cfg.headers ?? ({} as typeof cfg.headers))["Authorization"] = `Bearer ${newToken}`;
        }
        return apiClient.request(cfg);
      } catch (refreshErr: any) {
        const status = refreshErr?.response?.status;
        if (status === 401) {
          clearLoginCache();
          EventBus.$emit(C_EVENT.AUTH_EXPIRED);
        }
      }
    }
    return Promise.reject(error);
  }
);

export function getApiUrl() {
  return API_URL;
}

async function checkAddress(url: string, timeout = 500): Promise<boolean> {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), timeout);
    const res = await fetch(url.replace(/\/?$/, "/"), {
      method: "HEAD",
      signal: ctrl.signal,
      cache: "no-store",
    });
    clearTimeout(t);
    return res.ok;
  } catch {
    return false;
  }
}

/** 本地服务器根 URL（与 server/frontend 一致，用于可用性检测） */
function getLocalRootUrl(): string {
  const https = typeof window !== "undefined" && window.location.protocol === "https:";
  const port = LOCAL_PORTS[https ? "https" : "http"];
  return `http${https ? "s" : ""}://${LOCAL_IP}:${port}/`;
}

function getLocalApiUrl(): string {
  return getLocalRootUrl().replace(/\/$/, "") + "/api";
}

/** 本地可用性检测：HEAD 请求根路径。Ionic/Capacitor 下 origin 为 capacitor://localhost 或 ionic://localhost，服务端 CORS_ORIGINS 需包含二者 */
export async function checkLocalAddressAvailable(): Promise<boolean> {
  if (window.location.protocol === "https:") return false;
  return checkAddress(getLocalRootUrl());
}

function setBaseUrl(url: string): void {
  API_URL = url;
  apiClient.defaults.baseURL = url;
}

export function switchToLocal(): void {
  if (localIpAvailable === true) return;
  localIpAvailable = true;
  setBaseUrl(getLocalApiUrl());
  EventBus.$emit(C_EVENT.SERVER_SWITCH, false);
}

export function switchToRemote(): void {
  if (localIpAvailable === false) return;
  localIpAvailable = false;
  setBaseUrl(REMOTE_URL);
  EventBus.$emit(C_EVENT.SERVER_SWITCH, true);
}

export async function checkAndSwitchServer(): Promise<void> {
  const ok = await checkLocalAddressAvailable();
  if (ok && localIpAvailable !== true) switchToLocal();
  else if (!ok && localIpAvailable !== false) switchToRemote();
}

export function isLocalIpAvailable(): boolean | null {
  return localIpAvailable;
}

export function initNet(): void {
  localIpAvailable = null;
  setBaseUrl(REMOTE_URL);
  EventBus.$emit(C_EVENT.SERVER_SWITCH, true);
  checkAndSwitchServer();
}
