/**
 * 用户相关 API
 */
import { api } from "./config";
import { UData, type UserData } from "@/types";
import type { ApiResponse } from "@/types/api";
import type { PaginatedResponse } from "@/types/api";

/**
 * 获取用户列表（与 getAll 传 table=t_user 时返回格式一致）
 */
export async function getAllUser<T = unknown>(
  params?: { pageNum?: number; pageSize?: number; fields?: string; conditions?: string }
): Promise<PaginatedResponse<T>> {
  const response = await api.get("/getAllUser", { params: params || {} });
  return response.data;
}

/**
 * 获取用户数据（日程）
 */
export async function getSave(id: number | string): Promise<UserData> {
  if (id === undefined) {
    throw new Error("id is undefined");
  }

  const rsp = await api.get<ApiResponse<{ data: string; user_id: number }>>("/getData", {
    params: { id, table: "t_schedule", fields: "data,user_id" },
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  const ret = UData.parseUserData(rsp.data.data.data);
  ret.userId = rsp.data.data.user_id;
  return ret;
}

/**
 * 设置用户信息
 */
export async function setUserInfo(
  id: number | string,
  score: number
): Promise<{ id: number; score: number }> {
  const rsp = await api.post<ApiResponse<{ id: number; score: number }>>("/setData", {
    table: "t_user",
    data: { id, score },
  });

  console.log("setUserInfo", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }

  return rsp.data.data;
}

/**
 * 获取用户信息
 */
export async function getUserInfo(id: number | string): Promise<{ id: number; score: number }> {
  const rsp = await api.get<ApiResponse<{ id: number; score: number }>>("/getData", {
    params: { table: "t_user", id, fields: "id,score" },
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }

  return rsp.data.data;
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

  console.log("addScore", rsp.data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }

  return rsp.data.data;
}

/**
 * 撤销一次抽奖：删除该条积分历史、恢复用户积分、补充对应礼物库存
 */
export async function undoLottery(historyId: number): Promise<{ user_id: number; score: number }> {
  const rsp = await api.post<ApiResponse<{ user_id: number; score: number }>>("/undoLottery", {
    history_id: historyId,
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }

  return rsp.data.data;
}
