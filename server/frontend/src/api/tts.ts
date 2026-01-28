/**
 * TTS 相关 API
 */
import { api, getBaseUrl } from "./config";
import type { ApiResponse } from "@/types/api";
import type { TTSTask } from "@/types/tools/tts";

// 导出类型供外部使用
export type { TTSTask };

/**
 * 获取 TTS 任务列表
 */
export async function getTtsTaskList(): Promise<ApiResponse<TTSTask[]>> {
  const response = await api.get<ApiResponse<TTSTask[]>>("/tts/list");
  return response.data;
}

/**
 * 创建 TTS 任务
 */
export async function createTtsTask(params: {
  text: string;
  name?: string;
  role?: string;
  model?: string;
  speed?: number;
  vol?: number;
}): Promise<ApiResponse<{ task_id: string }>> {
  const response = await api.post<ApiResponse<{ task_id: string }>>("/tts/create", params);
  return response.data;
}

/**
 * 获取 TTS 任务详情
 */
export async function getTtsTask(taskId: string): Promise<ApiResponse<TTSTask>> {
  const response = await api.get<ApiResponse<TTSTask>>("/tts/get", {
    params: { task_id: taskId },
  });
  return response.data;
}

/**
 * 更新 TTS 任务
 */
export async function updateTtsTask(
  taskId: string,
  params: {
    name?: string;
    text?: string;
    role?: string;
    model?: string;
    speed?: number;
    vol?: number;
  }
): Promise<ApiResponse<null>> {
  const response = await api.post<ApiResponse<null>>("/tts/update", {
    task_id: taskId,
    ...params,
  });
  return response.data;
}

/**
 * 删除 TTS 任务
 */
export async function deleteTtsTask(taskId: string): Promise<ApiResponse<null>> {
  const response = await api.post<ApiResponse<null>>("/tts/delete", {
    task_id: taskId,
  });
  return response.data;
}

/**
 * 启动 TTS 任务
 */
export async function startTtsTask(taskId: string): Promise<ApiResponse<null>> {
  const response = await api.post<ApiResponse<null>>("/tts/start", {
    task_id: taskId,
  });
  return response.data;
}

/**
 * 停止 TTS 任务
 */
export async function stopTtsTask(taskId: string): Promise<ApiResponse<null>> {
  const response = await api.post<ApiResponse<null>>("/tts/stop", {
    task_id: taskId,
  });
  return response.data;
}

/**
 * TTS 任务 OCR 图片文字识别
 * 将 OCR 识别结果自动追加到指定 TTS 任务的文本末尾
 * @param taskId 任务 ID
 * @param files 图片文件数组
 */
export async function ocrTtsTask(taskId: string, files: File[]): Promise<ApiResponse<null>> {
  const formData = new FormData();

  // 添加 task_id
  formData.append("task_id", taskId);

  // 添加所有图片文件
  files.forEach(file => {
    formData.append("file", file);
  });

  const config = {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    timeout: 60000, // 60秒超时
    _isFileUpload: true,
  };

  const response = await api.post<ApiResponse<null>>("/tts/ocr", formData, config);
  return response.data;
}

/**
 * 启动 TTS 任务文本分析
 * 仅分析当前任务文本，将结构化结果保存到任务的 analysis 字段
 */
export async function analyzeTtsTask(taskId: string): Promise<ApiResponse<null>> {
  const response = await api.post<ApiResponse<null>>("/tts/analysis", {
    task_id: taskId,
  });
  return response.data;
}

/**
 * 获取 TTS 任务下载 URL
 * 如果本地 IP 可用，会自动使用本地地址，提高下载速度
 */
export function getTtsTaskDownloadUrl(taskId: string): string {
  // 使用 getBaseUrl 获取正确的基础 URL（会根据本地 IP 可用性智能选择）
  const baseURL = getBaseUrl();
  const downloadUrl = `${baseURL}/api/tts/download?task_id=${taskId}`;

  // 在开发环境下输出日志，方便调试
  if (import.meta.env.DEV) {
    console.log(`[TTS Download] Using baseURL: ${baseURL}, task_id: ${taskId}`);
  }

  return downloadUrl;
}
