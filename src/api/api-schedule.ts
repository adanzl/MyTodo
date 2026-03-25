import EventBus, { C_EVENT } from "@/types/EventBus";
import { UData, UserData } from "@/types/UserData";
import { apiClient } from "./api-client";
import type {
  ApiResponse,
  GetSaveResponseData,
  SetSaveDataBody,
  ScheduleListItem,
  ApiListResponse,
} from "./types";

export async function getSave(id: number): Promise<UserData> {
  if (id === undefined) {
    throw new Error("id is undefined");
  }
  const rsp = await apiClient.get<ApiResponse<GetSaveResponseData>>("/getData", {
    params: { id, table: "t_schedule", fields: "data,user_id" },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  const raw = rsp.data.data!;
  const ret: UserData = UData.parseUserData(raw.data);
  ret.userId = raw.user_id;
  EventBus.$emit(C_EVENT.UPDATE_SAVE, ret);
  return ret;
}

export function setSave(
  id: number | undefined,
  data: unknown
): Promise<void> {
  return new Promise((resolve, reject) => {
    if (id === undefined) {
      reject(new Error("id is undefined"));
      return;
    }
    const body: SetSaveDataBody = {
      id,
      data: JSON.stringify(data),
    };
    apiClient
      .post<ApiResponse<unknown>>("/setData", {
        table: "t_schedule",
        data: body,
      })
      .then((res) => {
        if (res.data.code === 0) {
          EventBus.$emit(C_EVENT.UPDATE_SAVE, data);
          resolve();
        } else {
          reject(new Error(res.data.msg));
        }
      })
      .catch(reject);
  });
}

export async function getScheduleList(): Promise<ApiListResponse<ScheduleListItem>> {
  const rsp = await apiClient.get<ApiResponse<ApiListResponse<ScheduleListItem>>>(
    "/getAll",
    { params: { table: "t_schedule", fields: "id,name,user_id" } }
  );
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data!;
}
