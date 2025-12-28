/**
 * 用户相关 API
 */
import { api } from "./config";
import { UData, type UserData } from "@/models";

interface ApiResponse<T = any> {
  code: number;
  msg?: string;
  data: T;
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
export async function setUserInfo(id: number | string, score: number): Promise<any> {
  const rsp = await api.post<ApiResponse>("/setData", {
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
): Promise<any> {
  const rsp = await api.post<ApiResponse>("/addScore", {
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
