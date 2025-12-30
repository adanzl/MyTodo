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
 */
export async function uploadPdf(file: File): Promise<ApiResponse<{ filename: string }>> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await api.post<ApiResponse<{ filename: string }>>("/pdf/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
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
