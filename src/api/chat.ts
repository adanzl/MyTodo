import { apiClient } from "./api-client";
import type { ApiResponse, RdsKeyValueBody } from "./types";

async function getRdsData(
  table: string,
  id: number | string
): Promise<string | null> {
  const rsp = await apiClient.get<ApiResponse<string | null>>("/getRdsData", {
    params: { table, id },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data ?? null;
}

async function setRdsData(
  table: string,
  id: number,
  value: string
): Promise<void> {
  const body: RdsKeyValueBody = { id, value };
  const rsp = await apiClient.post<ApiResponse<unknown>>("/setRdsData", {
    table,
    data: body,
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
}

export async function getConversationId(id: number): Promise<string | null> {
  return getRdsData("conversation:id", id);
}

export async function setConversationId(id: number, cId: string): Promise<void> {
  return setRdsData("conversation:id", id, cId);
}

export async function getChatSetting(id: number): Promise<string | null> {
  return getRdsData("chatSetting", id);
}

export async function setChatSetting(id: number, cId: string): Promise<void> {
  return setRdsData("chatSetting", id, cId);
}

export async function getChatMessages(
  key: string,
  startId: number | string | undefined,
  pageSize: number
): Promise<unknown> {
  const rsp = await apiClient.get<ApiResponse<unknown>>("/getRdsList", {
    params: { key: "chat:" + key, pageSize, startId },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

export async function getAiChatMessages(
  conversation_id: string,
  limit: number,
  user: string,
  first_id?: string | number
): Promise<unknown> {
  const rsp = await apiClient.get<ApiResponse<unknown>>("/chatMessages", {
    params: { conversation_id, limit, user, first_id },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

/** id 为 user id（number）或 conversation id（string），视后端约定使用 */
export async function getChatMem(id: number | string): Promise<string | null> {
  return getRdsData("mem", id);
}

export async function setChatMem(id: number, cId: string): Promise<void> {
  return setRdsData("mem", id, cId);
}
