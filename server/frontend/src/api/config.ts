/**
 * API 配置
 */
import axios from "axios";

// 与原版保持一致：支持远程和本地配置
const REMOTE = {
  url: "https://leo-zhao.natapp4.cc/",
  available: true,
};

// 从环境变量获取，如果没有则使用原版的默认值
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || REMOTE.url || "http://localhost:8000";

export function getApiUrl(): string {
  return API_BASE_URL;
}

export { API_BASE_URL, REMOTE };

// 创建 axios 实例
export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});
