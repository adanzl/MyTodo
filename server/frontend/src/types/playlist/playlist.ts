/**
 * 播放列表相关类型定义
 */

import type { MediaFile } from "../tools/media";
import type { DeviceType } from "@/constants/device";
import type { TriggerButton } from "@/constants/playlist";

/**
 * 播放列表项
 * 继承自 MediaFile，用于播放列表中的文件项
 */
export interface PlaylistItem extends MediaFile {
  /**
   * 文件URI（统一资源标识符）
   */
  uri?: string;
  /**
   * 文件路径
   */
  path?: string;
  /**
   * 文件名
   */
  name?: string;
  /**
   * 文件时长（秒）
   */
  duration?: number | null;
  /**
   * 文件大小（字节）
   */
  size?: number;
  /**
   * 文件扩展名
   */
  extension?: string;
}

/**
 * 播放列表定时任务配置
 */
export interface PlaylistSchedule {
  /**
   * 是否启用定时任务
   * 0: 未启用
   * 1: 已启用
   */
  enabled: 0 | 1;
  /**
   * Cron 表达式
   * 用于定义定时任务的执行时间
   */
  cron: string;
  /**
   * 播放持续时间（分钟）
   * 0 表示播放到列表结束
   */
  duration: number;
}

/**
 * 播放列表关联的设备
 */
export interface PlaylistDevice {
  /**
   * 设备类型
   */
  type: DeviceType;
  /**
   * 设备地址
   */
  address: string | null;
  /**
   * 设备名称（可选）
   */
  name?: string | null;
}

/**
 * 播放列表基础结构
 * 用于存储和传输播放列表数据
 */
export interface Playlist {
  /**
   * 播放列表ID
   */
  id: string;
  /**
   * 播放列表名称
   */
  name: string;
  /**
   * 主播放列表（文件列表）
   */
  playlist: PlaylistItem[];
  /**
   * 前置文件列表（7天，对应一周7天）
   * 每个元素是一天的前置文件列表
   */
  pre_lists: PlaylistItem[][];
  /**
   * 播放列表总文件数
   */
  total: number;
  /**
   * 当前播放索引（主播放列表中的索引）
   */
  current_index: number;
  /**
   * 前置文件索引（当前前置文件列表中的索引）
   * -1 表示不在前置文件中
   */
  pre_index: number;
  /**
   * 设备地址（兼容字段）
   */
  device_address: string | null;
  /**
   * 设备类型（兼容字段）
   */
  device_type: DeviceType;
  /**
   * 设备信息
   */
  device: PlaylistDevice;
  /**
   * 定时任务配置
   */
  schedule: PlaylistSchedule;
  /**
   * 触发按钮
   */
  trigger_button: TriggerButton | string;
  /**
   * 创建时间（时间戳，毫秒）
   */
  create_time?: string;
  /**
   * 更新时间（时间戳，毫秒）
   */
  updated_time?: string;
  /**
   * 更新时间（时间戳，毫秒，前端使用）
   */
  updatedAt: number;
  /**
   * 是否正在播放
   */
  isPlaying: boolean;
}

/**
 * 播放列表状态
 * 继承自 Playlist，包含运行时状态信息
 */
export interface PlaylistStatus extends Playlist {
  /**
   * 当前前置文件列表（根据选中的星期计算）
   */
  pre_files?: PlaylistItem[];
  /**
   * 是否正在播放前置文件
   */
  in_pre_files: boolean;
}

/**
 * 播放列表集合
 * 包含多个播放列表和当前激活的播放列表ID
 */
export interface PlaylistCollection {
  /**
   * 播放列表数组
   */
  playlists: Playlist[];
  /**
   * 当前激活的播放列表ID
   */
  activePlaylistId: string | null;
}

/**
 * API 返回的播放列表数据格式
 * 用于从 API 获取数据时的格式转换
 */
export interface PlaylistApiData {
  /**
   * 播放列表ID
   */
  id: string;
  /**
   * 播放列表名称
   */
  name: string;
  /**
   * 文件列表（API 格式）
   */
  files: PlaylistItem[];
  /**
   * 前置文件列表（API 格式，7天）
   */
  pre_lists?: PlaylistItem[][];
  /**
   * 前置文件（兼容字段）
   */
  pre_files?: PlaylistItem[];
  /**
   * 当前播放索引
   */
  current_index: number;
  /**
   * 前置文件索引
   */
  pre_index?: number;
  /**
   * 是否在前置文件中
   */
  in_pre_files?: boolean | 0 | 1;
  /**
   * 设备信息
   */
  device?: PlaylistDevice;
  /**
   * 设备地址（兼容字段）
   */
  device_address?: string | null;
  /**
   * 设备类型（兼容字段）
   */
  device_type?: DeviceType;
  /**
   * 定时任务配置
   */
  schedule?: PlaylistSchedule;
  /**
   * 触发按钮
   */
  trigger_button?: TriggerButton | string;
  /**
   * 创建时间
   */
  create_time?: string;
  /**
   * 更新时间
   */
  updated_time?: string;
  /**
   * 是否正在播放
   */
  isPlaying?: boolean | 0 | 1;
}

/**
 * 播放列表操作请求参数
 */
export interface PlaylistActionParams {
  /**
   * 播放列表ID
   */
  id?: string;
  /**
   * 其他参数
   */
  [key: string]: unknown;
}
