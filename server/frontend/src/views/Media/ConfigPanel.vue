<template>
  <div class="w-80 min-w-75 border rounded p-3 flex flex-col">
    <h3 class="text-lg font-semibold mb-3">配置详情</h3>

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
            <el-button
              type="success"
              size="small"
              @click="onPreviewCron"
              class="w-full"
            >
              预览执行时间
            </el-button>
          </div>
        </div>
      </div>

      <!-- 设备配置 -->
      <div class="border rounded p-3">
        <h4 class="text-sm font-semibold mb-2">设备配置</h4>

        <div class="space-y-2">
          <div>
            <div class="text-xs text-gray-600 mb-1">设备类型</div>
            <el-select
              :model-value="playlistStatus.device?.type || playlistStatus.device_type || null"
              @change="onUpdateDeviceType"
              placeholder="选择设备类型"
              size="small"
              class="w-full"
            >
              <el-option label="蓝牙" value="bluetooth" />
              <el-option label="DLNA" value="dlna" />
              <el-option label="设备代理" value="agent" />
              <el-option label="小米设备" value="mi" />
            </el-select>
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
                :model-value="playlistStatus.device?.address || playlistStatus.device_address || ''"
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
                :disabled="!playlistStatus.device?.address && !playlistStatus.device_address"
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
            <h5 class="text-xs font-semibold text-gray-700">
              <span
                v-if="
                  playlistStatus.device?.type === 'agent' ||
                  playlistStatus.device_type === 'agent' ||
                  playlistStatus.device?.type === 'bluetooth' ||
                  playlistStatus.device_type === 'bluetooth'
                "
              >
                已配对的设备
              </span>
              <span
                v-else-if="
                  playlistStatus.device?.type === 'dlna' || playlistStatus.device_type === 'dlna'
                "
              >
                DLNA 设备
              </span>
              <span
                v-else-if="playlistStatus.device?.type === 'mi' || playlistStatus.device_type === 'mi'"
              >
                小米设备
              </span>
              <span v-else>设备列表</span>
            </h5>
            <el-button
              v-if="
                playlistStatus.device?.type === 'dlna' || playlistStatus.device_type === 'dlna'
              "
              type="primary"
              size="small"
              @click="onScanDlnaDevices"
              :loading="dlnaScanning"
            >
              扫描设备
            </el-button>
            <el-button
              v-if="playlistStatus.device?.type === 'mi' || playlistStatus.device_type === 'mi'"
              type="primary"
              size="small"
              @click="onScanMiDevices"
              :loading="miScanning"
            >
              扫描设备
            </el-button>
            <el-button
              v-if="
                playlistStatus.device?.type === 'agent' ||
                playlistStatus.device_type === 'agent' ||
                playlistStatus.device?.type === 'bluetooth' ||
                playlistStatus.device_type === 'bluetooth'
              "
              type="primary"
              size="small"
              @click="onOpenScanDialog"
            >
              扫描设备
            </el-button>
          </div>

          <!-- 设备代理类型：显示已配对设备 -->
          <div
            v-if="
              playlistStatus.device?.type === 'agent' ||
              playlistStatus.device_type === 'agent' ||
              playlistStatus.device?.type === 'bluetooth' ||
              playlistStatus.device_type === 'bluetooth'
            "
          >
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
                      playlistStatus.device?.type === 'agent' ||
                      playlistStatus.device_type === 'agent'
                        ? onSelectAgentDevice(device)
                        : onSelectBluetoothDevice(device.address)
                    "
                    :disabled="
                      device.address ===
                      (playlistStatus.device?.address || playlistStatus.device_address)
                    "
                  >
                    选择
                  </el-button>
                </div>
              </div>
              <div v-if="connectedDeviceList.length === 0" class="text-xs text-gray-400 text-center py-4">
                暂无设备
              </div>
            </div>
          </div>

          <!-- DLNA 类型：显示 DLNA 设备 -->
          <div
            v-else-if="
              playlistStatus.device?.type === 'dlna' || playlistStatus.device_type === 'dlna'
            "
          >
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
                    @click="onUpdateDeviceAddress(device.location, device.name)"
                    :disabled="
                      device.location ===
                      (playlistStatus.device?.address || playlistStatus.device_address)
                    "
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
          <div
            v-else-if="playlistStatus.device?.type === 'mi' || playlistStatus.device_type === 'mi'"
          >
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
                    :disabled="
                      (device.deviceID || device.address) ===
                      (playlistStatus.device?.address || playlistStatus.device_address)
                    "
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
import { MAX_PLAYLIST_DURATION, TRIGGER_BUTTONS } from "@/constants/playlist";
import type { PlaylistStatus } from "@/types/playlist";
import type { BluetoothDevice, DlnaDevice, MiDevice, AgentDevice } from "@/types/device";

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
  onUpdateDeviceAddress: (address: string, name?: string | null) => void;
  onSelectBluetoothDevice: (address: string) => void;
  onSelectAgentDevice: (device: AgentDevice | string) => void;
  onSelectMiDevice: (device: MiDevice) => void;
  onScanDlnaDevices: () => void;
  onScanMiDevices: () => void;
  onOpenScanDialog: () => void;
}

defineProps<Props>();
</script>
