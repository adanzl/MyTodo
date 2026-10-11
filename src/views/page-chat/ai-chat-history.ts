export const AI_HISTORY_PAGE_SIZE = 3;
export const AI_HISTORY_MAX_PAGES = 8;

/**
 * Dify `/messages` 单条记录里我们关心的字段。
 *
 * `message_files` 是**数组**（多图时一项一个），实测每个元素形如
 * `{filename, type, mime_type, upload_file_id, url}`。其中 `filename` 由我们上传时
 * 指定为 `chat-<userId>-<时间戳>.<ext>`，与 pic 目录里的名字一致，
 * 所以可以直接拼 `/pic/view?name=<filename>`，不需要额外的映射表。
 */
export interface DifyMessageFile {
  filename?: string;
  type?: string;
}

export interface DifyHistoryItem {
  id?: string | number;
  query?: string;
  answer?: string | null;
  message_files?: DifyMessageFile[] | null;
}

import { historyBubbleKey } from "@/views/page-chat/ai-chat-reply";

export interface HistoryBubble {
  bubbleKey?: string;
  id?: string | number;
  content: string;
  role: string;
  /** 用户消息随附的图片文件名（见 DifyMessageFile 的说明） */
  images?: string[];
}

function hasId(id: string | number | undefined | null): id is string | number {
  return id !== undefined && id !== null && id !== "";
}

/**
 * 从 `message_files` 里挑出图片文件名。
 *
 * 只认 `type === "image"`；缺失 type 时按扩展名兜底，避免上游少个字段就丢图。
 * 历史里的 `url` 是 300 秒签名的临时地址，不能用；必须走我们自己的文件名。
 */
export function imageFilenamesFromMessageFiles(
  files: DifyHistoryItem["message_files"]
): string[] {
  if (!files || !Array.isArray(files)) return [];
  const names: string[] = [];
  for (const f of files) {
    const name = (f?.filename || "").trim();
    if (!name) continue;
    const type = (f?.type || "").toLowerCase();
    if (type && type !== "image") continue;
    if (!type && !/\.(jpe?g|png|gif|webp|bmp)$/i.test(name)) continue;
    names.push(name);
  }
  return names;
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
    const images = imageFilenamesFromMessageFiles(item.message_files);
    messages.unshift({
      bubbleKey: historyBubbleKey(item.id!, "me"),
      id: item.id,
      content: item.query ?? "",
      role: "me",
      ...(images.length > 0 ? { images } : {}),
    });
    added += 1;
  }
  return { messages, added };
}
