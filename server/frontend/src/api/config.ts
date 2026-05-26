/**
 * API 配置
 */
import axios, { type AxiosError, type AxiosRequestConfig, type AxiosResponse } from "axios";
import { logAndNoticeError } from "@/utils/error";
import { logger } from "@/utils/logger";
import { getAccessToken, getTokenExpiresAt, notifyAuthSessionExpired, refreshToken, setAccessToken } from "./api-auth";

// 与原版保持一致：支持远程和本地配置
const REMOTE = {
  url: "https://leo-zhao.natapp4.cc/",
  available: true,
};

// 本地 IP 地址
const LOCAL_IP = "192.168.50.171";
const LOCAL_HTTP_PORT = 8848; // HTTP 端口
const LOCAL_HTTPS_PORT = 8843; // HTTPS 端口

// 本地服务器 URL 配置
// ✅ 已配置 HTTPS，使用 8843 端口
const LOCAL_BASE_URL = `https://${LOCAL_IP}:${LOCAL_HTTPS_PORT}`;

// 如果需要切换回 HTTP，使用下面这行
// const LOCAL_BASE_URL = `http://${LOCAL_IP}:${LOCAL_HTTP_PORT}`;

type ServerMode = "local" | "remote";
type ServerStatusListener = (isLocal: boolean, changed: boolean) => void;

// 本地连通性探测结果，null 表示尚未探测
let localIpAvailable: boolean | null = null;
// 当前实际使用的服务器
let activeServerMode: ServerMode = "remote";
// 复用进行中的探测，避免并发重复探测
let localIpCheckPromise: Promise<boolean> | null = null;
let serverMonitorTimer: ReturnType<typeof setTimeout> | null = null;
let serverMonitorRunning = false;
let consecutiveLocalProbeFailures = 0;
const serverStatusListeners = new Set<ServerStatusListener>();

const LOCAL_IP_CHECK_TIMEOUT = 500;
const SERVER_CHECK_BASE_INTERVAL_MS = 5000;
const SERVER_CHECK_MAX_INTERVAL_MS = 60000;

function isPageHttps(): boolean {
  return typeof window !== "undefined" && window.location.protocol === "https:";
}

function getCurrentLocalPort(): number {
  return isPageHttps() ? LOCAL_HTTPS_PORT : LOCAL_HTTP_PORT;
}

function getLocalServerOrigin(): string {
  const protocol = isPageHttps() ? "https" : "http";
  const port = getCurrentLocalPort();
  return `${protocol}://${LOCAL_IP}:${port}`;
}

function getRemoteServerOrigin(): string {
  return REMOTE.url || "http://localhost:8000";
}

function ensureApiSuffix(url: string): string {
  return url.endsWith("/api") ? url : url.endsWith("/") ? `${url}api` : `${url}/api`;
}

function markLocalProbeSuccess(): void {
  localIpAvailable = true;
  consecutiveLocalProbeFailures = 0;
}

function markLocalProbeFailure(): void {
  localIpAvailable = false;
  consecutiveLocalProbeFailures += 1;
}

function getNextServerCheckDelay(isLocalAvailable: boolean): number {
  if (isLocalAvailable) {
    return SERVER_CHECK_BASE_INTERVAL_MS;
  }

  return Math.min(
    SERVER_CHECK_BASE_INTERVAL_MS * 2 ** consecutiveLocalProbeFailures,
    SERVER_CHECK_MAX_INTERVAL_MS
  );
}

function emitServerStatus(isLocal: boolean, changed: boolean): void {
  serverStatusListeners.forEach(listener => listener(isLocal, changed));
}

function ensureTrailingSlash(url: string): string {
  return url.replace(/\/?$/, "/");
}

async function checkAddress(url: string, timeout = LOCAL_IP_CHECK_TIMEOUT): Promise<boolean> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    await fetch(ensureTrailingSlash(url), {
      method: "GET", // 改用 GET 方法，更可靠
      signal: controller.signal,
      cache: "no-store",
      mode: "no-cors", // 避免CORS问题
      credentials: "omit", // 不发送凭据，减少扩展拦截的可能性
      redirect: "follow", // 自动跟随重定向
    });
    // no-cors 模式下，只要请求未抛异常就认为服务可达
    return true;
  } catch (error) {
    if ((error as Error).name !== "AbortError") {
      logger.debug("[API Config] Failed to check address", {
        url,
        error: (error as Error).message,
      });
    }
    return false;
  } finally {
    clearTimeout(timeoutId);
  }
}

