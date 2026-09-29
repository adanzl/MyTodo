import { apiClient } from "./api-client";
import type { ApiResponse } from "./types";
import type { ScheduleData, ScheduleOverridePayload, ScheduleSave } from "@/types/user-data";
import dayjs from "dayjs";

export interface GetTodoCalendarResponse {
  [date: string]: ScheduleData[];
}

/** 转为纯日期字符串 YYYY-MM-DD */
function serializeDate(v: any): any {
  if (dayjs.isDayjs(v)) return v.format("YYYY-MM-DD");
  return v;
}

function serializeScheduleData(data: any): any {
  return {
    ...data,
    startTs: serializeDate(data.startTs),
    endTs: serializeDate(data.endTs),
    repeatEndTs: serializeDate(data.repeatEndTs),
  };
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
  const rsp = await apiClient.get<ApiResponse<GetTodoCalendarResponse>>("/todo/calendar", {
    params: { startTime: startTime, endTime: endTime, userId: userId },
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
  const rsp = await apiClient.post<ApiResponse<{ id: number }>>("/todo/create", serializeScheduleData(scheduleData));
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
  const rsp = await apiClient.post<ApiResponse<unknown>>("/todo/update", serializeScheduleData({
    id: todoId,
    ...scheduleData,
  }));
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

/** 从弹窗数据构建当天覆盖 payload（含子任务定义，不含完成状态） */
export function buildScheduleOverridePayload(data: ScheduleData): ScheduleOverridePayload {
  return {
    title: data.title,
    color: data.color,
    priority: data.priority,
    groupId: data.groupId,
    order: data.order,
    score: data.score,
    subtasks: data.subtasks?.map((st) => ({
      id: st.id,
      name: st.name,
      order: st.order,
      score: st.score,
      imgIds: st.imgIds?.length ? [...st.imgIds] : [],
    })),
  };
}

export type TodoSavePayload = Partial<Omit<ScheduleSave, "scheduleOverride">> & {
  scheduleOverride?: ScheduleOverridePayload;
  schedule_override?: ScheduleOverridePayload;
  scheduleId?: number;
  schedule_id?: number;
};

/** 转为后端 /todo/save 约定的 snake_case 字段 */
function serializeScheduleSave(scheduleSave: TodoSavePayload): Record<string, unknown> {
  const {
    scheduleId,
    scheduleOverride,
    schedule_id: scheduleIdSnake,
    schedule_override: scheduleOverrideSnake,
    ...rest
  } = scheduleSave;
  const body: Record<string, unknown> = { ...rest };
  const sid = scheduleId ?? scheduleIdSnake;
  if (sid !== undefined) {
    body.schedule_id = sid;
  }
  const override = scheduleOverride ?? scheduleOverrideSnake;
  if (override !== undefined) {
    body.schedule_override = override;
  }
  return body;
}

/**
 * 保存待办事项（创建或更新）
 * @param scheduleSave - 待保存的待办数据（包含ID则为更新，否则为创建）
 */
export async function saveTodo(scheduleSave: TodoSavePayload): Promise<void> {
  const rsp = await apiClient.post<ApiResponse<unknown>>(
    "/todo/save",
    serializeScheduleSave(scheduleSave)
  );
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
