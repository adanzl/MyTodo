/**
 * 通用 API 接口
 */
import { api } from "./config";
import type { PaginatedResponse, DeleteResponse } from "@/types/api";

/**
 * 获取数据列表
 */
export async function getList<T = unknown>(
  table: string,
  conditions?: Record<string, unknown>,
  pageNum?: number,
  pageSize?: number
): Promise<PaginatedResponse<T>> {
  const params: Record<string, unknown> = { table };
  if (conditions) params.conditions = JSON.stringify(conditions);
  if (pageNum) params.pageNum = pageNum;
  if (pageSize) params.pageSize = pageSize;

  const response = await api.get("/getAll", { params });
  // 错误已在拦截器中处理，这里直接返回数据
  return response.data;
}

/**
 * 获取单条数据
 */
export async function getData<T = unknown>(
  table: string,
  id: number | string,
  fields?: string[]
): Promise<T> {
  const params: Record<string, unknown> = { table, id };
  if (fields) params.fields = fields;

  const response = await api.get("/getData", { params });
  // 错误已在拦截器中处理，这里直接返回数据
  return response.data.data;
}

/**
 * 设置数据（新增或更新）
 */
export async function setData<T = unknown>(
  table: string,
  data: Record<string, unknown>
): Promise<T> {
  if (data.id === -1) {
    data.id = null;
  }
  const response = await api.post("/setData", { table, data });
  // 错误已在拦截器中处理，这里直接返回数据
  return response.data.data;
}

/**
 * 删除数据
 */
export async function delData(table: string, id: number | string): Promise<DeleteResponse> {
  const response = await api.post("/delData", { table, id });
  // 错误已在拦截器中处理，这里直接返回数据
  return response.data.data;
}
