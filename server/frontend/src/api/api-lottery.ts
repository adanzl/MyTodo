/**
 * 抽奖相关 API（配置、礼物表 t_gift* CRUD）
 */
import { api } from "./config";
import { getList, getData, setData, delData } from "./api-common";
import type { ApiResponse, PaginatedResponse, DeleteResponse } from "@/types/api";
import type { GiftApiData, GiftCategory, GiftHistory } from "@/types/lottery";

/**
 * 抽奖配置数据结构
 */
export interface LotterySetting {
  fee: number;
  wish_count_threshold: number;
}

/** 奖池表 t_gift_pool */
export interface GiftPoolData {
  id: number;
  name: string;
  cost?: number;
  count?: number;
  count_mx?: number;
  cate_list?: string;
}

// ========== 抽奖配置（Redis） ==========

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

export interface RedeemResult {
  history_id: number;
  user_id: number;
  status: number;
  inventory: string;
}

/** 核销/取消核销礼物记录，并同步扣减/恢复用户背包 */
export async function redeemGift(historyId: number): Promise<RedeemResult> {
  const rsp = await api.post<ApiResponse<RedeemResult>>("/redeem", {
    history_id: historyId,
  });

  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }

  return rsp.data.data;
}

// ========== t_gift_category ==========

export async function getGiftCategoryList<T = GiftCategory>(
  conditions?: Record<string, unknown>,
  pageNum?: number,
  pageSize?: number
): Promise<PaginatedResponse<T>> {
  return getList<T>("t_gift_category", conditions, pageNum, pageSize);
}

export async function setGiftCategory(data: Record<string, unknown>): Promise<unknown> {
  return setData("t_gift_category", data);
}

export async function deleteGiftCategory(id: number | string): Promise<DeleteResponse> {
  return delData("t_gift_category", id);
}

// ========== t_gift ==========

export async function getGiftList<T = GiftApiData>(
  conditions?: Record<string, unknown>,
  pageNum?: number,
  pageSize?: number
): Promise<PaginatedResponse<T>> {
  return getList<T>("t_gift", conditions, pageNum, pageSize);
}

export async function getGift<T = GiftApiData>(
  id: number | string,
  fields: string | string[] = "*"
): Promise<T> {
  return getData<T>("t_gift", id, fields);
}

export async function setGift(data: Record<string, unknown>): Promise<unknown> {
  return setData("t_gift", data);
}

export async function deleteGift(id: number | string): Promise<DeleteResponse> {
  return delData("t_gift", id);
}

export async function getGiftsByIds<T = GiftApiData>(ids: number[]): Promise<PaginatedResponse<T>> {
  if (!ids.length) {
    return { code: 0, data: { data: [], pageNum: 1, pageSize: 0, totalCount: 0, totalPage: 0 } };
  }
  return getGiftList<T>({ id: { in: ids } });
}

// ========== t_gift_pool ==========

export async function getGiftPoolList<T = GiftPoolData>(
  conditions?: Record<string, unknown>,
  pageNum?: number,
  pageSize?: number
): Promise<PaginatedResponse<T>> {
  return getList<T>("t_gift_pool", conditions, pageNum, pageSize);
}

export async function getGiftPool<T = GiftPoolData>(
  id: number | string,
  fields: string | string[] = "*"
): Promise<T> {
  return getData<T>("t_gift_pool", id, fields);
}

export async function setGiftPool(data: Record<string, unknown>): Promise<unknown> {
  return setData("t_gift_pool", data);
}

export async function deleteGiftPool(id: number | string): Promise<DeleteResponse> {
  return delData("t_gift_pool", id);
}

// ========== t_gift_history ==========

export async function getGiftHistoryList<T = GiftHistory>(
  conditions?: Record<string, unknown>,
  pageNum?: number,
  pageSize?: number
): Promise<PaginatedResponse<T>> {
  return getList<T>("t_gift_history", conditions, pageNum, pageSize);
}

export async function setGiftHistory(data: Record<string, unknown>): Promise<unknown> {
  return setData("t_gift_history", data);
}
