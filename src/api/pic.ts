import { apiClient } from "./api-client";
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
