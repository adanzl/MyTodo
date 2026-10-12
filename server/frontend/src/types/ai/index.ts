/**
 * Dify 对话数据类型（对应后端 `/api/chat/*`，见 server/core/api/chat_routes.py）
 */

export interface DifyConversation {
  id: string;
  name: string;
  status?: string;
  inputs?: Record<string, unknown>;
  introduction?: string;
  /** 秒级 Unix 时间戳（注意：不是毫秒） */
  created_at: number;
  /** 秒级 Unix 时间戳（注意：不是毫秒） */
  updated_at: number;
}

/**
 * Dify 消息随附的文件（`message_files` 的元素）。
 *
 * 实测形如：
 * `{filename, type: "image", mime_type, belongs_to, url, upload_file_id, size}`
 * - `filename`：我们上传时定的名字（`chat-<userId>-<时间戳>.<ext>`），与 pic 目录里
 *   的文件名一致，可直接拼 `/api/pic/view?name=<filename>`；
 *   `url` 是 Dify 内网的签名地址，前端用不了。
 * - `belongs_to`：`user` 表示这张图属于提问，`assistant` 表示属于回答。
 */
export interface DifyMessageFile {
  id?: string;
  filename?: string;
  type?: string;
  mime_type?: string;
  belongs_to?: string;
  url?: string;
  upload_file_id?: string;
  size?: number;
}

export interface DifyMessage {
  id: string;
  conversation_id: string;
  parent_message_id?: string;
  query: string;
  answer: string | null;
  /** 秒级 Unix 时间戳（注意：不是毫秒） */
  created_at: number;
  status?: string;
  /** 生成失败时的原因，例如 "Run failed: Variable #conversation.Memory# not found" */
  error?: string | null;
  /** 该条消息随附的图片等文件；没有附件时 Dify 返回空数组 */
  message_files?: DifyMessageFile[] | null;
  message_tokens?: number;
  answer_tokens?: number;
  total_tokens?: number;
  total_price?: string;
  provider_response_latency?: number;
}

/** 会话列表按 updated_at 倒序；has_more=true 表示还有更早的会话 */
export interface DifyConversationPage {
  limit: number;
  has_more: boolean;
  data: DifyConversation[];
}

/** 消息页按 created_at 正序；has_more=true 表示还有更早的消息 */
export interface DifyMessagePage {
  limit: number;
  has_more: boolean;
  data: DifyMessage[];
}
