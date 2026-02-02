<template>
  <div class="w-80 min-w-75 border rounded p-3 flex flex-col">
    <h3 class="text-lg font-semibold mb-3">配置详情</h3>

    <!-- 功能按钮区域 -->
    <div v-if="playlistStatus" class="mb-3 flex flex-col gap-2">
      <!-- 任务id -->
      <div class="flex items-center gap-2">
        <span class="text-xs text-gray-500">任务 ID</span>
        <span class="text-xs font-mono text-gray-700 truncate" :title="playlistStatus.id">{{
          playlistStatus.id
        }}</span>
      </div>
      <div class="flex items-center gap-2 flex-wrap">
        <el-button type="default" @click="onOpenDeviceList" title="打开设备列表">
          <el-icon><Monitor /></el-icon>
          <span class="ml-1">设备列表</span>
        </el-button>
      </div>
    </div>

    <div v-if="playlistStatus" class="flex-1 overflow-y-auto space-y-4">
      <!-- Cron 定时任务配置 -->
      <div class="border rounded p-3">
        <div class="flex items-center justify-between mb-2">
          <h4 class="text-sm font-semibold">定时任务 (Cron)</h4>
          <el-switch
            :model-value="playlistStatus.schedule?.enabled === 1"
            @change="(val: boolean) => onToggleCronEnabled(val)"
            active-text="开启"
            inactive-text="关闭"
          >
          </el-switch>
        </div>

        <div class="space-y-2">
          <div>
            <div class="text-xs text-gray-600 mb-1">Cron 表达式</div>
            <div class="flex items-center gap-2">
              <el-input
                :model-value="playlistStatus.schedule?.cron || ''"
                @input="(val: string) => onUpdateCron(val)"
                placeholder="例如: 0 0 * * *"
                size="small"
                :disabled="playlistStatus.schedule?.enabled !== 1"
              >
              </el-input>
              <el-button
                type="info"
                size="small"
                @click="onOpenCronBuilder"
                :disabled="playlistStatus.schedule?.enabled !== 1"
              >
                助手
              </el-button>
            </div>
          </div>

          <div class="flex items-start gap-4">
            <div class="flex-1">
              <div class="text-xs text-gray-600 mb-1">持续时间（分钟）</div>
              <el-input-number
                :model-value="playlistStatus.schedule?.duration || 0"
                @change="onUpdateDuration"
                :min="0"
                :max="MAX_PLAYLIST_DURATION"
                :step="1"
                size="small"
                :disabled="playlistStatus.schedule?.enabled !== 1"
                class="w-full"
              >
              </el-input-number>
              <div class="text-xs text-gray-500 mt-1">0表示不自动停止</div>
            </div>
            <div class="flex-1">
              <div class="text-xs text-gray-600 mb-1">触发按钮</div>
              <el-select
                :model-value="playlistStatus.trigger_button || ''"
                @change="onUpdateTriggerButton"
                placeholder="选择触发按钮"
                size="small"
                class="w-full"
                clearable
              >
                <el-option label="空" :value="TRIGGER_BUTTONS.NONE" />
                <el-option label="按钮对-1" :value="TRIGGER_BUTTONS.BUTTON_1" />
                <el-option label="按钮对-2" :value="TRIGGER_BUTTONS.BUTTON_2" />
                <el-option label="按钮对-3" :value="TRIGGER_BUTTONS.BUTTON_3" />
              </el-select>
            </div>
          </div>

          <div v-if="playlistStatus.schedule?.cron && playlistStatus.schedule?.enabled === 1">
            <el-button type="success" size="small" @click="onPreviewCron" class="w-full">
              预览执行时间
            </el-button>
          </div>
        </div>
      </div>

      <!-- 设备配置 -->
      <div class="border rounded p-3">
        <h4 class="text-sm font-semibold mb-2">设备配置</h4>

        <div class="space-y-2">
          <div class="flex items-center gap-2">
            <div class="text-xs text-gray-600 whitespace-nowrap">设备类型</div>
            <el-select
              :model-value="deviceType"
              @change="onUpdateDeviceType"
              placeholder="选择设备类型"
              size="small"
              class="flex-1"
            >
              <el-option label="蓝牙" value="bluetooth" />
              <el-option label="DLNA" value="dlna" />
              <el-option label="设备代理" value="agent" />
              <el-option label="小米设备" value="mi" />
            </el-select>
          </div>

          <div class="flex items-center gap-2">
            <div class="text-xs text-gray-600 whitespace-nowrap">设备音量</div>
            <el-slider
              :model-value="localVolume"
              @input="(val: number) => (localVolume = val)"
              @change="(val: number) => handleVolumeChange(val)"
              :min="5"
              :max="100"
              :step="1"
              size="small"
              class="flex-1"
            />
          </div>

          <div>
            <div class="text-xs text-gray-600 mb-1 flex items-center gap-2">
              <span>设备地址</span>
              <span v-if="playlistStatus.device?.name" class="text-xs text-gray-500">
                {{ playlistStatus.device.name }}
              </span>
            </div>
            <div class="flex items-center gap-2">
              <el-input
                :model-value="deviceAddress"
                @input="(val: string) => onUpdateDeviceAddress(val)"
                placeholder="设备地址"
                size="small"
                class="flex-1"
              >
              </el-input>
              <el-button
                size="small"
                type="danger"
                plain
                @click="onUpdateDeviceAddress('')"
                :disabled="!deviceAddress"
                title="清空设备地址"
              >
                清空
              </el-button>
            </div>
          </div>
        </div>

        <!-- 设备列表 -->
        <div class="mt-3">
          <div class="flex items-center justify-between mb-2">
            <h5 class="text-xs font-semibold text-gray-700">{{ deviceListTitle }}</h5>
            <!-- 扫描设备按钮（聚合） -->
            <el-button
              v-if="deviceType"
              size="small"
              type="primary"
              plain
              @click="handleScanDevices"
              :loading="isScanning"
              :disabled="isScanning"
              :title="scanButtonTitle"
            >
              <el-icon v-if="!isScanning"><Refresh /></el-icon>
              <span class="ml-1">扫描设备</span>
            </el-button>
          </div>

          <!-- 设备代理类型：显示已配对设备 -->
          <div v-if="isAgentOrBluetooth">
            <div class="space-y-2 max-h-[200px] overflow-y-auto" v-loading="loading">
              <div
                v-for="device in connectedDeviceList"
                :key="device.address"
                class="flex items-center gap-2 p-2 border rounded hover:bg-gray-50"
              >
                <div class="flex-1 min-w-0">
                  <div class="text-sm font-medium truncate">{{ device.name }}</div>
                  <div class="text-xs text-gray-500 truncate">{{ device.address }}</div>
                </div>
                <div class="flex-shrink-0">
                  <el-button
                    size="small"
                    type="primary"
                    @click="
                      deviceType === 'agent'
                        ? onSelectAgentDevice(device as AgentDevice)
                        : onSelectBluetoothDevice(device.address)
                    "
                    :disabled="device.address === deviceAddress"
                  >
                    选择
                  </el-button>
                </div>
              </div>
              <div
                v-if="connectedDeviceList.length === 0"
                class="text-xs text-gray-400 text-center py-4"
              >
                暂无设备
              </div>
            </div>
          </div>

          <!-- DLNA 类型：显示 DLNA 设备 -->
          <div v-else-if="isDlna">
            <div class="space-y-2 max-h-[200px] overflow-y-auto" v-loading="dlnaScanning">
              <div
                v-for="device in dlnaDeviceList"
                :key="device.location"
                class="flex items-center gap-2 p-2 border rounded hover:bg-gray-50"
              >
                <div class="flex-1 min-w-0">
                  <div class="text-sm font-medium truncate">{{ device.name }}</div>
                  <div class="text-xs text-gray-500 truncate" :title="device.location">
                    {{ device.location }}
                  </div>
                </div>
                <div class="flex-shrink-0">
                  <el-button
                    size="small"
                    type="primary"
                    @click="
                      onUpdateDeviceAddress(device.location || device.address || '', device.name)
                    "
                    :disabled="(device.location || device.address) === deviceAddress"
                  >
                    选择
                  </el-button>
                </div>
              </div>
              <div
                v-if="dlnaDeviceList.length === 0 && !dlnaScanning"
                class="text-xs text-gray-400 text-center py-4"
              >
                暂无设备，点击"扫描设备"开始扫描
              </div>
            </div>
          </div>

          <!-- 小米设备类型：显示小米设备 -->
          <div v-else-if="isMi">
            <div class="space-y-2 max-h-[200px] overflow-y-auto" v-loading="miScanning">
              <div
                v-for="device in miDeviceList"
                :key="device.deviceID || device.address"
                class="flex items-center gap-2 p-2 border rounded hover:bg-gray-50"
              >
                <div class="flex-1 min-w-0">
                  <div class="text-sm font-medium truncate">{{ device.name }}</div>
                  <div
                    class="text-xs text-gray-500 truncate"
                    :title="device.deviceID || device.address"
                  >
                    {{ device.deviceID || device.address }}
                  </div>
                </div>
                <div class="flex-shrink-0">
                  <el-button
                    size="small"
                    type="primary"
                    @click="onSelectMiDevice(device)"
                    :disabled="(device.deviceID || device.address) === deviceAddress"
                  >
                    选择
                  </el-button>
                </div>
              </div>
              <div
                v-if="miDeviceList.length === 0 && !miScanning"
                class="text-xs text-gray-400 text-center py-4"
              >
                暂无设备，点击"扫描设备"开始扫描
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="flex-1 flex items-center justify-center text-sm text-gray-400">
      请先选择一个播放列表
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Monitor, Refresh } from "@element-plus/icons-vue";
import { MAX_PLAYLIST_DURATION, TRIGGER_BUTTONS } from "@/constants/playlist";
import type { PlaylistStatus } from "@/types/playlist";
import type { BluetoothDevice, DlnaDevice, MiDevice, AgentDevice } from "@/types/device";
import type { DeviceType } from "@/constants/device";

