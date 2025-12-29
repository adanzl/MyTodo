/**
 * 通用文件相关类型定义
 */

/**
 * 文件项接口（用于工具函数）
 * 兼容多种文件格式
 */
export interface FileItem {
  /**
   * 文件URI
   */
  uri?: string;
  /**
   * 文件路径
   */
  path?: string;
  /**
   * 文件字段（备用）
   */
  file?: string;
  /**
   * 文件时长（秒）
   */
  duration?: number | null;
  /**
   * 允许扩展字段
   */
  [key: string]: unknown;
}

/**
 * 规范化后的文件接口
 */
export interface NormalizedFile {
  /**
   * 文件URI（必需）
   */
  uri: string;
  /**
   * 文件时长（秒）
   */
  duration?: number | null;
}

