import EventBus, { C_EVENT } from "@/types/event-bus";
import {
  captureSessionScope,
  clearLoginCache,
  getAccessToken,
  getTokenExpiresAt,
  refreshToken,
  sessionScopeMatches,
  type SessionScope,
} from "@/utils/auth-util";
import axios, { type InternalAxiosRequestConfig } from "axios";

declare module "axios" {
  export interface InternalAxiosRequestConfig {
    /** 请求发出时会话快照，401 重试前必须仍匹配。 */
    lxSessionScope?: SessionScope;
    _retry?: boolean;
  }
}

const REMOTE_URL = "https://leo-zhao.natapp4.cc/api";
const LOCAL_IP = "192.168.50.172";
const LOCAL_PORTS = { http: 8848, https: 8843 };
let API_URL = "";
let localIpAvailable: boolean | null = null;

export const apiClient = axios.create({
  timeout: 30000,
  withCredentials: true,
});

const TOKEN_REFRESH_BUFFER_SEC = 6 * 3600;

/** 请求绑定的会话已切换（含等待续期期间换账号），应取消发送。 */
export class SessionChangedError extends Error {
  constructor(message = "会话已切换，已取消该请求") {
    super(message);
    this.name = "SessionChangedError";
  }
}

function assertSessionUnchanged(scope: SessionScope): void {
  if (!sessionScopeMatches(scope)) {
    throw new SessionChangedError();
  }
}

/**
 * 进入拦截器即绑定会话快照；重试不得覆盖。
 * 等待续期后再次核对，避免 A 的操作在换到 B 后仍携带 B 的凭证发出。
 */
function bindRequestSession(cfg: InternalAxiosRequestConfig): SessionScope {
  if (!cfg.lxSessionScope) {
    cfg.lxSessionScope = captureSessionScope();
  }
  return cfg.lxSessionScope;
}

apiClient.interceptors.request.use(
  async (cfg: InternalAxiosRequestConfig) => {
    const url = String(cfg.url || "");
    if (url.includes("/auth/login") || url.includes("/auth/refresh")) {
      const token = getAccessToken();
      if (token) {
        (cfg.headers = cfg.headers ?? ({} as typeof cfg.headers))["Authorization"] = `Bearer ${token}`;
      }
      return cfg;
    }

    const requestScope = bindRequestSession(cfg);
    assertSessionUnchanged(requestScope);

    const token = getAccessToken();
    const expiresAt = getTokenExpiresAt();
    const now = Date.now();
    const needRefresh =
      token &&
      expiresAt &&
      expiresAt - now < TOKEN_REFRESH_BUFFER_SEC * 1000;
    if (needRefresh) {
      try {
        await ensureRefreshed(requestScope);
      } catch {
        /* 续期失败仍带旧 access，由 401 重试 */
      }
    }

    assertSessionUnchanged(requestScope);

    const finalToken = getAccessToken();
    if (finalToken) {
      (cfg.headers = cfg.headers ?? ({} as typeof cfg.headers))["Authorization"] = `Bearer ${finalToken}`;
    }
    return cfg;
  },
  (err) => Promise.reject(err)
);

let isRefreshing = false;
/** 续期进行中的等待队列，按发起时的会话 scope 隔离。 */
let refreshWaiters: Array<{ scope: SessionScope; resolve: (token: string | null) => void }> = [];
let proactiveRefreshTimer: ReturnType<typeof setTimeout> | null = null;

const REFRESH_BUFFER_SEC = 300;

function clearProactiveRefreshTimer(): void {
  if (proactiveRefreshTimer != null) {
    clearTimeout(proactiveRefreshTimer);
    proactiveRefreshTimer = null;
  }
}

function resolveRefreshWaiters(token: string | null, refreshScope: SessionScope): void {
  const waiters = refreshWaiters;
  refreshWaiters = [];
  for (const w of waiters) {
    const ok = Boolean(token) && sessionScopeMatches(w.scope) && sessionScopeMatches(refreshScope);
    w.resolve(ok ? token : null);
  }
}

