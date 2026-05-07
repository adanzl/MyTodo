import { api } from "./config";

export interface UsageAbstractResponse {
  // 根据后端返回的实际结构调整
  [key: string]: any;
}

/**
 * 获取使用统计摘要
 * @param startTime 开始时间
 * @param endTime 结束时间
 * @param detail 是否返回详细信息 (0 或 1)
 */
export const getUsageAbstract = async (
  startTime: string,
  endTime: string,
  detail: number = 0
): Promise<UsageAbstractResponse> => {
  const response = await api.get("/usage/abstract", {
    params: {
      start_time: startTime,
      end_time: endTime,
      detail: detail,
    },
  });
  return response.data;
};
