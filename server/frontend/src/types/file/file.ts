/**
 * 文件相关类型定义
 */

/**
 * 媒体文件接口
 */
export interface MediaFile {
  /**
   * 文件URI（统一资源标识符）
   */
  uri?: string;
  /**
   * 文件路径
   */
  path?: string;
  /**
   * 文件名
   */
  name?: string;
  /**
   * 文件时长（秒）
   */
  duration?: number | null;
  /**
   * 文件大小（字节）
   */
  size?: number;
  /**
   * 文件扩展名
   */
  extension?: string;
  /**
   * 允许扩展字段
   */
  [key: string]: unknown;
}

/**
 * PDF 文件接口
 */
export interface PdfFile {
  /**
   * 文件ID
   */
  id: number;
  /**
   * 文件名
   */
  name: string;
  /**
   * 文件路径
   */
  path: string;
  /**
   * 文件大小（字节）
   */
  size?: number;
  /**
   * 是否已上传
   */
  uploaded?: boolean;
  /**
   * 是否已解锁（解密）
   */
  unlocked?: boolean;
  /**
   * 上传文件路径
   */
  uploaded_path?: string;
  /**
   * 已解锁文件路径
   */
  unlocked_path?: string;
  /**
   * 创建时间戳
   */
  create_time?: number;
  /**
   * 更新时间戳
   */
  update_time?: number;
  /**
   * 允许扩展字段
   */
  [key: string]: unknown;
}

/**
 * 媒体任务基础接口
 * 包含任务的基本信息
 */
export interface MediaTask {
  /**
   * 任务ID
   */
  task_id: string;
  /**
   * 任务名称
   */
  name: string;
  /**
   * 任务状态
   */
  status: string;
  /**
   * 任务文件列表（可选，列表接口可能包含）
   */
  files?: MediaTaskFile[];
  /**
   * 结果文件路径（可选，列表接口可能包含）
   */
  result_file?: string;
}

/**
 * 媒体任务详情接口
 * 包含任务的完整信息
 */
export interface MediaTaskDetail extends MediaTask {
  /**
   * 结果文件时长（秒）
   */
  result_duration?: number;
  /**
   * 错误消息
   */
  error_message?: string;
}

/**
 * 媒体任务文件接口
 * 用于音频合成任务中的文件
 */
export interface MediaTaskFile extends MediaFile {
  /**
   * 任务ID
   */
  task_id?: string;
  /**
   * 文件状态
   */
  status?: string;
  /**
   * 文件在任务中的索引
   */
  index?: number;
}

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
