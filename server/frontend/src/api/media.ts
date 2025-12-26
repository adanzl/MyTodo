/**
 * 媒体相关 API
 */
import { api } from "./config";

/**
 * 媒体操作接口
 */
export async function mediaAction(
  action: string,
  method: "GET" | "POST",
  params: Record<string, any> = {}
): Promise<any> {
  let rsp;
  if (method === "GET") {
    rsp = await api.get(`/api/media/${action}`, {
      params: params,
    });
  } else {
    rsp = await api.post(`/api/media/${action}`, params);
  }
  return rsp.data;
}


