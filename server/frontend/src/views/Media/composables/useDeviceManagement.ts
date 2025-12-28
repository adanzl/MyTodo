/**
 * 设备管理 Composable
 * 处理设备扫描、连接、选择等功能
 */
import { type Ref } from "vue";
import { ElMessage } from "element-plus";
import { bluetoothAction } from "@/api/bluetooth";
import { api } from "@/api/config";
import { logAndNoticeError } from "@/utils/error";

export function useDeviceManagement(
  playlistStatus: Ref<any>,
  pendingDeviceType: Ref<string | null>,
  connectedDeviceList: Ref<any[]>,
  dlnaDeviceList: Ref<any[]>,
  miDeviceList: Ref<any[]>,
  deviceList: Ref<any[]>,
  loading: Ref<boolean>,
  dlnaScanning: Ref<boolean>,
  miScanning: Ref<boolean>,
  scanDialogVisible: Ref<boolean>,
  agentListDialogVisible: Ref<boolean>,
  updateActivePlaylistData: (mutator: (playlistInfo: any) => any) => Promise<any>
) {
  // 获取小米设备 ID
  const getMiDeviceId = (device: any) => device.deviceID || device.address;

  // 刷新已连接设备列表
  const refreshConnectedList = async () => {
    const status = playlistStatus.value;
    const deviceType =
      pendingDeviceType.value || status?.device?.type || status?.device_type || "dlna";
    if (!["agent", "bluetooth"].includes(deviceType)) {
      connectedDeviceList.value = [];
      return;
    }

    try {
      loading.value = true;
      let rspData = null;
      if (deviceType === "agent") {
        const rsp = await api.get("/agent/list");
        rspData = rsp.data;
      } else {
        rspData = await bluetoothAction("paired", "GET");
      }

      if (rspData.code === 0) {
        connectedDeviceList.value = rspData.data || [];
      } else {
        ElMessage.error(rspData.msg || "获取设备失败");
      }
    } catch (error) {
      console.error("获取设备失败:", error);
      ElMessage.error("获取设备失败");
    } finally {
      loading.value = false;
    }
  };

  // 连接设备
  const handleConnectDevice = async (device: any) => {
    try {
      device.connecting = true;
      const rsp = await bluetoothAction("connect", "POST", {
        address: device.address,
      });
      if (rsp.code === 0) {
        ElMessage.success(`成功连接到设备: ${device.name}`);
        await refreshConnectedList();
        deviceList.value = deviceList.value.filter(d => d.address !== device.address);
      } else {
        ElMessage.error(rsp.msg || "连接失败");
      }
    } catch (error) {
      console.error("连接设备失败:", error);
      ElMessage.error("连接设备失败");
    } finally {
      device.connecting = false;
    }
  };

  // 扫描 DLNA 设备
  const scanDlnaDevices = async () => {
    try {
      dlnaScanning.value = true;
      const response = await api.get("/dlna/scan", {
        params: { timeout: 5 },
      });
      if (response.data.code === 0) {
        dlnaDeviceList.value = response.data.data || [];
        ElMessage.success(`扫描到 ${dlnaDeviceList.value.length} 个 DLNA 设备`);
      } else {
        ElMessage.error(response.data.msg || "扫描 DLNA 设备失败");
      }
    } catch (error) {
      logAndNoticeError(error as Error, "扫描 DLNA 设备失败");
    } finally {
      dlnaScanning.value = false;
    }
  };

  // 获取小米设备音量
  const getMiDeviceVolume = async (device: any) => {
    const deviceId = getMiDeviceId(device);
    if (!deviceId) return;

    const deviceList = miDeviceList.value;
    if (!Array.isArray(deviceList)) return;
    const targetDevice = deviceList.find((d: any) => getMiDeviceId(d) === deviceId);
    if (!targetDevice) return;

    targetDevice._volumeRefreshing = true;

    try {
      const response = await api.get("/mi/volume", {
        params: { device_id: deviceId },
      });

      if (response.data.code === 0) {
        targetDevice.volume = response.data.data?.volume ?? response.data.data ?? undefined;
      } else {
        ElMessage.error(response.data.msg || `获取设备 ${targetDevice.name || deviceId} 音量失败`);
      }
    } catch (error) {
      logAndNoticeError(error as Error, `获取设备 ${targetDevice.name || deviceId} 音量失败`);
    } finally {
      targetDevice._volumeRefreshing = false;
    }
  };

  // 扫描小米设备
  const scanMiDevices = async () => {
    try {
      miScanning.value = true;
      const response = await api.get("/mi/scan", {
        params: { timeout: 5 },
      });

      if (response.data.code === 0) {
        const devices = (response.data.data || []).map((device: any) => ({
          ...device,
          volume: undefined,
          _volumeChanging: false,
          _volumeRefreshing: false,
        }));
        miDeviceList.value = devices;

        await Promise.allSettled(
          miDeviceList.value.map((device: any) => getMiDeviceVolume(device))
        );

        ElMessage.success(`扫描到 ${devices.length} 个小米设备`);
      } else {
        ElMessage.error(response.data.msg || "扫描小米设备失败");
      }
    } catch (error) {
      logAndNoticeError(error as Error, "扫描小米设备失败");
    } finally {
      miScanning.value = false;
    }
  };

  // 更新设备列表（扫描蓝牙设备）
  const handleUpdateDeviceList = async () => {
    try {
      loading.value = true;
      const rsp = await bluetoothAction("scan", "GET");
      if (rsp.code === 0) {
        deviceList.value = (rsp.data || []).map((device: any) => ({
          ...device,
          connecting: false,
        }));
        ElMessage.success(`扫描完成，找到 ${deviceList.value.length} 个设备`);
      } else {
        ElMessage.error(rsp.msg || "扫描失败");
      }
    } catch (error) {
      console.error("扫描设备失败:", error);
      ElMessage.error("扫描设备失败");
    } finally {
      loading.value = false;
    }
  };

  // 打开扫描对话框
  const handleOpenScanDialog = () => {
    scanDialogVisible.value = true;
  };

  // 关闭扫描对话框
  const handleCloseScanDialog = () => {
    scanDialogVisible.value = false;
  };

  // 更新播放列表设备类型
  const handleUpdatePlaylistDeviceType = async (deviceType: string) => {
    if (!playlistStatus.value) return;

    if (!deviceType || deviceType === "") {
      return;
    }

    const validDeviceTypes = ["agent", "dlna", "bluetooth", "mi"];
    if (!validDeviceTypes.includes(deviceType)) {
      ElMessage.error(`无效的设备类型: ${deviceType}`);
      return;
    }

    pendingDeviceType.value = deviceType;
    const status = playlistStatus.value;
    status.device_type = deviceType;
    if (!status.device) {
      status.device = { type: deviceType, address: "", name: null };
    } else {
      status.device.type = deviceType;
    }

    await refreshConnectedList();
  };

  // 更新播放列表设备地址
  const handleUpdatePlaylistDeviceAddress = async (address: string, name: string | null = null) => {
    if (!playlistStatus.value) return;
    await updateActivePlaylistData(playlistInfo => {
      const finalType =
        pendingDeviceType.value || playlistInfo.device?.type || playlistInfo.device_type || "dlna";

      if (!playlistInfo.device) {
        playlistInfo.device = { address: "", type: finalType, name: null };
      }
      playlistInfo.device.type = finalType;
      playlistInfo.device.address = address;
      if (name !== null) {
        playlistInfo.device.name = name;
      }
      playlistInfo.device_address = address;
      playlistInfo.device_type = finalType;
      return playlistInfo;
    });
    pendingDeviceType.value = null;
  };

  // 选择蓝牙设备
  const handleSelectBluetoothDevice = async (address: string) => {
    const device = connectedDeviceList.value.find((d: any) => d.address === address);
    const name = device ? device.name : null;
    await handleUpdatePlaylistDeviceAddress(address, name);
  };

  // 选择设备代理设备
  const handleSelectAgentDevice = async (device: any) => {
    const address = typeof device === "string" ? device : device.address;
    const name = typeof device === "string" ? null : device.name;
    await handleUpdatePlaylistDeviceAddress(address, name);
  };

  // 选择小米设备
  const handleSelectMiDevice = async (device: any) => {
    const address = device.deviceID || device.address || "";
    const name = device.name || "";
    await handleUpdatePlaylistDeviceAddress(address, name);
  };

  // 打开设备列表对话框
  const handleOpenAgentListDialog = async () => {
    agentListDialogVisible.value = true;
    await refreshConnectedList();
  };

  return {
    getMiDeviceId,
    refreshConnectedList,
    handleConnectDevice,
    scanDlnaDevices,
    getMiDeviceVolume,
    scanMiDevices,
    handleUpdateDeviceList,
    handleOpenScanDialog,
    handleCloseScanDialog,
    handleUpdatePlaylistDeviceType,
    handleUpdatePlaylistDeviceAddress,
    handleSelectBluetoothDevice,
    handleSelectAgentDevice,
    handleSelectMiDevice,
    handleOpenAgentListDialog,
  };
}
