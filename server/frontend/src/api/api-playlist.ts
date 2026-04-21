/**
 * 播放列表相关 API
 */
import { api } from "./config";
import type { ApiResponse } from "@/types/api";
import type { PlaylistApiData } from "@/types/playlist";

/**
 * 获取播放列表集合
 * @param id 可选，播放列表ID，不传则返回所有播放列表
 */
export async function getPlaylist(id?: string): Promise<ApiResponse<unknown>> {
  const params = id ? { id } : {};
  const rsp = await api.get("/playlist/get", { params });
  return rsp.data;
}

/**
 * 获取播放列表更新历史
 * @param limit 返回的历史记录数量，默认10个，最大10个
 */
export async function getPlaylistHistory(
  limit: number = 10
): Promise<ApiResponse<Record<string, string>>> {
  const rsp = await api.get("/playlist/history", { params: { limit } });
  return rsp.data;
}

/**
 * 更新单个播放列表
 * @param playlistData 播放列表数据，必须包含 id 字段
 */
export async function updatePlaylist(
  playlistData: Partial<PlaylistApiData>
): Promise<ApiResponse<unknown>> {
  const rsp = await api.post("/playlist/update", playlistData);
  return rsp.data;
}

/**
 * 批量更新所有播放列表
 * @param collection 播放列表集合，格式为 {playlist_id: playlist_data, ...}
 */
export async function updateAllPlaylists(
  collection: Record<string, Partial<PlaylistApiData>>
): Promise<ApiResponse<unknown>> {
  const rsp = await api.post("/playlist/updateAll", collection);
  return rsp.data;
}

/**
 * 播放指定播放列表
 * @param id 播放列表ID
 */
export async function playPlaylist(id: string): Promise<ApiResponse<unknown>> {
  const rsp = await api.post("/playlist/play", { id });
  return rsp.data;
}

/**
 * 播放下一首
 * @param id 播放列表ID
 */
export async function playNext(id: string): Promise<ApiResponse<unknown>> {
  const rsp = await api.post("/playlist/playNext", { id });
  return rsp.data;
}

/**
 * 播放上一首
 * @param id 播放列表ID
 */
export async function playPre(id: string): Promise<ApiResponse<unknown>> {
  const rsp = await api.post("/playlist/playPre", { id });
  return rsp.data;
}

/**
 * 在指定播放列表绑定的设备上播放指定文件（单次推播）
 * @param id 播放列表ID
 * @param uri 文件URI
 */
export async function playFileOnDevice(id: string, uri: string): Promise<ApiResponse<unknown>> {
  const rsp = await api.post("/playlist/playFile", { id, uri });
  return rsp.data;
}

/**
 * 停止播放
 * @param id 播放列表ID
 */
export async function stopPlaylist(id: string): Promise<ApiResponse<unknown>> {
  const rsp = await api.post("/playlist/stop", { id });
  return rsp.data;
}

/**
 * 重新从 RDS 加载播放列表数据
 */
export async function reloadPlaylist(): Promise<ApiResponse<unknown>> {
  const rsp = await api.post("/playlist/reload", {});
  return rsp.data;
}

/**
 * 将播放列表中的所有文件转换为MP3格式
 * @param id 播放列表ID
 */
export async function convertPlaylistToMp3(id: string): Promise<ApiResponse<unknown>> {
  const rsp = await api.post("/playlist/convertToMp3", { id });
  return rsp.data;
}

/**
 * 移除播放列表中的重复文件路径
 * @param id 播放列表ID
 */
export async function removeDuplicateFiles(id: string): Promise<ApiResponse<unknown>> {
  const rsp = await api.post("/playlist/removeDuplicate", { id });
  return rsp.data;
}