async function probeLocalServer(): Promise<boolean> {
  try {
    const isAvailable = await checkAddress(getLocalServerOrigin());
    if (isAvailable) {
      markLocalProbeSuccess();
      return true;
    }
  } catch {
    // 静默降级到失败分支，避免探测流程打断业务
  }

  markLocalProbeFailure();
  return false;
}

function applyServerMode(mode: ServerMode): void {
  const nextBaseUrl = ensureApiSuffix(mode === "local" ? getLocalServerOrigin() : getRemoteServerOrigin());
  const changed = activeServerMode !== mode || api.defaults.baseURL !== nextBaseUrl;

  activeServerMode = mode;
  api.defaults.baseURL = nextBaseUrl;

  if (mode === "local") {
    localIpAvailable = true;
  }

  if (changed) {
    logger.info(`[API Config] Switched to ${mode} server: ${nextBaseUrl}`);
  }
}

// 检测本地 IP 是否可用
export async function checkLocalIpAvailable(): Promise<boolean> {
  if (!localIpCheckPromise) {
    localIpCheckPromise = probeLocalServer();
  }

  try {
    return await localIpCheckPromise;
  } finally {
    localIpCheckPromise = null;
  }
}

export async function checkAndSwitchServer(): Promise<boolean> {
  const localAvailable = await checkLocalIpAvailable();
  applyServerMode(localAvailable ? "local" : "remote");
  return localAvailable;
}

async function runServerMonitorCycle(): Promise<void> {
  const previousMode = activeServerMode;
  const isLocal = await checkAndSwitchServer();
  const nextDelay = getNextServerCheckDelay(isLocal);

  if (!serverMonitorRunning) {
    return;
  }

  emitServerStatus(isLocal, previousMode !== activeServerMode);
  serverMonitorTimer = setTimeout(() => {
    void runServerMonitorCycle();
  }, nextDelay);
}

export async function startServerMonitor(): Promise<void> {
  if (serverMonitorRunning) {
    return;
  }

  serverMonitorRunning = true;
  logger.info(
    `[Server Monitor] Started, base ${SERVER_CHECK_BASE_INTERVAL_MS / 1000}s, max ${SERVER_CHECK_MAX_INTERVAL_MS / 1000}s`
  );
  await runServerMonitorCycle();
}

export function stopServerMonitor(): void {
  serverMonitorRunning = false;
  if (serverMonitorTimer) {
    clearTimeout(serverMonitorTimer);
    serverMonitorTimer = null;
  }
  logger.info("[Server Monitor] Stopped");
}

export function subscribeServerStatus(listener: ServerStatusListener): () => void {
  serverStatusListeners.add(listener);
  return () => {
    serverStatusListeners.delete(listener);
  };
}

// 切换到本地服务器
export function switchToLocal(): void {
  applyServerMode("local");
}

// 切换到远程服务器
export function switchToRemote(): void {
  applyServerMode("remote");
}

// 初始化 BASE_URL：优先使用环境变量，否则默认使用远程
let BASE_URL: string;

if (import.meta.env.VITE_API_BASE_URL) {
  // 如果有环境变量配置，优先使用环境变量
  BASE_URL = import.meta.env.VITE_API_BASE_URL;
  logger.info(`[API Config] Using base URL from environment: ${BASE_URL}`);
} else {
  // 默认使用远程服务器
  BASE_URL = getRemoteServerOrigin();
  logger.info(`[API Config] Initial base URL (remote): ${BASE_URL}`);
}

// 确保 baseURL 以 /api 结尾
const API_BASE_URL = ensureApiSuffix(BASE_URL);

/**
 * 获取当前实际使用的 API URL（不含 /api 后缀）
 * 会根据本地 IP 可用性返回正确的地址
 */
