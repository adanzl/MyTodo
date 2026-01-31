import { apiClient } from "./api-client";
import type {
  ApiResponse,
  ApiListResponse,
  ColorListItem,
  SetColorDataBody,
} from "./types";

export async function getColorList(
  pageNum?: number,
  pageSize?: number
): Promise<ApiListResponse<ColorListItem>> {
  const rsp = await apiClient.get<ApiResponse<ApiListResponse<ColorListItem>>>(
    "/getAll",
    { params: { table: "t_colors", pageNum, pageSize } }
  );
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data!;
}

export async function setColor(
  id: number | undefined,
  name: string,
  color: string
): Promise<string> {
  const body: SetColorDataBody = { id, name, color };
  const rsp = await apiClient.post<ApiResponse<string>>("/setData", {
    table: "t_colors",
    data: body,
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data!;
}

export async function delColor(id: number): Promise<void> {
  const rsp = await apiClient.post<ApiResponse<unknown>>("/delData", {
    id,
    table: "t_colors",
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
}
