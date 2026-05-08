import { apiClient } from "./api-client";
import type { ApiResponse } from "./types";
import type { ScheduleData, ScheduleSave } from "@/types/user-data";

export interface GetTodoCalendarResponse {
  [date: string]: ScheduleData[];
}

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

export async function createTodo(scheduleData: Partial<ScheduleData>): Promise<number> {
  const rsp = await apiClient.post<ApiResponse<{ id: number }>>("/todo/create", scheduleData);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data!.id;
}

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

export async function saveTodo(scheduleSave: Partial<ScheduleSave>): Promise<void> {
  const rsp = await apiClient.post<ApiResponse<unknown>>("/todo/save", scheduleSave);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
}
