/**
 * 设备相关 API
 * 包含蓝牙、小米设备、DLNA 设备的操作接口
 */
import { api } from "./config";
import type { ApiResponse } from "@/types/api";
import type { MiDeviceStatus } from "@/types/device/device";

// ========== 蓝牙设备 API ==========

/**
 * 蓝牙操作接口
 */
export async function bluetoothAction(
  action: string,
  method: "GET" | "POST",
  params?: Record<string, unknown>
): Promise<ApiResponse<unknown>> {
  let rsp;
  const routePrefix = "bluetooth";
  if (method === "GET") {
    rsp = await api.get(`/${routePrefix}/${action}`, {
      params: params,
    });
  } else {
    rsp = await api.post(`/${routePrefix}/${action}`, params);
  }
  return rsp.data;
}

// ========== 小米设备 API ==========

/**
 * 扫描小米设备
 */
export async function scanMiDevices(timeout?: number): Promise<ApiResponse<unknown[]>> {
  const response = await api.get("/mi/scan", {
    params: { timeout },
  });
  return response.data;
}

/**
 * 获取小米设备状态（包含音量和播放状态）
 */
export async function getMiDeviceStatus(deviceId: string): Promise<ApiResponse<MiDeviceStatus>> {
  const response = await api.get("/mi/status", {
    params: { device_id: deviceId },
  });
  return response.data;
}

/**
 * 设置小米设备音量
 */
export async function setMiDeviceVolume(
  deviceId: string,
  volume: number
): Promise<ApiResponse<{ volume: number }>> {
  const response = await api.post("/mi/volume", {
    device_id: deviceId,
    volume,
  });
  return response.data;
}

/**
 * 停止小米设备播放
 */
export async function stopMiDevice(deviceId: string): Promise<ApiResponse<{ message: string }>> {
  const response = await api.post("/mi/stop", {
    device_id: deviceId,
  });
  return response.data;
}

// ========== DLNA 设备 API ==========

/**
 * 扫描 DLNA 设备
 */
export async function scanDlnaDevices(timeout?: number): Promise<ApiResponse<unknown[]>> {
  const response = await api.get("/dlna/scan", {
    params: { timeout },
  });
  return response.data;
}

/**
 * 获取 DLNA 设备音量
 */
export async function getDlnaDeviceVolume(
  location: string
): Promise<ApiResponse<{ volume: number }>> {
  const response = await api.get("/dlna/volume", {
    params: { location },
  });
  return response.data;
}

/**
 * 设置 DLNA 设备音量
 */
export async function setDlnaDeviceVolume(
  location: string,
  volume: number
): Promise<ApiResponse<{ volume: number }>> {
  const response = await api.post("/dlna/volume", {
    location,
    volume,
  });
  return response.data;
}

/**
 * 停止 DLNA 设备播放
 */
export async function stopDlnaDevice(location: string): Promise<ApiResponse<{ message: string }>> {
  const response = await api.post("/dlna/stop", {
    location,
  });
  return response.data;
}
