<template>
  <el-drawer
    v-model="internalVisible"
    :size="1200"
    direction="rtl"
    :before-close="handleClose"
    header-class="h-12 !mb-1"
  >
    <template #header>
      <div class="flex items-center gap-3 w-full pr-4">
        <span class="text-lg font-semibold">设备管理</span>
        <el-button
          v-if="activeTab === 'agent' || activeTab === 'bluetooth'"
          type="primary"
          plain
          size="small"
          @click="handleRefreshButton"
          :loading="getRefreshLoadingState"
        >
          <el-icon v-if="!getRefreshLoadingState"><Refresh /></el-icon>
          <span class="ml-1">刷新</span>
        </el-button>
        <el-button
          v-else
          type="primary"
          plain
          size="small"
          @click="handleScanDevice"
          :loading="getScanningState"
        >
          <el-icon v-if="!getScanningState"><Refresh /></el-icon>
          <span class="ml-1">扫描</span>
        </el-button>
      </div>
    </template>
    <el-tabs v-model="activeTab" class="h-full flex flex-col">
      <!-- Agent设备页签 -->
      <el-tab-pane label="Agent设备" name="agent">
        <div class="flex flex-col gap-4 h-full overflow-y-auto">
          <el-table
            :data="agentList"
            stripe
            class="w-full"
            v-loading="agentListLoading"
            :height="600"
          >
            <el-table-column prop="name" label="设备名称" min-width="150" />
            <el-table-column label="详情" min-width="250">
              <template #default="{ row }">
                <div class="flex flex-col gap-1">
                  <div class="text-sm flex items-start">
                    <span class="text-gray-600 inline-block w-12 flex-shrink-0">地址：</span>
                    <span class="text-gray-800">{{ row.address }}</span>
                  </div>
                  <div class="text-sm flex items-start">
                    <span class="text-gray-600 inline-block w-12 flex-shrink-0">ID：</span>
                    <span class="text-gray-800">{{ row.agent_id }}</span>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="支持的操作" min-width="100">
              <template #default="{ row }">
                <el-tag
                  v-for="action in row.actions"
                  :key="action"
                  size="small"
                  type="info"
                  class="mr-1"
                >
                  {{ action }}
                </el-tag>
                <span v-if="!row.actions || row.actions.length === 0" class="text-gray-400"
                  >无</span
                >
              </template>
            </el-table-column>
            <el-table-column label="状态/心跳" width="90">
              <template #default="{ row }">
                <div class="flex flex-col items-center gap-1">
                  <el-tag :type="row.is_online ? 'success' : 'danger'" size="small">
                    {{ row.is_online ? "在线" : "离线" }}
                  </el-tag>
                  <span class="text-xs text-gray-500"> {{ row.last_heartbeat_ago }}秒前 </span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="测试按钮" width="180">
              <template #default="{ row }">
                <div class="flex flex-col gap-1">
                  <div
                    v-for="(buttonGroup, groupIndex) in buttonGroups"
                    :key="groupIndex"
                    class="flex gap-1 items-center"
                  >
                    <el-icon class="!w-4 !h-5"><Cpu /></el-icon>
                    <span class="text-[12px] mr-1 !w-4">{{ buttonGroup.label }}</span>
                    <el-button
                      v-for="(key, btnIndex) in buttonGroup.keys"
                      :key="btnIndex"
                      size="small"
                      type="primary"
                      plain
                      @click="handleTestAgentButton(row.agent_id, key)"
                      :loading="row[`testing_${key}`]"
                      class="flex-1"
                    >
                      {{ key }}
                    </el-button>
                  </div>
                </div>
              </template>
            </el-table-column>
            <template #empty>
              <div class="text-center text-gray-400 py-8">暂无设备，请等待设备注册</div>
            </template>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- 蓝牙设备页签 -->
      <el-tab-pane label="蓝牙设备" name="bluetooth">
        <div class="flex flex-col gap-4 h-full overflow-y-auto">
          <el-table
            :data="bluetoothDeviceList"
            stripe
            class="w-full"
            v-loading="bluetoothScanning"
            :height="600"
          >
            <el-table-column prop="name" label="设备名称" min-width="200" />
            <el-table-column prop="address" label="设备地址" min-width="180" />
            <el-table-column label="信号强度" width="120">
              <template #default="{ row }">
                <span v-if="row.rssi !== undefined" class="text-sm"> {{ row.rssi }} dBm </span>
                <span v-else class="text-gray-400">-</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag
                  :type="row.connecting ? 'warning' : row.rssi !== undefined ? 'success' : 'info'"
                  size="small"
                >
                  {{ row.connecting ? "连接中" : row.rssi !== undefined ? "已发现" : "未知" }}
                </el-tag>
              </template>
            </el-table-column>
            <template #empty>
              <div class="text-center text-gray-400 py-8">暂无设备，点击"扫描"开始扫描</div>
            </template>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- DLNA设备页签 -->
      <el-tab-pane label="DLNA设备" name="dlna">
        <div class="flex flex-col gap-4 h-full overflow-y-auto">
          <el-table
            :data="dlnaDeviceList"
            stripe
            class="w-full"
            v-loading="dlnaScanning"
            :height="600"
          >
            <el-table-column prop="name" label="设备名称" min-width="150" />
            <el-table-column label="详情" min-width="400">
              <template #default="{ row }">
                <div class="flex flex-col gap-1">
                  <div class="text-sm flex items-start">
                    <span class="text-gray-600 inline-block w-12 flex-shrink-0">位置：</span>
                    <span class="text-gray-800 flex-1 truncate" :title="row.location">
                      {{ row.location || "-" }}
                    </span>
                  </div>
                  <div v-if="row.manufacturer || row.model_name" class="text-sm flex items-start">
                    <span class="text-gray-600 inline-block w-12 flex-shrink-0">型号：</span>
                    <span class="text-gray-800">
                      {{ row.manufacturer || "" }} {{ row.model_name || "" }}
                    </span>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="功能" min-width="200">
              <template #default="{ row }">
                <div class="flex flex-col gap-2">
                  <div class="flex items-center gap-2">
                    <span class="text-gray-600 inline-block w-11 flex-shrink-0">音量：</span>
                    <span class="text-gray-800 w-5">
                      {{ row.volume !== undefined ? row.volume : "-" }}
                    </span>
                    <el-button
                      size="small"
                      type="info"
                      plain
                      circle
                      @click="getDlnaDeviceVolume(row)"
                      :loading="row._volumeRefreshing"
                      :disabled="row._volumeRefreshing || row._volumeChanging"
                      title="刷新音量"
                      class="p-0.5 !w-[17px] !h-[17px]"
                    >
                      <el-icon v-if="!row._volumeRefreshing"><Refresh /></el-icon>
                    </el-button>
                    <el-button
                      size="small"
                      class="!w-8 !h-6"
                      type="danger"
                      plain
                      @click="handleStopDlnaDevice(row)"
                      :disabled="row._stopping"
                      title="停止播放"
                    >
                      <el-icon v-if="row._stopping" class="animate-spin"> <Loading /> </el-icon>
                      <span v-else>⏹</span>
                    </el-button>
                  </div>
                  <div class="flex items-center gap-2">
                    <el-slider
                      :model-value="row.volume ?? 0"
                      @input="(val: number) => (row.volume = val)"
                      @change="(val: number) => setDlnaDeviceVolume(row, val)"
                      :min="5"
                      :max="100"
                      :step="1"
                      :disabled="
                        row._volumeChanging || row._volumeRefreshing || row.volume === undefined
                      "
                      size="small"
                      class="flex-1 max-w-[200px]"
                    >
                    </el-slider>
                  </div>
                </div>
              </template>
            </el-table-column>
            <template #empty>
              <div class="text-center text-gray-400 py-8">暂无设备，点击"扫描"开始扫描</div>
            </template>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- 小米设备页签 -->
      <el-tab-pane label="小米设备" name="mi">
        <div class="flex flex-col gap-4 h-full overflow-y-auto">
          <el-table :data="miDeviceList" stripe class="w-full" v-loading="miScanning" :height="600">
            <el-table-column prop="name" label="设备名称" min-width="150" />
            <el-table-column label="详情" min-width="400">
              <template #default="{ row }">
                <div class="flex flex-col gap-1">
                  <div class="text-sm flex items-start">
                    <span class="text-gray-600 inline-block w-12 flex-shrink-0">ID：</span>
                    <span class="text-gray-800">{{ row.deviceID || "-" }}</span>
                  </div>
                  <div class="text-sm flex items-start">
                    <span class="text-gray-600 inline-block w-12 flex-shrink-0">地址：</span>
                    <span class="text-gray-800 w-40">{{ row.mac || "-" }}</span>
                    <span class="text-gray-600 inline-block w-12 flex-shrink-0">DTD：</span>
                    <span class="text-gray-800 w-40">{{ row.miotDID || "-" }}</span>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="功能" min-width="200">
              <template #default="{ row }">
                <div class="flex flex-col gap-2">
                  <div class="flex items-center gap-2">
                    <span class="text-gray-600 inline-block w-11 flex-shrink-0">音量：</span>
                    <span class="text-gray-800 w-5">
                      {{ row.volume !== undefined ? row.volume : "-" }}
                    </span>
                    <el-button
                      size="small"
                      type="info"
                      plain
                      circle
                      @click="getMiDeviceVolume(row)"
                      :loading="row._volumeRefreshing"
                      :disabled="row._volumeRefreshing || row._volumeChanging"
                      title="刷新音量"
                      class="p-0.5 !w-[17px] !h-[17px]"
                    >
                      <el-icon v-if="!row._volumeRefreshing"><Refresh /></el-icon>
                    </el-button>
                    <el-button
                      size="small"
                      class="!w-8 !h-6"
                      type="danger"
                      plain
                      @click="handleStopMiDevice(row)"
                      :disabled="row._stopping"
                      title="停止播放"
                    >
                      <el-icon v-if="row._stopping" class="animate-spin"> <Loading /> </el-icon>
                      <span v-else>⏹</span>
                    </el-button>
                  </div>
                  <div class="flex items-center gap-2">
                    <el-slider
                      :model-value="row.volume ?? 0"
                      @input="(val: number) => (row.volume = val)"
                      @change="(val: number) => setMiDeviceVolume(row, val)"
                      :min="5"
                      :max="100"
                      :step="1"
                      :disabled="
                        row._volumeChanging || row._volumeRefreshing || row.volume === undefined
                      "
                      size="small"
                      class="flex-1 max-w-[200px]"
                    >
                    </el-slider>
                  </div>
                </div>
              </template>
            </el-table-column>
            <template #empty>
              <div class="text-center text-gray-400 py-8">暂无设备，点击"扫描"开始扫描</div>
            </template>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted, onMounted, computed } from "vue";