export function scheduleProactiveRefresh(expiresInSeconds: number): void {
  clearProactiveRefreshTimer();
  if (expiresInSeconds <= 0) return;
  const delayMs =
    Math.min(expiresInSeconds * 0.8, Math.max(0, expiresInSeconds - REFRESH_BUFFER_SEC)) * 1000;
  proactiveRefreshTimer = setTimeout(async () => {
    proactiveRefreshTimer = null;
    const scope = captureSessionScope();
    try {
      const data = await refreshToken(API_URL, scope);
      if (data?.access_token && sessionScopeMatches(scope)) {
        scheduleProactiveRefresh(data.expires_in);
      }
    } catch {
      /* 静默；下次有请求会预刷新 / 或 401 重试 */
    }
  }, delayMs);
}

EventBus.$on(C_EVENT.LOGIN_CACHE_CLEARED, clearProactiveRefreshTimer);

async function ensureRefreshed(callerScope?: SessionScope): Promise<string | null> {
  const myScope = callerScope ?? captureSessionScope();
  if (isRefreshing) {
    return new Promise((resolve) => {
      refreshWaiters.push({ scope: myScope, resolve });
    });
  }
  isRefreshing = true;
  const refreshScope = captureSessionScope();
  try {
    const data = await refreshToken(API_URL, refreshScope);
    const token =
      sessionScopeMatches(refreshScope) && data?.access_token
        ? data.access_token
        : getAccessToken();
    resolveRefreshWaiters(token, refreshScope);
    if (data?.expires_in && sessionScopeMatches(refreshScope)) {
      scheduleProactiveRefresh(data.expires_in);
    }
    return sessionScopeMatches(myScope) ? token : null;
  } catch (e: any) {
    if (e?.response?.status === 401 && sessionScopeMatches(refreshScope)) {
      clearProactiveRefreshTimer();
      clearLoginCache();
      EventBus.$emit(C_EVENT.AUTH_EXPIRED);
    }
    resolveRefreshWaiters(null, refreshScope);
    throw e;
  } finally {
    isRefreshing = false;
  }
}

apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    const cfg = error.config as InternalAxiosRequestConfig | undefined;
    if (error.response?.status === 401 && cfg && !cfg._retry) {
      const requestScope = cfg.lxSessionScope;
      if (requestScope && !sessionScopeMatches(requestScope)) {
        return Promise.reject(error);
      }
      cfg._retry = true;
      if (requestScope) {
        bindRequestSession(cfg);
      }
      try {
        const newToken = await ensureRefreshed(requestScope ?? captureSessionScope());
        if (requestScope && !sessionScopeMatches(requestScope)) {
          return Promise.reject(new SessionChangedError());
        }
        if (newToken) {
          (cfg.headers = cfg.headers ?? ({} as typeof cfg.headers))["Authorization"] = `Bearer ${newToken}`;
        } else if (requestScope) {
          return Promise.reject(error);
        }
        return apiClient.request(cfg);
      } catch {
        // 401 时已在 ensureRefreshed 中 clear + AUTH_EXPIRED（且 scope 仍匹配）
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
    // 使用 no-cors 模式进行简单的连通性检查，避免CORS预检请求
    await fetch(url.replace(/\/?$/, "/"), {
      method: "GET", // 改用 GET 方法，更可靠
      signal: ctrl.signal,
      cache: "no-store",
      mode: "no-cors", // 使用 no-cors 避免跨域问题
      // 添加额外的选项以减少浏览器扩展的干扰
      credentials: "omit", // 不发送凭据，减少扩展拦截的可能性
      redirect: "follow", // 自动跟随重定向
    });
    clearTimeout(t);
    // no-cors 模式下，只要能连接成功（不抛异常）就认为可达
    return true;
  } catch (error: any) {
    // 如果是超时错误，说明服务器不可达
    if (error.name === 'AbortError') {
      // 静默处理超时，避免频繁报错
    } else {
      // 仅在非超时错误时输出警告
      console.debug("[checkAddress] Failed to check address:", url, error.message);
    }
    return false;
  }
}

function getLocalRootUrl(): string {
  const https = typeof window !== "undefined" && window.location.protocol === "https:";
  const port = LOCAL_PORTS[https ? "https" : "http"];
  return `http${https ? "s" : ""}://${LOCAL_IP}:${port}/`;
}

function getLocalApiUrl(): string {
  return getLocalRootUrl().replace(/\/$/, "") + "/api";
}

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
  const localUrl = getLocalApiUrl();
  console.log("[API Client] Switching to local server:", localUrl);
  setBaseUrl(localUrl);
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
  if (ok && localIpAvailable !== true) {
    switchToLocal();
  } else if (!ok && localIpAvailable !== false) {
    switchToRemote();
  }
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
