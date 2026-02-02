import _ from "lodash";
import { apiClient } from "./api-client";
import type {
  ApiResponse,
  UserInfo,
  SetUserDataPayload,
  GetUserListResponse,
  UserListItem,
  AddScoreBody,
} from "./types";

/** 用户列表缓存时长（毫秒），5 分钟内不重复请求 */
const USER_LIST_CACHE_MS = 5 * 60 * 1000;
let userListCache: { data: GetUserListResponse; ts: number } | null = null;
let userListPending: Promise<GetUserListResponse> | null = null;

async function fetchUserList(): Promise<GetUserListResponse> {
  const rsp = await apiClient.get<ApiResponse<GetUserListResponse>>("/getAllUser");
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  const payload = rsp.data.data!;
  _.forEach(payload.data, (item: UserListItem) => {
    if (item.wish_list && typeof item.wish_list === "string") {
      item.wish_list = JSON.parse(item.wish_list) as UserListItem["wish_list"];
    }
  });
  return payload;
}

/**
 * 获取用户列表（带缓存）
 * @param force 是否强制刷新，忽略缓存
 */
export async function getUserList(force = false): Promise<GetUserListResponse> {
  const now = Date.now();
  if (!force && userListCache && now - userListCache.ts < USER_LIST_CACHE_MS) {
    return userListCache.data;
  }
  if (userListPending) {
    return userListPending;
  }
  userListPending = fetchUserList();
  try {
    const data = await userListPending;
    userListCache = { data, ts: Date.now() };
    return data;
  } finally {
    userListPending = null;
  }
}

/** 清除用户列表缓存（修改用户数据后调用，如 addScore、setUserData） */
export function clearUserListCache(): void {
  userListCache = null;
}

export async function getUserInfo(id: number): Promise<UserInfo> {
  const rsp = await apiClient.get<ApiResponse<UserInfo>>("/getData", {
    params: { table: "t_user", id, fields: "id,score" },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data!;
}

export async function setUserData(data: SetUserDataPayload): Promise<void> {
  const rsp = await apiClient.post<ApiResponse<unknown>>("/setData", {
    table: "t_user",
    data,
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  clearUserListCache();
}

export async function addScore(
  user: number,
  action: string,
  value: number,
  msg: string
): Promise<void> {
  const body: AddScoreBody = { user, action, value, msg };
  const rsp = await apiClient.post<ApiResponse<unknown>>("/addScore", body);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  clearUserListCache();
}
