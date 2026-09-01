/**
 * 金币相关 API
 */
import { api } from "./config";
import type { ApiResponse, PaginatedResponse } from "@/types/api";
import type { User } from "@/types/user";

export interface CoinHistory {
  id: number;
  user_id: number;
  value: number;
  action: string;
  pre_value: number;
  current: number;
  msg: string;
  dt: string;
  out_key?: string;
  user?: User;
}

/**
 * 获取金币历史记录列表
 */
export async function getCoinHistoryList(
  conditions?: Record<string, unknown>,
  pageNum?: number,
  pageSize?: number
): Promise<PaginatedResponse<CoinHistory>> {
  const params: Record<string, unknown> = { table: "t_coin_history" };
  if (conditions) params.conditions = JSON.stringify(conditions);
  if (pageNum) params.pageNum = pageNum;
  if (pageSize) params.pageSize = pageSize;

  const response = await api.get("/getAll", { params });
  return response.data;
}

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