export function getApiUrl(): string {
  // 从 axios 实例获取最新的 baseURL，去掉 /api 后缀
  const currentBaseUrl = api.defaults.baseURL || BASE_URL;
  return currentBaseUrl.replace(/\/api$/, "");
}

/**
 * 获取完整的基础 URL（用于文件下载等场景）
 * 优先使用本地 IP（如果可用），否则使用远程 URL
 */
export function getBaseUrl(): string {
  return getApiUrl();
}

/**
 * 返回当前是否正在使用本地服务器
 */
export function isLocalIpAvailable(): boolean | null {
  return activeServerMode === "local";
}

export {
  API_BASE_URL,
  BASE_URL as REMOTE_BASE_URL,
  REMOTE,
  LOCAL_IP,
  getCurrentLocalPort,
  LOCAL_HTTP_PORT,
  LOCAL_HTTPS_PORT,
  LOCAL_BASE_URL,
};

// 创建 axios 实例，baseURL 已包含 /api 前缀
export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  withCredentials: true, // IMPORTANT: cross-origin refresh cookie
});

// Ensure we only run one refresh flow at a time
let isRefreshing = false;
let refreshWaiters: Array<(token: string | null) => void> = [];

function notifyRefreshWaiters(token: string | null) {
  refreshWaiters.forEach(cb => cb(token));
  refreshWaiters = [];
}

async function ensureRefreshed(): Promise<string | null> {
  if (isRefreshing) {
    return new Promise(resolve => {
      refreshWaiters.push(resolve);
    });
  }

  isRefreshing = true;
  try {
    const data = await refreshToken();
    const token = data?.access_token || getAccessToken();
    notifyRefreshWaiters(token);
    return token;
  } catch (e) {
    const status = (e as AxiosError).response?.status;
    if (status === 401) {
      setAccessToken(null);
      // 跳转登录由 /auth/refresh 401 的响应拦截分支统一 notify，避免与 ensure 重复
    }
    notifyRefreshWaiters(null);
    throw e;
  } finally {
    isRefreshing = false;
  }
}

// token 即将过期时提前续期的缓冲时间（秒），1 小时
const TOKEN_REFRESH_BUFFER_SEC = 3600;

// 请求拦截器：每次请求都从 localStorage 读取 token 并写入 headers，兼容网站端
// 若 token 即将过期则主动续期，实现“有请求就自动续期”
api.interceptors.request.use(
  async cfg => {
    // 跳过 auth 相关接口，避免循环
    const url = String(cfg.url || "");
    if (url.includes("/auth/login") || url.includes("/auth/refresh")) {
      const token = getAccessToken();
      const value = token ? `Bearer ${token}` : "";
      (api.defaults.headers.common as Record<string, string>)["Authorization"] = value;
      cfg.headers = { ...(cfg.headers || {}), Authorization: value } as typeof cfg.headers;
      return cfg;
    }

    const token = getAccessToken();
    const expiresAt = getTokenExpiresAt();
    const now = Date.now();
    const needRefresh = token && expiresAt && expiresAt - now < TOKEN_REFRESH_BUFFER_SEC * 1000;
    if (needRefresh) {
      try {
        await ensureRefreshed();
      } catch {
        // 续期失败时 ensureRefreshed 会清空 token，需保留原 token 继续请求，401 时由响应拦截器处理
      }
    }

    // 优先用最新 token，续期失败时 ensureRefreshed 会清空，此时用续期前的 token 兜底
    const finalToken = getAccessToken() || token;
    const value = finalToken ? `Bearer ${finalToken}` : "";
    // 同步到 axios 默认头，确保网站端请求也能带上（部分环境 per-request 合并异常）
    (api.defaults.headers.common as Record<string, string>)["Authorization"] = value;
    // 合并到当前请求 headers，不覆盖已有项
    const prev = (cfg.headers || {}) as Record<string, unknown>;
    cfg.headers = { ...prev, Authorization: value } as typeof cfg.headers;

    logger.debug(
      "[API Request]",
      cfg.method?.toUpperCase(),
      cfg.baseURL,
      cfg.url,
      cfg.params || cfg.data
    );
    return cfg;
  },
  error => {
    logger.error("API Request Error:", error);
    return Promise.reject(error);
  }
);

