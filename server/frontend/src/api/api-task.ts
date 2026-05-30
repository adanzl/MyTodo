/**
 * 素材管理 API
 * 提供素材的增删改查功能
 */
import { getList, getData, setData, delData } from "./api-common";
import { api } from "./config";
import type { PaginatedResponse } from "@/types/api";
import type { TaskDetail } from "@/types/tasks/taskDetail";
import type { MaterialDetail } from "@/types/tasks/materialDetail";

/**
 * 素材数据结构
 */
export interface Material {
  id?: number;
  name: string;
  path: string;
  cate_id: number;
  type: number;
  data?: string | MaterialDetail; // 存储时为 JSON 字符串，读取时可能是对象
}

/**
 * 素材项数据结构（用于任务预览等场景）
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
 * 素材分类数据结构
 */
export interface MaterialCategory {
  id: number;
  name: string;
  parent?: number; // 父级ID，-1表示顶级目录
}

/**
 * 获取素材列表（支持基于 cate_id 筛选）
 * @param cateId - 分类ID，可选
 * @param pageNum - 页码，默认1
 * @param pageSize - 每页数量，默认20
 */
export async function getMaterialList(
  cateId?: number,
  pageNum: number = 1,
  pageSize: number = 20
): Promise<PaginatedResponse<Material>> {
  const conditions = cateId !== undefined && cateId !== null ? { cate_id: cateId } : undefined;
  return getList<Material>("t_material", conditions, pageNum, pageSize);
}

/**
 * 获取单个素材详情
 * @param id - 素材ID
 */
export async function getMaterial(id: number, fields?: string): Promise<Material> {
  return getData<Material>("t_material", id, fields);
}

/**
 * 添加素材
 * @param material - 素材数据
 */
export async function addMaterial(material: Omit<Material, "id">): Promise<Material> {
  return setData<Material>("t_material", {
    id: -1, // -1 表示新增
    ...material,
  });
}

/**
 * 更新素材
 * @param material - 素材数据（必须包含 id）
 */
export async function updateMaterial(material: Material): Promise<Material> {
  return setData<Material>("t_material", material as unknown as Record<string, unknown>);
}

/**
 * 删除素材
 * @param id - 素材ID
 */
export async function deleteMaterial(id: number): Promise<void> {
  await delData("t_material", id);
}

// ==================== 素材分类 API ====================

/**
 * 获取素材分类列表
 * @param pageNum - 页码，默认1
 * @param pageSize - 每页数量，默认20
 * @param parent - 父级ID筛选（可选），不传则获取所有分类
 */
export async function getMaterialCategoryList(
  pageNum: number = 1,
  pageSize: number = 20,
  parent?: number | null
): Promise<PaginatedResponse<MaterialCategory>> {
  const conditions = parent !== undefined && parent !== null ? { parent } : undefined;
  return getList<MaterialCategory>("t_material_category", conditions, pageNum, pageSize);
}

/**
 * 获取单个素材分类详情
 * @param id - 分类ID
 */
export async function getMaterialCategory(id: number): Promise<MaterialCategory> {
  return getData<MaterialCategory>("t_material_category", id);
}

/**
 * 添加素材分类
 * @param category - 分类数据
 */
export async function addMaterialCategory(
  category: Omit<MaterialCategory, "id">
): Promise<MaterialCategory> {
  return setData<MaterialCategory>("t_material_category", {
    id: -1, // -1 表示新增
    ...category,
  });
}

/**
 * 更新素材分类
 * @param category - 分类数据（必须包含 id）
 */
export async function updateMaterialCategory(
  category: MaterialCategory
): Promise<MaterialCategory> {
  return setData<MaterialCategory>(
    "t_material_category",
    category as unknown as Record<string, unknown>
  );
}

/**
 * 删除素材分类
 * @param id - 分类ID
 * @param deleteMaterials - 是否删除类别下的素材，默认 false
 */
export async function deleteMaterialCategory(
  id: number,
  deleteMaterials: boolean = false
): Promise<void> {
  const response = await api.post("/material/category/delete", {
    id,
    deleteMaterials,
  });
  if (response.data.code !== 0) {
    throw new Error(response.data.msg || "删除失败");
  }
}

/**
 * 获取素材的父目录链
 * @param materialId - 素材ID
 */
export async function getMaterialParentChain(
  materialId: number
): Promise<Array<{ id: number; name: string; parent?: number | null }>> {
  const response = await api.get("/task/parent", {
    params: { materialId },
  });
  if (response.data.code !== 0) {
    throw new Error(response.data.msg || "获取父目录链失败");
  }
  return response.data.data || [];
}

// ==================== 任务管理 API ====================

/**
 * 任务数据结构
 */
export interface Task {
  id?: number;
  name: string;
  start_date: string;
  end_date: string;
  duration: number;
  user_id: string;
  /** 休息日规则(JSON 或 JSON字符串)。0=周日..6=周六；dates/work_dates 为 YYYY-MM-DD；null 表示清空 */
  rest_days?: string | { weekdays?: number[]; dates?: string[]; work_dates?: string[] } | null;
  status?: number; // 1: 进行中, 2: 已结束, 0: 未开始， -1：未开启
  priority?: number; // 任务优先级 数字越小优先级越高，高优先级任务没有完成低优先级任务会锁定
  type: number; // 0:每日任务；1：持续性任务
  data: string | TaskDetail;
  pre_todo?: string; // 前置日程JSON字符串，格式：{"user_id": [todo_ids]}
  block_time?: TaskBlockTimeRule[];
  lock?: boolean; // 任务是否锁定
  msg?: string; // 锁定提示信息
}

