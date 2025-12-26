/**
 * 错误处理工具函数
 */
import { ElMessage } from "element-plus";
import type { AxiosError } from "axios";

interface ErrorOptions {
  context?: string;
}

/**
 * 处理 API 错误
 */
export function logAndNoticeError(
  error: Error | AxiosError,
  defaultMessage: string,
  options: ErrorOptions = {}
): void {
  const { context } = options;
  const errorContext = context ? `${defaultMessage} (${context})` : defaultMessage;
  console.error(errorContext, error);

  const axiosError = error as AxiosError<{ msg?: string }>;
  const errorMessage =
    axiosError?.response?.data?.msg || error?.message || "未知错误";
  ElMessage.error(`${defaultMessage}: ${errorMessage}`);
}


