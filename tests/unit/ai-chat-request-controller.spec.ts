import { createAiRequestController } from "@/views/page-chat/ai-chat-request-controller";
import { describe, expect, it } from "vitest";

describe("ai-chat-request-controller", () => {
  it("outbound 阶段视为 in-flight，accept 后进入 ai/asr", () => {
    const c = createAiRequestController();
    c.register("r1", "text", "hello");
    expect(c.isInFlight()).toBe(true);
    expect(c.isAwaitingServerAck()).toBe(true);
    expect(c.markAccepted("r1", 0)).toBe(true);
    expect(c.isAwaitingServerAck()).toBe(false);
    expect(c.get("r1")?.phase).toBe("ai");
  });

  it("voice accept 后处于 asr 阶段", () => {
    const c = createAiRequestController();
    c.register("v1", "voice");
    c.markAccepted("v1", 0);
    expect(c.get("v1")?.phase).toBe("asr");
  });

  it("新请求使旧请求事件失效", () => {
    const c = createAiRequestController();
    c.register("old", "text");
    c.register("new", "text");
    expect(c.accepts("old")).toBe(false);
    expect(c.accepts("new")).toBe(true);
  });

  it("dismiss 后不再接受事件且不再 in-flight", () => {
    const c = createAiRequestController();
    c.register("x", "text");
    c.markAccepted("x", 0);
    c.dismiss("x", "failed");
    expect(c.accepts("x")).toBe(false);
    expect(c.isInFlight()).toBe(false);
  });

  it("失败后复用同一 ID 注册应恢复接收与完整状态流", () => {
    const c = createAiRequestController();
    c.register("A", "text", "question");
    expect(c.accepts("A")).toBe(true);
    c.markAccepted("A", 0);
    c.dismiss("A", "failed");
    c.purge("A");
    expect(c.accepts("A")).toBe(false);
    expect(c.markAccepted("A")).toBe(false);
    expect(c.isInFlight()).toBe(false);

    c.register("A", "text", "question", { requireNewAttempt: true });
    expect(c.get("A")?.attempt).toBe(0);
    expect(c.accepts("A")).toBe(true);
    expect(c.acceptsEvent("A", 0)).toBe(false);
    expect(c.isInFlight()).toBe(true);
    expect(c.isAwaitingServerAck()).toBe(true);
    expect(c.markAccepted("A", 0)).toBe(false);
    expect(c.markAccepted("A", 1)).toBe(true);
    expect(c.get("A")?.phase).toBe("ai");
    expect(c.isAwaitingServerAck()).toBe(false);
    expect(c.isInFlight()).toBe(true);
  });

  it("同 ID 重试后拒绝旧 attempt 的 Socket 事件", () => {
    const c = createAiRequestController();
    c.register("A", "text", "q");
    c.markAccepted("A", 0);
    expect(c.acceptsEvent("A", 0)).toBe(true);
    expect(c.markAccepted("A", 1)).toBe(true);
    expect(c.get("A")?.attempt).toBe(1);
    expect(c.acceptsEvent("A", 0)).toBe(false);
    expect(c.acceptsEvent("A", 1)).toBe(true);
  });

  it("新确认到达前拒绝任意生成事件（含旧 attempt）", () => {
    const c = createAiRequestController();
    c.register("A", "text", "q");
    c.markAccepted("A", 0);
    c.purge("A");
    c.register("A", "text", "q", { requireNewAttempt: true });
    expect(c.get("A")?.attempt).toBe(0);
    expect(c.acceptsEvent("A", 0)).toBe(false);
    expect(c.acceptsEvent("A", 1)).toBe(false);
    expect(c.markAccepted("A", 0)).toBe(false);
    c.markAccepted("A", 1);
    expect(c.acceptsEvent("A", 1)).toBe(true);
  });

  it("迟到旧确认不能降低 attempt", () => {
    const c = createAiRequestController();
    c.register("A", "text", "q");
    expect(c.markAccepted("A", 1)).toBe(true);
    expect(c.get("A")?.attempt).toBe(1);
    expect(c.markAccepted("A", 0)).toBe(false);
    expect(c.get("A")?.attempt).toBe(1);
    expect(c.acceptsEvent("A", 1)).toBe(true);
    expect(c.acceptsEvent("A", 0)).toBe(false);
  });

  it("拒绝迟到的旧轮次 query 终态", () => {
    const c = createAiRequestController();
    c.register("A", "text", "q");
    c.markAccepted("A", 0);
    c.purge("A");
    c.register("A", "text", "q");
    c.markAccepted("A", 1);
    expect(c.acceptsQueryResult("A", 0, "done")).toBe(false);
    expect(c.acceptsQueryResult("A", 1, "done")).toBe(true);
    expect(c.acceptsQueryResult("A", 0, "failed")).toBe(false);
  });

  it("冷恢复接受历史同一 attempt，并可继续接收该轮事件", () => {
    const c = createAiRequestController();
    c.register("A", "text", "q");
    c.markAccepted("A", 0);
    c.purge("A");

    expect(c.acceptsQueryResult("A", 0, "ai")).toBe(true);
    expect(c.acceptsQueryResult("A", 0, "done")).toBe(true);
    c.restore("A", "text", "q", 0);
    expect(c.markAccepted("A", 0)).toBe(true);
    expect(c.acceptsEvent("A", 0)).toBe(true);
  });

  it("冷恢复仍拒绝比历史 attempt 更旧的快照", () => {
    const c = createAiRequestController();
    c.register("A", "text", "q");
    c.markAccepted("A", 1);
    c.purge("A");

    expect(c.acceptsQueryResult("A", 0, "done")).toBe(false);
    expect(c.acceptsQueryResult("A", 1, "done")).toBe(true);
  });

  it("明确重新生成必须等服务端确认更大的 attempt", () => {
    const c = createAiRequestController();
    c.register("A", "text", "q");
    c.markAccepted("A", 0);
    c.dismiss("A", "failed");
    c.purge("A");

    c.register("A", "text", "q", { requireNewAttempt: true });
    expect(c.get("A")?.attempt).toBe(0);
    expect(c.acceptsQueryResult("A", 0, "ai")).toBe(false);
    expect(c.markAccepted("A", 0)).toBe(false);
    expect(c.markAccepted("A", 1)).toBe(true);
    expect(c.acceptsEvent("A", 0)).toBe(false);
    expect(c.acceptsEvent("A", 1)).toBe(true);
  });

  it("恢复 A 后仍忽略已 supersede 的其他请求", () => {
    const c = createAiRequestController();
    c.register("A", "text");
    c.register("B", "text");
    c.dismiss("B", "failed");
    c.register("A", "text");
    expect(c.accepts("A")).toBe(true);
    expect(c.accepts("B")).toBe(false);
  });
});
