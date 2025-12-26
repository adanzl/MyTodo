/**
 * Cron 定时任务相关 API
 */
import { api } from "./config";

/**
 * Cron 定时任务操作接口
 */
export async function cronAction(
  action: string,
  method: "GET" | "POST",
  params: Record<string, any> = {}
): Promise<any> {
  let rsp;
  if (method === "GET") {
    rsp = await api.get(`/api/cron/${action}`, {
      params: params,
    });
  } else {
    rsp = await api.post(`/api/cron/${action}`, params);
  }
  return rsp.data;
}


