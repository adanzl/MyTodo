<template>
  <ion-segment-content id="ttsTasks">
    <ion-content class="">
      <ion-refresher slot="fixed" @ionRefresh="onRefresh">
        <ion-refresher-content></ion-refresher-content>
      </ion-refresher>
      <div class="flex flex-col h-full p-2 border-t-1 border-gray-200">
        <div v-if="loading && tasks.length === 0" class="p-4 text-center text-gray-500">
          加载中…
        </div>
        <div v-else-if="error" class="p-4 text-center text-red-500">
          {{ error }}
        </div>
        <div v-else-if="tasks.length === 0" class="p-4 text-center text-gray-500">
          暂无 TTS 任务
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="task in tasks"
            :key="task.task_id"
            class="rounded-lg border border-gray-200 bg-white p-3 shadow-sm cursor-pointer active:opacity-80"
            @click="openDetail(task)">
            <div class="flex items-center justify-between">
              <span class="font-medium text-gray-800">{{ task.name || task.task_id }}</span>
              <ion-badge :color="statusColor(task.status)" class="p-1">{{
                statusLabel(task.status)
              }}</ion-badge>
            </div>
            <div v-if="task.text" class="mt-1 line-clamp-2 text-sm text-gray-600">
              {{ task.text.slice(0, 80) }}{{ task.text.length > 80 ? "…" : "" }}
            </div>
            <div class="mt-2 flex items-center gap-3 text-xs text-gray-400">
              <span v-if="task.total_chars != null">字数 {{ task.total_chars }}</span>
              <span>{{ formatTime(task.update_time) }}</span>
            </div>
          </div>
        </div>
      </div>
    </ion-content>

    <!-- 全屏详情弹窗 -->
    <ion-modal
      :is-open="!!selectedTask"
      class="ion-modal-fullscreen"
      :initial-breakpoint="1"
      :breakpoints="[0, 1]"
      @didDismiss="selectedTask = null">
      <ion-header>
        <ion-toolbar>
          <ion-buttons slot="start">
            <ion-button @click="selectedTask = null">
              <ion-icon :icon="closeOutline" />
            </ion-button>
          </ion-buttons>
          <ion-title>{{ selectedTask?.name || selectedTask?.task_id || "任务详情" }}</ion-title>
          <ion-buttons slot="end" class="mr-2">
            <ion-button @click="scrollToAnalysis" color="primary" class="!mr-3">分析</ion-button>
            <ion-button :disabled="!canGoPrev" @click="goPrev">
              <ion-icon :icon="arrowUpOutline" />
            </ion-button>
            <ion-button :disabled="!canGoNext" @click="goNext">
              <ion-icon :icon="arrowDownOutline" />
            </ion-button>
          </ion-buttons>
        </ion-toolbar>
      </ion-header>
      <ion-content class="ion-padding">
        <template v-if="selectedTask">
          <div class="space-y-3">
            <div class="flex items-center justify-between flex-wrap gap-3">
              <ion-badge :color="statusColor(selectedTask.status)" class="p-1">{{
                statusLabel(selectedTask.status)
              }}</ion-badge>
              <span class="text-sm text-gray-500 flex-1 truncate">
                {{ (selectedTask.error_message || "").slice(0, 80) }}
                {{ (selectedTask.error_message || "").length > 80 ? "…" : "" }}
              </span>
            </div>

            <!-- 音频预览（仿 server/frontend MediaComponent） -->
            <AudioPreview
              v-if="selectedTask.status === 'success'"
              :src="getTtsDownloadUrl(selectedTask.task_id)"
              :duration-seconds="selectedTask.duration ?? undefined"
              class="w-full"
            />

            <div v-if="selectedTask.text" class="rounded-lg bg-gray-100 p-3">
              <div class="text-gray-800 whitespace-pre-wrap break-words">
                {{ selectedTask.text }}
              </div>
            </div>

            <!-- 分析内容（参考 server/frontend TTS.vue） -->
            <div
              ref="analysisSectionRef"
              class="rounded-lg border border-gray-200 px-3 flex flex-col gap-1 min-h-[120px]">
              <h4 class="text-sm font-semibold text-gray-700">分析内容</h4>
              <template v-if="!selectedTask.analysis">
                <div class="text-xs text-gray-400">
                  暂无分析结果，可在服务端对该任务执行「分析」后刷新查看。
                </div>
              </template>
              <template v-else>
                <div class="space-y-3 text-xs pr-1">
                  <!-- 美词 -->
                  <div v-if="selectedTask.analysis.words?.length" class="flex gap-3">
                    <div
                      class="w-10 h-6 rounded-md bg-blue-50 border border-blue-300 flex items-center justify-center flex-shrink-0">
                      <span class="text-[11px] leading-tight text-blue-700 text-center">美词</span>
                    </div>
                    <div class="flex-1 flex flex-wrap gap-1 items-start">
                      <span
                        v-for="(w, idx) in selectedTask.analysis.words"
                        :key="idx"
                        class="inline-block px-2 py-0.5 rounded bg-blue-100 text-blue-800">
                        {{ w }}
                      </span>
                    </div>
                  </div>
                  <!-- 精彩句段 -->
                  <div v-if="selectedTask.analysis.sentence?.length" class="flex gap-3">
                    <div
                      class="w-10 h-10 rounded-md bg-emerald-50 border border-emerald-300 flex items-center justify-center flex-shrink-0">
                      <span class="text-[11px] leading-tight text-emerald-700 text-center">
                        精彩<br />句段
                      </span>
                    </div>
                    <div class="flex-1 space-y-1">
                      <p
                        v-for="(s, idx) in selectedTask.analysis.sentence"
                        :key="idx"
                        class="leading-snug text-gray-700">
                        {{ s }}
                      </p>
                    </div>
                  </div>
                  <!-- 好句花园（摘要） -->
                  <div v-if="selectedTask.analysis.abstract" class="flex gap-3">
                    <div
                      class="w-10 h-10 rounded-md bg-amber-50 border border-amber-300 flex items-center justify-center flex-shrink-0">
                      <span class="text-[11px] leading-tight text-amber-700 text-center">
                        好句<br />花园
                      </span>
                    </div>
                    <div class="flex-1">
                      <p class="leading-snug text-gray-700">
                        {{ selectedTask.analysis.abstract }}
                      </p>
                    </div>
                  </div>
                  <!-- 涂鸦 -->
                  <div v-if="selectedTask.analysis.doodle" class="flex gap-3">
                    <div
                      class="w-10 h-6 rounded-md bg-pink-50 border border-pink-300 flex items-center justify-center flex-shrink-0">
                      <span class="text-[11px] leading-tight text-pink-700 text-center">涂鸦</span>
                    </div>
                    <div class="flex-1">
                      <p class="leading-snug text-gray-700">
                        {{ selectedTask.analysis.doodle }}
                      </p>
                    </div>
                  </div>
                </div>
              </template>
            </div>
            <div v-if="selectedTask.role" class="rounded bg-gray-50 p-2 text-[12px]">
              <span class="text-gray-500">角色</span>
              <div>{{ selectedTask.role }}</div>
            </div>
            <div class="grid grid-cols-2 gap-3 text-sm">
              <div v-if="selectedTask.total_chars != null" class="rounded bg-gray-50 p-2">
                <span class="text-gray-500">字数</span>
                <div>{{ selectedTask.total_chars }}</div>
              </div>
              <div v-if="selectedTask.duration != null" class="rounded bg-gray-50 p-2">
                <span class="text-gray-500">时长</span>
                <div>{{ formatDuration(selectedTask.duration) }}</div>
              </div>
              <div v-if="selectedTask.speed != null" class="rounded bg-gray-50 p-2">
                <span class="text-gray-500">语速</span>
                <div>{{ selectedTask.speed }}</div>
              </div>
              <div v-if="selectedTask.vol != null" class="rounded bg-gray-50 p-2">
                <span class="text-gray-500">音量</span>
                <div>{{ selectedTask.vol }}</div>
              </div>
            </div>

            <div
              v-if="selectedTask.ocr_running || selectedTask.analysis_running"
              class="flex gap-2 text-sm text-amber-600">
              <span v-if="selectedTask.ocr_running">OCR 进行中</span>
              <span v-if="selectedTask.analysis_running">解析进行中</span>
            </div>
          </div>
        </template>
      </ion-content>
    </ion-modal>
  </ion-segment-content>
