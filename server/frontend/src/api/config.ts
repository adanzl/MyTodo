/**
 * API 配置
 */
import axios, { type AxiosError, type AxiosResponse } from "axios";
import { logAndNoticeError } from "@/utils/error";
import { logger } from "@/utils/logger";

// 与原版保持一致：支持远程和本地配置
const REMOTE = {
  url: "https://leo-zhao.natapp4.cc/",
  available: true,
};

// 本地 IP 地址
const LOCAL_IP = "192.168.50.171";
const LOCAL_PORT = 8848;
const LOCAL_BASE_URL = `http://${LOCAL_IP}:${LOCAL_PORT}`;

// 全局变量：保存 IP 可用性检测结果
let localIpAvailable: boolean | null = null; // null 表示未检测，true/false 表示检测结果

// 检测本地 IP 是否可用
export async function checkLocalIpAvailable(): Promise<boolean> {
  try {
    const url = `http://${LOCAL_IP}:${LOCAL_PORT}/`;
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

export { API_BASE_URL, BASE_URL as REMOTE_BASE_URL, REMOTE, LOCAL_IP, LOCAL_PORT, LOCAL_BASE_URL };

// 创建 axios 实例，baseURL 已包含 /api 前缀
export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 可以在这里添加请求头、token 等
    logger.debug(
      "[API Request]",
      config.method?.toUpperCase(),
      config.baseURL,
      config.url,
      config.params || config.data
    );
    return config;
  },
  error => {
    logger.error("API Request Error:", error);
    return Promise.reject(error);
  }
);

// 响应拦截器 - 统一处理错误
api.interceptors.response.use(
  (response: AxiosResponse) => {
    // 检查业务错误码
    if (response.data && typeof response.data === "object" && "code" in response.data) {
      if (response.data.code !== 0) {
        // 业务错误，抛出错误让调用方处理
        const error = new Error(response.data.msg || "请求失败") as AxiosError;
        error.response = response;
        return Promise.reject(error);
      }
    }
    return response;
  },
  (error: AxiosError) => {
    // 检查是否是取消的请求，如果是则不处理
    if (
      error.code === "ECONNABORTED" ||
      error.message?.includes("canceled") ||
      error.message?.includes("aborted")
    ) {
      // 请求已被取消，直接返回，不进行任何重试
      return Promise.reject(error);
    }

    // 检查是否是文件上传请求 - 必须在最前面检查，避免任何重试逻辑
    const isFileUpload =
      (error.config as any)?._isFileUpload === true ||
      error.config?.data instanceof FormData ||
      (typeof error.config?.headers?.["Content-Type"] === "string" &&
        error.config.headers["Content-Type"].includes("multipart/form-data")) ||
      error.config?.url?.includes("/pdf/upload") ||
      error.config?.url?.includes("/upload");

    // 如果是文件上传请求，无论什么错误都不重试，直接拒绝
    if (isFileUpload) {
      logger.warn(`File upload failed, not retrying to avoid re-upload: ${error.config?.url}`, {
        code: error.code,
        message: error.message,
        status: error.response?.status,
      });
      // 直接拒绝，不进行任何后续处理
      return Promise.reject(error);
    }

    // 网络错误、超时等
    if (error.response) {
      // 服务器返回了错误状态码
      const status = error.response.status;
      const data = error.response.data as { msg?: string } | undefined;
      const errorMessage = data?.msg || `请求失败 (${status})`;

      // 根据状态码处理不同的错误
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
      // 请求已发出但没有收到响应
      logAndNoticeError(error, "网络错误，请检查网络连接", { context: "API" });
    } else {
      // 请求配置错误
      logAndNoticeError(error, "请求配置错误", { context: "API" });
    }

    return Promise.reject(error);
  }
);
