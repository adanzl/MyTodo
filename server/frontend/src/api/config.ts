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
let checkPromise: Promise<boolean> | null = null; // 保存检测的Promise，避免重复检测
let initializationComplete = false; // 初始化是否完成

// 检测本地 IP 是否可用（只检测一次）
async function checkLocalIpAvailable(): Promise<boolean> {
  // 如果已经检测过，直接返回结果
  if (localIpAvailable !== null) {
    return localIpAvailable;
  }

  // 如果正在检测中，返回同一个 Promise
  if (checkPromise) {
    return checkPromise;
  }

  // 开始检测
  checkPromise = (async () => {
    try {
      // 检测根路径，任何响应（包括404、500等）都说明服务器在运行
      const url = `http://${LOCAL_IP}:${LOCAL_PORT}/`;
      const controller = new AbortController();
      const TIMEOUT = 200;
      const timeoutId = setTimeout(() => controller.abort(), TIMEOUT); // 500ms超时

      try {
        await fetch(url, {
          method: "HEAD", // 使用HEAD方法更轻量
          signal: controller.signal,
          mode: "no-cors", // 避免CORS问题
        });
        clearTimeout(timeoutId);
        // 只要能收到响应就说明服务器可用（no-cors模式下response.ok可能为false）
        localIpAvailable = true;
        logger.info(`[API Config] Local IP ${LOCAL_IP}:${LOCAL_PORT} is available`);
        return true;
      } catch (error: any) {
        clearTimeout(timeoutId);
        // 如果是abort错误说明超时，其他错误说明连接失败
        localIpAvailable = false;
        if (error.name === "AbortError") {
          logger.info(`[API Config] Local IP ${LOCAL_IP}:${LOCAL_PORT} timeout: ${TIMEOUT}ms`);
        } else {
          logger.info(
            `[API Config] Local IP ${LOCAL_IP}:${LOCAL_PORT} is not available:`,
            error.message
          );
        }
        return false;
      }
    } catch (error) {
      localIpAvailable = false;
      logger.warn(`[API Config] Failed to check local IP availability:`, error);
      return false;
    }
  })();

  return checkPromise;
}

// 初始化 BASE_URL：优先使用环境变量，否则先尝试本地IP
let BASE_URL: string;

if (import.meta.env.VITE_API_BASE_URL) {
  // 如果有环境变量配置，优先使用环境变量
  BASE_URL = import.meta.env.VITE_API_BASE_URL;
  logger.info(`[API Config] Using base URL from environment: ${BASE_URL}`);
  initializationComplete = true;
} else {
  // 默认先尝试使用本地IP
  BASE_URL = LOCAL_BASE_URL;
  logger.info(`[API Config] Initial base URL (local IP): ${BASE_URL}`);

  // 异步检测本地 IP 是否可用
  checkLocalIpAvailable()
    .then(available => {
      if (!available) {
        // IP 不可用，切换到远程 URL
        BASE_URL = REMOTE.url || "http://localhost:8000";
        const newApiBaseUrl = BASE_URL.endsWith("/api")
          ? BASE_URL
          : BASE_URL.endsWith("/")
            ? `${BASE_URL}api`
            : `${BASE_URL}/api`;
        api.defaults.baseURL = newApiBaseUrl;
        logger.info(`[API Config] Local IP not available, switched to remote: ${newApiBaseUrl}`);
      } else {
        logger.info(`[API Config] Local IP available, using: ${LOCAL_BASE_URL}`);
      }
      initializationComplete = true;
    })
    .catch(error => {
      // 检测失败，切换到远程 URL
      logger.error(`[API Config] Error checking local IP:`, error);
      BASE_URL = REMOTE.url || "http://localhost:8000";
      const newApiBaseUrl = BASE_URL.endsWith("/api")
        ? BASE_URL
        : BASE_URL.endsWith("/")
          ? `${BASE_URL}api`
          : `${BASE_URL}/api`;
      api.defaults.baseURL = newApiBaseUrl;
      logger.info(`[API Config] Fallback to remote: ${newApiBaseUrl}`);
      initializationComplete = true;
    });
}

// 确保 baseURL 以 /api 结尾
const API_BASE_URL = BASE_URL.endsWith("/api")
  ? BASE_URL
  : BASE_URL.endsWith("/")
    ? `${BASE_URL}api`
    : `${BASE_URL}/api`;

export function getApiUrl(): string {
  // 从 axios 实例获取最新的 baseURL，去掉 /api 后缀
  const currentBaseUrl = api.defaults.baseURL || BASE_URL;
  return currentBaseUrl.replace(/\/api$/, "");
}

export { API_BASE_URL, BASE_URL as REMOTE_BASE_URL, REMOTE };

// 创建 axios 实例，baseURL 已包含 /api 前缀
export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// 请求拦截器
api.interceptors.request.use(
  async config => {
    // 如果初始化未完成，等待初始化完成
    if (!initializationComplete) {
      logger.debug("[API Config] Waiting for initialization to complete...");
      if (!import.meta.env.VITE_API_BASE_URL) {
        await checkLocalIpAvailable();
      }
      // 等待一小会确保baseURL已更新
      await new Promise(resolve => setTimeout(resolve, 50));
    }

    // 确保使用最新的 baseURL（如果已经被更新）
    if (api.defaults.baseURL && config.baseURL !== api.defaults.baseURL) {
      config.baseURL = api.defaults.baseURL;
      logger.debug(`[API Config] Updated request baseURL to: ${config.baseURL}`);
    }

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

    // 如果使用本地 IP 且请求失败，标记为不可用并切换到远程 URL
    if (!import.meta.env.VITE_API_BASE_URL) {
      // 检查当前是否使用本地IP（通过 baseURL 判断）
      const currentBaseUrl = api.defaults.baseURL || "";
      const isUsingLocalIp = currentBaseUrl.includes(LOCAL_IP);

      logger.debug(
        `[API Error] localIpAvailable: ${localIpAvailable}, isUsingLocalIp: ${isUsingLocalIp}, currentBaseUrl: ${currentBaseUrl}`
      );

      if (isUsingLocalIp && error.request && !error.response) {
        // 网络错误，标记本地 IP 为不可用
        logger.warn(
          `[API Config] Network error with local IP, switching to remote URL. Error: ${error.message}`
        );
        localIpAvailable = false;
        BASE_URL = REMOTE.url || "http://localhost:8000";
        const newApiBaseUrl = BASE_URL.endsWith("/api")
          ? BASE_URL
          : BASE_URL.endsWith("/")
            ? `${BASE_URL}api`
            : `${BASE_URL}/api`;
        api.defaults.baseURL = newApiBaseUrl;
        logger.info(`[API Config] Switched to remote URL: ${newApiBaseUrl}`);

        // 重试当前请求（非文件上传请求）
        if (error.config) {
          // 确保使用新的 baseURL
          error.config.baseURL = newApiBaseUrl;
          logger.info(
            `[API Config] Retrying request with new baseURL: ${error.config.method?.toUpperCase()} ${newApiBaseUrl}${error.config.url}`
          );
          return api.request(error.config);
        }
      }
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
