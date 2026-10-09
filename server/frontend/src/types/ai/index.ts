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
