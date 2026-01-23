import { api } from "./config";

export interface LoginResponse {
  code: number;
  msg: string;
  access_token: string;
  expires_in: number;
  user: { id: number; name: string; icon?: string };
}

const KEY_ACCESS_TOKEN = "access_token";

export function getAccessToken(): string | null {
  return localStorage.getItem(KEY_ACCESS_TOKEN);
}

export function setAccessToken(token: string | null): void {
  if (!token) {
    localStorage.removeItem(KEY_ACCESS_TOKEN);
    return;
  }
  localStorage.setItem(KEY_ACCESS_TOKEN, token);
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const resp = await api.post<LoginResponse>("/auth/login", { username, password });
  if (resp.data?.access_token) {
    setAccessToken(resp.data.access_token);
  }
  return resp.data;
}

export async function refreshToken(): Promise<{ access_token: string; expires_in: number }> {
  const resp = await api.post("/auth/refresh");
  const token = resp.data?.access_token;
  if (token) setAccessToken(token);
  return resp.data;
}

export async function logout(): Promise<void> {
  await api.post("/auth/logout");
  setAccessToken(null);
}
