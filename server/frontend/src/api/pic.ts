/**
 * 图片相关 API
 */
import { api, getBaseUrl } from "./config";
import type { ApiResponse } from "@/types/api";

export interface PicUploadResult {
  filename: string;
  path: string;
}

/**
 * 上传图片到 pic 目录
 */
export async function uploadPic(file: File): Promise<ApiResponse<PicUploadResult>> {
  const formData = new FormData();
  formData.append("file", file);

  const config = {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 60000,
  };

  const response = await api.post<ApiResponse<PicUploadResult>>("/pic/upload", formData, config);
  return response.data;
}

/**
 * 获取图片展示 URL（兼容 base64 和文件名）
 * - base64: 直接返回原值
 * - 文件名: 返回 pic/view 接口 URL
 */
export function getPicDisplayUrl(img: string): string {
  if (!img) return "";
  if (img.startsWith("data:")) return img;
  const baseURL = getBaseUrl();
  return `${baseURL}/api/pic/view?name=${encodeURIComponent(img)}`;
}
