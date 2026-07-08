/**
 * 任务管理 API
 * 提供任务的增删改查功能
 */
import { apiClient } from "./api-client";
import type { ApiResponse, ApiPagedResponse } from "./types";

/**
 * 任务数据结构
 */
export interface Task {
  id?: number;
  name: string;
  start_date: string;
  end_date?: string;
  duration: number;
  user_id: string;
  status?: number; // 1: 进行中, 2: 已结束, 0: 未开始， -1：未开启
  priority?: number; // 任务优先级，数字越小越高；-1 不参与优先级锁定
  type: number; // 0:每日任务；1：持续性任务
  data: string | TaskDetail;
  lock?: boolean; // 任务是否被锁定
  msg?: string; // 锁定提示信息
}

/**
 * 任务详情数据结构
 */
export interface TaskDetail {
  // 每日素材配置
  // key: 天数索引（从0开始）
  // value: 该天的素材列表
  dailyMaterials: Record<
    string,
    Array<{
      id: number;
      name: string;
      type: number;
      status?: Record<string, number>; // key: user_id, value: 1表示完成，0或未定义表示未完成
    }>
  >;
  [key: string]: any;
}

/**
 * 音频文件
 */
export interface AudioFile {
  id: string;
  name: string;
  duration: string;
  path?: string;
}

/**
 * 页面
 */
export interface Page {
  audioIds: string[];
}

/**
 * 素材详情
 */
export interface SubtitleFile {
  path: string;
  label?: string;
  lang?: string;
}

export interface MaterialDetail {
  pdfLength?: number;
  audioList?: AudioFile[];
  subtitleList?: SubtitleFile[];
  remark?: string;
  pages: Page[];
}

/**
 * 素材项数据结构
 */
export interface MaterialItem {
  id: number;
  name: string;
  path: string;
  cate_id: number;
  type: number;
  data?: string | MaterialDetail;
  [key: string]: any;
}

/**
 * 获取任务列表
 * @param userId - 用户ID
 * @param pageNum - 页码，默认1
 * @param pageSize - 每页数量，默认20
 * @param startDate - 开始日期（可选，格式 YYYY-MM-DD）
 * @param endDate - 结束日期（可选，格式 YYYY-MM-DD）
 */
export async function getTaskList(
  userId?: number,
  pageNum: number = 1,
  pageSize: number = 20,
  startDate?: string,
  endDate?: string
): Promise<ApiResponse<ApiPagedResponse<Task>>> {
  // 如果有 userId 和 startDate，使用新的带锁定状态的 API
  if (userId && userId > 0 && startDate) {
    const rsp = await apiClient.get<ApiResponse<ApiPagedResponse<Task>>>("/task/list", {
      params: {
        userId,
        startDate,
        pageNum,
        pageSize,
      },
    });

    if (rsp.data.code !== 0) {
      throw new Error(rsp.data.msg || "获取任务列表失败");
    }

    // 解析 data 字段
    const tasks = rsp.data.data?.data || [];
    rsp.data.data!.data = tasks.map(task => ({
      ...task,
      data: typeof task.data === 'string' ? JSON.parse(task.data) : task.data,
    }));

    return rsp.data;
  }
  
  // 否则使用原有的通用 API
  const params: any = {
    table: "t_task",
    pageNum,
    pageSize,
  };

  // 构建条件
  const conditions: any = {};
  
  if (userId && userId > 0) {
    // 使用 LIKE 条件匹配 user_id 字段（如 "3,4" 中包含 "3"）
    conditions.user_id = { like: `%${userId}%` };
  }
  
  if (startDate) {
    conditions.start_date = { '<=': startDate };
  }
  
  if (endDate) {
    conditions.end_date = { '>=': endDate };
  }
  
  if (Object.keys(conditions).length > 0) {
    params.conditions = JSON.stringify(conditions);
  }

  const rsp = await apiClient.get<ApiResponse<ApiPagedResponse<Task>>>("/getAll", {
    params,
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "获取任务列表失败");
  }

  // 解析 data 字段
  const tasks = rsp.data.data?.data || [];
  rsp.data.data!.data = tasks.map(task => ({
    ...task,
    data: typeof task.data === 'string' ? JSON.parse(task.data) : task.data,
  }));

  return rsp.data;
}

