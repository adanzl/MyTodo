/**
 * 文件管理 API
 * 提供文件扫描、目录遍历等功能
 */
import { api } from "./config";

// ==================== 目录列表 API ====================

/**
 * 目录项
 */
export interface DirectoryItem {
    name: string;
    path?: string;
    isDirectory: boolean;
    size?: number;
    modified?: number; // 修改时间戳
    accessible?: boolean;
    subItems?: DirectoryItem[];
}

/**
 * 列出目录内容
 * @param path - 目录路径
 * @param extensions - 文件扩展名过滤，多个用逗号分隔，"all" 表示所有文件
 * @param recursive - 是否递归扫描（用于批量添加目录）
 */
export async function listDirectory(
    path: string,
    extensions: string = "all",
    recursive: boolean = false
): Promise<DirectoryItem[]> {
    const response = await api.get("/listDirectory", {
        params: { path, extensions, recursive }
    });

    if (response.data.code !== 0) {
        throw new Error(response.data.msg || "获取文件列表失败");
    }

    return response.data.data || [];
}
