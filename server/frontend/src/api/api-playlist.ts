/**
 * 播放列表相关 API
 */
import { api } from "./config";
import type { ApiResponse } from "@/types/api";

/**
 * 播放列表操作接口
 */
export async function playlistAction(
  action: string,
  method: "GET" | "POST",
  params: Record<string, unknown> = {}
): Promise<ApiResponse<unknown>> {
  let rsp;
  if (method === "GET") {
    rsp = await api.get(`/playlist/${action}`, {
      params: params,
    });
  } else {
    rsp = await api.post(`/playlist/${action}`, params);
  }
  return rsp.data;
}

/**
 * 在指定播放列表绑定的设备上播放指定文件（单次推播）
 */
export async function playFileOnDevice(
  playlistId: string,
  fileUri: string
): Promise<ApiResponse<unknown>> {
  return playlistAction("playFile", "POST", { id: playlistId, uri: fileUri });
}
