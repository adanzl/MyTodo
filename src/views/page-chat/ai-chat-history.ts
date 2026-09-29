export const AI_HISTORY_PAGE_SIZE = 3;
export const AI_HISTORY_MAX_PAGES = 8;

export interface DifyHistoryItem {
  id?: string | number;
  query?: string;
  answer?: string | null;
}

import { historyBubbleKey } from "@/views/page-chat/ai-chat-reply";

export interface HistoryBubble {
  bubbleKey?: string;
  id?: string | number;
  content: string;
  role: string;
}

function hasId(id: string | number | undefined | null): id is string | number {
  return id !== undefined && id !== null && id !== "";
}

/** Dify 这一页按时间从旧到新。用最旧一条做下一页游标，空回答也要前进。 */
export function oldestHistoryId(
  page: DifyHistoryItem[]
): string | number | undefined {
  const id = page[0]?.id;
  return hasId(id) ? id : undefined;
}

/**
 * 把一页历史插到现有消息前面。
 * 空回答不展示，已有消息不重复插入。返回新增的轮次数。
 */
export function prependHistoryTurns(
  existing: HistoryBubble[],
  page: DifyHistoryItem[]
): { messages: HistoryBubble[]; added: number } {
  const messages = existing.slice();
  const seen = new Set(
    messages.filter((msg) => hasId(msg.id)).map((msg) => String(msg.id))
  );
  let added = 0;
  for (let i = page.length - 1; i >= 0; i--) {
    const item = page[i];
    if (!item || item.answer == null || item.answer === "") continue;
    if (hasId(item.id) && seen.has(String(item.id))) continue;
    if (hasId(item.id)) seen.add(String(item.id));
    messages.unshift({
      bubbleKey: historyBubbleKey(item.id!, "server"),
      id: item.id,
      content: item.answer,
      role: "server",
    });
    messages.unshift({
      bubbleKey: historyBubbleKey(item.id!, "me"),
      id: item.id,
      content: item.query ?? "",
      role: "me",
    });
    added += 1;
  }
  return { messages, added };
}
