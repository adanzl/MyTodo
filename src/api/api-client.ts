import EventBus, { C_EVENT } from "@/types/EventBus";
import { clearLoginCache, getAccessToken, refreshToken } from "@/utils/Auth";
import axios, { type AxiosRequestConfig, type InternalAxiosRequestConfig } from "axios";

const REMOTE_URL = "https://leo-zhao.natapp4.cc/api";
const LOCAL_IP = "192.168.50.171";
const LOCAL_PORTS = { http: 8848, https: 8843 };
let API_URL = "";
let localIpAvailable: boolean | null = null;

export const apiClient = axios.create({
  timeout: 30000,
  withCredentials: true,
});

apiClient.interceptors.request.use(
  (cfg: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token) {
      (cfg.headers = cfg.headers ?? ({} as typeof cfg.headers))["Authorization"] = `Bearer ${token}`;
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
          (cfg.headers = cfg.headers ?? ({} as typeof cfg.headers))["Authorization"] = `Bearer ${newToken}`;
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

async function checkAddress(url: string, timeout = 500): Promise<boolean> {
  try {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), timeout);
    const res = await fetch(url.replace(/\/?$/, "/"), {
      method: "HEAD",
      signal: ctrl.signal,
      cache: "no-store",
    });
    clearTimeout(t);
    return res.ok;
  } catch {
    return false;
  }
}

function getLocalApiUrl(): string {
  const https = typeof window !== "undefined" && window.location.protocol === "https:";
  const port = LOCAL_PORTS[https ? "https" : "http"];
  return `http${https ? "s" : ""}://${LOCAL_IP}:${port}/api`;
}

export async function checkLocalAddressAvailable(): Promise<boolean> {
  return checkAddress(getLocalApiUrl());
}

function setBaseUrl(url: string): void {
  API_URL = url;
  apiClient.defaults.baseURL = url;
}

export function switchToLocal(): void {
  if (localIpAvailable === true) return;
  localIpAvailable = true;
  setBaseUrl(getLocalApiUrl());
  EventBus.$emit(C_EVENT.SERVER_SWITCH, false);
}

export function switchToRemote(): void {
  if (localIpAvailable === false) return;
  localIpAvailable = false;
  setBaseUrl(REMOTE_URL);
  EventBus.$emit(C_EVENT.SERVER_SWITCH, true);
}

export async function checkAndSwitchServer(): Promise<void> {
  const ok = await checkLocalAddressAvailable();
  if (ok && localIpAvailable !== true) switchToLocal();
  else if (!ok && localIpAvailable !== false) switchToRemote();
}

export function isLocalIpAvailable(): boolean | null {
  return localIpAvailable;
}

export function initNet(): void {
  localIpAvailable = null;
  setBaseUrl(REMOTE_URL);
  EventBus.$emit(C_EVENT.SERVER_SWITCH, true);
  checkAndSwitchServer();
}
