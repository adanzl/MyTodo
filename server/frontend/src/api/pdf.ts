/**
 * PDF 相关 API
 */
import { api } from "./config";
import type { ApiResponse } from "@/types/api";
import type { PdfTask } from "@/types/tools";

/**
 * 获取 PDF 任务列表
 */
export async function getPdfList(): Promise<ApiResponse<PdfTask[]>> {
  const response = await api.get<ApiResponse<PdfTask[]>>("/pdf/list");
  return response.data;
}

/**
 * 上传 PDF 文件
 * @param file 要上传的文件
 * @param onProgress 上传进度回调函数，参数为进度百分比 (0-100)
 * @param signal 可选的 AbortSignal，用于取消上传
 */
export async function uploadPdf(
  file: File,
  onProgress?: (progress: number) => void,
  signal?: AbortSignal
): Promise<ApiResponse<{ filename: string }>> {
  const formData = new FormData();
  formData.append("file", file);

  // 标记这是一个文件上传请求，用于错误处理时识别
  const config = {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    timeout: 600000, // 10分钟超时（600000毫秒）
    signal, // 支持取消请求
    // 添加自定义标记，确保错误处理能识别这是文件上传
    _isFileUpload: true,
    onUploadProgress: (progressEvent: any) => {
      if (onProgress && progressEvent.total) {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percentCompleted);
      }
    },
  };

  const response = await api.post<ApiResponse<{ filename: string }>>("/pdf/upload", formData, config);
  return response.data;
}

/**
 * 解密 PDF 文件（异步处理）
 */
export async function decryptPdf(
  task_id: string,
  password?: string
): Promise<ApiResponse<{ message: string }>> {
  const data: { task_id: string; password?: string } = { task_id };
  if (password !== undefined && password !== null && password !== "") {
    data.password = password;
  }
  const response = await api.post<ApiResponse<{ message: string }>>("/pdf/decrypt", data);
  return response.data;
}

/**
 * 获取任务状态
 */
export async function getTaskStatus(task_id: string): Promise<ApiResponse<PdfTask>> {
  const response = await api.get<ApiResponse<PdfTask>>(`/pdf/task/${encodeURIComponent(task_id)}`);
  return response.data;
}

/**
 * 下载 PDF 文件
 */
export function getPdfDownloadUrl(filename: string, type: "uploaded" | "unlocked"): string {
  // 使用 api 实例的 baseURL，然后拼接路径
  const baseURL = api.defaults.baseURL || "";
  return `${baseURL}/pdf/download/${encodeURIComponent(filename)}?type=${type}`;
}

/**
 * 删除 PDF 任务
 */
export async function deletePdf(task_id: string): Promise<ApiResponse<{ message: string }>> {
  const response = await api.post<ApiResponse<{ message: string }>>("/pdf/delete", {
    task_id,
  });
  return response.data;
}
