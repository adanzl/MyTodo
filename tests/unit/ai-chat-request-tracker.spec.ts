import { createAiRequestTracker } from "@/views/page-chat/ai-chat-request-tracker";
import { describe, expect, it } from "vitest";

describe("ai-chat-request-tracker", () => {
  it("只接受当前活跃请求的 clientRequestId", () => {
    const t = createAiRequestTracker();
    t.activate("a");
    expect(t.accepts("a")).toBe(true);
    expect(t.accepts("b")).toBe(false);
    expect(t.accepts(undefined)).toBe(false);
  });

  it("新请求会使旧请求事件失效", () => {
    const t = createAiRequestTracker();
    t.activate("old");
    t.activate("new");
    expect(t.accepts("old")).toBe(false);
    expect(t.accepts("new")).toBe(true);
  });

  it("dismiss 后忽略该请求", () => {
    const t = createAiRequestTracker();
    t.activate("x");
    t.dismiss("x");
    expect(t.accepts("x")).toBe(false);
    expect(t.getActive()).toBeNull();
  });
});
