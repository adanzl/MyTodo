/**
 * 音频转码相关 API
 */
import { api } from "./config";
import type { ApiResponse } from "@/types/api";
import type { ConvertTask } from "@/types/tools";

// 导出类型供外部使用
export type { ConvertTask };

/**
 * 获取转码任务列表
 */
export async function getConvertTaskList(): Promise<ApiResponse<{ tasks: ConvertTask[] }>> {
  const response = await api.get<ApiResponse<{ tasks: ConvertTask[] }>>("/media/convert/list");
  return response.data;
}

/**
 * 创建转码任务
 */
export async function createConvertTask(params?: {
  name?: string;
  output_dir?: string;
}): Promise<ApiResponse<{ task_id: string }>> {
  const response = await api.post<ApiResponse<{ task_id: string }>>(
    "/media/convert/create",
    params || {}
  );
  return response.data;
}

/**
 * 获取转码任务详情
 */
export async function getConvertTask(taskId: string): Promise<ApiResponse<ConvertTask>> {
  const response = await api.post<ApiResponse<ConvertTask>>("/media/convert/get", {
    task_id: taskId,
  });
  return response.data;
}

/**
 * 删除转码任务
 */
export async function deleteConvertTask(
  taskId: string
): Promise<ApiResponse<{ success: boolean }>> {
  const response = await api.post<ApiResponse<{ success: boolean }>>("/media/convert/delete", {
    task_id: taskId,
  });
  return response.data;
}

/**
 * 更新转码任务信息
 */
export async function updateConvertTask(
  taskId: string,
  updates: {
    name?: string;
    directory?: string;
    output_dir?: string;
  }
): Promise<ApiResponse<ConvertTask>> {
  const response = await api.post<ApiResponse<ConvertTask>>("/media/convert/update", {
    task_id: taskId,
    ...updates,
  });
  return response.data;
}

/**
 * 开始转码任务
 */
export async function startConvertTask(taskId: string): Promise<ApiResponse<{ success: boolean }>> {
  const response = await api.post<ApiResponse<{ success: boolean }>>("/media/convert/start", {
    task_id: taskId,
  });
  return response.data;
}
