import EventBus, { C_EVENT } from "@/types/EventBus";
import { clearLoginCache, getAccessToken, refreshToken } from "@/utils/Auth";
import axios, { type AxiosRequestConfig, type InternalAxiosRequestConfig } from "axios";

const REMOTE = { url: "https://leo-zhao.natapp4.cc/api", available: false };
const LOCAL = { url: "http://192.168.50.171:8848/api", available: false };
let API_URL = "";
/** 本地地址是否可用：null=未检测，true=使用本地，false=使用远程 */
let localIpAvailable: boolean | null = null;

export const apiClient = axios.create({
  timeout: 30000,
  withCredentials: true,
});

apiClient.interceptors.request.use(
  (cfg: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token) {
      if (!cfg.headers) cfg.headers = {} as InternalAxiosRequestConfig["headers"];
      (cfg.headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
    }
    return cfg;
  },
  (err) => Promise.reject(err)
);

let isRefreshing = false;
let refreshWaiters: Array<(token: string | null) => void> = [];
async function ensureRefreshed(): Promise<string | null> {
  if (isRefreshing) {
    return new Promise((resolve) => {
      refreshWaiters.push(resolve);
    });
  }
  isRefreshing = true;
  try {
    const data = await refreshToken(API_URL);
    const token = data?.access_token || getAccessToken();
    refreshWaiters.forEach((cb) => cb(token));
    refreshWaiters = [];
    return token;
  } catch (e: any) {
    if (e?.response?.status === 401) {
      clearLoginCache();
    }
    refreshWaiters.forEach((cb) => cb(null));
    refreshWaiters = [];
    throw e;
  } finally {
    isRefreshing = false;
  }
}

apiClient.interceptors.response.use(
  (res) => res,
  async (error) => {
    const cfg = error.config as (AxiosRequestConfig & { _retry?: boolean }) | undefined;
    if (error.response?.status === 401 && cfg && !cfg._retry) {
      cfg._retry = true;
      try {
        const newToken = await ensureRefreshed();
        if (newToken) {
          if (!cfg.headers) cfg.headers = {} as AxiosRequestConfig["headers"];
          (cfg.headers as Record<string, string>)["Authorization"] = `Bearer ${newToken}`;
        }
        return apiClient.request(cfg);
      } catch (refreshErr: any) {
        const status = refreshErr?.response?.status;
        if (status === 401) {
          clearLoginCache();
          EventBus.$emit(C_EVENT.AUTH_EXPIRED);
        }
      }
    }
    return Promise.reject(error);
  }
);

export function getApiUrl() {
  return API_URL;
}

async function checkAddress(url: string, timeout: number = 10000): Promise<boolean> {
  const target = url.replace(/\/$/, "") + "/";
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);
    const res = await fetch(target, {
      method: "HEAD",
      signal: controller.signal,
      cache: "no-store",
    });
    clearTimeout(timeoutId);
    return res.ok;
  } catch {
    return false;
  }
}

export async function checkLocalAddressAvailable(): Promise<boolean> {
  const protocol = typeof window !== "undefined" ? window.location.protocol : "https:";
  if (protocol === "https:") return false;
  return checkAddress(LOCAL.url, 500);
}

export function switchToLocal(): void {
  if (localIpAvailable === true) return;
  localIpAvailable = true;
  REMOTE.available = false;
  LOCAL.available = true;
  API_URL = LOCAL.url;
  apiClient.defaults.baseURL = API_URL;
  EventBus.$emit(C_EVENT.SERVER_SWITCH, false);
}

export function switchToRemote(): void {
  if (localIpAvailable === false) return;
  localIpAvailable = false;
  REMOTE.available = true;
  LOCAL.available = false;
  API_URL = REMOTE.url;
  apiClient.defaults.baseURL = API_URL;
  EventBus.$emit(C_EVENT.SERVER_SWITCH, true);
}

export async function checkAndSwitchServer(): Promise<void> {
  const available = await checkLocalAddressAvailable();
  if (available && localIpAvailable !== true) {
    switchToLocal();
  } else if (!available && localIpAvailable !== false) {
    switchToRemote();
  }
}

export function isLocalIpAvailable(): boolean | null {
  return localIpAvailable;
}

export function initNet(): void {
  API_URL = REMOTE.url;
  REMOTE.available = true;
  LOCAL.available = false;
  localIpAvailable = null;
  apiClient.defaults.baseURL = API_URL;
  EventBus.$emit(C_EVENT.SERVER_SWITCH, true);
  checkAndSwitchServer();
}