interface Props {
  playlistStatus: PlaylistStatus | null;
  connectedDeviceList: (BluetoothDevice | AgentDevice)[];
  dlnaDeviceList: DlnaDevice[];
  miDeviceList: MiDevice[];
  loading: boolean;
  dlnaScanning: boolean;
  miScanning: boolean;
  onToggleCronEnabled: (enabled: boolean) => void;
  onUpdateCron: (cron: string) => void;
  onUpdateDuration: (duration: number | null) => void;
  onUpdateTriggerButton: (triggerButton: string) => void;
  onOpenCronBuilder: () => void;
  onPreviewCron: () => void;
  onUpdateDeviceType: (deviceType: string) => void;
  onUpdateDeviceVolume: (volume: number) => void;
  onUpdateDeviceAddress: (address: string, name?: string | null) => void;
  onSelectBluetoothDevice: (address: string) => void;
  onSelectAgentDevice: (device: AgentDevice | string) => void;
  onSelectMiDevice: (device: MiDevice) => void;
  onScanDlnaDevices: () => void;
  onScanMiDevices: () => void;
  onOpenScanDialog: () => void;
  onOpenDeviceList: () => void;
}

const props = defineProps<Props>();

// 获取设备类型
const deviceType = computed<DeviceType | null>(() => {
  return props.playlistStatus?.device?.type || props.playlistStatus?.device_type || null;
});

