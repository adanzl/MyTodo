/**
 * 文字提取相关 API
 */
import { api, getBaseUrl } from "./config";
import type { ApiResponse } from "@/types/api";
import type { VideoDumpSite, VideoDumpTask } from "@/types/tools/video-dump";

export async function getVideoDumpSites(): Promise<ApiResponse<VideoDumpSite[]>> {
  const response = await api.get<ApiResponse<VideoDumpSite[]>>("/video_dump/sites");
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
