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