// 获取设备地址
const deviceAddress = computed(() => {
  return props.playlistStatus?.device?.address || props.playlistStatus?.device_address || "";
});

// 获取设备音量（播放列表属性）
const deviceVolume = computed(() => {
  const volume = props.playlistStatus?.device_volume;
  return volume !== undefined && volume !== null ? volume : 20;
});

// 本地音量状态（用于实时更新 UI）
const localVolume = ref(deviceVolume.value);

// 限制音量范围
const clampVolume = (volume: number): number => {
  return Math.max(5, Math.min(100, volume));
};

// 处理音量变化
const handleVolumeChange = (volume: number) => {
  const clampedVolume = clampVolume(volume);
  props.onUpdateDeviceVolume(clampedVolume);
};

// 监听设备音量变化，同步到本地状态
watch(
  deviceVolume,
  newVolume => {
    localVolume.value = newVolume;
  },
  { immediate: true }
);

// 判断是否为指定设备类型
const isDeviceType = (type: DeviceType) => computed(() => deviceType.value === type);

const isAgentOrBluetooth = computed(() => {
  const type = deviceType.value;
  return type === "agent" || type === "bluetooth";
});

const isDlna = isDeviceType("dlna");
const isMi = isDeviceType("mi");

// 设备列表标题
const deviceListTitle = computed(() => {
  if (isAgentOrBluetooth.value) return "已配对的设备";
  if (isDlna.value) return "DLNA 设备";
  if (isMi.value) return "小米设备";
  return "设备列表";
});

// 扫描按钮标题
const scanButtonTitle = computed(() => {
  if (isAgentOrBluetooth.value) return "扫描设备";
  if (isDlna.value) return "扫描 DLNA 设备";
  if (isMi.value) return "扫描小米设备";
  return "扫描设备";
});

// 是否正在扫描
const isScanning = computed(() => {
  return props.dlnaScanning || props.miScanning;
});

// 统一的扫描设备处理函数
const handleScanDevices = () => {
  if (isAgentOrBluetooth.value) {
    props.onOpenScanDialog();
  } else if (isDlna.value) {
    props.onScanDlnaDevices();
  } else if (isMi.value) {
    props.onScanMiDevices();
  }
};
</script>
