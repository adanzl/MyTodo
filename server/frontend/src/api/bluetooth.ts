/**
 * 蓝牙相关 API
 */
import { api } from "./config";
import type { ApiResponse } from "@/types/api";

/**
 * 蓝牙操作接口
 */
export async function bluetoothAction(
  action: string,
  method: "GET" | "POST",
  params?: Record<string, unknown>
): Promise<ApiResponse<unknown>> {
  let rsp;
  const routePrefix = "bluetooth";
  if (method === "GET") {
    rsp = await api.get(`/${routePrefix}/${action}`, {
      params: params,
    });
  } else {
    rsp = await api.post(`/${routePrefix}/${action}`, params);
  }
  return rsp.data;
}
