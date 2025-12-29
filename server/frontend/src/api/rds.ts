/**
 * Redis 数据相关 API
 */
import { api } from "./config";
import type { ApiResponse } from "@/types/api";

/**
 * 获取rds列表数据
 */
export async function getRdsList<T = unknown>(
  key: string,
  startId: number,
  pageSize: number
): Promise<T> {
  const rsp = await api.get<ApiResponse<T>>("/getRdsList", {
    params: { key: key, pageSize: pageSize, startId: startId },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

/**
 * 获取rds数据
 */
export async function getRdsData<T = unknown>(table: string, id: number | string): Promise<T> {
  const rsp = await api.get<ApiResponse<T>>("/getRdsData", {
    params: { table: table, id: id },
  });
  // console.log("getRdsData", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

/**
 * 设置rds数据
 */
export async function setRdsData<T = unknown>(
  table: string,
  id: number | string,
  value: unknown
): Promise<T> {
  const rsp = await api.post<ApiResponse<T>>("/setRdsData", {
    table: table,
    data: {
      id: id,
      value: value,
    },
  });
  console.log("setRdsData", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}