// ElMessage 已通过自动导入插件自动导入，无需手动导入
import { Refresh, Cpu, Loading } from "@element-plus/icons-vue";
import { api } from "@/api/config";
import { logAndNoticeError } from "@/utils";
import { DEVICE_SCAN_TIMEOUT, AGENT_LIST_REFRESH_INTERVAL } from "@/constants/device";
import { bluetoothAction } from "@/api/bluetooth";
import type { MiDevice, AgentDevice, DlnaDevice, BluetoothDevice } from "@/types/device/device";

interface Props {
  visible?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  visible: false,
});

const emit = defineEmits<{
  "update:visible": [value: boolean];
}>();

const internalVisible = ref(props.visible);
const activeTab = ref("agent");

// Agent设备相关状态
const agentList = ref<AgentDevice[]>([]);
const agentListLoading = ref(false);
let agentRefreshTimer: ReturnType<typeof setInterval> | null = null;

// 蓝牙设备相关状态
const bluetoothDeviceList = ref<BluetoothDevice[]>([]);
const bluetoothScanning = ref(false);

// DLNA设备相关状态
const dlnaDeviceList = ref<DlnaDevice[]>([]);
const dlnaScanning = ref(false);

// 小米设备相关状态
const miDeviceList = ref<MiDevice[]>([]);
const miScanning = ref(false);

