/**
 * LocalCache 单测：set/get/remove/has，过期与异常路径
 */
import { LocalCache } from "@/utils/LocalCache";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

describe("LocalCache", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.useFakeTimers({ now: 1000000000000 });
  });

  afterEach(() => {
    vi.useRealTimers();
    localStorage.clear();
  });

  describe("set / get", () => {
    it("set 后 get 在 ttl 内可读回", () => {
      LocalCache.set("k", { a: 1 }, 60);
      expect(LocalCache.get<{ a: number }>("k")).toEqual({ a: 1 });
    });

    it("get 时已过期则返回 null 并移除该 key", () => {
      LocalCache.set("k", "v", 1);
      vi.advanceTimersByTime(2000);
      expect(LocalCache.get("k")).toBeNull();
      expect(localStorage.getItem("k")).toBeNull();
    });

    it("key 不存在时 get 返回 null", () => {
      expect(LocalCache.get("none")).toBeNull();
    });

    it("可缓存任意可 JSON 序列化的值", () => {
      LocalCache.set("arr", [1, 2], 10);
      expect(LocalCache.get<number[]>("arr")).toEqual([1, 2]);
      LocalCache.set("str", "hello", 10);
      expect(LocalCache.get<string>("str")).toBe("hello");
    });
  });

  describe("remove", () => {
    it("remove 后 get 返回 null", () => {
      LocalCache.set("k", "v", 60);
      LocalCache.remove("k");
      expect(LocalCache.get("k")).toBeNull();
    });
  });

  describe("has", () => {
    it("set 后 has 为 true", () => {
      LocalCache.set("k", "v", 60);
      expect(LocalCache.has("k")).toBe(true);
    });

    it("remove 后 has 为 false", () => {
      LocalCache.set("k", "v", 60);
      LocalCache.remove("k");
      expect(LocalCache.has("k")).toBe(false);
    });

    it("过期后 has 为 false（get 会移除）", () => {
      LocalCache.set("k", "v", 1);
      vi.advanceTimersByTime(2000);
      expect(LocalCache.has("k")).toBe(false);
    });

    it("从未 set 的 key has 为 false", () => {
      expect(LocalCache.has("missing")).toBe(false);
    });
  });

  describe("异常路径", () => {
    it("localStorage 中非合法 JSON 时 get 会抛错", () => {
      localStorage.setItem("bad", "not json");
      expect(() => LocalCache.get("bad")).toThrow();
    });
  });
});
