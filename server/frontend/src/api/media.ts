/**
 * 媒体相关 API
 */
import { api } from "./config";
import type { ApiResponse } from "@/types/api";
import type { MediaTask, MediaTaskDetail, MediaTaskFile } from "@/types/tools";

// 导出类型供外部使用
export type { MediaTask, MediaTaskDetail, MediaTaskFile };

/**
 * 媒体操作接口
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
 * 媒体任务相关 API
 */

/**
 * 获取媒体任务列表
 */
export async function getMediaTaskList(): Promise<ApiResponse<{ tasks: MediaTask[] }>> {
  const response = await api.get<ApiResponse<{ tasks: MediaTask[] }>>("/media/task/list");
  return response.data;
}

/**
 * 创建媒体任务
 */
export async function createMediaTask(): Promise<ApiResponse<{ task_id: string }>> {
  const response = await api.post<ApiResponse<{ task_id: string }>>("/media/task/create", {});
  return response.data;
}

/**
 * 获取媒体任务详情
 */
export async function getMediaTask(taskId: string): Promise<ApiResponse<MediaTaskDetail>> {
  const response = await api.post<ApiResponse<MediaTaskDetail>>("/media/task/get", {
    task_id: taskId,
  });
  return response.data;
}

/**
 * 删除媒体任务
 */
export async function deleteMediaTask(taskId: string): Promise<ApiResponse<{ success: boolean }>> {
  const response = await api.post<ApiResponse<{ success: boolean }>>("/media/task/delete", {
    task_id: taskId,
  });
  return response.data;
}

/**
 * 添加文件到媒体任务
 */
export async function addFileToMediaTask(
  taskId: string,
  filePath: string
): Promise<ApiResponse<{ success: boolean }>> {
  const response = await api.post<ApiResponse<{ success: boolean }>>("/media/task/addFileByPath", {
    task_id: taskId,
    file_path: filePath,
  });
  return response.data;
}

/**
 * 从媒体任务删除文件
 */
export async function deleteFileFromMediaTask(
  taskId: string,
  fileIndex: number
): Promise<ApiResponse<{ success: boolean }>> {
  const response = await api.post<ApiResponse<{ success: boolean }>>("/media/task/deleteFile", {
    task_id: taskId,
    file_index: fileIndex,
  });
  return response.data;
}

/**
 * 开始媒体任务合成
 */
export async function startMediaTask(taskId: string): Promise<ApiResponse<{ success: boolean }>> {
  const response = await api.post<ApiResponse<{ success: boolean }>>("/media/task/start", {
    task_id: taskId,
  });
  return response.data;
}

/**
 * 重新排序媒体任务文件
 */
export async function reorderMediaTaskFiles(
  taskId: string,
  fileIndices: number[]
): Promise<ApiResponse<{ success: boolean }>> {
  const response = await api.post<ApiResponse<{ success: boolean }>>("/media/task/reorderFiles", {
    task_id: taskId,
    file_indices: fileIndices,
  });
  return response.data;
}

/**
 * 获取媒体任务下载 URL
 */
export function getMediaTaskDownloadUrl(taskId: string): string {
  // 使用 api 实例的 baseURL，然后拼接路径
  const baseURL = api.defaults.baseURL || "";
  return `${baseURL}/media/task/download?task_id=${taskId}`;
}

/**
 * 转存媒体任务结果文件
 */
export async function saveMediaTaskResult(
  taskId: string,
  targetPath: string
): Promise<ApiResponse<{ success: boolean }>> {
  const response = await api.post<ApiResponse<{ success: boolean }>>("/media/task/save", {
    task_id: taskId,
    target_path: targetPath,
  });
  return response.data;
}
