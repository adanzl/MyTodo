/**
 * PDF 排版相关 API
 */
import { api, getBaseUrl } from "./config";
import type { ApiResponse } from "@/types/api";
import type { PdfLayoutTask } from "@/types/tools/pdf-layout";

/**
 * 获取 PDF 排版任务列表
 */
export async function getPdfLayoutList(): Promise<ApiResponse<PdfLayoutTask[]>> {
  const response = await api.get<ApiResponse<PdfLayoutTask[]>>("/pdf_layout/list");
  return response.data;
}

/**
 * 上传 PDF 文件
 * @param file 要上传的文件
 * @param onProgress 上传进度回调函数，参数为进度百分比 (0-100)
 * @param signal 可选的 AbortSignal，用于取消上传
 */
export async function uploadPdfLayout(
  file: File,
  onProgress?: (progress: number) => void,
  signal?: AbortSignal
): Promise<ApiResponse<PdfLayoutTask>> {
  const formData = new FormData();
  formData.append("file", file);

  const config = {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    timeout: 600000,
    signal,
    _isFileUpload: true,
    onUploadProgress: (progressEvent: any) => {
      if (onProgress && progressEvent.total) {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percentCompleted);
      }
    },
  };

  const response = await api.post<ApiResponse<PdfLayoutTask>>("/pdf_layout/upload", formData, config);
  return response.data;
}

/**
 * 执行 PDF 排版处理（异步处理）
 */
export async function processPdfLayout(
  task_id: string
): Promise<ApiResponse<{ message: string }>> {
  const data = { task_id };
  const response = await api.post<ApiResponse<{ message: string }>>("/pdf_layout/process", data);
  return response.data;
}

/**
 * 获取任务状态
 */
export async function getPdfLayoutTaskStatus(task_id: string): Promise<ApiResponse<PdfLayoutTask>> {
  const response = await api.get<ApiResponse<PdfLayoutTask>>(`/pdf_layout/task/${encodeURIComponent(task_id)}`);
  return response.data;
}

/**
 * 下载排版后的 PDF 文件
 */
export function getPdfLayoutDownloadUrl(filename: string, type: "uploaded" | "output"): string {
  const baseURL = getBaseUrl();
  const downloadUrl = `${baseURL}/api/pdf_layout/download/${encodeURIComponent(filename)}?type=${type}`;

  if (import.meta.env.DEV) {
    console.log(`[PDF Layout Download] Using baseURL: ${baseURL}, file: ${filename}, type: ${type}`);
  }

  return downloadUrl;
}

/**
 * 删除 PDF 排版任务
 */
export async function deletePdfLayout(task_id: string): Promise<ApiResponse<{ message: string }>> {
  const response = await api.post<ApiResponse<{ message: string }>>("/pdf_layout/delete", {
    task_id,
  });
  return response.data;
}

/**
 * 生成并保存骑缝排版 PDF
 */
export async function savePdfLayout(
  task_id: string,
  fill_configs: number[]
): Promise<ApiResponse<PdfLayoutTask>> {
  const response = await api.post<ApiResponse<PdfLayoutTask>>("/pdf_layout/save", {
    task_id,
    fill_configs,
  });
  return response.data;
}

/**
 * 保存任务的填充配置
 */
export async function savePdfLayoutFillConfigs(
  task_id: string,
  fill_configs: number[]
): Promise<ApiResponse<{ message: string }>> {
  const response = await api.put<ApiResponse<{ message: string }>>(
    `/pdf_layout/${encodeURIComponent(task_id)}/config`,
    { fill_configs }
  );
  return response.data;
}
