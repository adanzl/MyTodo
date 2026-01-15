/**
 * 设备相关类型定义
 */
import type { DeviceType } from "@/constants/device";

/**
 * 基础设备接口
 */
export interface BaseDevice {
  /**
   * 设备名称
   */
  name: string;
  /**
   * 设备地址
   */
  address: string;
  /**
   * 设备类型
   */
  type?: DeviceType;
  /**
   * 允许扩展字段
   */
  [key: string]: unknown;
}

/**
 * 蓝牙设备
 */
export interface BluetoothDevice extends BaseDevice {
  /**
   * 信号强度（RSSI）
   */
  rssi?: number;
  /**
   * 是否正在连接
   */
  connecting?: boolean;
  /**
   * 设备类型
   */
  type?: "bluetooth";
}

/**
 * DLNA 设备
 */
export interface DlnaDevice extends BaseDevice {
  /**
   * 设备位置（URL）
   */
  location?: string;
  /**
   * 制造商
   */
  manufacturer?: string;
  /**
   * 型号名称
   */
  model_name?: string;
  /**
   * 音量（0-100）
   */
  volume?: number;
  /**
   * 是否正在改变音量（内部状态）
   */
  _volumeChanging?: boolean;
  /**
   * 是否正在刷新音量（内部状态）
   */
  _volumeRefreshing?: boolean;
  /**
   * 是否正在停止（内部状态）
   */
  _stopping?: boolean;
  /**
   * 设备类型
   */
  type?: "dlna";
}

/**
 * 小米设备播放状态
 */
export interface MiDeviceStatus {
  /**
   * 播放状态：PLAYING（播放中）、STOPPED（已停止）
   */
  state?: "PLAYING" | "STOPPED";
  /**
   * 状态码：OK、ERROR
   */
  status?: "OK" | "ERROR";
  /**
   * 当前曲目索引（从1开始）
   */
  track?: number;
  /**
   * 总时长，格式如 "00:03:45"
   */
  duration?: string;
  /**
   * 已播放时长，格式如 "00:01:30"
   */
  position?: string;
  /**
   * 音量（0-100）
   */
  volume?: number;
  /**
   * 错误信息
   */
  error?: string;
}

/**
 * 小米设备
 */
export interface MiDevice extends BaseDevice {
  /**
   * 设备ID（优先使用）
   */
  deviceID?: string;
  /**
   * MAC 地址
   */
  mac?: string;
  /**
   * 米家设备ID
   */
  miotDID?: string;
  /**
   * 音量（0-100）
   */
  volume?: number;
  /**
   * 播放状态
   */
  status?: MiDeviceStatus;
  /**
   * 是否正在改变音量（内部状态）
   */
  _volumeChanging?: boolean;
  /**
   * 是否正在刷新状态（内部状态）
   */
  _statusRefreshing?: boolean;
  /**
   * 是否正在停止（内部状态）
   */
  _stopping?: boolean;
  /**
   * 设备类型
   */
  type?: "mi";
}

/**
 * Agent 设备
 */
export interface AgentDevice extends BaseDevice {
  /**
   * Agent ID
   */
  agent_id: string;
  /**
   * 支持的操作列表
   */
  actions?: string[];
  /**
   * 是否在线
   */
  is_online?: boolean;
  /**
   * 上次心跳时间（秒前）
   */
  last_heartbeat_ago?: number;
  /**
   * 设备类型
   */
  type?: "agent";
  /**
   * 测试按钮状态（动态字段）
   * 格式：testing_F{number}
   */
  [key: `testing_F${number}`]: boolean | undefined;
}

/**
 * 设备联合类型
 */
export type Device = BluetoothDevice | DlnaDevice | MiDevice | AgentDevice;

/**
 * 设备类型守卫函数
 */
export function isBluetoothDevice(device: Device): device is BluetoothDevice {
  return device.type === "bluetooth" || "rssi" in device || "connecting" in device;
}

export function isDlnaDevice(device: Device): device is DlnaDevice {
  return device.type === "dlna" || "location" in device;
}

export function isMiDevice(device: Device): device is MiDevice {
  return device.type === "mi" || "deviceID" in device || "miotDID" in device;
}

export function isAgentDevice(device: Device): device is AgentDevice {
  return device.type === "agent" || "agent_id" in device;
}
