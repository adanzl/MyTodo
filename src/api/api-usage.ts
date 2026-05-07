import { apiClient } from "./api-client";
import type { ApiResponse } from "./types";

/** 使用类型常量 */
export const USAGE_TYPE_VIDEO = 'matVideo';
export const USAGE_TYPE_PDF = 'matPdf';

/** 添加使用记录参数 */
export interface UsageItem {
  /** 使用类型：matVideo 表示视频素材，matPdf 表示 PDF 素材 */
  type: string;
  start_time: string;
  duration: number;
  user_id: number;
  out_key?: number | null;
}


/**
 * 添加使用记录
 */
export async function addUsage(data: UsageItem): Promise<void> {
  const rsp = await apiClient.post<ApiResponse<unknown>>("/usage/add", data);
  if (rsp.data.code !== 0) {
    throw new Error(rsp.data.msg || "添加使用记录失败");
  }
}

