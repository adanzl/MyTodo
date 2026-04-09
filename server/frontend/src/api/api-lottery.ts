/**
 * 抽奖相关 API
 */
import { api } from "./config";
import type { ApiResponse } from "@/types/api";

/**
 * 抽奖配置数据结构
 */
export interface LotterySetting {
  fee: number;
  wish_count_threshold: number;
}

/**
 * 获取抽奖配置
 */
export async function getLotterySetting(): Promise<LotterySetting> {
  const rsp = await api.get<ApiResponse<string>>("/getRdsData", {
    params: { table: "lottery", id: 2 },
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }

  if (!rsp.data.data) {
    return {
      fee: 10,
      wish_count_threshold: 5,
    };
  }

  const parsed = JSON.parse(rsp.data.data);
  return {
    fee: parsed.fee ?? 10,
    wish_count_threshold: parsed.wish_count_threshold ?? 5,
  };
}

/**
 * 设置抽奖配置
 */
export async function setLotterySetting(setting: LotterySetting): Promise<void> {
  const rsp = await api.post<ApiResponse<void>>("/setRdsData", {
    table: "lottery",
    data: {
      id: 2,
      value: JSON.stringify(setting),
    },
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
}

/**
 * 撤销一次抽奖：删除该条积分历史、恢复用户积分、补充对应礼物库存
 */
export async function undoLottery(historyId: number): Promise<{ user_id: number; score: number }> {
  const rsp = await api.post<ApiResponse<{ user_id: number; score: number }>>("/undoLottery", {
    history_id: historyId,
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }

  return rsp.data.data;
}
