<template>
  <ion-segment-content id="tabMiDevices">
    <ion-content :scroll-y="true" class="ion-padding">
      <ion-refresher slot="fixed" :disabled="!enabled" @ionRefresh="onRefresh">
        <ion-refresher-content />
      </ion-refresher>

      <div v-if="!enabled" class="flex flex-col justify-center items-center h-full text-gray-400">
        <ion-icon :icon="radioOutline" class="text-6xl mb-4" />
        <p>仅管理员可用</p>
      </div>

      <div v-else-if="showSpinner" class="flex justify-center items-center h-full">
        <ion-spinner name="crescent" />
      </div>

      <div v-else-if="devices.length === 0" class="flex flex-col justify-center items-center h-full text-gray-400">
        <ion-icon :icon="radioOutline" class="text-6xl mb-4" />
        <p>暂无设备，下拉扫描</p>
      </div>

      <div v-else class="space-y-3">
        <ion-card v-for="(device, index) in devices" :key="deviceKey(device, index)">
          <ion-card-content>
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0 flex-1">
                <h2 class="text-lg font-semibold truncate">{{ device.name || "未命名设备" }}</h2>
                <p class="text-xs text-gray-500 mt-1 truncate">{{ device.deviceID || device.address || "-" }}</p>
              </div>
              <span
                class="text-xs shrink-0"
                :class="device.status?.state === 'PLAYING' ? 'text-green-600' : 'text-gray-500'">
                {{ statusLabel(device) }}
              </span>
            </div>

            <p v-if="device.status?.position || device.status?.duration" class="text-xs text-blue-600 mt-2">
              {{ device.status?.position || "--" }} / {{ device.status?.duration || "--" }}
            </p>

            <div class="flex items-center gap-2 mt-2">
              <span class="text-xs text-gray-600 w-8 shrink-0">音量</span>
              <span class="text-xs w-6 text-right shrink-0">
                {{ device.volume !== undefined ? device.volume : "-" }}
              </span>
              <ion-range
                class="flex-1 px-1"
                :min="5"
                :max="100"
                :step="1"
                :value="device.volume ?? 0"
                :disabled="volumeDisabled(device)"
                @ionInput="onVolumeInput(device, $event)"
                @ionChange="onVolumeCommit(device, $event)" />
            </div>

            <div class="flex items-center gap-2 mt-2">
              <ion-button
                size="small"
                fill="outline"
                :disabled="device._statusRefreshing || device._volumeChanging"
                @click="refreshStatus(device)">
                <ion-icon :icon="refreshOutline" class="w-4 h-4" />
              </ion-button>
              <ion-button
                size="small"
                fill="outline"
                color="danger"
                :disabled="device._stopping"
                @click="stop(device)">
                <ion-icon :icon="stopOutline" class="w-4 h-4" />
              </ion-button>
              <ion-button
                size="small"
                fill="outline"
                class="ml-auto!"
                :disabled="device._speaking || device._statusRefreshing || device._volumeChanging"
                @click="speak(device)">
                <ion-icon :icon="micOutline" class="w-4 h-4" />
              </ion-button>
            </div>
          </ion-card-content>
        </ion-card>
      </div>
    </ion-content>
  </ion-segment-content>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  alertController,
  IonCard,
  IonCardContent,
  IonRange,
  IonRefresher,
  IonRefresherContent,
  IonSegmentContent,
  IonSpinner,
} from "@ionic/vue";
import { micOutline, radioOutline, refreshOutline, stopOutline } from "ionicons/icons";
import {
  getMiDeviceStatus,
  scanMiDevices,
  setMiDeviceVolume,
  speakMiDevice,
  stopMiDevice,
  type MiDevice,
} from "@/api/api-devices";
import EventBus, { C_EVENT } from "@/types/event-bus";

const props = defineProps<{
  active: boolean;
  enabled: boolean;
}>();

const devices = ref<MiDevice[]>([]);
const scanning = ref(false);
const loadedOnce = ref(false);
const committedVolume = new Map<string, number>();
let scanTask: Promise<void> | null = null;

const showSpinner = computed(() => scanning.value && devices.value.length === 0);

const deviceKey = (device: MiDevice, index: number) =>
  `${device.deviceID || device.address || device.name || "device"}-${index}`;

const getDeviceId = (device: MiDevice) => device.deviceID || device.address || "";

const statusLabel = (device: MiDevice) => {
  if (device._statusRefreshing && !device.status) return "获取中";
  if (device.status?.state === "PLAYING") return "播放中";
  if (device.status) return "已停止";
  return "-";
};

const volumeDisabled = (device: MiDevice) =>
  device.volume === undefined || !!device._volumeChanging || !!device._statusRefreshing;

const rangeValue = (event: CustomEvent) => {
  const value = event.detail?.value;
  return typeof value === "number" ? value : Number(value) || 0;
};

const clampVolume = (volume: number) => Math.max(0, Math.min(100, Math.round(volume)));

const requireIdentity = (device: MiDevice) => {
  const deviceId = getDeviceId(device);
  const deviceDid = device.miotDID;
  if (!deviceId || !deviceDid) {
    EventBus.$emit(C_EVENT.TOAST, "设备 ID 或 DID 无效");
    return null;
  }
  return { deviceId, deviceDid };
};

