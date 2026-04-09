/**
 * 积分相关 API
 */
import { api } from "./config";
import type { ApiResponse, PaginatedResponse } from "@/types/api";
import type { User } from "@/types/user";

export interface ScoreHistory {
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
 * 获取积分历史记录列表
 */
export async function getScoreHistoryList(
  conditions?: Record<string, unknown>,
  pageNum?: number,
  pageSize?: number
): Promise<PaginatedResponse<ScoreHistory>> {
  const params: Record<string, unknown> = { table: "t_score_history" };
  if (conditions) params.conditions = JSON.stringify(conditions);
  if (pageNum) params.pageNum = pageNum;
  if (pageSize) params.pageSize = pageSize;

  const response = await api.get("/getAll", { params });
  return response.data;
}

/**
 * 变更积分
 */
export async function addScore(
  user: number | string,
  action: string,
  value: number,
  msg: string
): Promise<{ success: boolean }> {
  const rsp = await api.post<ApiResponse<{ success: boolean }>>("/addScore", {
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
