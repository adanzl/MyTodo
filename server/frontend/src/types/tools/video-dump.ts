/**
 * 文字提取相关类型定义
 */

export interface VideoDumpFileInfo {
  name: string;
  path: string;
  size?: number;
  modified?: number;
}

export interface VideoDumpSite {
  id: string;
  label: string;
  hosts: string[];
}

export interface VideoDumpTask {
  task_id: string;
  name?: string;
  status: string;
  source_url?: string;
  platform?: string;
  platform_label?: string;
  stage?: string;
  subtitle_source?: string;
  uploaded_path?: string;
  uploaded_info?: VideoDumpFileInfo | null;
  output_path?: string | null;
  output_info?: VideoDumpFileInfo | null;
  subtitle_path?: string | null;
  subtitle_info?: VideoDumpFileInfo | null;
  text?: string;
  error_message?: string | null;
  create_time: number;
  update_time: number;
}
