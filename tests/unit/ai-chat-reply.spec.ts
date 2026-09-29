import {
  applyChatChunkToMessages,
  failServerReply,
  finishServerReply,
  newBubbleKey,
} from "@/views/page-chat/ai-chat-reply";
import type { ChatMsg } from "@/views/page-chat/ai-chat-types";
import { describe, expect, it } from "vitest";

function serverThinking(id: string): ChatMsg {
  return {
    bubbleKey: newBubbleKey("srv"),
    role: "server",
    content: "正在思考…",
    status: "thinking",
    clientRequestId: id,
    retryText: "hello",
  };
}

describe("ai-chat-reply", () => {
  it("已停止的回复不再接受 chunk", () => {
    const messages = [serverThinking("r1")];
    finishServerReply(messages, "r1", { stopped: true });
    expect(applyChatChunkToMessages(messages, { clientRequestId: "r1", content: "late" })).toBe(
      false
    );
    expect(messages[0].content).not.toContain("late");
  });

  it("失败时保留已流式正文，错误单独存放", () => {
    const messages = [serverThinking("r1")];
    applyChatChunkToMessages(messages, { clientRequestId: "r1", content: "part" });
    failServerReply(messages, "r1", "断线了", "hello");
    expect(messages[0].content).toBe("part");
    expect(messages[0].errorMessage).toBe("断线了");
    expect(messages[0].status).toBe("error");
  });

  it("首字前停止显示已停止而非正在思考", () => {
    const messages = [serverThinking("r1")];
    finishServerReply(messages, "r1", { stopped: true });
    expect(messages[0].status).toBe("stopped");
    expect(messages[0].content).toBe("已停止");
  });

  it("识别阶段停止会结束用户侧识别气泡", () => {
    const messages = [
      {
        bubbleKey: newBubbleKey("me"),
        role: "me",
        content: "正在识别…",
        status: "recognizing" as const,
        clientRequestId: "v1",
      },
    ];
    finishServerReply(messages, "v1", { stopped: true });
    expect(messages[0].status).toBe("stopped");
    expect(messages[0].content).toBe("已取消识别");
  });
});
