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

/** 将文件名或 base64 转成可展示的图片 URL */
export function getPicDisplayUrl(img: string, w?: number, h?: number): string {
  if (!img) return "";
  if (img.startsWith("data:")) return img;
  const baseURL = getApiUrl();
  let url = `${baseURL}/pic/view?name=${encodeURIComponent(img)}`;
  if (w != null && h != null && w > 0 && h > 0) {
    url += `&w=${w}&h=${h}`;
  }
  return url;
}
