/**
 * 设备相关常量
 */

/**
 * 设备类型列表
 */
export const DEVICE_TYPES = ["agent", "dlna", "bluetooth", "mi"] as const;

/**
 * 设备类型
 */
export type DeviceType = (typeof DEVICE_TYPES)[number];

/**
 * Agent 设备列表刷新间隔（毫秒）
 */
export const AGENT_LIST_REFRESH_INTERVAL = 10000; // 10秒

/**
 * 设备扫描超时时间（秒）
 */
export const DEVICE_SCAN_TIMEOUT = 5;
