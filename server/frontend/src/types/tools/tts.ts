/**
 * TTS 相关类型定义
 */

/**
 * TTS 任务接口
 */
export interface TTSTask {
  /**
   * 任务ID
   */
  task_id: string;
  /**
   * 任务名称
   */
  name: string;
  /**
   * 任务状态：pending, processing, success, failed
   */
  status: string;
  /**
   * 待合成的文本内容
   */
  text: string;
  /**
   * 发音人/音色（可选）
   */
  role?: string;
  /**
   * 语速，默认 1.0
   */
  speed?: number;
  /**
   * 音量，默认 50
   */
  vol?: number;
  /**
   * 工作目录路径
   */
  work_dir?: string;
  /**
   * 输出音频文件路径
   */
  output_file?: string;
  /**
   * 错误消息
   */
  error_message?: string;
  /**
   * 创建时间戳
   */
  create_time: number;
  /**
   * 更新时间戳
   */
  update_time: number;
  /**
   * 已生成字数（实时更新）
   */
  generated_chars?: number;
  /**
   * 文本总字数（按统计规则计算）
   */
  total_chars?: number;
  /**
   * 音频时长（秒），任务完成后写入
   */
  duration?: number;
}
