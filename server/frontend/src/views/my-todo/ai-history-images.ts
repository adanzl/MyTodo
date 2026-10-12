/**
 * 后台「AI 对话记录」里的图片解析。
 *
 * 图片来自 Dify `/messages` 每条记录的 `message_files`（数组，多图一项一个）。实测：
 *
 * ```json
 * {"id": "...", "filename": "chat-4-1791808178982.png", "type": "image",
 *  "url": "/files/db1be6d5-.../file-preview?timestamp=...&sign=...",
 *  "mime_type": "image/png", "belongs_to": "user", "upload_file_id": "..."}
 * ```
 *
 * 两点决定了这里的写法：
 *
 * 1. `url` 是 Dify 内网 + 300 秒签名的临时地址，前端用不了；能用的是 `filename`
 *    —— 上传时由我们命名（`chat-<userId>-<时间戳>.<ext>`），与 pic 目录里的文件名
 *    一致，所以直接拼 `/api/pic/view?name=<filename>`（见 `@/api/api-pic`）。
 * 2. `belongs_to` 区分图片属于提问（`user`）还是回答（`assistant`）；
 *    列表是分列显示的，所以这里按归属拆开返回。
 *
 * 移动端有一份等价实现（`src/views/page-chat/ai-chat-history.ts`），但两边是独立的
 * 前端工程（一个在仓库根的 Ionic 应用、一个在 `server/frontend`），无法共用代码，
 * 只能各自维护、保持行为一致。
 */

import type { DifyMessageFile } from "@/types/ai";

/** 没有 type 字段时，用扩展名兜底判断是不是图片 */
const IMAGE_EXT_RE = /\.(jpe?g|png|gif|webp|bmp)$/i;

/** 按归属分好的图片文件名 */
export interface MessageImages {
  /** 提问随附的图片（belongs_to 为 user，或缺省） */
  question: string[];
  /** 回答随附的图片（belongs_to 为 assistant） */
  answer: string[];
}

/**
 * 从一个附件元素里取出可用的文件名，不是图片就返回空串。
 *
 * 只认 `type === "image"`；缺 `type` 时按扩展名兜底，避免上游少个字段就丢图。
 */
function imageNameOf(item: unknown): string {
  const name =
    typeof item === "string"
      ? item
      : String((item as DifyMessageFile | null | undefined)?.filename ?? "");
  const trimmed = name.trim();
  if (!trimmed) return "";

  const type =
    typeof item === "string"
      ? ""
      : String((item as DifyMessageFile)?.type ?? "").toLowerCase();
  if (type) return type === "image" ? trimmed : "";
  return IMAGE_EXT_RE.test(trimmed) ? trimmed : "";
}

/**
 * 把 `message_files` 拆成「提问的图」与「回答的图」。
 *
 * 非图片附件（Dify 也支持文档等）会被忽略：这里只能渲染图片。
 * 缺 `belongs_to` 时按提问处理 —— 目前实测只有用户上传的图片，这样最不容易漏图。
 */
export function splitMessageImages(files: unknown): MessageImages {
  const result: MessageImages = { question: [], answer: [] };
  if (!Array.isArray(files)) return result;

  for (const item of files) {
    const name = imageNameOf(item);
    if (!name) continue;
    const belongs = String(
      (item as DifyMessageFile | null | undefined)?.belongs_to ?? ""
    ).toLowerCase();
    if (belongs === "assistant") result.answer.push(name);
    else result.question.push(name);
  }
  return result;
}
