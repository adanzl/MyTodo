/**
 * 抽奖相关接口：配置读写、奖品信息、执行抽奖。
 * 与后端约定及边界条件见：docs/业务说明.md § 抽奖规则
 */
import { apiClient } from "./api-client";
import type {
  ApiResponse,
  ApiPagedResponse,
  GiftItem,
  GiftListItem,
  GiftCategoryItem,
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

export async function doLottery(userId: number, poolId: number): Promise<DoLotteryResult> {
  const body: DoLotteryBody = { user_id: userId, pool_id: poolId };
  const rsp = await apiClient.post<ApiResponse<DoLotteryResult>>("/doLottery", body);
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

/** 奖池管理相关接口 */
export interface LotteryPool {
  id?: number;
  name: string;
  cost?: number;
  count?: number;
  count_mx?: number;
  cate_list?: string;
  total_count?: number;
  remaining_count?: number;
  start_time?: string;
  end_time?: string;
}

export async function setLotteryPool(pool: LotteryPool): Promise<void> {
  const rsp = await apiClient.post<ApiResponse<unknown>>("/setData", {
    table: "t_gift_pool",
    data: pool,
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
}

export async function delLotteryPool(id: number): Promise<void> {
  const rsp = await apiClient.post<ApiResponse<unknown>>("/delData", {
    table: "t_gift_pool",
    id,
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
}

/** 获取奖品列表（支持分页和筛选） */
export async function getGiftList(params?: {
  /** 筛选条件，例如 { enable: 1, show: 1, cate_id: 5 } */
  conditions?: Record<string, unknown>;
  /** 页码，默认 1 */
  pageNum?: number;
  /** 每页数量，默认 10 */
  pageSize?: number;
}): Promise<ApiPagedResponse<GiftListItem>> {
  const { conditions, pageNum = 1, pageSize = 10 } = params ?? {};
  const rsp = await apiClient.get<ApiResponse<ApiPagedResponse<GiftListItem>>>("/getAll", {
    params: {
      table: "t_gift",
      conditions: conditions ? JSON.stringify(conditions) : undefined,
      pageNum,
      pageSize,
    },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data!;
}

/** 设置奖品数据（新增或更新） */
export async function setGiftData(data: GiftListItem): Promise<void> {
  const payload = { ...data };
  if (payload.id === -1 || payload.id === undefined) {
    delete payload.id;
  }
  const rsp = await apiClient.post<ApiResponse<unknown>>("/setData", {
    table: "t_gift",
    data: payload,
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
}

/** 删除奖品 */
export async function delGiftData(id: number): Promise<void> {
  const rsp = await apiClient.post<ApiResponse<unknown>>("/delData", {
    table: "t_gift",
    id,
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
}

/** 获取奖品类别列表 */
export async function getGiftCategoryList(params?: {
  conditions?: Record<string, unknown>;
  pageNum?: number;
  pageSize?: number;
}): Promise<ApiPagedResponse<GiftCategoryItem>> {
  const { conditions, pageNum = 1, pageSize = 10 } = params ?? {};
  const rsp = await apiClient.get<ApiResponse<ApiPagedResponse<GiftCategoryItem>>>("/getAll", {
    params: {
      table: "t_gift_category",
      conditions: conditions ? JSON.stringify(conditions) : undefined,
      pageNum,
      pageSize,
    },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data!;
}

/** 设置奖品类别数据 */
export async function setGiftCategoryData(data: GiftCategoryItem): Promise<void> {
  const payload = { ...data };
  if (payload.id === -1 || payload.id === undefined) {
    delete payload.id;
  }
  const rsp = await apiClient.post<ApiResponse<unknown>>("/setData", {
    table: "t_gift_category",
    data: payload,
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
}

/** 删除奖品类别 */
export async function delGiftCategory(id: number): Promise<void> {
  const rsp = await apiClient.post<ApiResponse<unknown>>("/delData", {
    table: "t_gift_category",
    id,
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
}

/** 获取奖池列表 */
export async function getGiftPoolList(params?: {
  conditions?: Record<string, unknown>;
  pageNum?: number;
  pageSize?: number;
}): Promise<ApiPagedResponse<LotteryPool>> {
  const { conditions, pageNum = 1, pageSize = 10 } = params ?? {};
  const rsp = await apiClient.get<ApiResponse<ApiPagedResponse<LotteryPool>>>("/getAll", {
    params: {
      table: "t_gift_pool",
      conditions: conditions ? JSON.stringify(conditions) : undefined,
      pageNum,
      pageSize,
    },
  });
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg);
  }
  return rsp.data.data!;
}


