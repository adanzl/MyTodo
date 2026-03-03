/**
 * 音频合成相关 API
 */
import { api, getBaseUrl } from "./config";
import type { ApiResponse } from "@/types/api";
import type { MediaTask, MediaTaskDetail, MediaTaskFile } from "@/types/tools";

// 导出类型供外部使用
export type { MediaTask, MediaTaskDetail, MediaTaskFile };

/**
 * 媒体操作接口（保留用于其他媒体功能）
 */
export async function mediaAction(
  action: string,
  method: "GET" | "POST",
  params: Record<string, unknown> = {}
): Promise<ApiResponse<unknown>> {
  let rsp;
  if (method === "GET") {
    rsp = await api.get(`/media/${action}`, {
      params: params,
    });
  } else {
    rsp = await api.post(`/media/${action}`, params);
  }
  return rsp.data;
}

/**
 * 音频合成任务相关 API
 */

/**
 * 获取音频合成任务列表
 */
export async function getAudioMergeTaskList(): Promise<ApiResponse<{ tasks: MediaTask[] }>> {
  const response = await api.get<ApiResponse<{ tasks: MediaTask[] }>>("/media/merge/list");
  return response.data;
}

/**
 * 创建音频合成任务
 */
export async function createAudioMergeTask(): Promise<ApiResponse<{ task_id: string }>> {
  const response = await api.post<ApiResponse<{ task_id: string }>>("/media/merge/create", {});
  return response.data;
}

/**
 * 获取音频合成任务详情
 */
export async function getAudioMergeTask(taskId: string): Promise<ApiResponse<MediaTaskDetail>> {
  const response = await api.post<ApiResponse<MediaTaskDetail>>("/media/merge/get", {
    task_id: taskId,
  });
  return response.data;
}

/**
 * 删除音频合成任务
 */
export async function deleteAudioMergeTask(
  taskId: string
): Promise<ApiResponse<{ success: boolean }>> {
  const response = await api.post<ApiResponse<{ success: boolean }>>("/media/merge/delete", {
    task_id: taskId,
  });
  return response.data;
}

/**
 * 添加文件到音频合成任务
 */
export async function addFileToAudioMergeTask(
  taskId: string,
  filePath: string
): Promise<ApiResponse<{ success: boolean }>> {
  const response = await api.post<ApiResponse<{ success: boolean }>>("/media/merge/addFileByPath", {
    task_id: taskId,
    file_path: filePath,
  });
  return response.data;
}

/**
 * 从音频合成任务删除文件
 */
export async function deleteFileFromAudioMergeTask(
  taskId: string,
  fileIndex: number
): Promise<ApiResponse<{ success: boolean }>> {
  const response = await api.post<ApiResponse<{ success: boolean }>>("/media/merge/deleteFile", {
    task_id: taskId,
    file_index: fileIndex,
  });
  return response.data;
}

/**
 * 开始音频合成任务
 */
export async function startAudioMergeTask(
  taskId: string
): Promise<ApiResponse<{ success: boolean }>> {
  const response = await api.post<ApiResponse<{ success: boolean }>>("/media/merge/start", {
    task_id: taskId,
  });
  return response.data;
}

/**
 * 重新排序音频合成任务文件
 */
export async function reorderAudioMergeTaskFiles(
  taskId: string,
  fileIndices: number[]
): Promise<ApiResponse<{ success: boolean }>> {
  const response = await api.post<ApiResponse<{ success: boolean }>>("/media/merge/reorderFiles", {
    task_id: taskId,
    file_indices: fileIndices,
  });
  return response.data;
}

/**
 * 获取音频合成任务下载 URL
 * 如果本地 IP 可用，会自动使用本地地址，提高下载速度
 */
export function getAudioMergeTaskDownloadUrl(taskId: string): string {
  // 使用 getBaseUrl 获取正确的基础 URL（会根据本地 IP 可用性智能选择）
  const baseURL = getBaseUrl();
  const downloadUrl = `${baseURL}/api/media/merge/download?task_id=${taskId}`;

  // 在开发环境下输出日志，方便调试
  if (import.meta.env.DEV) {
    console.log(`[Audio Download] Using baseURL: ${baseURL}, task_id: ${taskId}`);
  }

  return downloadUrl;
}

/**
 * 转存音频合成任务结果文件
 */
export async function saveAudioMergeTaskResult(
  taskId: string,
  targetPath: string
): Promise<ApiResponse<{ success: boolean }>> {
  const response = await api.post<ApiResponse<{ success: boolean }>>("/media/merge/save", {
    task_id: taskId,
    target_path: targetPath,
  });
  return response.data;
}

// 为了向后兼容，保留旧的函数名作为别名
export const getMediaTaskList = getAudioMergeTaskList;
export const createMediaTask = createAudioMergeTask;
export const getMediaTask = getAudioMergeTask;
export const deleteMediaTask = deleteAudioMergeTask;
export const addFileToMediaTask = addFileToAudioMergeTask;
export const deleteFileFromMediaTask = deleteFileFromAudioMergeTask;
export const startMediaTask = startAudioMergeTask;
export const reorderMediaTaskFiles = reorderAudioMergeTaskFiles;
export const getMediaTaskDownloadUrl = getAudioMergeTaskDownloadUrl;
export const saveMediaTaskResult = saveAudioMergeTaskResult;
