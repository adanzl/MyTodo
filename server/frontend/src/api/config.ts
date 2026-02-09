/**
 * API 配置
 */
import axios, { type AxiosError, type AxiosRequestConfig, type AxiosResponse } from "axios";
import { logAndNoticeError } from "@/utils/error";
import { logger } from "@/utils/logger";
import { getAccessToken, getTokenExpiresAt, refreshToken, setAccessToken } from "./auth";

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

// 全局变量：保存 IP 可用性检测结果
let localIpAvailable: boolean | null = null; // null 表示未检测，true/false 表示检测结果

// 检测本地 IP 是否可用
export async function checkLocalIpAvailable(): Promise<boolean> {
  try {
    // 根据当前页面的协议动态选择本地服务器的协议
    const isPageHttps = typeof window !== "undefined" && window.location.protocol === "https:";
    const protocol = isPageHttps ? "https" : "http";
    const port = isPageHttps ? LOCAL_HTTPS_PORT : LOCAL_HTTP_PORT;
    const url = `${protocol}://${LOCAL_IP}:${port}/`;
    
    const controller = new AbortController();
    const TIMEOUT = 500;
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT); // 500ms超时

    try {
      await fetch(url, {
        method: "HEAD", // 使用HEAD方法更轻量
        signal: controller.signal,
        mode: "no-cors", // 避免CORS问题
      });
      clearTimeout(timeoutId);
      return true;
    } catch (error: any) {
      clearTimeout(timeoutId);
      return false;
    }
  } catch (error) {
    return false;
  }
}

// 切换到本地服务器
export function switchToLocal(): void {
  if (localIpAvailable === true) return; // 已经是本地了

  // 根据当前页面的协议动态选择本地服务器的协议
  const isPageHttps = typeof window !== "undefined" && window.location.protocol === "https:";
  const protocol = isPageHttps ? "https" : "http";
  const port = isPageHttps ? LOCAL_HTTPS_PORT : LOCAL_HTTP_PORT;
  const localBaseUrl = `${protocol}://${LOCAL_IP}:${port}`;

  localIpAvailable = true;
  const newApiBaseUrl = `${localBaseUrl}/api`;
  api.defaults.baseURL = newApiBaseUrl;
  logger.info(`[API Config] Switched to local server: ${newApiBaseUrl}`);
}

// 切换到远程服务器
export function switchToRemote(): void {
  if (localIpAvailable === false) return; // 已经是远程了

  localIpAvailable = false;
  const remoteUrl = REMOTE.url || "http://localhost:8000";
  const newApiBaseUrl = remoteUrl.endsWith("/api")
    ? remoteUrl
    : remoteUrl.endsWith("/")
      ? `${remoteUrl}api`
      : `${remoteUrl}/api`;
  api.defaults.baseURL = newApiBaseUrl;
  logger.info(`[API Config] Switched to remote server: ${newApiBaseUrl}`);
}

// 初始化 BASE_URL：优先使用环境变量，否则默认使用远程
let BASE_URL: string;

if (import.meta.env.VITE_API_BASE_URL) {
  // 如果有环境变量配置，优先使用环境变量
  BASE_URL = import.meta.env.VITE_API_BASE_URL;
  logger.info(`[API Config] Using base URL from environment: ${BASE_URL}`);
} else {
  // 默认使用远程服务器
  BASE_URL = REMOTE.url || "http://localhost:8000";
  logger.info(`[API Config] Initial base URL (remote): ${BASE_URL}`);
}

// 确保 baseURL 以 /api 结尾
const API_BASE_URL = BASE_URL.endsWith("/api")
  ? BASE_URL
  : BASE_URL.endsWith("/")
    ? `${BASE_URL}api`
    : `${BASE_URL}/api`;

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
  if (localIpAvailable === true) {
    // 根据当前页面的协议动态选择本地服务器的协议
    const isPageHttps = typeof window !== "undefined" && window.location.protocol === "https:";
    const protocol = isPageHttps ? "https" : "http";
    const port = isPageHttps ? LOCAL_HTTPS_PORT : LOCAL_HTTP_PORT;
    return `${protocol}://${LOCAL_IP}:${port}`;
  } else if (localIpAvailable === false) {
    return REMOTE.url || "http://localhost:8000";
  } else {
    // 检测中，返回当前的 BASE_URL
    return getApiUrl();
  }
}

/**
 * 检查本地 IP 是否可用（供外部调用）
 */
export function isLocalIpAvailable(): boolean | null {
  return localIpAvailable;
}

// 导出当前使用的端口（用于显示）
const LOCAL_PORT = LOCAL_BASE_URL.startsWith("https://") ? LOCAL_HTTPS_PORT : LOCAL_HTTP_PORT;

export {
  API_BASE_URL,
  BASE_URL as REMOTE_BASE_URL,
  REMOTE,
  LOCAL_IP,
  LOCAL_PORT,
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
    setAccessToken(null);
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
    const needRefresh =
      token &&
      expiresAt &&
      expiresAt - now < TOKEN_REFRESH_BUFFER_SEC * 1000;
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
      if (response.data.code !== 0) {
        const error = new Error(response.data.msg || "请求失败") as AxiosError;
        error.response = response;
        return Promise.reject(error);
      }
    }
    return response;
  },
  async (error: AxiosError) => {
    const cfg = error.config as (AxiosRequestConfig & { _retry?: boolean; _isFileUpload?: boolean }) | undefined;

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

    // 401 或 422（token 签名验证失败）-> 清除旧 token、尝试 refresh、重试一次
    const isTokenError =
      error.response?.status === 401 ||
      (error.response?.status === 422 &&
        /signature|token|invalid/i.test(
          String((error.response?.data as { msg?: string })?.msg || error.message || "")
        ));
    if (isTokenError && cfg && !cfg._retry) {
      cfg._retry = true;
      setAccessToken(null); // 清除可能无效的 token
      try {
        const newToken = await ensureRefreshed();
        if (newToken) {
          cfg.headers = cfg.headers || {};
          (cfg.headers as any)["Authorization"] = `Bearer ${newToken}`;
        }
        return api.request(cfg);
      } catch (e) {
        // fallthrough to normal error handling
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
      } else if (status === 401 || (status === 422 && /signature|token|invalid/i.test(errorMessage))) {
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