export interface TaskBlockTimeSlot {
  start: string;
  end: string;
}

export interface TaskBlockTimeRule {
  role: string;
  time: TaskBlockTimeSlot[];
}

/** 取 common 规则的禁用时段（列表展示、编辑表单用） */
export function getCommonBlockTimeSlots(rules?: unknown): TaskBlockTimeSlot[] {
  if (!rules) return [];
  // 约定：后端存/返 JSON string；这里不做过多兜底校验
  const arr = (typeof rules === "string" ? (JSON.parse(rules) as TaskBlockTimeRule[]) : (rules as TaskBlockTimeRule[])) ?? [];
  const rule = arr.find((r) => r.role === "common" || !r.role);
  return rule?.time?.filter((s) => s.start && s.end) ?? [];
}

/**
 * 获取任务列表
 * @param userId - 用户ID（可选）
 * @param pageNum - 页码，默认1
 * @param pageSize - 每页数量，默认20
 * @param startDate - 查询范围开始日期（格式 YYYY-MM-DD）
 * @param endDate - 查询范围结束日期（可选，缺省时等于 startDate）
 */
export async function getTaskList(
  userId?: number,
  pageNum: number = 1,
  pageSize: number = 20,
  startDate?: string,
  endDate?: string
): Promise<PaginatedResponse<Task>> {
  const params: Record<string, any> = {
    pageNum,
    pageSize,
  };

  if (userId && userId > 0) {
    params.userId = userId;
  }

  if (startDate) {
    params.startDate = startDate;
    params.endDate = endDate ?? startDate;
  }

  const response = await api.get("/task/list", { params });
  const result = response.data as PaginatedResponse<Task>;
  return result;
}

/**
 * 获取单个任务详情
 * @param id - 任务ID
 */
export async function getTask(id: number, fields?: string): Promise<Task> {
  return await getData<Task>("t_task", id, fields);
}

/**
 * 添加任务
 * @param task - 任务数据
 */
export async function addTask(task: Omit<Task, "id">): Promise<Task> {
  const response = await api.post("/task/update", task as unknown as Record<string, unknown>);
  const result = response.data as { code: number; msg?: string; data?: Task };
  if (result.code !== 0 || !result.data) {
    throw new Error(result.msg || "添加任务失败");
  }
  return result.data;
}

/**
 * 更新任务
 * @param task - 任务数据（必须包含 id）
 */
export async function updateTask(task: Task): Promise<Task> {
  const response = await api.post("/task/update", task as unknown as Record<string, unknown>);
  const result = response.data as { code: number; msg?: string; data?: Task };
  if (result.code !== 0 || !result.data) {
    throw new Error(result.msg || "更新任务失败");
  }
  return result.data;
}

/**
 * 删除任务
 * @param id - 任务ID
 */
export async function deleteTask(id: number): Promise<void> {
  await delData("t_task", id);
}

/**
 * 批量获取素材详情
 * @param ids - 素材 ID 数组
 */
export async function getMaterialListByIds(ids: number[]): Promise<MaterialItem[]> {
  if (ids.length === 0) return [];

  // 构建查询条件：id IN (...)
  const conditions = {
    id: { in: ids },
  };

  const response = await getList<Material>("t_material", conditions, 1, ids.length);

  if (response.code !== 0 || !response.data) {
    throw new Error(response.msg || "批量获取素材失败");
  }

  // 解析 data 字段并转换为 MaterialItem
  const materials = response.data.data || [];
  return materials.map(material => ({
    ...material,
    id: material.id!, // 确保 id 存在
    data: typeof material.data === "string" ? JSON.parse(material.data) : material.data,
  })) as MaterialItem[];
}

/**
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
      status?: Record<string, number>; // key: user_id, value: 1表示完成
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
export async function getTaskCalendar(
  date: string,
  userId?: number
): Promise<TaskCalendarResponse> {
  const params: any = { date };

  if (userId && userId > 0) {
    params.user_id = userId;
  }

  const response = await api.post("/task/calendar", params);

  if (response.data.code !== 0) {
    throw new Error(response.data.msg || "获取任务日历失败");
  }

  return response.data.data!;
}

// ==================== 任务历史记录 API ====================

/**
 * 任务历史记录数据结构
 */
export interface TaskHistory {
  id?: number;
  user_id: number;
  task_id: number;
  material_id: number;
  reward?: number;
  dt?: string;
  state?: number;
  date_str: string;
}

/**
 * 获取任务历史记录列表
 * @param userId - 用户ID（可选）
 * @param taskId - 任务ID（可选）
 * @param pageNum - 页码，默认1
 * @param pageSize - 每页数量，默认20
 */
export async function getTaskHistoryList(
  userId?: number,
  taskId?: number,
  pageNum: number = 1,
  pageSize: number = 20
): Promise<PaginatedResponse<TaskHistory>> {
  const conditions: Record<string, any> = {};

  if (userId && userId > 0) {
    conditions.user_id = userId;
  }

  if (taskId && taskId > 0) {
    conditions.task_id = taskId;
  }

  return getList<TaskHistory>("t_task_history", conditions, pageNum, pageSize);
}
