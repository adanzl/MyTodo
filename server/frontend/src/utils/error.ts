/**
 * 错误处理工具函数
 */
import { ElMessage } from "element-plus";
import type { AxiosError } from "axios";
import { logger } from "./logger";

interface ErrorOptions {
  context?: string;
}

/**
 * 处理 API 错误
 * @param error 错误对象
 * @param defaultMessage 默认错误消息
 * @param options 选项
 */
export function logAndNoticeError(
  error: Error | AxiosError,
  defaultMessage: string,
  options: ErrorOptions = {}
): void {
  const { context } = options;
  const errorContext = context ? `${defaultMessage} (${context})` : defaultMessage;

  // 使用统一的 logger
  logger.error(errorContext, error);

  // 提取错误消息
  const axiosError = error as AxiosError<{ msg?: string }>;
  const errorMessage = axiosError?.response?.data?.msg || error?.message || "未知错误";

  // 显示错误提示
  ElMessage.error(`${defaultMessage}: ${errorMessage}`);
}
