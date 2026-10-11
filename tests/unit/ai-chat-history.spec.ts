import {
  imageFilenamesFromMessageFiles,
  oldestHistoryId,
  prependHistoryTurns,
  type DifyHistoryItem,
} from "@/views/page-chat/ai-chat-history";
import { describe, expect, it } from "vitest";

describe("ai-chat-history", () => {
  const page: DifyHistoryItem[] = [
    { id: "empty-old", query: "喵", answer: "" },
    { id: "mid", query: "2", answer: "在呢" },
    { id: "new", query: "想你了", answer: "我也想你" },
  ];

  it("空回答不展示，其余按从旧到新排在前面", () => {
    const { messages, added } = prependHistoryTurns([], page);
    expect(added).toBe(2);
    expect(messages.map((msg) => msg.content)).toEqual([
      "2",
      "在呢",
      "想你了",
      "我也想你",
    ]);
  });

  it("下一页游标取原始页最旧的 id，包括被跳过的空回答", () => {
    expect(oldestHistoryId(page)).toBe("empty-old");
  });

  it("已出现的消息不会再次插入", () => {
    const first = prependHistoryTurns([], page).messages;
    const again = prependHistoryTurns(first, page);
    expect(again.added).toBe(0);
    expect(again.messages).toHaveLength(first.length);
  });

  it("新的一页会插到已有消息前面", () => {
    const current = prependHistoryTurns([], page).messages;
    const older: DifyHistoryItem[] = [
      { id: "older", query: "早", answer: "早呀" },
    ];
    const { messages, added } = prependHistoryTurns(current, older);
    expect(added).toBe(1);
    expect(messages[0]).toMatchObject({ content: "早", role: "me" });
    expect(messages[2]).toMatchObject({ content: "2", role: "me" });
  });
});

describe("imageFilenamesFromMessageFiles", () => {
  it("取多图（message_files 实测是数组）", () => {
    expect(
      imageFilenamesFromMessageFiles([
        { filename: "chat-1-1.png", type: "image" },
        { filename: "chat-1-2.jpg", type: "image" },
      ])
    ).toEqual(["chat-1-1.png", "chat-1-2.jpg"]);
  });

  it("缺失或非法输入一律返回空数组", () => {
    expect(imageFilenamesFromMessageFiles(null)).toEqual([]);
    expect(imageFilenamesFromMessageFiles(undefined)).toEqual([]);
    expect(imageFilenamesFromMessageFiles([])).toEqual([]);
    // 上游字段异常（不是数组）也不能崩
    expect(
      imageFilenamesFromMessageFiles(
        { filename: "a.png" } as unknown as DifyHistoryItem["message_files"]
      )
    ).toEqual([]);
  });

  it("过滤掉非图片类型，也跳过没有文件名的项", () => {
    expect(
      imageFilenamesFromMessageFiles([
        { filename: "doc.pdf", type: "document" },
        { filename: "", type: "image" },
        { filename: "chat-1-3.png", type: "image" },
      ])
    ).toEqual(["chat-1-3.png"]);
  });

  it("缺 type 时按扩展名兜底，避免上游少个字段就丢图", () => {
    expect(
      imageFilenamesFromMessageFiles([
        { filename: "chat-1-4.png" },
        { filename: "chat-1-5.JPEG" },
        { filename: "notes.txt" },
      ])
    ).toEqual(["chat-1-4.png", "chat-1-5.JPEG"]);
  });
});

describe("历史气泡带图", () => {
  it("图片文件名挂到用户气泡上，供模板渲染", () => {
    const page: DifyHistoryItem[] = [
      {
        id: "h1",
        query: "看看这张图",
        answer: "看到了",
        message_files: [{ filename: "chat-1-9.png", type: "image" }],
      },
    ];

    const { messages } = prependHistoryTurns([], page);
    const user = messages.find((m) => m.role === "me");

    expect(user?.images).toEqual(["chat-1-9.png"]);
  });

  it("没有图片的轮次不带 images 字段（避免渲染空容器）", () => {
    const page: DifyHistoryItem[] = [
      { id: "h2", query: "只有文字", answer: "好" },
    ];

    const { messages } = prependHistoryTurns([], page);
    const user = messages.find((m) => m.role === "me");

    expect(user?.images).toBeUndefined();
  });
});
