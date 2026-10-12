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

/** 导出接口的返回：文件本体 + 服务端给出的文件名与条数 */
export interface ChatExportResult {
  blob: Blob;
  filename: string;
  /** 服务端回传的条数；响应头读不到时为 undefined */
  count?: number;
}

/** 从 Content-Disposition 取文件名，优先 RFC 5987 的 filename*（中文名） */
function parseDispositionFilename(disposition: string): string {
  if (!disposition) return "";
  const star = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
  if (star?.[1]) {
    try {
      return decodeURIComponent(star[1].trim());
    } catch {
      // 解码失败时退回下面的 filename=
    }
  }
  const plain = /filename=(?:"([^"]*)"|([^;]+))/i.exec(disposition);
  return (plain?.[1] ?? plain?.[2] ?? "").trim();
}

/** 响应头缺失时的兜底文件名 */
function fallbackFilename(user: string): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  const ts =
    `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}` +
    `-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
  return `AI对话-${user}-${ts}.csv`;
}

/**
 * 导出某个会话的消息记录（CSV 文件）。
 *
 * 取数与 CSV 生成都在服务端完成：Dify 的 `/messages` 只支持游标分页且不返回总数，
 * 放前端就得由浏览器反复往返翻页、把整段会话缓存进内存再过滤。
 *
 * 失败时后端仍返回 `{code:-1,msg}` 的 JSON（HTTP 200）。因为这里 `responseType` 是
 * blob，axios 拦截器只看到一个 Blob、无法自动判错，所以靠 Content-Type 自行区分。
 */
export async function exportChatMessages(params: {
  conversationId: string;
  user: string;
  start?: string | null;
  end?: string | null;
  /**
   * API 的 origin（如 `https://example.com`），用于把 CSV 里的图片拼成绝对 URL。
   * 由调用方传入的原因：服务端未必知道自己被访问的公网地址（可能在反代后面），
   * 而浏览器一定知道。留空时后端退回相对路径。
   */
  base?: string;
}): Promise<ChatExportResult> {
  const rsp = await api.get<Blob>("/chat/export", {
    params: {
      conversation_id: params.conversationId,
      user: params.user,
      start: params.start || undefined,
      end: params.end || undefined,
      base: params.base || undefined,
    },
    responseType: "blob",
    // 服务端要翻页拉全整个会话，比普通接口慢
    timeout: 120000,
  });

  const contentType = String(rsp.headers["content-type"] || "");
  if (contentType.includes("application/json")) {
    const text = await rsp.data.text();
    let message = "导出失败";
    try {
      message = (JSON.parse(text) as { msg?: string }).msg || message;
    } catch {
      // 不是合法 JSON 时沿用默认文案
    }
    throw new Error(message);
  }

  const countRaw = rsp.headers["x-export-count"];
  const parsedCount = countRaw ? Number(countRaw) : Number.NaN;

  return {
    blob: rsp.data,
    filename:
      parseDispositionFilename(String(rsp.headers["content-disposition"] || "")) ||
      fallbackFilename(params.user),
    count: Number.isNaN(parsedCount) ? undefined : parsedCount,
  };
}
