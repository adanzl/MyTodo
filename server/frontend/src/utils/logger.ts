/**
 * 日志工具
 * 统一管理日志输出，生产环境自动过滤 console.log
 */

const isDev = import.meta.env.DEV;

/**
 * 日志级别
 */
export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
}

/**
 * 日志配置
 */
interface LoggerConfig {
  /**
   * 是否在开发环境输出日志
   * @default true
   */
  enableInDev?: boolean;
  /**
   * 是否在开发环境输出调试日志
   * @default false
   */
  enableDebugInDev?: boolean;
  /**
   * 是否在生产环境输出错误日志
   * @default true
   */
  enableErrorInProd?: boolean;
}

const defaultConfig: LoggerConfig = {
  enableInDev: true,
  enableDebugInDev: false, // 默认关闭调试日志
  enableErrorInProd: true,
};

/**
 * 统一的日志工具
 */
export const logger = {
  /**
   * 调试日志（仅在开发环境输出，默认关闭）
   */
  debug: (...args: unknown[]) => {
    if (isDev && defaultConfig.enableInDev && defaultConfig.enableDebugInDev) {
      console.debug("[DEBUG]", ...args);
    }
  },

  /**
   * 信息日志（仅在开发环境输出）
   */
  info: (...args: unknown[]) => {
    if (isDev && defaultConfig.enableInDev) {
      console.info("[INFO]", ...args);
    }
  },

  /**
   * 警告日志（仅在开发环境输出）
   */
  warn: (...args: unknown[]) => {
    if (isDev && defaultConfig.enableInDev) {
      console.warn("[WARN]", ...args);
    }
  },

  /**
   * 错误日志（始终输出）
   */
  error: (...args: unknown[]) => {
    if (isDev || defaultConfig.enableErrorInProd) {
      console.error("[ERROR]", ...args);
    }
  },

  /**
   * 配置日志行为
   */
  configure: (config: LoggerConfig) => {
    Object.assign(defaultConfig, config);
  },
};
