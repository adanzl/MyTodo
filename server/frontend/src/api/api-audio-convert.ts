/**
 * 音频转码相关 API
 */
import type { AxiosRequestConfig } from "axios";
import { api, getBaseUrl } from "./config";
import type { ApiResponse } from "@/types/api";
import type { ConvertSourceType, ConvertTask } from "@/types/tools";

// 导出类型供外部使用
export type { ConvertTask };

type FileUploadRequestConfig = AxiosRequestConfig & {
  _isFileUpload?: boolean;
};

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
  source_type?: ConvertSourceType;
}): Promise<ApiResponse<ConvertTask>> {
  const response = await api.post<ApiResponse<ConvertTask>>(
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
    overwrite?: boolean;
    source_type?: ConvertSourceType;
  }
): Promise<ApiResponse<ConvertTask>> {
  const response = await api.post<ApiResponse<ConvertTask>>("/media/convert/update", {
    task_id: taskId,
    ...updates,
  });
  return response.data;
}

/**
 * 上传待转码文件
 */
export async function uploadConvertFiles(
  taskId: string,
  files: File[],
  onProgress?: (progress: number) => void,
  signal?: AbortSignal
): Promise<ApiResponse<ConvertTask>> {
  const formData = new FormData();
  formData.append("task_id", taskId);
  files.forEach(file => {
    formData.append("files[]", file);
  });

  const config: FileUploadRequestConfig = {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    timeout: 600000,
    signal,
    _isFileUpload: true,
    onUploadProgress: progressEvent => {
      if (onProgress && progressEvent.total) {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(progress);
      }
    },
  };

  const response = await api.post<ApiResponse<ConvertTask>>("/media/convert/upload", formData, config);
  return response.data as ApiResponse<ConvertTask>;
}

/**
 * 开始转码任务
 */
export async function startConvertTask(taskId: string): Promise<ApiResponse<ConvertTask>> {
  const response = await api.post<ApiResponse<ConvertTask>>("/media/convert/start", {
    task_id: taskId,
  });
  return response.data;
}

/**
 * 获取单个转码结果 MP3 的下载 URL（必须使用转码后的 output_path，而非源文件路径）
 */
export function getConvertFileDownloadUrl(taskId: string, outputPath: string): string {
  const baseURL = getBaseUrl();
  const params = new URLSearchParams({
    task_id: taskId,
    output_path: outputPath,
  });
  return `${baseURL}/api/media/convert/download?${params.toString()}`;
}
