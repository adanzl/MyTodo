/**
 * API 配置
 */
import axios, { type AxiosError, type AxiosRequestConfig, type AxiosResponse } from "axios";
import { logAndNoticeError } from "@/utils/error";
import { logger } from "@/utils/logger";
import { getAccessToken, refreshToken, setAccessToken } from "./auth";

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
    // 使用 LOCAL_BASE_URL，这样会自动使用正确的协议（http 或 https）
    const url = `${LOCAL_BASE_URL}/`;
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

  // 检测协议兼容性：如果页面是 HTTPS，本地服务器必须也是 HTTPS
  const isPageHttps = typeof window !== "undefined" && window.location.protocol === "https:";
  const isLocalHttps = LOCAL_BASE_URL.startsWith("https://");

  if (isPageHttps && !isLocalHttps) {
    logger.warn(
      `[API Config] ⚠️ Cannot switch to HTTP local server from HTTPS page. ` +
        `Mixed Content blocked. Please configure HTTPS for local server or use HTTP to access the page.`
    );
    console.warn(
      `🚫 无法切换到本地服务器！\n` +
        `原因：当前页面使用 HTTPS，但本地服务器是 HTTP\n` +
        `解决方案：\n` +
        `1. 为本地服务器配置 HTTPS (推荐)\n` +
        `2. 或通过 HTTP 访问前端页面\n` +
        `详见：/server/setup-local-https.md`
    );
    return; // 阻止切换
  }

  localIpAvailable = true;
  const newApiBaseUrl = `${LOCAL_BASE_URL}/api`;
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
    return LOCAL_BASE_URL;
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

// 请求拦截器
api.interceptors.request.use(
  cfg => {
    // attach access token
    const token = getAccessToken();
    if (token) {
      cfg.headers = cfg.headers || {};
      (cfg.headers as any)["Authorization"] = `Bearer ${token}`;
    }

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

    // 401 -> refresh -> retry once
    if (error.response?.status === 401 && cfg && !cfg._retry) {
      cfg._retry = true;
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
      } else if (status === 401) {
        logAndNoticeError(error, "未授权，请重新登录", { context: "API" });
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
