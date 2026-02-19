/**
 * 抽奖相关接口：配置读写、奖品信息、执行抽奖。
 * 与后端约定及边界条件见：docs/业务说明.md § 抽奖规则
 */
import { apiClient } from "./api-client";
import type {
  ApiResponse,
  GiftItem,
  DoLotteryBody,
  DoLotteryResult,
  DoExchangeResult,
  LotteryConfig,
} from "./types";

export async function getLotteryData(): Promise<LotteryConfig> {
  const rsp = await apiClient.get<ApiResponse<LotteryConfig>>("/getRdsData", {
    params: { table: "lottery", id: 2 },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return (rsp.data.data ?? "") as LotteryConfig;
}

export async function setLotteryData(value: string): Promise<void> {
  const rsp = await apiClient.post<ApiResponse<unknown>>("/setRdsData", {
    table: "lottery",
    data: { id: 2, value },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
}

export async function getGiftData(id: number): Promise<GiftItem> {
  const rsp = await apiClient.get<ApiResponse<GiftItem>>("/getData", {
    params: { id, table: "t_gift", fields: "*" },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data!;
}

export async function doLottery(
  userId: number,
  cateId: number
): Promise<DoLotteryResult> {
  const body: DoLotteryBody = { user_id: userId, cate_id: cateId };
  const rsp = await apiClient.post<ApiResponse<DoLotteryResult>>(
    "/doLottery",
    body
  );
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data!;
}

/** 兑换：扣库存、扣积分并记录历史 */
export async function doExchange(
  userId: number,
  giftId: number
): Promise<DoExchangeResult> {
  const rsp = await apiClient.post<ApiResponse<DoExchangeResult>>("/exchange", {
    user_id: userId,
    gift_id: giftId,
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data!;
}

/** 礼物成本均值接口返回 */
export interface GiftAvgCostResult {
  /** 所有符合条件礼物的总体均值 */
  avg_cost: number;
  /** 参与统计的礼物总数量 */
  total_count: number;
  /** 按类别统计的均值信息 */
  by_category: Array<{
    cate_id: number | null;
    /** 类别名称（如果存在） */
    cate_name?: string | null;
    avg_cost: number;
    count: number;
  }>;
}

export async function getGiftAvgCost(params?: {
  /** 是否按启用状态筛选（1: 只看启用，0: 只看未启用） */
  enable?: number;
  /** 是否按兑换属性筛选（1: 只看可兑换，0: 只看不可兑换） */
  exchange?: number;
}): Promise<GiftAvgCostResult> {
  const rsp = await apiClient.get<ApiResponse<GiftAvgCostResult>>(
    "/giftAvgCost",
    { params }
  );
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg ?? "请求失败");
  }
  return rsp.data.data!;
}
