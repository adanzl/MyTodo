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
 * @param img 图片数据（base64 或文件名）
 * @param w 可选，目标宽度
 * @param h 可选，目标高度（与 w 同时传入时按比例缩放并缓存）
 */
export function getPicDisplayUrl(img: string, w?: number, h?: number): string {
  if (!img) return "";
  if (img.startsWith("data:")) return img;
  const baseURL = getBaseUrl();
  let url = `${baseURL}/api/pic/view?name=${encodeURIComponent(img)}`;
  if (w != null && h != null && w > 0 && h > 0) {
    url += `&w=${w}&h=${h}`;
  }
  return url;
}
