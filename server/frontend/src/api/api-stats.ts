import { api } from "./config";

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

export interface WonGift {
  id: number;
  name: string;
  count: number;
  image: string;
  cost: number;
}

export interface CategoryStat {
  cate_id: number | null;
  cate_name: string;
  win_count: number;
  gift_types: number;
  total_cost: number;
  total_exchange_price: number;
  won_gifts: WonGift[];
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
