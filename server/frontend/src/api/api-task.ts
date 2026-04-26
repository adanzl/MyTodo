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
  const conditions = cateId ? { cate_id: cateId } : undefined;
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
 */
export async function getMaterialCategoryList(
  pageNum: number = 1,
  pageSize: number = 20
): Promise<PaginatedResponse<MaterialCategory>> {
  return getList<MaterialCategory>("t_material_category", undefined, pageNum, pageSize);
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
 */
export async function deleteMaterialCategory(id: number): Promise<void> {
  await delData("t_material_category", id);
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
  status?: number; // 1: 进行中, 2: 已结束, 0: 未开始， -1：未开启
  data: string | TaskDetail;
}

/**
 * 获取任务列表
 * @param userId - 用户ID（可选，使用LIKE匹配）
 * @param pageNum - 页码，默认1
 * @param pageSize - 每页数量，默认20
 * @param startDate - 开始日期（可选，格式 YYYY-MM-DD），查询 start_date <= startDate 的任务
 * @param endDate - 结束日期（可选，格式 YYYY-MM-DD），查询 end_date >= endDate 的任务
 */
export async function getTaskList(
  userId?: number,
  pageNum: number = 1,
  pageSize: number = 20,
  startDate?: string,
  endDate?: string
): Promise<PaginatedResponse<Task>> {
  const conditions: Record<string, any> = {};
  if (userId && userId > 0) {
    // 使用 LIKE 条件匹配 user_id 字段（如 "3,4" 中包含 "3"）
    conditions.user_id = { like: `%${userId}%` };
  }

  // 添加日期范围查询条件
  if (startDate) {
    conditions.start_date = { '<=': startDate };
  }
  if (endDate) {
    conditions.end_date = { '>=': endDate };
  }

  return getList<Task>(
    "t_task",
    Object.keys(conditions).length > 0 ? conditions : undefined,
    pageNum,
    pageSize
  );
}

/**
 * 获取单个任务详情
 * @param id - 任务ID
 */
export async function getTask(id: number, fields?: string): Promise<Task> {
  return getData<Task>("t_task", id, fields);
}

/**
 * 添加任务
 * @param task - 任务数据
 */
export async function addTask(task: Omit<Task, "id">): Promise<Task> {
  return setData<Task>("t_task", {
    id: -1, // -1 表示新增
    ...task,
  });
}

/**
 * 更新任务
 * @param task - 任务数据（必须包含 id）
 */
export async function updateTask(task: Task): Promise<Task> {
  return setData<Task>("t_task", task as unknown as Record<string, unknown>);
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
    id: { in: ids }
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
    data: typeof material.data === 'string' ? JSON.parse(material.data) : material.data,
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
  
  const response = await api.post("/task/calendar", params);
  
  if (response.data.code !== 0) {
    throw new Error(response.data.msg || "获取任务日历失败");
  }

  return response.data.data!;
}
