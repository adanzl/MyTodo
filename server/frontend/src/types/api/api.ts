/**
 * API 响应类型定义
 */

/**
 * 标准 API 响应接口
 * @template T - 响应数据的类型
 */
export interface ApiResponse<T = unknown> {
  /**
   * 响应码，0 表示成功
   */
  code: number;
  /**
   * 响应消息
   */
  msg?: string;
  /**
   * 响应数据
   */
  data: T;
}

/**
 * 分页响应接口
 * @template T - 列表项的类型
 */
export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  /**
   * 总记录数
   */
  total?: number;
  /**
   * 当前页码
   */
  pageNum?: number;
  /**
   * 每页大小
   */
  pageSize?: number;
}

/**
 * 成功响应类型（code === 0）
 */
export type SuccessResponse<T = unknown> = ApiResponse<T> & {
  code: 0;
};

/**
 * 错误响应类型（code !== 0）
 */
export type ErrorResponse = ApiResponse<never> & {
  code: number;
  msg: string;
};

/**
 * 空响应（无数据返回）
 */
export interface EmptyResponse {
  code: number;
  msg?: string;
}

/**
 * 删除操作响应
 */
export interface DeleteResponse {
  success: boolean;
  message?: string;
}
