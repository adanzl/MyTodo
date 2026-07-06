/**
 * 浏览器配置相关 API
 */
import { api } from "./config";
import type { ApiResponse } from "@/types/api";

export interface BrowserAppConfig {
  version: string;
  url: string;
}

export interface BrowserWhitelistConfig {
  open: string;
  urls: string[];
}

export interface BrowserAdminConfig {
  pin: string;
}

export interface BrowserConfig {
  version: string;
  timestamp: string;
  publishTime: string;
  env: string;
  app: BrowserAppConfig;
  admin: BrowserAdminConfig;
  whitelist: BrowserWhitelistConfig;
}

/** 获取浏览器配置 */
export async function getBrowserConfig(): Promise<BrowserConfig> {
  const rsp = await api.get<ApiResponse<BrowserConfig>>("/browser/config");
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

/** 更新浏览器配置 */
export async function setBrowserConfig(data: Partial<BrowserConfig>): Promise<BrowserConfig> {
  const rsp = await api.post<ApiResponse<BrowserConfig>>("/browser/config/set", data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

/** 发布版本（自动递增 patch） */
export async function publishBrowserVersion(): Promise<{ version: string }> {
  const rsp = await api.post<ApiResponse<{ version: string }>>("/browser/publish");
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}