// 响应拦截器 - 统一处理错误 + 401 自动 refresh 重试
api.interceptors.response.use(
  (response: AxiosResponse) => {
    if (response.data && typeof response.data === "object" && "code" in response.data) {
      const rawCode = (response.data as { code: unknown }).code;
      const normalizedCode =
        typeof rawCode === "string" && rawCode.trim() !== "" && !Number.isNaN(Number(rawCode.trim()))
          ? Number(rawCode.trim())
          : rawCode;
      const isSuccessCode = normalizedCode === 0;

      // 兼容部分后端/代理把数值 code 序列化成字符串的情况。
      (response.data as { code: unknown }).code = normalizedCode;

      if (!isSuccessCode) {
        const error = new Error(response.data.msg || "请求失败") as AxiosError;
        error.response = response;
        return Promise.reject(error);
      }
    }
    return response;
  },
  async (error: AxiosError) => {
    const cfg = error.config as
      | (AxiosRequestConfig & { _retry?: boolean; _isFileUpload?: boolean })
      | undefined;

    // Ignore cancels
    if (
      error.code === "ECONNABORTED" ||
      error.message?.includes("canceled") ||
      error.message?.includes("aborted")
    ) {
      return Promise.reject(error);
    }

    // Do not retry uploads
    const isFileUpload =
      (cfg as any)?._isFileUpload === true ||
      cfg?.data instanceof FormData ||
      (typeof (cfg?.headers as any)?.["Content-Type"] === "string" &&
        String((cfg?.headers as any)?.["Content-Type"]).includes("multipart/form-data")) ||
      String(cfg?.url || "").includes("/pdf/upload") ||
      String(cfg?.url || "").includes("/upload");

    if (isFileUpload) {
      logger.warn(`File upload failed, not retrying to avoid re-upload: ${cfg?.url}`, {
        code: error.code,
        message: error.message,
        status: error.response?.status,
      });
      return Promise.reject(error);
    }

    const urlStr = String(cfg?.url || "");
    if (urlStr.includes("/auth/refresh") && error.response?.status === 401) {
      setAccessToken(null);
      notifyAuthSessionExpired();
      return Promise.reject(error);
    }

    // 401 或 422（token 签名验证失败）-> 尝试 refresh 重试一次
    const isRefreshRequest = urlStr.includes("/auth/refresh");
    const isTokenError =
      !isRefreshRequest &&
      (error.response?.status === 401 ||
        (error.response?.status === 422 &&
          /signature|token|invalid/i.test(
            String((error.response?.data as { msg?: string })?.msg || error.message || "")
          )));
    if (isTokenError && cfg && !cfg._retry) {
      cfg._retry = true;
      // 不要在此 setAccessToken(null)，否则会清空 refresh_token，续期必败
      try {
        const newToken = await ensureRefreshed();
        if (newToken) {
          cfg.headers = cfg.headers || {};
          (cfg.headers as any)["Authorization"] = `Bearer ${newToken}`;
        }
        return api.request(cfg);
      } catch (e) {
        if ((e as AxiosError)?.response?.status === 401) {
          return Promise.reject(error);
        }
      }
    }

    // Existing error handling
    if (error.response) {
      const status = error.response.status;
      const data = error.response.data as { msg?: string } | undefined;
      const errorMessage = data?.msg || `请求失败 (${status})`;

      if (status >= 500) {
        logAndNoticeError(error, "服务器错误", { context: "API" });
      } else if (status === 404) {
        logAndNoticeError(error, "资源未找到", { context: "API" });
      } else if (status === 403) {
        logAndNoticeError(error, "无权限访问", { context: "API" });
      } else if (
        status === 401 ||
        (status === 422 && /signature|token|invalid/i.test(errorMessage))
      ) {
        logAndNoticeError(error, "token无效，请重新登录", { context: "API" });
      } else {
        logAndNoticeError(error, errorMessage, { context: "API" });
      }
    } else if (error.request) {
      logAndNoticeError(error, "网络错误，请检查网络连接", { context: "API" });
    } else {
      logAndNoticeError(error, "请求配置错误", { context: "API" });
    }

    return Promise.reject(error);
  }
);
