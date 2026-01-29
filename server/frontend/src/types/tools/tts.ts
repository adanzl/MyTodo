/**
 * TTS 相关类型定义
 */

/**
 * 文本分析结果结构（对应 txt_ali 返回的 JSON）
 */
export interface TTSAnalysis {
  title?: string;
  words?: string[];
  sentence?: string[];
  abstract?: string;
  doodle?: string;
  // 预留扩展字段
  [key: string]: unknown;
}

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
   * 模型选择（可选）：cosyvoice-v3-flash 或 cosyvoice-v3-plus
   */
  model?: string;
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

  /**
   * 文本分析结果（调用 /tts/analysis 后写入）
   */
  analysis?: TTSAnalysis | null;

  /**
   * 是否正在执行 OCR 子任务（不改变主状态，但锁定更新/启动/删除）
   */
  ocr_running?: boolean;

  /**
   * 是否正在执行分析子任务（不改变主状态，但锁定更新/启动/删除）
   */
  analysis_running?: boolean;
}
