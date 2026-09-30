/**
 * Auth 模块单测：get/set/clear token、login/refresh/logout 分支与异常路径
 */
import {
  clearLoginCache,
  getAccessToken,
  getRefreshToken,
  getTokenExpiresAt,
  login,
  logout,
  refreshToken,
  setAccessToken,
  setTokenWithExpiry,
} from "@/utils/auth-util";
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
      localStorage.setItem("lx_access_token", "old");
      localStorage.setItem("lx_access_token_expires_at", "123");
      setAccessToken(null);
      expect(localStorage.getItem("lx_access_token")).toBeNull();
      expect(localStorage.getItem("lx_access_token_expires_at")).toBeNull();
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
    it("移除 lx_access_token、lx_access_token_expires_at、lx_refresh_token、lx_saveUser、lx_bAuth、lx_session_revision", () => {
      localStorage.setItem("lx_access_token", "x");
      localStorage.setItem("lx_access_token_expires_at", "123");
      localStorage.setItem("lx_refresh_token", "rt");
      localStorage.setItem("lx_saveUser", "1");
      localStorage.setItem("lx_bAuth", "1");
      localStorage.setItem("lx_session_revision", "rev-1");
      localStorage.removeItem("lx_web_logout_signal");
      clearLoginCache();
      expect(localStorage.getItem("lx_access_token")).toBeNull();
      expect(localStorage.getItem("lx_access_token_expires_at")).toBeNull();
      expect(localStorage.getItem("lx_refresh_token")).toBeNull();
      expect(localStorage.getItem("lx_saveUser")).toBeNull();
      expect(localStorage.getItem("lx_bAuth")).toBeNull();
      expect(localStorage.getItem("lx_session_revision")).toBeNull();
      expect(localStorage.getItem("lx_web_logout_signal")).toBe("1");
    });
  });

  describe("login", () => {
    it("成功且返回 access_token 时写入 localStorage；有 refresh_token 时一并存", async () => {
      mockPost.mockResolvedValueOnce({
        data: {
          code: 0,
          access_token: "new_token",
          refresh_token: "ref_rtk",
          expires_in: 3600,
          user: { id: 42, name: "user" },
        },
      });
      const result = await login(baseUrl, "user", "pass");
      expect(result.access_token).toBe("new_token");
      expect(getAccessToken()).toBe("new_token");
      expect(getRefreshToken()).toBe("ref_rtk");
      expect(localStorage.getItem("lx_saveUser")).toBe("42");
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

    it("有 access_token 但缺少 user.id 时抛错且不写入", async () => {
      mockPost.mockResolvedValueOnce({
        data: { code: 0, access_token: "orphan_token", expires_in: 3600 },
      });
      await expect(login(baseUrl, "u", "p")).rejects.toThrow("user.id");
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
    it("有 access 与 refresh 时 body 为 refresh_token，且头带 Authorization", async () => {
      setAccessToken("old_token");
      localStorage.setItem("lx_refresh_token", "the_rtk");
      mockPost.mockResolvedValueOnce({
        data: { access_token: "new_token", expires_in: 3600 },
      });
      await refreshToken(baseUrl);
      expect(mockPost).toHaveBeenCalledWith(
        "https://example.com/api/auth/refresh",
        { refresh_token: "the_rtk" },
        expect.objectContaining({
          headers: {
            "Content-Type": "application/json",
            Authorization: "Bearer old_token",
          },
        })
      );
      expect(getAccessToken()).toBe("new_token");
    });

    it("无 refresh_token 时发空 body（仍可依赖 Cookie 续期）", async () => {
      mockPost.mockResolvedValueOnce({
        data: { access_token: "fresh", expires_in: 3600 },
      });
      await refreshToken(baseUrl);
      expect(mockPost).toHaveBeenCalledWith(
        "https://example.com/api/auth/refresh",
        {},
        expect.objectContaining({ headers: { "Content-Type": "application/json" } })
      );
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
      localStorage.setItem("lx_access_token", "x");
      mockPost.mockResolvedValueOnce({});
      await logout(baseUrl);
      expect(getAccessToken()).toBeNull();
    });

    it("请求失败时仍清除本地缓存", async () => {
      localStorage.setItem("lx_access_token", "x");
      mockPost.mockRejectedValueOnce(new Error("Network error"));
      await expect(logout(baseUrl)).rejects.toThrow("Network error");
      expect(getAccessToken()).toBeNull();
    });
  });
});
