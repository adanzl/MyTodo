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

// 从环境变量获取，如果没有则使用原版的默认值
const BASE_URL = import.meta.env.VITE_API_BASE_URL || REMOTE.url || "http://localhost:8000";

// 确保 baseURL 以 /api 结尾
const API_BASE_URL = BASE_URL.endsWith("/api")
  ? BASE_URL
  : BASE_URL.endsWith("/")
    ? `${BASE_URL}api`
    : `${BASE_URL}/api`;

export function getApiUrl(): string {
  return BASE_URL;
}

export { API_BASE_URL, BASE_URL as REMOTE_BASE_URL, REMOTE };

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
      "API Request:",
      config.method?.toUpperCase(),
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
