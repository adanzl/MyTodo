import { apiClient } from "./api-client";
import { getApiUrl } from "./api-client";
import type { ApiResponse, ApiListResponse, PicListItem, SetPicDataBody } from "./types";

export async function getPic(id: number): Promise<string> {
  const rsp = await apiClient.get<ApiResponse<string>>("/getData", {
    params: { table: "t_user_pic", id, idx: 1 },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data!;
}

export async function getPicList(
  pageNum?: number,
  pageSize?: number
): Promise<ApiListResponse<PicListItem>> {
  const rsp = await apiClient.get<ApiResponse<ApiListResponse<PicListItem>>>(
    "/getAll",
    { params: { table: "t_user_pic", pageNum, pageSize } }
  );
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data!;
}

export async function setPic(
  id: number | undefined,
  data: string
): Promise<string> {
  const body: SetPicDataBody = { id, data };
  const rsp = await apiClient.post<ApiResponse<string>>("/setData", {
    table: "t_user_pic",
    data: body,
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data!;
}

export async function delPic(id: number): Promise<void> {
  const rsp = await apiClient.post<ApiResponse<unknown>>("/delData", {
    id,
    table: "t_user_pic",
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
}

// ---- 上传礼品图片 & 预览 ----

export interface PicUploadResult {
  filename: string;
  path: string;
}

/** 上传图片到 pic 目录 */
export async function uploadPic(file: File): Promise<PicUploadResult> {
  const formData = new FormData();
  formData.append("file", file);

  const rsp = await apiClient.post<ApiResponse<PicUploadResult>>("/pic/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 60000,
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data!;
}

const DEFAULT_PIC_PLACEHOLDER = (() => {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 96 96" role="img" aria-label="暂无图片">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="96" y2="96" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#f9fafb"/>
      <stop offset="100%" stop-color="#e5e7eb"/>
    </linearGradient>
  </defs>
  <rect width="96" height="96" fill="url(#bg)"/>
  <rect x="22" y="26" width="52" height="44" rx="6" fill="#fff" fill-opacity="0.65" stroke="#d1d5db" stroke-width="1.5"/>
  <circle cx="36" cy="42" r="4" fill="#cbd5e1"/>
  <path d="M28 60l14-12 10 8 16-18" fill="none" stroke="#cbd5e1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
})();

/**
 * 将文件名或 base64 转成可展示的图片 URL
 * @param img 图片数据（文件名或 base64）
 * @param w 可选，目标宽度，不传则使用原图
 * @param h 可选，目标高度，不传则使用原图
 */
export function getPicDisplayUrl(img: string, w?: number, h?: number): string {
  if (!img) {
    return DEFAULT_PIC_PLACEHOLDER;
  }
  if (img.startsWith("data:")) return img;
  if (img.startsWith("http://") || img.startsWith("https://")) return img;
  const baseURL = getApiUrl();
  let url = `${baseURL}/pic/view?name=${encodeURIComponent(img)}`;
  if (w != null && h != null && w > 0 && h > 0) {
    url += `&w=${w}&h=${h}`;
  }
  return url;
}
