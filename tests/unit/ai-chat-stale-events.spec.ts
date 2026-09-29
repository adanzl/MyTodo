import { createAiRequestTracker } from "@/views/page-chat/ai-chat-request-tracker";
import {
  applyChatChunkToMessages,
  finishServerReply,
  newBubbleKey,
} from "@/views/page-chat/ai-chat-reply";
import type { ChatMsg } from "@/views/page-chat/ai-chat-types";
import { describe, expect, it } from "vitest";

function serverFor(id: string, content = "正在思考…"): ChatMsg {
  return {
    bubbleKey: newBubbleKey("srv"),
    role: "server",
    content,
    status: "thinking",
    clientRequestId: id,
    retryText: "q",
  };
}

/** 模拟：A 超时 dismiss → 发送 B → A 的迟到事件不应影响 B */
describe("ai-chat stale events (A timeout → B)", () => {
  it("ignores stale chunk/end/error for dismissed request A", () => {
    const tracker = createAiRequestTracker();
    const messages: ChatMsg[] = [serverFor("req-A")];

    tracker.activate("req-A");
    tracker.dismiss("req-A");

    tracker.activate("req-B");
    messages.push(serverFor("req-B"));

    expect(tracker.accepts("req-A")).toBe(false);
    const applyIfAccepted = (data: {
      clientRequestId: string;
      content: string;
    }) => {
      if (!tracker.accepts(data.clientRequestId)) return;
      applyChatChunkToMessages(messages, data);
    };

    applyIfAccepted({ clientRequestId: "req-A", content: "stale-chunk" });
    const bubbleA = messages.find((m) => m.clientRequestId === "req-A");
    expect(bubbleA?.content).toBe("正在思考…");

    expect(tracker.accepts("req-B")).toBe(true);
    applyIfAccepted({ clientRequestId: "req-B", content: "hello" });
    const bubbleB = messages.find(
      (m) => m.clientRequestId === "req-B" && m.role === "server"
    );
    expect(bubbleB?.content).toBe("hello");

    if (tracker.accepts("req-A")) finishServerReply(messages, "req-A");
    expect(bubbleB?.status).toBe("streaming");

    if (tracker.accepts("req-B")) finishServerReply(messages, "req-B");
    expect(bubbleB?.status).toBe("done");
  });
});
