import { flushPromises, shallowMount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import PageChat from "@/views/page-chat/PageChat.vue";

const mocks = vi.hoisted(() => ({
  recorder: { open: vi.fn(), start: vi.fn(), stop: vi.fn(), close: vi.fn() },
  socket: {
    connected: true,
    on: vi.fn(),
    emit: vi.fn(),
    removeAllListeners: vi.fn(),
    disconnect: vi.fn(),
  },
  toast: vi.fn(),
  aiTab: {
    getPendingClientRequestIds: vi.fn(() => []),
    getRequestRetryText: vi.fn(() => "hello"),
    prepareForResend: vi.fn(),
    confirmUserSent: vi.fn(),
    ensureAwaitingReply: vi.fn(),
    restoreServerReply: vi.fn(),
    finishActiveReply: vi.fn(),
    failActiveReply: vi.fn(),
    scrollToBottomIfNeeded: vi.fn(),
  },
}));

vi.mock("recorder-core/recorder.wav.min", () => ({ default: () => mocks.recorder }));
vi.mock("socket.io-client", () => ({ default: () => mocks.socket }));
vi.mock("@/api/api-client", () => ({ getApiUrl: () => "https://example.com/api" }));
vi.mock("@/api/api-chat", () => ({
  getChatSetting: async (): Promise<null> => null,
  setChatSetting: vi.fn(),
}));
vi.mock("@/api/api-user", () => ({
  getUserList: async (): Promise<{ data: never[] }> => ({ data: [] }),
}));
vi.mock("@/types/event-bus", () => ({
  default: { $emit: mocks.toast },
  C_EVENT: { TOAST: "toast" },
}));
vi.mock("@/views/page-chat/TabChatRoom.vue", () => ({
  default: { template: "<div />" },
}));
vi.mock("@/views/page-chat/TabAiChat.vue", () => ({
  default: {
    template: "<div />",
    methods: mocks.aiTab,
  },
}));
vi.mock("@/views/page-chat/TabTtsTasks.vue", () => ({
  default: { template: "<div />" },
}));
vi.mock("@/views/page-chat/dialogs/ChatSetting.vue", () => ({
  default: { template: "<div />" },
}));
vi.mock("@/components/ServerRemoteBadge.vue", () => ({
  default: { template: "<div />" },
}));

let wrapper: ReturnType<typeof shallowMount>;
let state: any;

function emitted(event: string) {
  return mocks.socket.emit.mock.calls.filter(([name]) => name === event);
}

beforeEach(async () => {
  vi.clearAllMocks();
  mocks.socket.connected = true;
  wrapper = shallowMount(PageChat, {
    global: {
      provide: { globalVar: { user: { id: 1, name: "test" } } },
      config: { warnHandler: () => {} },
    },
  });
  await flushPromises();
  state = (wrapper.vm as any).$.setupState;
  state.aiChatTabRef = mocks.aiTab;
  state.socketHandshakeOk = true;
  state.socketReady = true;
});

afterEach(() => {
  wrapper.unmount();
});

describe("AI 手动重试恢复", () => {
  it("同 ID 重试先查询服务端状态，不立即重新发送 message", () => {
    state.retryAiMessage("hello", "rid-recover");

    expect(emitted("queryChatRequest")).toContainEqual([
      "queryChatRequest",
      JSON.stringify({ clientRequestIds: ["rid-recover"] }),
    ]);
    expect(emitted("message")).toHaveLength(0);
  });

  it("服务端仍在 ai 阶段时恢复原 attempt，不重新生成", () => {
    state.retryAiMessage("hello", "rid-ai");
    state.onChatRequestStatus({
      items: [{ clientRequestId: "rid-ai", phase: "ai", attempt: 0, replyText: "partial" }],
    });

    expect(emitted("message")).toHaveLength(0);
    expect(mocks.aiTab.restoreServerReply).toHaveBeenCalledWith("rid-ai", "partial", false);
    expect(state.aiRequestController.get("rid-ai")?.attempt).toBe(0);
    expect(state.aiRequestController.get("rid-ai")?.phase).toBe("ai");
  });

  it("服务端已完成时直接恢复结果，不重新生成", () => {
    state.retryAiMessage("hello", "rid-done");
    state.onChatRequestStatus({
      items: [{ clientRequestId: "rid-done", phase: "done", attempt: 0, replyText: "answer" }],
    });

    expect(emitted("message")).toHaveLength(0);
    expect(mocks.aiTab.restoreServerReply).toHaveBeenCalledWith("rid-done", "answer", true);
    expect(mocks.aiTab.finishActiveReply).toHaveBeenCalledWith("rid-done");
  });

  it("只有服务端 failed 后才发起新 attempt，并拒绝原轮确认", () => {
    state.retryAiMessage("hello", "rid-failed");
    state.onChatRequestStatus({
      items: [{ clientRequestId: "rid-failed", phase: "failed", attempt: 0 }],
    });

    expect(emitted("message")).toHaveLength(1);
    expect(JSON.parse(emitted("message")[0][1])).toMatchObject({
      clientRequestId: "rid-failed",
      content: "hello",
    });
    expect(state.aiRequestController.get("rid-failed")?.attempt).toBe(0);
    expect(state.aiRequestController.get("rid-failed")?.awaitingNextAttempt).toBe(true);

    state.onMsgAccepted({ clientRequestId: "rid-failed", kind: "text", attempt: 0 });
    expect(state.aiRequestController.get("rid-failed")?.phase).toBe("outbound");

    state.onMsgAccepted({ clientRequestId: "rid-failed", kind: "text", attempt: 1 });
    expect(state.aiRequestController.get("rid-failed")?.attempt).toBe(1);
    expect(state.aiRequestController.get("rid-failed")?.phase).toBe("ai");
  });

  it("服务端没有记录时按原 ID 首次发送，不要求更大 attempt", () => {
    state.retryAiMessage("hello", "rid-missing");
    state.onChatRequestStatus({
      items: [{ clientRequestId: "rid-missing", phase: null }],
    });

    expect(emitted("message")).toHaveLength(1);
    expect(state.aiRequestController.get("rid-missing")?.attempt).toBe(0);
    expect(state.aiRequestController.get("rid-missing")?.awaitingNextAttempt).toBe(false);
  });
});
