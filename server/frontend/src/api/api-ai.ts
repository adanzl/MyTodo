/**
 * AI 相关 API（OCR 等）
 */
import { api } from "./config";
import type { ApiResponse } from "@/types/api";

/**
 * OCR 图片文字识别
 * @param files 图片文件数组
 */
export async function ocrImages(files: File[]): Promise<ApiResponse<{ text: string }>> {
  const formData = new FormData();
  
  // 添加所有图片文件
  files.forEach((file) => {
    formData.append("file", file);
  });

  const config = {
    headers: {
      "Content-Type": "multipart/form-data",
    },
    timeout: 60000, // 60秒超时
    _isFileUpload: true,
  };

  const response = await api.post<ApiResponse<{ text: string }>>("/ai/ocr", formData, config);
  return response.data;
}
