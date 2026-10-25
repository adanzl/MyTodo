/**
 * 小米设备相关 API
 */
import { apiClient } from "./api-client";
import type { ApiResponse } from "./types";

export interface MiDeviceStatus {
  state?: "PLAYING" | "STOPPED";
  status?: "OK" | "ERROR";
  track?: number;
  duration?: string;
  position?: string;
  volume?: number;
  error?: string;
}

export interface MiDevice {
  name: string;
  address: string;
  deviceID?: string;
  mac?: string;
  miotDID?: string;
  volume?: number;
  status?: MiDeviceStatus;
  _volumeChanging?: boolean;
  _statusRefreshing?: boolean;
  _stopping?: boolean;
  _speaking?: boolean;
}

const SCAN_TIMEOUT = 5;

export async function scanMiDevices(timeout = SCAN_TIMEOUT): Promise<ApiResponse<MiDevice[]>> {
  const rsp = await apiClient.get("/mi/scan", { params: { timeout } });
  return rsp.data;
}

export async function getMiDeviceStatus(
  deviceId: string,
  deviceDid?: string
): Promise<ApiResponse<MiDeviceStatus>> {
  const rsp = await apiClient.get("/mi/status", {
    params: { device_id: deviceId, device_did: deviceDid },
  });
  return rsp.data;
}

export async function setMiDeviceVolume(
  deviceId: string,
  deviceDid: string,
  volume: number
): Promise<ApiResponse<{ volume: number }>> {
  const rsp = await apiClient.post("/mi/volume", {
    device_id: deviceId,
    device_did: deviceDid,
    volume,
  });
  return rsp.data;
}

export async function stopMiDevice(
  deviceId: string,
  deviceDid: string
): Promise<ApiResponse<{ message: string }>> {
  const rsp = await apiClient.post("/mi/stop", {
    device_id: deviceId,
    device_did: deviceDid,
  });
  return rsp.data;
}

export async function speakMiDevice(
  deviceId: string,
  deviceDid: string,
  text: string
): Promise<ApiResponse<{ message: string }>> {
  const rsp = await apiClient.post("/mi/speak", {
    device_id: deviceId,
    device_did: deviceDid,
    text,
  });
  return rsp.data;
}
