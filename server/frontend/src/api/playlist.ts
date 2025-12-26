/**
 * 播放列表相关 API
 */
import { api } from "./config";

/**
 * 播放列表操作接口
 */
export async function playlistAction(
  action: string,
  method: "GET" | "POST",
  params: Record<string, any> = {}
): Promise<any> {
  let rsp;
  if (method === "GET") {
    rsp = await api.get(`/api/playlist/${action}`, {
      params: params,
    });
  } else {
    rsp = await api.post(`/api/playlist/${action}`, params);
  }
  return rsp.data;
}


