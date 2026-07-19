/**
 * PDF 排版相关类型定义
 */

/**
 * PDF 排版文件信息接口
 */
export interface PdfLayoutFileInfo {
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
 * PDF 排版任务接口
 */
export interface PdfLayoutTask {
  /**
   * 任务ID（文件名）
   */
  task_id: string;
  /**
   * 任务名称（后端 TaskBase.name）
   */
  name?: string;
  /**
   * 文件名（兼容历史字段；当前后端等同于 task_id）
   */
  filename?: string;
  /**
   * 任务状态：uploaded, pending, processing, success, failed
   */
  status: string;
  /**
   * 上传文件路径
   */
  uploaded_path?: string;
  /**
   * 上传文件信息
   */
  uploaded_info: PdfLayoutFileInfo;
  /**
   * 排版输出文件路径
   */
  output_path?: string | null;
  /**
   * 排版输出文件信息（如果存在）
   */
  output_info?: PdfLayoutFileInfo | null;
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
  /**
   * 填充配置
   */
  fill_configs?: number[];
}
