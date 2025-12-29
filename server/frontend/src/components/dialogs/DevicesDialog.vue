<template>
  <el-dialog v-model="internalVisible" width="810" :before-close="handleClose">
    <template #header>
      <div></div>
    </template>
    <div class="flex flex-col gap-4">
      <div>
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-2">
            <h4 class="text-base font-semibold w-24">Agent设备</h4>
            <el-button
              type="primary"
              plain
              size="small"
              @click="handleRefreshAgentList"
              :loading="agentListLoading"
            >
              <el-icon v-if="!agentListLoading"><Refresh /></el-icon>
              <span class="ml-1">刷新</span>
            </el-button>
          </div>
        </div>
        <el-table
          :data="agentList"
          stripe
          class="w-full"
          v-loading="agentListLoading"
          :height="200"
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
              <span v-if="!row.actions || row.actions.length === 0" class="text-gray-400">无</span>
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
                <div class="flex gap-1 items-center">
                  <el-icon class="!w-4 !h-5"><Cpu /></el-icon>
                  <span class="text-[12px] mr-1 !w-4">B1</span>
                  <el-button
                    v-for="i in 2"
                    :key="i"
                    size="small"
                    type="primary"
                    plain
                    @click="handleTestAgentButton(row.agent_id, `F${12 + i}`)"
                    :loading="row[`testing_F${12 + i}`]"
                    class="flex-1"
                  >
                    F{{ 12 + i }}
                  </el-button>
                </div>
                <div class="flex gap-1 items-center">
                  <el-icon class="!w-4 !h-5"><Cpu /></el-icon>
                  <span class="text-[12px] mr-1 !w-4">B2</span>
                  <el-button
                    v-for="i in 2"
                    :key="i + 2"
                    size="small"
                    type="primary"
                    plain
                    @click="handleTestAgentButton(row.agent_id, `F${12 + i + 2}`)"
                    :loading="row[`testing_F${12 + i + 2}`]"
                    class="flex-1"
                  >
                    F{{ 12 + i + 2 }}
                  </el-button>
                </div>
                <div class="flex gap-1 items-center">
                  <el-icon class="!w-4 !h-5"><Cpu /></el-icon>
                  <span class="text-[12px] mr-1 !w-4">B3</span>
                  <el-button
                    v-for="i in 2"
                    :key="i + 4"
                    size="small"
                    type="primary"
                    plain
                    @click="handleTestAgentButton(row.agent_id, `F${12 + i + 4}`)"
                    :loading="row[`testing_F${12 + i + 4}`]"
                    class="flex-1"
                  >
                    F{{ 12 + i + 4 }}
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
      <div>
        <div class="flex items-center justify-between mb-2">
          <div class="flex items-center gap-2">
            <h4 class="text-base font-semibold w-24">小米设备</h4>
            <el-button
              type="primary"
              plain
              size="small"
              @click="scanMiDevices"
              :loading="miScanning"
            >
              <el-icon v-if="!miScanning"><Refresh /></el-icon>
              <span class="ml-1">扫描</span>
            </el-button>
          </div>
        </div>
        <el-table :data="miDeviceList" stripe class="w-full" v-loading="miScanning" :height="280">
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
                    @input="
                      (val: number) => {
                        row.volume = val;
                      }
                    "
                    @change="
                      (val: number) => {
                        setMiDeviceVolume(row, val);
                      }
                    "
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
            <div class="text-center text-gray-400 py-8">暂无设备，点击"扫描设备"开始扫描</div>
          </template>
        </el-table>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { Refresh, Cpu, Loading } from "@element-plus/icons-vue";
import { api } from "@/api/config";
import { logAndNoticeError } from "@/utils";
import { DEVICE_SCAN_TIMEOUT } from "@/constants/device";
import { useAgentDevice } from "@/composables/useAgentDevice";
import type { MiDevice } from "@/types/device";

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
const miDeviceList = ref<MiDevice[]>([]);
const miScanning = ref(false);

// 使用 useAgentDevice composable
const {
  agentList,
  loading: agentListLoading,
  refreshAgentList,
  testAgentButton,
  startRefresh,
  stopRefresh,
} = useAgentDevice();

// 刷新Agent设备列表（包装函数以保持接口一致）
const handleRefreshAgentList = async () => {
  await refreshAgentList(true, false);
};

// 测试Agent按钮（包装函数以保持接口一致）
const handleTestAgentButton = async (agentId: string, key: string) => {
  await testAgentButton(agentId, key);
};

// 辅助函数
const getMiDeviceId = (device: MiDevice): string => {
  return device.deviceID || device.address || "";
};

const clampVolume = (volume: number): number => {
  return Math.max(0, Math.min(100, volume));
};

// 扫描小米设备
const scanMiDevices = async () => {
  try {
    miScanning.value = true;
    const response = await api.get("/mi/scan", {
      params: { timeout: DEVICE_SCAN_TIMEOUT },
    });
    const result = response.data;

    if (result.code === 0) {
      const devices: MiDevice[] = (result.data || []).map((device: Partial<MiDevice>) => ({
        ...device,
        volume: undefined,
        _volumeChanging: false,
        _volumeRefreshing: false,
      }));
      miDeviceList.value = devices;

      await Promise.allSettled(miDeviceList.value.map(device => getMiDeviceVolume(device)));

      ElMessage.success(`扫描到 ${devices.length} 个小米设备`);
    } else {
      ElMessage.error(result.msg || "扫描小米设备失败");
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

    if (result.code === 0) {
      targetDevice.volume = result.data?.volume ?? result.data ?? undefined;
    } else {
      ElMessage.error(result.msg || `获取设备 ${targetDevice.name || deviceId} 音量失败`);
    }
  } catch (error) {
    logAndNoticeError(error as Error, `获取设备 ${targetDevice.name || deviceId} 音量失败`);
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

    if (result.code === 0) {
      device.volume = clampedVolume;
      ElMessage.success("音量设置成功");
    } else {
      ElMessage.error(result.msg || "设置音量失败");
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

    if (response.data.code === 0) {
      ElMessage.success("停止播放成功");
    } else {
      ElMessage.error(response.data.msg || "停止播放失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "停止小米设备播放失败");
  } finally {
    device._stopping = false;
  }
};

// 关闭对话框
const handleClose = () => {
  internalVisible.value = false;
};

// 监听对话框显示状态
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

onMounted(() => {
  if (props.visible) {
    startRefresh();
  }
});

onUnmounted(() => {
  // 停止自动刷新
  stopRefresh();
});
</script>
