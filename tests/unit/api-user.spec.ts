/**
 * api/user 单测：getUserInfo、getUserList、setUserData、addScore 成功与 code!==0 抛错
 */
import {
  addScore,
  clearUserListCache,
  getUserInfo,
  getUserList,
  setUserData,
} from "@/api/user";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockGet = vi.fn();
const mockPost = vi.fn();
vi.mock("@/api/api-client", () => ({
  apiClient: {
    get: (url: string, config?: unknown) => mockGet(url, config),
    post: (url: string, body?: unknown, config?: unknown) =>
      mockPost(url, body, config),
  },
}));

describe("api/user", () => {
  beforeEach(() => {
    clearUserListCache();
  });

  describe("getUserInfo", () => {
    it("code===0 时返回 data", async () => {
      mockGet.mockResolvedValueOnce({
        data: { code: 0, data: { id: 1, score: 100 } },
      });
      const result = await getUserInfo(1);
      expect(result).toEqual({ id: 1, score: 100 });
      expect(mockGet).toHaveBeenCalledWith("/getData", {
        params: { table: "t_user", id: 1, fields: "id,score" },
      });
    });

    it("code!==0 时抛出 Error(msg)", async () => {
      mockGet.mockResolvedValueOnce({
        data: { code: 1, msg: "用户不存在" },
      });
      await expect(getUserInfo(1)).rejects.toThrow("用户不存在");
    });

    it("请求失败时抛出异常", async () => {
      mockGet.mockRejectedValueOnce(new Error("Network error"));
      await expect(getUserInfo(1)).rejects.toThrow("Network error");
    });
  });

  describe("getUserList", () => {
    it("code===0 时返回 payload，wish_list 为字符串时会被 parse", async () => {
      mockGet.mockReset();
      mockGet.mockResolvedValueOnce({
        data: {
          code: 0,
          data: {
            data: [
              { id: 1, name: "a", wish_list: "[1,2]" },
              { id: 2, name: "b" },
            ],
          },
        },
      });
      const result = await getUserList();
      expect(result.data).toHaveLength(2);
      expect(result.data[0].wish_list).toEqual([1, 2]);
      expect(result.data[1].wish_list).toBeUndefined();
    });

    it("code!==0 时抛出 Error(msg)", async () => {
      mockGet.mockResolvedValueOnce({
        data: { code: 500, msg: "服务异常" },
      });
      await expect(getUserList()).rejects.toThrow("服务异常");
    });

    it("5 分钟内复用缓存，不重复请求", async () => {
      mockGet.mockReset();
      mockGet.mockResolvedValue({
        data: {
          code: 0,
          data: { data: [{ id: 1, name: "a" }] },
        },
      });
      const r1 = await getUserList();
      const r2 = await getUserList();
      expect(r1.data).toHaveLength(1);
      expect(r2.data).toHaveLength(1);
      expect(mockGet).toHaveBeenCalledTimes(1);
    });

    it("force=true 时忽略缓存重新请求", async () => {
      mockGet.mockReset();
      mockGet.mockResolvedValue({
        data: {
          code: 0,
          data: { data: [{ id: 1, name: "a" }] },
        },
      });
      await getUserList();
      await getUserList(true);
      expect(mockGet).toHaveBeenCalledTimes(2);
    });
  });

  describe("setUserData", () => {
    it("code===0 时不抛错且 post 被正确调用", async () => {
      mockPost.mockReset();
      mockPost.mockResolvedValueOnce({ data: { code: 0, data: { id: 1 } } });
      await setUserData({ score: 200 });
      expect(mockPost).toHaveBeenCalledWith(
        "/setData",
        { table: "t_user", data: { score: 200 } },
        undefined
      );
    });

    it("code!==0 时抛出 Error(msg)", async () => {
      mockPost.mockReset();
      mockPost.mockResolvedValueOnce({
        data: { code: 400, msg: "参数错误" },
      });
      await expect(setUserData({})).rejects.toThrow("参数错误");
    });
  });

  describe("addScore", () => {
    it("code===0 时不抛错且 post 被正确调用", async () => {
      mockPost.mockReset();
      mockPost.mockResolvedValueOnce({ data: { code: 0, data: { ok: true } } });
      await addScore(1, "task", 10, "完成日程");
      expect(mockPost).toHaveBeenCalledWith(
        "/addScore",
        { user: 1, action: "task", value: 10, msg: "完成日程" },
        undefined
      );
    });

    it("code!==0 时抛出 Error(msg)", async () => {
      mockPost.mockReset();
      mockPost.mockResolvedValueOnce({
        data: { code: 403, msg: "积分不足" },
      });
      await expect(addScore(1, "shop", -100, "兑换")).rejects.toThrow("积分不足");
    });
  });
});
