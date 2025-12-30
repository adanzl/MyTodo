/**
 * PDF 相关类型定义
 */

/**
 * PDF 文件信息接口
 */
export interface PdfFileInfo {
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
   * 修改时间戳
   */
  modified?: number;
}

/**
 * PDF 任务接口
 */
export interface PdfTask {
  /**
   * 任务ID（文件名）
   */
  task_id: string;
  /**
   * 文件名
   */
  filename: string;
  /**
   * 任务状态：uploaded, pending, processing, success, failed
   */
  status: string;
  /**
   * 上传文件信息
   */
  uploaded_info: PdfFileInfo;
  /**
   * 已解密文件信息（如果存在）
   */
  unlocked_info?: PdfFileInfo | null;
  /**
   * 错误信息（如果失败）
   */
  error_message?: string | null;
  /**
   * 创建时间戳
   */
  create_time: number;
  /**
   * 更新时间戳
   */
  update_time: number;
}
