import { api } from "./config";
import type { Gift } from "@/types/lottery/lotteryData";

export interface UserStats {
  lotteryCount: number;
  lotteryCost: number;
  exchangeCount: number;
  exchangeCost: number;
  taskCount: number;
  taskIncome: number;
  adminCount: number;
  adminIncome: number;
}

export interface CategoryStat {
  cate_id: number | null;
  cate_name: string;
  win_count: number;
  gift_types: number;
  total_cost: number;
  total_exchange_price: number;
}

export interface StatsResponse {
  user_id: number;
  stats: UserStats;
  categoryStats: CategoryStat[];
}

/**
 * 获取用户统计数据
 */
export const getUserStats = async (
  userId: number | number[],
  startDate?: string,
  endDate?: string
): Promise<StatsResponse[]> => {
  const userIdStr = Array.isArray(userId) ? userId.join(",") : userId.toString();
  const response = await api.get("/lottery/stats", {
    params: {
      user_id: userIdStr,
      start_date: startDate,
      end_date: endDate,
    },
  });
  return response.data;
};

/**
 * 获取分类下的礼物列表
 */
export const getCategoryGifts = async (cateId: number): Promise<Gift[]> => {
  const response = await api.get("/getAll", {
    params: {
      table: "t_gift",
      conditions: JSON.stringify({ cate_id: cateId }),
      pageNum: 1,
      pageSize: 1000,
    },
  });
  return response.data?.data || [];
};
