/**
 * 金币相关 API
 */
import { api } from "./config";
import type { ApiResponse } from "@/types/api";

/**
 * 变更金币
 */
export async function addCoin(
  user: number | string,
  action: string,
  value: number,
  msg: string
): Promise<{ success: boolean }> {
  const rsp = await api.post<ApiResponse<{ success: boolean }>>("/addCoin", {
    user,
    action,
    value,
    msg,
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }

  return rsp.data.data;
}
