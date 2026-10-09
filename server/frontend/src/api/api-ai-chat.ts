/**
 * AI 对话（Dify）相关 API
 *
 * 后端代理见 server/core/api/chat_routes.py，对外路径 `/api/chat/*`。
 * 注意 `user` 参数同时决定使用哪个 Dify 应用：
 * `leo` / `灿灿` 各自独立，其他用户名（含 `昭昭`）走昭昭的应用，见后端 `dify_api_key`。
 */
import { api } from "./config";
import type { ApiResponse } from "@/types/api";
import type { DifyConversationPage, DifyMessagePage } from "@/types/ai";

/** 拉取某个用户的会话列表（按 updated_at 倒序） */
export async function getConversations(
  user: string,
  limit: number,
  lastId?: string
): Promise<DifyConversationPage> {
  const rsp = await api.get<ApiResponse<DifyConversationPage>>("/chat/conversations", {
    params: { user, limit, last_id: lastId },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "获取会话列表失败");
  }
  return rsp.data.data;
}

/**
 * 拉取某个会话的消息（按时间从旧到新）
 * @param firstId 本页最旧一条的 id，用于往更早翻页
 */
export async function getConversationMessages(
  conversationId: string,
  limit: number,
  user: string,
  firstId?: string
): Promise<DifyMessagePage> {
  const rsp = await api.get<ApiResponse<DifyMessagePage | null>>("/chat/messages", {
    params: {
      conversation_id: conversationId,
      limit,
      user,
      first_id: firstId,
    },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "获取会话消息失败");
  }
  // 后端取数失败时会返回 code:0 + data:null（见 chat_routes.py 的说明），
  // 这里显式拦成错误，避免被当成「这个会话没有消息」。
  if (!rsp.data.data) {
    throw new Error("获取会话消息失败，请稍后重试");
  }
  return rsp.data.data;
}
