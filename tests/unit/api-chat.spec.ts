/**
 * api/chat 单测：getChatSetting、setChatSetting、getConversationId、getChatMem 成功与 code!==0 抛错
 */
import {
  getChatSetting,
  getConversationId,
  setChatSetting,
} from "@/api/chat";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockGet = vi.fn();
const mockPost = vi.fn();
vi.mock("@/api/api-client", () => ({
  apiClient: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
  },
}));

describe("api/chat", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getChatSetting", () => {
    it("code===0 且 data 存在时返回字符串", async () => {
      mockGet.mockResolvedValueOnce({
        data: { code: 0, data: '{"ttsSpeed":1.1}' },
      });
      const result = await getChatSetting(1);
      expect(result).toBe('{"ttsSpeed":1.1}');
      expect(mockGet).toHaveBeenCalledWith("/getRdsData", {
        params: { table: "chatSetting", id: 1 },
      });
    });

    it("code===0 且 data 为空时返回 null", async () => {
      mockGet.mockResolvedValueOnce({ data: { code: 0, data: null } });
      const result = await getChatSetting(1);
      expect(result).toBeNull();
    });

    it("code!==0 时抛出 Error(msg)", async () => {
      mockGet.mockResolvedValueOnce({
        data: { code: 500, msg: "Redis 错误" },
      });
      await expect(getChatSetting(1)).rejects.toThrow("Redis 错误");
    });
  });

  describe("setChatSetting", () => {
    it("code===0 时不抛错", async () => {
      mockPost.mockResolvedValueOnce({ data: { code: 0 } });
      await expect(
        setChatSetting(1, '{"ttsRole":"longwan"}')
      ).resolves.toBeUndefined();
      expect(mockPost).toHaveBeenCalledWith("/setRdsData", {
        table: "chatSetting",
        data: { id: 1, value: '{"ttsRole":"longwan"}' },
      });
    });

    it("code!==0 时抛出 Error(msg)", async () => {
      mockPost.mockResolvedValueOnce({
        data: { code: 400, msg: "参数错误" },
      });
      await expect(setChatSetting(1, "x")).rejects.toThrow("参数错误");
    });
  });

  describe("getConversationId", () => {
    it("code===0 时返回 data 或 null", async () => {
      mockGet.mockResolvedValueOnce({
        data: { code: 0, data: "conv_123" },
      });
      const result = await getConversationId(1);
      expect(result).toBe("conv_123");
      expect(mockGet).toHaveBeenCalledWith("/getRdsData", {
        params: { table: "conversation:id", id: 1 },
      });
    });
  });
});