/**
 * 获取单个任务详情
 * @param id - 任务ID
 */
export async function getTask(id: number): Promise<Task> {
  const rsp = await apiClient.get<ApiResponse<Task>>("/getData", {
    params: {
      table: "t_task",
      id,
    },
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "获取任务详情失败");
  }

  return rsp.data.data!;
}

/**
 * 获取素材详情
 * @param id - 素材ID
 */
export async function getMaterial(id: number): Promise<MaterialItem> {
  const rsp = await apiClient.get<ApiResponse<MaterialItem>>("/getData", {
    params: {
      table: "t_material",
      id,
      fields: "*", // 获取所有字段
    },
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "获取素材详情失败");
  }

  return rsp.data.data!;
}

/**
 * 获取素材列表
 * @param pageNum - 页码，默认1
 * @param pageSize - 每页数量，默认20
 */
export async function getMaterialList(
  pageNum: number = 1,
  pageSize: number = 20
): Promise<ApiResponse<ApiPagedResponse<MaterialItem>>> {
  const rsp = await apiClient.get<ApiResponse<ApiPagedResponse<MaterialItem>>>("/getAll", {
    params: {
      table: "t_material",
      pageNum,
      pageSize,
    },
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "获取素材列表失败");
  }

  return rsp.data;
}

/**
 * 批量获取素材详情
 * @param ids - 素材 ID 数组
 */
export async function getMaterialListByIds(ids: number[]): Promise<MaterialItem[]> {
  if (ids.length === 0) return [];
  
  // 构建查询条件：id IN (...)
  const conditions = {
    id: { in: ids }
  };
  
  const rsp = await apiClient.get<ApiResponse<ApiPagedResponse<MaterialItem>>>("/getAll", {
    params: {
      table: "t_material",
      conditions: JSON.stringify(conditions),
      pageNum: 1,
      pageSize: ids.length,
    },
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "批量获取素材失败");
  }

  // 解析 data 字段
  const materials = rsp.data.data?.data || [];
  return materials.map(material => ({
    ...material,
    data: typeof material.data === 'string' ? JSON.parse(material.data) : material.data,
  }));
}

/**
 * 添加任务
 * @param task - 任务数据
 */
export async function addTask(task: Omit<Task, "id">): Promise<Task> {
  const rsp = await apiClient.post<ApiResponse<Task>>("/setData", {
    table: "t_task",
    data: {
      id: -1, // -1 表示新增
      ...task,
    },
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "添加任务失败");
  }

  return rsp.data.data!;
}

/**
 * 更新任务
 * @param task - 任务数据（必须包含 id）
 */
export async function updateTask(task: Task): Promise<Task> {
  const rsp = await apiClient.post<ApiResponse<Task>>("/setData", {
    table: "t_task",
    data: task,
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "更新任务失败");
  }

  return rsp.data.data!;
}

/**
 * 删除任务
 * @param id - 任务ID
 */
export async function deleteTask(id: number): Promise<void> {
  const rsp = await apiClient.post<ApiResponse<void>>("/delData", {
    table: "t_task",
    id,
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "删除任务失败");
  }
}

/**
 * 更新任务进度
 * @param taskId - 任务ID
 * @param materialId - 素材ID
 * @param dayNumber - 第几天
 * @param completed - 是否完成
 */
export async function updateTaskProgress(
  taskId: number,
  materialId: number,
  dayNumber: number,
  completed: boolean
): Promise<Task> {
  // 先获取当前任务
  const task = await getTask(taskId);
  
  // 解析 data 字段
  const taskData = typeof task.data === "string" ? JSON.parse(task.data) : task.data;
  
  // 初始化 progress 对象
  if (!taskData.progress) {
    taskData.progress = {};
  }
  
  // 初始化素材进度
  if (!taskData.progress[materialId]) {
    taskData.progress[materialId] = {};
  }
  
  // 更新进度
  taskData.progress[materialId][String(dayNumber)] = completed ? 1 : 0;
  
  // 更新任务
  return updateTask({
    ...task,
    data: taskData,
  });
}/**
 * 任务日历数据结构
 */
