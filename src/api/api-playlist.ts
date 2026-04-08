/**
 * 播放列表相关 API
 */
import { apiClient } from "./api-client";
import type { ApiResponse } from "./types";

export interface PlaylistItem {
  uri: string;
  name?: string;
  duration?: number;
  order?: number;
}

export interface PlaylistSchedule {
  enabled: number;
  cron?: string;
  duration?: number;
}

export interface Playlist {
  id: string;
  name: string;
  pre_lists?: PlaylistItem[][];
  playlist?: PlaylistItem[];
  schedule?: PlaylistSchedule;
  trigger_button?: string;
  total?: number;
  current_index?: number;
  isPlaying?: boolean;
  in_pre_files?: boolean;
}

/**
 * 获取播放列表
 */
export async function getPlaylists(): Promise<ApiResponse<Playlist[]>> {
  const rsp = await apiClient.get('/playlist/get');
  return rsp.data;
}

/**
 * 获取单个播放列表
 */
export async function getPlaylist(id: string): Promise<ApiResponse<Playlist>> {
  const rsp = await apiClient.get('/playlist/get', { params: { id } });
  return rsp.data;
}

/**
 * 更新播放列表
 */
export async function updatePlaylist(playlist: Playlist): Promise<ApiResponse<void>> {
  const rsp = await apiClient.post('/playlist/update', playlist);
  return rsp.data;
}

/**
 * 更新所有播放列表
 */
export async function updateAllPlaylists(playlists: Record<string, Playlist>): Promise<ApiResponse<void>> {
  const rsp = await apiClient.post('/playlist/updateAll', playlists);
  return rsp.data;
}

/**
 * 播放播放列表
 */
export async function playPlaylist(id: string): Promise<ApiResponse<void>> {
  const rsp = await apiClient.post('/playlist/play', { id });
  return rsp.data;
}

/**
 * 暂停播放列表
 */
export async function pausePlaylist(id: string): Promise<ApiResponse<void>> {
  const rsp = await apiClient.post('/playlist/pause', { id });
  return rsp.data;
}

/**
 * 播放下一首
 */
export async function playNext(id: string): Promise<ApiResponse<void>> {
  const rsp = await apiClient.post('/playlist/playNext', { id });
  return rsp.data;
}

/**
 * 播放上一首
 */
export async function playPre(id: string): Promise<ApiResponse<void>> {
  const rsp = await apiClient.post('/playlist/playPre', { id });
  return rsp.data;
}

/**
 * 停止播放
 */
export async function stopPlaylist(id: string): Promise<ApiResponse<void>> {
  const rsp = await apiClient.post('/playlist/stop', { id });
  return rsp.data;
}

/**
 * 在指定播放列表绑定的设备上播放指定文件（单次推播）
 */
export async function playFileOnDevice(
  playlistId: string,
  fileUri: string
): Promise<ApiResponse<unknown>> {
  const rsp = await apiClient.post('/playlist/playFile', { id: playlistId, uri: fileUri });
  return rsp.data;
}
