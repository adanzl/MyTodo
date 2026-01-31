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
}

export async function getUserList(): Promise<GetUserListResponse> {
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
}
