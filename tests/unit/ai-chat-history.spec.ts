import {
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
