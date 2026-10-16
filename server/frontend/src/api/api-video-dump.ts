/**
 * 文字提取相关 API
 */
import { api, getBaseUrl } from "./config";
import type { ApiResponse } from "@/types/api";
import type {
  VideoDumpLoginSite,
  VideoDumpQrPoll,
  VideoDumpQrStart,
  VideoDumpSite,
  VideoDumpTask,
} from "@/types/tools/video-dump";

export async function getVideoDumpSites(): Promise<ApiResponse<VideoDumpSite[]>> {
  const response = await api.get<ApiResponse<VideoDumpSite[]>>("/video_dump/sites");
  return response.data;
}

export async function getVideoDumpLogin(): Promise<ApiResponse<VideoDumpLoginSite[]>> {
  const response = await api.get<ApiResponse<VideoDumpLoginSite[]>>("/video_dump/login");
  return response.data;
}

export async function startBilibiliQr(): Promise<ApiResponse<VideoDumpQrStart>> {
  const response = await api.post<ApiResponse<VideoDumpQrStart>>("/video_dump/login/bilibili/qr");
  return response.data;
}

export async function pollBilibiliQr(loginId: string): Promise<ApiResponse<VideoDumpQrPoll>> {
  const response = await api.get<ApiResponse<VideoDumpQrPoll>>("/video_dump/login/bilibili/poll", {
    params: { login_id: loginId },
  });
  return response.data;
}

export async function startDouyinQr(): Promise<ApiResponse<VideoDumpQrStart>> {
  const response = await api.post<ApiResponse<VideoDumpQrStart>>("/video_dump/login/douyin/qr");
  return response.data;
}

export async function pollDouyinQr(loginId: string): Promise<ApiResponse<VideoDumpQrPoll>> {
  const response = await api.get<ApiResponse<VideoDumpQrPoll>>("/video_dump/login/douyin/poll", {
    params: { login_id: loginId },
  });
  return response.data;
}

export async function logoutVideoDump(site: string): Promise<ApiResponse<{ ready: boolean }>> {
  const response = await api.post<ApiResponse<{ ready: boolean }>>("/video_dump/login/logout", { site });
  return response.data;
}

export async function getVideoDumpList(): Promise<ApiResponse<VideoDumpTask[]>> {
  const response = await api.get<ApiResponse<VideoDumpTask[]>>("/video_dump/list");
  return response.data;
}

export async function createVideoDump(url: string): Promise<ApiResponse<VideoDumpTask>> {
  const response = await api.post<ApiResponse<VideoDumpTask>>("/video_dump/create", { url });
  return response.data;
}

export async function getVideoDumpTaskStatus(task_id: string): Promise<ApiResponse<VideoDumpTask>> {
  const response = await api.get<ApiResponse<VideoDumpTask>>(`/video_dump/task/${encodeURIComponent(task_id)}`);
  return response.data;
}

export function getVideoDumpDownloadUrl(taskId: string, type: "video" | "text" | "subtitle"): string {
  const baseURL = getBaseUrl();
  return `${baseURL}/api/video_dump/download/${encodeURIComponent(taskId)}?type=${type}`;
}

export async function deleteVideoDump(
  task_id?: string,
  clear_all = false
): Promise<ApiResponse<{ message: string; deleted?: number; skipped?: number; failed?: number }>> {
  const response = await api.post<
    ApiResponse<{ message: string; deleted?: number; skipped?: number; failed?: number }>
  >("/video_dump/delete", clear_all ? { clear_all: true } : { task_id });
  return response.data;
}
