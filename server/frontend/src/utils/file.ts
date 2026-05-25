/**
 * 文件相关工具函数
 */
import { api } from "@/api/config";
import type { FileItem, NormalizedFile } from "@/types/tools";

const NAME_COLLATOR = new Intl.Collator('en', { numeric: true, sensitivity: 'base' });

function compareByName(a: string, b: string): number {
  return NAME_COLLATOR.compare(a, b);
}

/**
 * 通用排序函数：按名称自然排序（英文/数字在前，中文在后）
 */
export function sortByName<T extends { name: string }>(items: T[]): T[] {
  return items.sort((a, b) => compareByName(a.name, b.name));
}

export type CategoryItem = { id: number; name: string; parent?: number };
export type CategoryTreeNode<T extends CategoryItem = CategoryItem> = T & {
  children: CategoryTreeNode<T>[];
};

/** el-cascader 目录选择器通用配置 */
export const CATEGORY_CASCADER_PROPS = {
  value: 'id',
  label: 'name',
  children: 'children',
  checkStrictly: true,
  emitPath: false,
} as const;

/**
 * 递归按名称自然排序树节点
 */
export function sortTreeByName<T extends { name: string; children?: T[] }>(nodes: T[]): T[] {
  sortByName(nodes);
  for (const node of nodes) {
    if (node.children?.length) {
      sortTreeByName(node.children);
    }
  }
  return nodes;
}

/**
 * 将扁平目录列表构建为已排序的树形结构
 */
export function buildCategoryTree<T extends CategoryItem>(categories: T[]): CategoryTreeNode<T>[] {
  const map = new Map<number, CategoryTreeNode<T>>();
  const roots: CategoryTreeNode<T>[] = [];

  for (const item of categories) {
    if (item.id == null) continue;
    map.set(item.id, { ...item, children: [] });
  }

  for (const item of categories) {
    if (item.id == null) continue;

    const node = map.get(item.id);
    if (!node) continue;

    const parentId = item.parent ?? -1;
    if (parentId === -1 || !map.has(parentId)) {
      roots.push(node);
      continue;
    }

    map.get(parentId)!.children.push(node);
  }

  return sortTreeByName(roots);
}

export type MaterialSortKey = 'name' | 'id';
export type SortOrder = 'asc' | 'desc';

export interface SortMaterialsOptions<T> {
  sortBy?: MaterialSortKey;
  order?: SortOrder;
  isFolderFn?: (item: T) => boolean;
}

/**
 * 素材列表排序：先目录后文件，再按指定字段排序
 */
export function sortMaterials<T extends { id?: number; name: string; type?: string | number; isFolder?: boolean }>(
  items: T[],
  options: SortMaterialsOptions<T> = {}
): T[] {
  const {
    sortBy = 'name',
    order = 'asc',
    isFolderFn,
  } = options;
  const isFolder = isFolderFn ?? ((item: T) => item.type === 'folder' || item.isFolder === true);

  return items.sort((a, b) => {
    const aIsFolder = isFolder(a);
    const bIsFolder = isFolder(b);
    if (aIsFolder !== bIsFolder) {
      return aIsFolder ? -1 : 1;
    }

    let compareResult = 0;
    if (sortBy === 'id') {
      compareResult = (a.id ?? 0) - (b.id ?? 0);
    } else {
      compareResult = compareByName(a.name, b.name);
    }

    if (compareResult !== 0) {
      return order === 'desc' ? -compareResult : compareResult;
    }

    return compareByName(a.name, b.name);
  });
}

/**
 * 从文件项中提取文件名
 */
export function getFileName(fileItem: FileItem | null | undefined): string {
  const filePath = fileItem?.uri || fileItem?.path || fileItem?.file || "";
  return filePath ? String(filePath).split("/").pop() || filePath : "";
}

/**
 * 规范化文件列表格式（对象格式）
 */
export function normalizeFiles(files: FileItem[], includeDuration = true): NormalizedFile[] {
  if (!Array.isArray(files)) return [];
  return files
    .map(fileItem => {
      if (!fileItem || typeof fileItem !== "object") return null;
      const normalized: NormalizedFile = {
        uri: fileItem.uri || "",
      };
      if (includeDuration) {
        normalized.duration = fileItem.duration || null;
      }
      return normalized;
    })
    .filter((item): item is NormalizedFile => item !== null);
}

/**
 * 计算文件列表总时长（秒）
 */
export function calculateFilesTotalDuration(files: FileItem[]): number {
  if (!Array.isArray(files) || files.length === 0) {
    return 0;
  }
  return files.reduce((total, file) => {
    const duration = file?.duration;
    return total + (typeof duration === "number" && duration > 0 ? duration : 0);
  }, 0);
}

/**
 * 获取媒体文件的播放URL
 */
export function getMediaFileUrl(filePath: string): string {
  if (!filePath || typeof filePath !== "string" || filePath.trim() === "") {
    console.warn("getMediaFileUrl: 文件路径无效", filePath);
    return "";
  }

  try {
    const baseURL = api.defaults.baseURL || "";
    if (!baseURL || typeof baseURL !== "string") {
      console.warn("getMediaFileUrl: API baseURL无效", baseURL);
      return "";
    }

    const path = filePath.startsWith("/") ? filePath.slice(1) : filePath;
    if (!path || path.trim() === "") {
      console.warn("getMediaFileUrl: 处理后的路径为空", filePath);
      return "";
    }

    const encodedPath = path
      .split("/")
      .map(part => encodeURIComponent(part))
      .join("/");
    const mediaUrl = `${baseURL}/media/files/${encodedPath}`;

    // 验证生成的 URL
    if (mediaUrl.includes("index.html") || mediaUrl.endsWith(".html")) {
      console.error("getMediaFileUrl: 生成的URL包含HTML页面", { filePath, mediaUrl });
      return "";
    }

    return mediaUrl;
  } catch (error) {
    console.error("getMediaFileUrl: 生成URL时出错", error, { filePath });
    return "";
  }
}
