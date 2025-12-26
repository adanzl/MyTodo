/**
 * 蓝牙相关 API
 */
import { api } from "./config";

/**
 * 蓝牙操作接口
 */
export async function bluetoothAction(
  action: string,
  method: "GET" | "POST",
  params?: Record<string, any>
): Promise<any> {
  let rsp;
  const routePrefix = "bluetooth";
  if (method === "GET") {
    rsp = await api.get(`/api/${routePrefix}/${action}`, {
      params: params,
    });
  } else {
    rsp = await api.post(`/api/${routePrefix}/${action}`, params);
  }
  return rsp.data;
}


