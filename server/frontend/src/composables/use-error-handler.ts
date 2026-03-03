/**
 * 错误处理 Composable
 * 统一处理错误，提供一致的错误处理体验
 */
import type { AxiosError } from "axios";
import { logAndNoticeError } from "@/utils/error";
import { logger } from "@/utils/logger";

export interface ErrorHandlerOptions {
  /**
   * 是否显示错误提示
   * @default true
   */
  showMessage?: boolean;
  /**
   * 是否记录错误日志
   * @default true
   */
  logError?: boolean;
  /**
   * 错误上下文信息
   */
  context?: string;
  /**
   * 自定义错误消息
   */
  customMessage?: string;
}

/**
 * 统一错误处理 Composable
 */
export function useErrorHandler() {
  /**
   * 处理错误
   * @param error 错误对象
   * @param defaultMessage 默认错误消息
   * @param options 处理选项
   */
  const handleError = (
    error: unknown,
    defaultMessage: string,
    options: ErrorHandlerOptions = {}
  ): void => {
    const { showMessage = true, logError = true, context, customMessage } = options;

    // 转换为 Error 对象
    const errorObj =
      error instanceof Error
        ? error
        : new Error(error !== null && error !== undefined ? String(error) : "未知错误");

    // 记录错误日志
    if (logError) {
      if (context) {
        logger.error(`[${context}] ${defaultMessage}`, errorObj);
      } else {
        logger.error(defaultMessage, errorObj);
      }
    }

    // 显示错误提示
    if (showMessage) {
      const message = customMessage || defaultMessage;
      if (error instanceof Error && "response" in error) {
        // Axios 错误，使用 logAndNoticeError 处理
        logAndNoticeError(error as AxiosError, message, { context });
      } else {
        // 普通错误，直接显示消息
        logAndNoticeError(errorObj, message, { context });
      }
    }
  };

  /**
   * 静默处理错误（只记录日志，不显示提示）
   */
  const handleErrorSilently = (error: unknown, context?: string): void => {
    handleError(error, "操作失败", {
      showMessage: false,
      logError: true,
      context,
    });
  };

  /**
   * 处理错误并返回默认值
   */
  const handleErrorWithFallback = <T>(
    error: unknown,
    defaultMessage: string,
    fallbackValue: T,
    options?: ErrorHandlerOptions
  ): T => {
    handleError(error, defaultMessage, options);
    return fallbackValue;
  };

  return {
    handleError,
    handleErrorSilently,
    handleErrorWithFallback,
  };
}