// 测试按钮组配置
const buttonGroups = [
  { label: "B1", keys: ["F13", "F14"] },
  { label: "B2", keys: ["F15", "F16"] },
  { label: "B3", keys: ["F17", "F18"] },
];

// ========== Agent设备相关方法 ==========
// 刷新Agent设备列表
const refreshAgentList = async (showLoading = true, showMessage = false) => {
  try {
    if (showLoading) {
      agentListLoading.value = true;
    }

    const response = await api.get("/agent/list");
    const result = response.data;

    if (result?.code === 0) {
      agentList.value = result.data || [];
      if (showMessage) {
        ElMessage.success(`已获取 ${agentList.value.length} 个 Agent 设备`);
      }
    } else {
      const shouldShowError = showMessage || showLoading;
      if (shouldShowError) {
        ElMessage.error(result?.msg || "获取设备列表失败");
      }
      agentList.value = [];
    }
  } catch (error) {
    console.error("获取Agent设备列表失败:", error);
    const shouldShowError = showMessage || showLoading;
    if (shouldShowError) {
      logAndNoticeError(error as Error, "获取设备列表失败");
    }
    agentList.value = [];
  } finally {
    if (showLoading) {
      agentListLoading.value = false;
    }
  }
};

// 测试Agent按钮
const testAgentButton = async (agentId: string, key: string) => {
  const device = agentList.value.find(d => d.agent_id === agentId);
  if (!device) {
    ElMessage.error("设备不存在");
    return;
  }

  // 设置测试状态
  const testingKey = `testing_${key}`;
  const deviceWithState = device as AgentDevice & Record<string, boolean>;
  deviceWithState[testingKey] = true;

  try {
    const response = await api.post("/agent/mock", {
      agent_id: agentId,
      action: "keyboard",
      key: key,
      value: "test",
    });

    const result = response.data;

    if (result?.code === 0) {
      ElMessage.success(`测试按钮 ${key} 成功`);
    } else {
      ElMessage.error(result?.msg || `测试按钮 ${key} 失败`);
    }
  } catch (error) {
    logAndNoticeError(error as Error, `测试按钮 ${key} 失败`);
  } finally {
    deviceWithState[testingKey] = false;
  }
};

