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
