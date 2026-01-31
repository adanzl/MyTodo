/**
 * api/schedule 单测：getSave、setSave、getScheduleList 成功与异常路径
 */
import { getScheduleList, setSave } from "@/api/schedule";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mockGet = vi.fn();
const mockPost = vi.fn();
vi.mock("@/api/api-client", () => ({
  apiClient: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
  },
}));

vi.mock("@/types/EventBus", () => ({
  default: { $emit: vi.fn() },
  C_EVENT: { UPDATE_SAVE: "updateSave" },
}));

describe("api/schedule", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getScheduleList", () => {
    it("code===0 时返回 ApiListResponse<ScheduleListItem>", async () => {
      mockGet.mockResolvedValueOnce({
        data: {
          code: 0,
          data: {
            data: [
              { id: 1, name: "默认", user_id: 1 },
            ],
          },
        },
      });
      const result = await getScheduleList();
      expect(result.data).toHaveLength(1);
      expect(result.data[0]).toEqual({ id: 1, name: "默认", user_id: 1 });
      expect(mockGet).toHaveBeenCalledWith("/getAll", {
        params: { table: "t_schedule", fields: "id,name,user_id" },
      });
    });

    it("code!==0 时抛出 Error(msg)", async () => {
      mockGet.mockResolvedValueOnce({
        data: { code: 500, msg: "服务异常" },
      });
      await expect(getScheduleList()).rejects.toThrow("服务异常");
    });
  });

  describe("setSave", () => {
    it("id 为 undefined 时 reject", async () => {
      await expect(
        setSave(undefined, { schedules: [] })
      ).rejects.toThrow("id is undefined");
      expect(mockPost).not.toHaveBeenCalled();
    });

    it("code===0 时 resolve", async () => {
      mockPost.mockResolvedValueOnce({ data: { code: 0 } });
      await expect(setSave(1, { id: 1, name: "x", schedules: [], save: {} })).resolves.toBeUndefined();
      expect(mockPost).toHaveBeenCalledWith("/setData", {
        table: "t_schedule",
        data: {
          id: 1,
          data: expect.any(String),
        },
      });
    });

    it("code!==0 时 reject Error(msg)", async () => {
      mockPost.mockResolvedValueOnce({
        data: { code: 400, msg: "数据格式错误" },
      });
      await expect(setSave(1, {})).rejects.toThrow("数据格式错误");
    });
  });
});