// 启动自动刷新
const startRefresh = () => {
  refreshAgentList(true, false);
  stopRefresh(); // 确保先清除旧的定时器
  agentRefreshTimer = setInterval(() => {
    refreshAgentList(false, false);
  }, AGENT_LIST_REFRESH_INTERVAL);
};

// 停止自动刷新
const stopRefresh = () => {
  if (agentRefreshTimer) {
    clearInterval(agentRefreshTimer);
    agentRefreshTimer = null;
  }
};

// 刷新Agent设备列表
const handleRefreshAgentList = () => refreshAgentList(true, false);

// 测试Agent按钮
const handleTestAgentButton = (agentId: string, key: string) => testAgentButton(agentId, key);

// ========== 蓝牙设备相关方法 ==========
// 获取已配对的蓝牙设备列表
const refreshBluetoothPairedDevices = async () => {
  try {
    bluetoothScanning.value = true;
    const response = await bluetoothAction("paired", "GET");

    if (response?.code === 0) {
      const devices = Array.isArray(response.data) ? response.data : [];
      bluetoothDeviceList.value = devices.map(
        (device: Partial<BluetoothDevice>): BluetoothDevice => ({
          name: device.name || "",
          address: device.address || "",
          ...device,
          connecting: false,
        })
      );
      ElMessage.success(`已获取 ${bluetoothDeviceList.value.length} 个已配对蓝牙设备`);
    } else {
      ElMessage.error(response?.msg || "获取已配对设备列表失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "获取已配对设备列表失败");
  } finally {
    bluetoothScanning.value = false;
  }
};

// 刷新蓝牙设备列表（统一入口）
const handleRefreshBluetoothPaired = () => refreshBluetoothPairedDevices();

// ========== 统一的扫描/刷新方法 ==========
// 获取当前页签的刷新加载状态
const getRefreshLoadingState = computed(() => {
  if (activeTab.value === "agent") {
    return agentListLoading.value;
  } else if (activeTab.value === "bluetooth") {
    return bluetoothScanning.value;
  }
  return false;
});

// 获取当前页签的扫描状态
const getScanningState = computed(() => {
  switch (activeTab.value) {
    case "dlna":
      return dlnaScanning.value;
    case "mi":
      return miScanning.value;
    default:
      return false;
  }
});

// 统一的刷新处理方法
const handleRefreshButton = () => {
  if (activeTab.value === "agent") {
    handleRefreshAgentList();
  } else if (activeTab.value === "bluetooth") {
    handleRefreshBluetoothPaired();
  }
};

// 统一的扫描处理方法
const handleScanDevice = () => {
  switch (activeTab.value) {
    case "dlna":
      scanDlnaDevices();
      break;
    case "mi":
      scanMiDevices();
      break;
  }
};

// ========== 小米设备相关方法 ==========
// 辅助函数
const getMiDeviceId = (device: MiDevice): string => {
  return device.deviceID || device.address || "";
};

const clampVolume = (volume: number): number => {
  return Math.max(0, Math.min(100, volume));
};

// 初始化小米设备状态
const initMiDeviceState = (device: Partial<MiDevice>): MiDevice => {
  return {
    ...device,
    volume: undefined,
    _volumeChanging: false,
    _volumeRefreshing: false,
  } as MiDevice;
};

// 扫描小米设备
const scanMiDevices = async () => {
  try {
    miScanning.value = true;
    const response = await api.get("/mi/scan", {
      params: { timeout: DEVICE_SCAN_TIMEOUT },
    });
    const result = response.data;

    if (result?.code === 0) {
      const devices = (result.data || []).map((device: Partial<MiDevice>) =>
        initMiDeviceState(device)
      );
      miDeviceList.value = devices;

      // 并行获取所有设备的音量
      await Promise.allSettled(devices.map((device: MiDevice) => getMiDeviceVolume(device)));

      ElMessage.success(`扫描到 ${devices.length} 个小米设备`);
    } else {
      ElMessage.error(result?.msg || "扫描小米设备失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "扫描小米设备失败");
  } finally {
    miScanning.value = false;
  }
};

// 获取小米设备音量
const getMiDeviceVolume = async (device: MiDevice) => {
  const deviceId = getMiDeviceId(device);
  if (!deviceId) return;

  const targetDevice = miDeviceList.value.find(d => getMiDeviceId(d) === deviceId);
  if (!targetDevice) return;

  targetDevice._volumeRefreshing = true;

  try {
    const response = await api.get("/mi/volume", {
      params: { device_id: deviceId },
    });
    const result = response.data;

    if (result?.code === 0) {
      targetDevice.volume = result.data?.volume ?? result.data ?? undefined;
    } else {
      const deviceName = targetDevice.name || deviceId;
      ElMessage.error(result?.msg || `获取设备 ${deviceName} 音量失败`);
    }
  } catch (error) {
    const deviceName = targetDevice.name || deviceId;
    logAndNoticeError(error as Error, `获取设备 ${deviceName} 音量失败`);
  } finally {
    targetDevice._volumeRefreshing = false;
  }
};

// 设置小米设备音量
const setMiDeviceVolume = async (device: MiDevice, volume: number) => {
  const deviceId = getMiDeviceId(device);
  if (!deviceId) {
    ElMessage.error("设备ID无效");
    return;
  }

  const clampedVolume = clampVolume(volume);
  device._volumeChanging = true;

  try {
    const response = await api.post("/mi/volume", {
      device_id: deviceId,
      volume: clampedVolume,
    });
    const result = response.data;

    if (result?.code === 0) {
      device.volume = clampedVolume;
      ElMessage.success("音量设置成功");
    } else {
      ElMessage.error(result?.msg || "设置音量失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "设置小米设备音量失败");
  } finally {
    device._volumeChanging = false;
  }
};

// 停止小米设备播放
const handleStopMiDevice = async (device: MiDevice) => {
  const deviceId = getMiDeviceId(device);
  if (!deviceId) {
    ElMessage.warning("设备ID无效");
    return;
  }

  try {
    device._stopping = true;
    const response = await api.post("/mi/stop", {
      device_id: deviceId,
    });
    const result = response.data;

    if (result?.code === 0) {
      ElMessage.success("停止播放成功");
    } else {
      ElMessage.error(result?.msg || "停止播放失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "停止小米设备播放失败");
  } finally {
    device._stopping = false;
  }
};

// ========== DLNA设备相关方法 ==========
// 获取DLNA设备标识
const getDlnaDeviceLocation = (device: DlnaDevice): string => {
  return device.location || device.address || "";
};

// 初始化DLNA设备状态
const initDlnaDeviceState = (device: Partial<DlnaDevice>): DlnaDevice => {
  return {
    ...device,
    volume: undefined,
    _volumeChanging: false,
    _volumeRefreshing: false,
  } as DlnaDevice;
};

// 扫描DLNA设备
const scanDlnaDevices = async () => {
  try {
    dlnaScanning.value = true;
    const response = await api.get("/dlna/scan", {
      params: { timeout: DEVICE_SCAN_TIMEOUT },
    });
    const result = response.data;

    if (result?.code === 0) {
      const devices = (result.data || []).map((device: Partial<DlnaDevice>) =>
        initDlnaDeviceState(device)
      );
      dlnaDeviceList.value = devices;

      // 并行获取所有设备的音量
      await Promise.allSettled(devices.map((device: DlnaDevice) => getDlnaDeviceVolume(device)));

      ElMessage.success(`扫描到 ${devices.length} 个 DLNA 设备`);
    } else {
      ElMessage.error(result?.msg || "扫描 DLNA 设备失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "扫描 DLNA 设备失败");
  } finally {
    dlnaScanning.value = false;
  }
};

// 获取DLNA设备音量
const getDlnaDeviceVolume = async (device: DlnaDevice) => {
  const location = getDlnaDeviceLocation(device);
  if (!location) return;

  const targetDevice = dlnaDeviceList.value.find(d => getDlnaDeviceLocation(d) === location);
  if (!targetDevice) return;

  targetDevice._volumeRefreshing = true;

  try {
    const response = await api.get("/dlna/volume", {
      params: { location: location },
    });
    const result = response.data;

    if (result?.code === 0) {
      targetDevice.volume = result.data?.volume ?? result.data ?? undefined;
    } else {
      const deviceName = targetDevice.name || location;
      ElMessage.error(result?.msg || `获取设备 ${deviceName} 音量失败`);
    }
  } catch (error) {
    const deviceName = targetDevice.name || location;
    logAndNoticeError(error as Error, `获取设备 ${deviceName} 音量失败`);
  } finally {
    targetDevice._volumeRefreshing = false;
  }
};

// 设置DLNA设备音量
const setDlnaDeviceVolume = async (device: DlnaDevice, volume: number) => {
  const location = getDlnaDeviceLocation(device);
  if (!location) {
    ElMessage.error("设备位置无效");
    return;
  }

  const clampedVolume = clampVolume(volume);
  device._volumeChanging = true;

  try {
    const response = await api.post("/dlna/volume", {
      location: location,
      volume: clampedVolume,
    });
    const result = response.data;

    if (result?.code === 0) {
      device.volume = clampedVolume;
      ElMessage.success("音量设置成功");
    } else {
      ElMessage.error(result?.msg || "设置音量失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "设置 DLNA 设备音量失败");
  } finally {
    device._volumeChanging = false;
  }
};

// 停止DLNA设备播放
const handleStopDlnaDevice = async (device: DlnaDevice) => {
  const location = getDlnaDeviceLocation(device);
  if (!location) {
    ElMessage.warning("设备位置无效");
    return;
  }

  try {
    device._stopping = true;
    const response = await api.post("/dlna/stop", {
      location: location,
    });
    const result = response.data;

    if (result?.code === 0) {
      ElMessage.success("停止播放成功");
    } else {
      ElMessage.error(result?.msg || "停止播放失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "停止 DLNA 设备播放失败");
  } finally {
    device._stopping = false;
  }
};

// ========== 通用方法 ==========
// 关闭抽屉
const handleClose = () => {
  internalVisible.value = false;
};

// 监听抽屉显示状态
watch(
  () => props.visible,
  isVisible => {
    internalVisible.value = isVisible;
    if (isVisible) {
      startRefresh();
    } else {
      stopRefresh();
    }
  },
  { immediate: true }
);

watch(internalVisible, newVal => {
  if (newVal !== props.visible) {
    emit("update:visible", newVal);
  }
});

// 监听页签切换，切换到蓝牙页签时自动刷新
watch(activeTab, (newTab, oldTab) => {
  if (newTab === "bluetooth" && oldTab !== "bluetooth") {
    // 切换到蓝牙页签时自动执行一次刷新
    handleRefreshBluetoothPaired();
  }
});

onMounted(() => {
  if (props.visible) {
    startRefresh();
    // 如果初始页签是蓝牙页签，也执行一次刷新
    if (activeTab.value === "bluetooth") {
      handleRefreshBluetoothPaired();
    }
  }
});

onUnmounted(() => {
  stopRefresh();
});
</script>
