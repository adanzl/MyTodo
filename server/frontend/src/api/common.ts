/**
 * 通用 API 接口
 */
import { api } from "./config";

interface ApiResponse<T = any> {
  code: number;
  msg?: string;
  data: T;
}

/**
 * 获取数据列表
 */
export async function getList<T = any>(
  table: string,
  conditions?: Record<string, any>,
  pageNum?: number,
  pageSize?: number
): Promise<ApiResponse<T>> {
  const params: Record<string, any> = { table };
  if (conditions) params.conditions = JSON.stringify(conditions);
  if (pageNum) params.pageNum = pageNum;
  if (pageSize) params.pageSize = pageSize;

  const response = await api.get("/api/getAll", { params });
  if (response.data.code !== 0) {
    throw new Error(response.data.msg);
  }
  return response.data;
}

/**
 * 获取单条数据
 */
export async function getData<T = any>(
  table: string,
  id: number | string,
  fields?: string[]
): Promise<T> {
  const params: Record<string, any> = { table, id };
  if (fields) params.fields = fields;

  const response = await api.get("/api/getData", { params });
  if (response.data.code !== 0) {
    throw new Error(response.data.msg);
  }
  return response.data.data;
}

/**
 * 设置数据（新增或更新）
 */
export async function setData<T = any>(
  table: string,
  data: Record<string, any>
): Promise<T> {
  if (data.id === -1) {
    data.id = null;
  }
  const response = await api.post("/api/setData", { table, data });
  if (response.data.code !== 0) {
    throw new Error(response.data.msg);
  }
  return response.data.data;
}

/**
 * 删除数据
 */
export async function delData(table: string, id: number | string): Promise<any> {
  const response = await api.post("/api/delData", { table, id });
  if (response.data.code !== 0) {
    throw new Error(response.data.msg);
  }
  return response.data.data;
}


