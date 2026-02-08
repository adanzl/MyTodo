/**
 * Auth 模块单测：get/set/clear token、login/refresh/logout 分支与异常路径
 */
import {
  clearLoginCache,
  getAccessToken,
  getTokenExpiresAt,
  login,
  logout,
  refreshToken,
  setAccessToken,
  setTokenWithExpiry,
} from "@/utils/Auth";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mockPost = vi.hoisted(() => vi.fn());
vi.mock("axios", () => ({ default: { post: mockPost } }));

describe("Auth", () => {
  const baseUrl = "https://example.com/api";

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  describe("getAccessToken / setAccessToken / getTokenExpiresAt / setTokenWithExpiry", () => {
    it("getAccessToken 无 token 时返回 null", () => {
      expect(getAccessToken()).toBeNull();
    });

    it("setAccessToken(null) 移除 token 及过期时间", () => {
      localStorage.setItem("access_token", "old");
      localStorage.setItem("access_token_expires_at", "123");
      setAccessToken(null);
      expect(localStorage.getItem("access_token")).toBeNull();
      expect(localStorage.getItem("access_token_expires_at")).toBeNull();
    });

    it("setAccessToken(token) 写入 token，getAccessToken 可读回", () => {
      setAccessToken("abc123");
      expect(getAccessToken()).toBe("abc123");
    });

    it("setTokenWithExpiry 写入 token 及过期时间，getTokenExpiresAt 可读回", () => {
      const now = Date.now();
      setTokenWithExpiry("xyz", 3600);
      expect(getAccessToken()).toBe("xyz");
      const expiresAt = getTokenExpiresAt();
      expect(expiresAt).not.toBeNull();
      expect(expiresAt! - now).toBeGreaterThanOrEqual(3599000);
      expect(expiresAt! - now).toBeLessThanOrEqual(3601000);
    });
  });

  describe("clearLoginCache", () => {
    it("移除 access_token、access_token_expires_at、saveUser、bAuth", () => {
      localStorage.setItem("access_token", "x");
      localStorage.setItem("access_token_expires_at", "123");
      localStorage.setItem("saveUser", "1");
      localStorage.setItem("bAuth", "1");
      clearLoginCache();
      expect(localStorage.getItem("access_token")).toBeNull();
      expect(localStorage.getItem("access_token_expires_at")).toBeNull();
      expect(localStorage.getItem("saveUser")).toBeNull();
      expect(localStorage.getItem("bAuth")).toBeNull();
    });
  });

  describe("login", () => {
    it("成功且返回 access_token 时写入 localStorage", async () => {
      mockPost.mockResolvedValueOnce({
        data: { code: 0, access_token: "new_token", expires_in: 3600 },
      });
      const result = await login(baseUrl, "user", "pass");
      expect(result.access_token).toBe("new_token");
      expect(getAccessToken()).toBe("new_token");
      expect(mockPost).toHaveBeenCalledWith(
        "https://example.com/api/auth/login",
        { username: "user", password: "pass" },
        expect.objectContaining({ withCredentials: true })
      );
    });

    it("成功但无 access_token 时不写入", async () => {
      mockPost.mockResolvedValueOnce({ data: { code: 0, msg: "ok" } });
      await login(baseUrl, "u", "p");
      expect(getAccessToken()).toBeNull();
    });

    it("baseUrl 末尾斜杠会被去掉再拼接路径", async () => {
      mockPost.mockResolvedValueOnce({ data: {} });
      await login("https://host.com/api/", "u", "p");
      expect(mockPost).toHaveBeenCalledWith(
        "https://host.com/api/auth/login",
        expect.any(Object),
        expect.any(Object)
      );
    });

    it("请求失败时抛出异常", async () => {
      mockPost.mockRejectedValueOnce(new Error("Network error"));
      await expect(login(baseUrl, "u", "p")).rejects.toThrow("Network error");
    });
  });

  describe("refreshToken", () => {
    it("有旧 token 时请求头带 Authorization", async () => {
      setAccessToken("old_token");
      mockPost.mockResolvedValueOnce({
        data: { access_token: "new_token", expires_in: 3600 },
      });
      await refreshToken(baseUrl);
      expect(mockPost).toHaveBeenCalledWith(
        expect.any(String),
        {},
        expect.objectContaining({
          headers: { Authorization: "Bearer old_token" },
        })
      );
      expect(getAccessToken()).toBe("new_token");
    });

    it("无旧 token 时请求头可为空对象", async () => {
      mockPost.mockResolvedValueOnce({
        data: { access_token: "fresh", expires_in: 3600 },
      });
      await refreshToken(baseUrl);
      expect(getAccessToken()).toBe("fresh");
    });

    it("响应无 access_token 时返回空字符串且不写入", async () => {
      mockPost.mockResolvedValueOnce({ data: { code: 401 } });
      const result = await refreshToken(baseUrl);
      expect(result.access_token).toBe("");
      expect(result.expires_in).toBe(0);
      expect(getAccessToken()).toBeNull();
    });

    it("请求失败时抛出异常", async () => {
      mockPost.mockRejectedValueOnce(new Error("refresh failed"));
      await expect(refreshToken(baseUrl)).rejects.toThrow("refresh failed");
    });
  });

  describe("logout", () => {
    it("无论请求成功与否都会 clearLoginCache", async () => {
      localStorage.setItem("access_token", "x");
      mockPost.mockResolvedValueOnce({});
      await logout(baseUrl);
      expect(getAccessToken()).toBeNull();
    });

    it("请求失败时仍清除本地缓存", async () => {
      localStorage.setItem("access_token", "x");
      mockPost.mockRejectedValueOnce(new Error("Network error"));
      await expect(logout(baseUrl)).rejects.toThrow("Network error");
      expect(getAccessToken()).toBeNull();
    });
  });
});
