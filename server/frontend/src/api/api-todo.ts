import { api } from "./config";
import type { ApiResponse } from "@/types/api";

export interface ScheduleData {
  id: number;
  user_id: number;
  title: string;
  startTs: string;
  endTs: string;
  allDay: boolean;
  order: number;
  reminder: string;
  repeat: string;
  repeatEndTs: string;
  score?: number;
  subtasks?: Array<{
    id: number;
    name?: string;
    title?: string;
  }>;
}

/**
 * 获取待办事项列表
 * @param userId - 用户ID
 * @param pageNum - 页码
 * @param pageSize - 每页数量
 * @returns 待办事项列表数据
 */
export async function getTodoList(
  userId: number,
  pageNum: number = 1,
  pageSize: number = 20
): Promise<{ data: ScheduleData[]; totalCount: number; pageNum: number; pageSize: number }> {
  const rsp = await api.get<ApiResponse<any>>("/todo/list", {
    params: {
      user_id: userId,
      page_num: pageNum,
      page_size: pageSize,
    },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

/**
 * 按时间范围获取待办事项列表
 * @param startTime - 开始时间（格式：YYYY-MM-DD）
 * @param endTime - 结束时间（格式：YYYY-MM-DD）
 * @param userId - 用户ID
 * @returns 待办事项列表数据
 */
export async function getTodoListByTime(
  startTime: string,
  endTime: string,
  userId: number
): Promise<{ data: ScheduleData[]; totalCount: number; pageNum: number; pageSize: number }> {
  const rsp = await api.get<ApiResponse<any>>("/todo/listByTime", {
    params: {
      start_time: startTime,
      end_time: endTime,
      user_id: userId,
    },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data;
}

/**
 * 获取单个待办事项详情
 * @param todoId - 待办事项ID
 * @param date - 日期（格式：YYYY-MM-DD）
 * @param userId - 用户ID
 * @returns 待办事项完整数据
 */
export async function getTodo(todoId: number, date: string, userId: number): Promise<ScheduleData> {
  const rsp = await api.get<ApiResponse<ScheduleData>>("/todo/get", {
    params: { id: todoId, date, user_id: userId },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data!;
}

/**
 * 创建新待办事项
 * @param scheduleData - 待办事项数据（部分字段）
 * @returns 新建待办的ID
 */
export async function createTodo(scheduleData: Partial<ScheduleData>): Promise<number> {
  const rsp = await api.post<ApiResponse<{ id: number }>>("/todo/create", scheduleData);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data!.id;
}

/**
 * 更新待办事项
 * @param todoId - 待办事项ID
 * @param scheduleData - 待更新的待办数据（部分字段）
 */
export async function updateTodo(
  todoId: number,
  scheduleData: Partial<ScheduleData>
): Promise<void> {
  const rsp = await api.post<ApiResponse<unknown>>("/todo/update", {
    id: todoId,
    ...scheduleData,
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
}

/**
 * 保存待办事项（创建或更新）
 * @param scheduleSave - 待保存的待办数据（包含ID则为更新，否则为创建）
 */
export async function saveTodo(scheduleSave: Partial<ScheduleData>): Promise<void> {
  const rsp = await api.post<ApiResponse<unknown>>("/todo/save", scheduleSave);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
}

/**
 * 删除待办事项
 * @param todoId - 待办事项ID
 */
export async function deleteTodo(todoId: number): Promise<void> {
  const rsp = await api.post<ApiResponse<unknown>>("/todo/delete", { id: todoId });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
}
