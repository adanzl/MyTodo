/**
 * 定时器管理 Composable
 * 统一管理 setInterval，确保正确清理，避免内存泄漏
 */
import { onUnmounted } from "vue";
import { logger } from "@/utils/logger";

export interface UseIntervalOptions {
  /**
   * 是否立即执行一次
   * @default false
   */
  immediate?: boolean;
  /**
   * 是否在组件卸载时自动清理
   * @default true
   */
  autoCleanup?: boolean;
}

/**
 * 创建定时器管理
 * @param callback 定时执行的回调函数
 * @param delay 延迟时间（毫秒），如果为 null 则不启动定时器
 * @param options 配置选项
 * @returns 控制定时器的方法
 */
export function useInterval(
  callback: () => void | Promise<void>,
  delay: number | null,
  options: UseIntervalOptions = {}
): {
  start: () => void;
  stop: () => void;
  restart: (newDelay?: number) => void;
  isRunning: () => boolean;
} {
  const { immediate = false, autoCleanup = true } = options;
  let timer: ReturnType<typeof setInterval> | null = null;
  let currentDelay: number | null = delay;

  const execute = async () => {
    try {
      await callback();
    } catch (error) {
      logger.error("[useInterval] 定时器回调执行失败:", error);
    }
  };

  const start = () => {
    if (currentDelay === null || currentDelay <= 0) {
      return;
    }

    // 如果已经运行，先停止
    stop();

    // 如果设置了立即执行，先执行一次
    if (immediate) {
      execute();
    }

    // 启动定时器
    timer = setInterval(execute, currentDelay);
  };

  const stop = () => {
    if (timer !== null) {
      clearInterval(timer);
      timer = null;
    }
  };

  const restart = (newDelay?: number) => {
    if (newDelay !== undefined) {
      currentDelay = newDelay;
    }
    start();
  };

  const isRunning = (): boolean => {
    return timer !== null;
  };

  // 如果提供了 delay，自动启动
  if (delay !== null && delay > 0) {
    start();
  }

  // 组件卸载时自动清理
  if (autoCleanup) {
    onUnmounted(() => {
      stop();
    });
  }

  return {
    start,
    stop,
    restart,
    isRunning,
  };
}

/**
 * 创建可控制的定时器（需要手动启动）
 * @param callback 定时执行的回调函数
 * @param delay 延迟时间（毫秒）
 * @param options 配置选项
 * @returns 控制定时器的方法
 */
export function useControllableInterval(
  callback: () => void | Promise<void>,
  delay: number,
  options: UseIntervalOptions = {}
) {
  // 使用内部状态存储 delay，以便在 start 时使用
  let storedDelay: number = delay;
  const interval = useInterval(callback, null, { ...options, autoCleanup: true });

  return {
    start: () => {
      interval.restart(storedDelay);
    },
    stop: interval.stop,
    restart: (newDelay?: number) => {
      if (newDelay !== undefined) {
        storedDelay = newDelay;
      }
      interval.restart(storedDelay);
    },
    isRunning: interval.isRunning,
  };
}
