/**
 * 请求拦截器：进入时绑定会话，等待续期后若会话变化则取消（不携带新账号 token）。
 */
import { SessionChangedError } from "@/api/api-client";
import {
  applyLoginSession,
  captureSessionScope,
  sessionScopeMatches,
  type LoginResponse,
} from "@/utils/auth-util";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

describe("SessionChangedError / sessionScopeMatches", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("换账号后会话 scope 不再匹配", () => {
    applyLoginSession("1", {
      code: 0,
      msg: "",
      access_token: "a1",
      expires_in: 3600,
    } as LoginResponse);
    const scopeA = captureSessionScope();
    applyLoginSession("2", {
      code: 0,
      msg: "",
      access_token: "b1",
      expires_in: 3600,
    } as LoginResponse);
    expect(sessionScopeMatches(scopeA)).toBe(false);
  });

  it("SessionChangedError 可被识别", () => {
    const err = new SessionChangedError();
    expect(err.name).toBe("SessionChangedError");
  });
});
