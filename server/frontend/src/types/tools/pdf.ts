/**
 * PDF 相关类型定义
 */

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
