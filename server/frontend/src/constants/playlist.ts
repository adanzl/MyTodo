/**
 * 播放列表相关常量
 */
import type { DeviceType } from "./device";
import { DEVICE_TYPES } from "./device";

/**
 * 播放列表刷新间隔（毫秒）
 */
export const PLAYLIST_REFRESH_INTERVAL = 5000; // 5秒

/**
 * 默认播放列表名称
 */
export const DEFAULT_PLAYLIST_NAME = "默认播放列表";

/**
 * 最大播放持续时间（分钟）
 * 1440 分钟 = 24 小时
 */
export const MAX_PLAYLIST_DURATION = 1440;

/**
 * 一周的天数
 * 用于 pre_lists 数组长度
 */
export const WEEKDAYS_COUNT = 7;

/**
 * 有效的设备类型列表
 */
export const VALID_DEVICE_TYPES: DeviceType[] = [...DEVICE_TYPES];

/**
 * 默认设备类型
 */
export const DEFAULT_DEVICE_TYPE: DeviceType = "dlna";

/**
 * localStorage 中存储激活播放列表ID的键名
 */
export const STORAGE_KEY_ACTIVE_PLAYLIST_ID = "active_playlist_id";

/**
 * 默认 Cron 表达式示例
 */
export const DEFAULT_CRON_EXAMPLES = {
  DAILY: "0 0 * * *", // 每天0点
  WEEKDAYS: "0 0 9 * * 1-5", // 工作日9点
  MONTHLY: "0 0 0 1 * *", // 每月1号0点
} as const;

/**
 * 触发按钮选项
 */
export const TRIGGER_BUTTONS = {
  NONE: "",
  BUTTON_1: "B1",
  BUTTON_2: "B2",
  BUTTON_3: "B3",
} as const;

export type TriggerButton = (typeof TRIGGER_BUTTONS)[keyof typeof TRIGGER_BUTTONS];