export interface TaskCalendarItem {
  date: string;
  tasks: Array<{
    task_id: number;
    task_name: string;
    completed: number;
    total: number;
    materials: Array<{
      id: number;
      name: string;
      type: number;
      status?: number;
    }>;
  }>;
}

/**
 * 任务日历响应数据
 */
export interface TaskCalendarResponse {
  calendar: Record<string, TaskCalendarItem>;
  year: number;
  month: number;
  days_in_month: number;
}

/**
 * 获取任务日历
 * @param date - 日期(格式 YYYY-MM-DD)
 * @param userId - 用户ID(可选)
 */
export async function getTaskCalendar(date: string, userId?: number): Promise<TaskCalendarResponse> {
  const params: any = { date };
  
  if (userId && userId > 0) {
    params.user_id = userId;
  }
  
  const rsp = await apiClient.post<ApiResponse<TaskCalendarResponse>>("/task/calendar", params);

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "获取任务日历失败");
  }

  return rsp.data.data!;
}/**
 * 完成素材打卡
 * @param taskId - 任务ID
 * @param materialId - 素材ID
 * @param date - 日期(格式 YYYY-MM-DD)
 * @param userId - 用户ID
 */
export async function finishMaterial(
  taskId: number,
  materialId: number,
  date: string,
  userId: number
): Promise<{ score: number }> {
  const rsp = await apiClient.post<ApiResponse<{ success: boolean; score: number }>>("/task/finish", {
    task_id: taskId,
    material_id: materialId,
    date,
    user_id: userId,
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "完成素材打卡失败");
  }

  return rsp.data.data!;
}

/**
 * 申请解锁视频素材（提交审批）
 * @param materialId - 素材ID
 * @param userId - 用户ID
 * @param taskId - 任务ID(可选)
 * @param durationHours - 申请解锁时长(小时)
 */
export async function requestUnlockMaterial(
  materialId: number,
  userId: number,
  taskId?: number,
  durationHours: number = 1
): Promise<{ success: boolean; id: number; replaced: boolean }> {
  const body: any = {
    material_id: materialId,
    user_id: userId,
    duration_hours: durationHours,
  };
  if (taskId) {
    body.task_id = taskId;
  }
  const rsp = await apiClient.post<ApiResponse<{ success: boolean; id: number; replaced: boolean }>>("/material/unlimit/apply", body);

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "申请解锁失败");
  }

  return rsp.data.data!;
}

/** 不限时申请列表项 */
export interface UnlimitApplication {
  id: number;
  user_id: number;
  material_id: number;
  task_id?: number;
  duration_hours: number;
  status: 'pending' | 'approved' | 'denied';
  created_at: string;
  approved_at?: string;
  denied_at?: string;
}

/**
 * 列出不限时申请
 * @param status - 过滤状态，默认 pending
 */
export async function listUnlimitApplications(
  status?: string
): Promise<{ applications: UnlimitApplication[]; total: number }> {
  const params: any = {};
  if (status) {
    params.status = status;
  }
  const rsp = await apiClient.get<ApiResponse<{ applications: UnlimitApplication[]; total: number }>>(
    "/material/unlimit/list",
    { params }
  );

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "获取申请列表失败");
  }

  return rsp.data.data!;
}

/**
 * 批量审批通过不限时申请
 * @param ids - 申请ID列表
 */
export async function approveUnlimitApplications(
  ids: number[]
): Promise<{ approved: number; not_found: number[] }> {
  const rsp = await apiClient.post<ApiResponse<{ approved: number; not_found: number[] }>>(
    "/material/unlimit/approve",
    { ids }
  );

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "审批失败");
  }

  return rsp.data.data!;
}

/**
 * 批量拒绝不限时申请
 * @param ids - 申请ID列表
 */
export async function denyUnlimitApplications(
  ids: number[]
): Promise<{ denied: number; not_found: number[] }> {
  const rsp = await apiClient.post<ApiResponse<{ denied: number; not_found: number[] }>>(
    "/material/unlimit/deny",
    { ids }
  );

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "拒绝失败");
  }

  return rsp.data.data!;
}