</template>

<script setup lang="ts">
import {
  IonBadge,
  IonButton,
  IonButtons,
  IonContent,
  IonHeader,
  IonIcon,
  IonModal,
  IonRefresher,
  IonRefresherContent,
  IonSegmentContent,
  IonTitle,
  IonToolbar,
} from "@ionic/vue";
import { arrowDownOutline, arrowUpOutline, closeOutline } from "ionicons/icons";
import { computed, ref } from "vue";
import AudioPreview from "@/components/AudioPreview.vue";
import { getTtsDownloadUrl, getTtsTaskList, type TtsTaskItem } from "@/utils/NetUtil";
import type { RefresherCustomEvent } from "@ionic/vue";

const tasks = ref<TtsTaskItem[]>([]);
const loading = ref(false);
const error = ref("");
const selectedTask = ref<TtsTaskItem | null>(null);
const analysisSectionRef = ref<HTMLElement | null>(null);

const currentIndex = computed(() => {
  if (!selectedTask.value || tasks.value.length === 0) return -1;
  const idx = tasks.value.findIndex((t) => t.task_id === selectedTask.value!.task_id);
  return idx;
});
const canGoPrev = computed(() => currentIndex.value > 0);
const canGoNext = computed(
  () => currentIndex.value >= 0 && currentIndex.value < tasks.value.length - 1
);

function openDetail(task: TtsTaskItem) {
  selectedTask.value = task;
}

function goPrev() {
  if (!canGoPrev.value) return;
  selectedTask.value = tasks.value[currentIndex.value - 1];
}

function goNext() {
  if (!canGoNext.value) return;
  selectedTask.value = tasks.value[currentIndex.value + 1];
}

function scrollToAnalysis() {
  analysisSectionRef.value?.scrollIntoView({ behavior: "smooth", block: "start" });
}

const STATUS_LABELS: Record<string, string> = {
  pending: "等待中",
  processing: "处理中",
  success: "成功",
  failed: "失败",
  uploaded: "已上传",
};

function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

function statusColor(status: string): string {
  switch (status) {
    case "success":
      return "success";
    case "processing":
      return "primary";
    case "failed":
      return "danger";
    default:
      return "medium";
  }
}

function formatTime(ts: number): string {
  if (!ts) return "";
  const d = new Date(ts * 1000);
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  if (sameDay) {
    return d.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  }
  return d.toLocaleDateString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(seconds: number | null | undefined): string {
  if (seconds == null || seconds < 0) return "—";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

async function loadTasks() {
  loading.value = true;
  error.value = "";
  try {
    tasks.value = await getTtsTaskList();
  } catch (e: any) {
    error.value = e?.message ?? "加载失败";
    tasks.value = [];
  } finally {
    loading.value = false;
  }
}

async function onRefresh(e: RefresherCustomEvent) {
  await loadTasks();
  e.target.complete();
}

loadTasks();
</script>

<style scoped>
.ion-modal-fullscreen {
  --width: 100%;
  --height: 100%;
  --border-radius: 0;
  --box-shadow: none;
}
</style>