const refreshStatus = async (device: MiDevice, quiet = false) => {
  const deviceId = getDeviceId(device);
  const deviceDid = device.miotDID;
  if (!deviceId || !deviceDid) {
    if (!quiet) EventBus.$emit(C_EVENT.TOAST, "设备 ID 或 DID 无效");
    return;
  }
  const target = devices.value.find((item) => getDeviceId(item) === deviceId) ?? device;
  target._statusRefreshing = true;
  try {
    const result = await getMiDeviceStatus(deviceId, deviceDid);
    if (result?.code === 0) {
      target.status = result.data;
      if (result.data?.volume !== undefined) {
        target.volume = result.data.volume;
        committedVolume.set(deviceId, result.data.volume);
      }
    } else if (!quiet) {
      EventBus.$emit(C_EVENT.TOAST, result?.msg || "获取设备状态失败");
    }
  } catch (error) {
    console.error("获取设备状态失败:", error);
    if (!quiet) EventBus.$emit(C_EVENT.TOAST, "获取设备状态失败");
  } finally {
    target._statusRefreshing = false;
  }
};

const scan = async () => {
  if (!props.enabled) return;
  if (scanTask) return scanTask;

  scanTask = (async () => {
    scanning.value = true;
    try {
      const result = await scanMiDevices();
      if (result?.code === 0) {
        const list = (Array.isArray(result.data) ? result.data : []) as Partial<MiDevice>[];
        devices.value = list.map((device) => {
          const next: MiDevice = {
            name: device.name || "",
            address: device.address || "",
            deviceID: device.deviceID,
            mac: device.mac,
            miotDID: device.miotDID,
            volume: undefined,
            status: undefined,
            _volumeChanging: false,
            _statusRefreshing: false,
            _stopping: false,
            _speaking: false,
          };
          return next;
        });
        await Promise.allSettled(devices.value.map((device) => refreshStatus(device, true)));
        EventBus.$emit(C_EVENT.TOAST, `扫描到 ${devices.value.length} 个小米设备`);
      } else {
        EventBus.$emit(C_EVENT.TOAST, result?.msg || "扫描小米设备失败");
      }
    } catch (error) {
      console.error("扫描小米设备失败:", error);
      EventBus.$emit(C_EVENT.TOAST, "扫描小米设备失败");
    } finally {
      loadedOnce.value = true;
      scanning.value = false;
      scanTask = null;
    }
  })();

  return scanTask;
};

const onVolumeInput = (device: MiDevice, event: CustomEvent) => {
  device.volume = clampVolume(rangeValue(event));
};

const onVolumeCommit = async (device: MiDevice, event: CustomEvent) => {
  const identity = requireIdentity(device);
  if (!identity) return;
  const volume = clampVolume(rangeValue(event));
  if (committedVolume.get(identity.deviceId) === volume) return;
  device._volumeChanging = true;
  try {
    const result = await setMiDeviceVolume(identity.deviceId, identity.deviceDid, volume);
    if (result?.code === 0) {
      device.volume = volume;
      committedVolume.set(identity.deviceId, volume);
      EventBus.$emit(C_EVENT.TOAST, "音量设置成功");
    } else {
      EventBus.$emit(C_EVENT.TOAST, result?.msg || "设置音量失败");
    }
  } catch (error) {
    console.error("设置小米设备音量失败:", error);
    EventBus.$emit(C_EVENT.TOAST, "设置音量失败");
  } finally {
    device._volumeChanging = false;
  }
};

const speak = async (device: MiDevice) => {
  const identity = requireIdentity(device);
  if (!identity) return;
  const deviceName = device.name || identity.deviceId;

  const alert = await alertController.create({
    header: "文字播报",
    message: `向「${deviceName}」发送要播报的文字`,
    inputs: [
      {
        name: "text",
        type: "textarea",
        placeholder: "请输入要播报的内容",
      },
    ],
    buttons: [
      { text: "取消", role: "cancel" },
      {
        text: "发送",
        handler: (data) => {
          const text = String(data?.text || "").trim();
          if (!text) {
            EventBus.$emit(C_EVENT.TOAST, "内容不能为空");
            return false;
          }
          if (text.length > 500) {
            EventBus.$emit(C_EVENT.TOAST, "内容不能超过 500 字");
            return false;
          }
          void sendSpeak(device, text);
          return true;
        },
      },
    ],
  });
  await alert.present();
};

const sendSpeak = async (device: MiDevice, text: string) => {
  const identity = requireIdentity(device);
  if (!identity) return;
  device._speaking = true;
  try {
    const result = await speakMiDevice(identity.deviceId, identity.deviceDid, text);
    EventBus.$emit(C_EVENT.TOAST, result?.code === 0 ? "已发送播报" : result?.msg || "播报失败");
  } catch (error) {
    console.error("小米设备文字播报失败:", error);
    EventBus.$emit(C_EVENT.TOAST, "播报失败");
  } finally {
    device._speaking = false;
  }
};

const stop = async (device: MiDevice) => {
  const identity = requireIdentity(device);
  if (!identity) return;
  device._stopping = true;
  try {
    const result = await stopMiDevice(identity.deviceId, identity.deviceDid);
    if (result?.code === 0) {
      EventBus.$emit(C_EVENT.TOAST, "已停止播放");
      await refreshStatus(device);
    } else {
      EventBus.$emit(C_EVENT.TOAST, result?.msg || "停止播放失败");
    }
  } catch (error) {
    console.error("停止小米设备播放失败:", error);
    EventBus.$emit(C_EVENT.TOAST, "停止播放失败");
  } finally {
    device._stopping = false;
  }
};

const onRefresh = (event: CustomEvent) => {
  scan().finally(() => {
    (event.target as HTMLIonRefresherElement).complete();
  });
};

watch(
  () => props.active && props.enabled,
  (visible) => {
    if (visible && !loadedOnce.value) {
      void scan();
    }
  }
);

</script>
