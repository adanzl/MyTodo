import { apiClient } from "./api-client";
import type { ApiResponse, ApiPagedResponse } from "./types";

export async function getList<T = unknown>(
  table: string,
  conditions?: Record<string, unknown>,
  pageNum: number = 1,
  pageSize: number = 10
): Promise<ApiPagedResponse<T>> {
  const rsp = await apiClient.get<ApiResponse<ApiPagedResponse<T>>>("/getAll", {
    params: {
      table,
      conditions: conditions ? JSON.stringify(conditions) : undefined,
      pageNum,
      pageSize,
    },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data!;
}

export async function getRdsData(table: string, id: number): Promise<unknown> {
  const rsp = await apiClient.get<ApiResponse<unknown>>("/getRdsData", {
    params: { table, id },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function setRdsData(
  table: string,
  id: number,
  value: unknown
): Promise<unknown> {
  const rsp = await apiClient.post<ApiResponse<unknown>>("/setRdsData", {
    table,
    data: { id, value },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

/** 设置单条数据（新增或更新） */
export async function setData<T = unknown>(
  table: string,
  data: Record<string, unknown>
): Promise<T> {
  const payload = { ...data };
  if (payload.id === -1) {
    delete payload.id;
  }
  const rsp = await apiClient.post<ApiResponse<T>>("/setData", {
    table,
    data: payload,
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data!;
}

/** 删除单条数据 */
export async function delData(table: string, id: number | string): Promise<void> {
  const rsp = await apiClient.post<ApiResponse<unknown>>("/delData", {
    table,
    id,
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
}
