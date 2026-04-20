/**
 * 素材管理 API
 * 提供素材的增删改查功能
 */
import { getList, getData, setData, delData } from "./api-common";
import type { PaginatedResponse } from "@/types/api";
import type { TaskDetail } from "@/types/tasks/taskDetail";

/**
 * 素材数据结构
 */
export interface Material {
  id?: number;
  name: string;
  path: string;
  cate_id: number;
  type: number;
  data?: string | TaskDetail; // 存储时为 JSON 字符串，读取时可能是对象
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
