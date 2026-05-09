import { apiClient } from "./api-client";
import type { ApiResponse } from "./types";
import type { ScheduleData, ScheduleSave } from "@/types/user-data";

export interface GetTodoCalendarResponse {
  [date: string]: ScheduleData[];
}

/**
 * 获取日程日历数据
 * @param startTime - 开始时间（格式：YYYY-MM-DD）
 * @param endTime - 结束时间（格式：YYYY-MM-DD）
 * @param userId - 用户ID
 * @returns 按日期分组的日程数据对象
 */
export async function getTodoCalendar(
  startTime: string,
  endTime: string,
  userId: number
): Promise<GetTodoCalendarResponse> {
  const rsp = await apiClient.get<ApiResponse<GetTodoCalendarResponse>>(
    "/todo/calendar",
    {
      params: { start_time: startTime, end_time: endTime, user_id: userId },
    }
  );
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
  const rsp = await apiClient.post<ApiResponse<{ id: number }>>("/todo/create", scheduleData);
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
  const rsp = await apiClient.post<ApiResponse<unknown>>("/todo/update", {
    id: todoId,
    ...scheduleData,
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
}

/**
 * 获取单个待办事项详情
 * @param todoId - 待办事项ID
 * @param date - 日期（格式：YYYY-MM-DD）
 * @param userId - 用户ID
 * @returns 待办事项完整数据
 */
export async function getTodo(
  todoId: number,
  date: string,
  userId: number
): Promise<ScheduleData> {
  const rsp = await apiClient.get<ApiResponse<ScheduleData>>("/todo/get", {
    params: { id: todoId, date, user_id: userId },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data!;
}

/**
 * 保存待办事项（创建或更新）
 * @param scheduleSave - 待保存的待办数据（包含ID则为更新，否则为创建）
 */
export async function saveTodo(scheduleSave: Partial<ScheduleSave>): Promise<void> {
  const rsp = await apiClient.post<ApiResponse<unknown>>("/todo/save", scheduleSave);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
}

/**
 * 删除待办事项
 * @param todoId - 待办事项ID
 */
export async function deleteTodo(todoId: number): Promise<void> {
  const rsp = await apiClient.post<ApiResponse<unknown>>("/todo/delete", { id: todoId });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
}
