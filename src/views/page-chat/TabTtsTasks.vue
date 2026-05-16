<template>
  <ion-segment-content id="ttsTasks">
    <ion-content class="">
      <ion-refresher slot="fixed" @ionRefresh="onRefresh">
        <ion-refresher-content></ion-refresher-content>
      </ion-refresher>
      <div class="flex flex-col h-full p-2 border-t border-gray-300">
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
            class="rounded-lg border border-gray-300 bg-white p-3 shadow-sm cursor-pointer active:opacity-80"
            @click="openDetail(task)">
            <div class="flex items-center justify-between gap-2">
              <span class="font-medium text-gray-800 flex-1 truncate">{{
                task.name || task.task_id
              }}</span>
              <ion-icon
                v-if="task.has_analysis"
                :icon="checkmarkCircleOutline"
                class="w-4 h-4"></ion-icon>
              <ion-badge :color="statusColor(task.status)" class="p-1 w-10 text-[10px]">{{
                statusLabel(task.status)
              }}</ion-badge>
            </div>
            <div class="mt-2 flex items-center gap-3 text-xs text-gray-400">
              <div v-if="task.total_chars != null" class="flex gap-1">
                字数
                <div class="w-7! text-right">{{ task.total_chars }}</div>
              </div>
              <span v-if="task.duration != null">时长 {{ formatDuration(task.duration) }}</span>
              <span class="flex-1 text-right">{{ formatTime(task.update_time) }}</span>
            </div>
          </div>
        </div>
      </div>
    </ion-content>
    <!-- 添加按钮 -->
    <FabButton
      v-if="active"
      :disabled="addButtonCooling"
      @click="createAndOpenTask"
      class="right-[5%] bottom-[1%]"
      bottom="1%"
      right="5%"
      :hasBar="true">
      <ion-icon :icon="add" size="large"></ion-icon>
    </FabButton>
    <!-- 全屏详情弹窗 -->
    <TtsTaskDialog
      :selected-task="selectedTask"
      :can-go-prev="canGoPrev"
      :can-go-next="canGoNext"
      @close="closeDetailModal"
      @prev="goPrev"
      @next="goNext"
      @open-rename="openRenameDialog"
      @task-updated="handleTaskUpdated"
      @task-deleted="handleTaskDeleted"
      ref="ttsTaskDialogRef" />
    <!-- 改名弹窗（样式类似 alert，Tailwind 实现） -->
    <ion-modal
      :is-open="renameModalOpen"
      class="[--width:100%] [--height:100%] [--border-radius:0] [--box-shadow:none] [--backdrop-opacity:0] [--background:transparent]"
      @didDismiss="renameModalOpen = false">
      <div
        class="fixed inset-0 z-1 flex items-center justify-center bg-black/50 p-5"
        @click.self="renameModalOpen = false">
        <div class="w-full max-w-100 min-w-65 rounded-2xl bg-white p-4 shadow-xl">
          <h2 class="mb-3 text-center text-lg font-semibold text-gray-900">任务改名</h2>
          <ion-input
            v-model="renameInputValue"
            placeholder="任务名称"
            class="mb-3 rounded-lg border border-gray-300 text-base px-2!"
            :clear-input="true"
            :clear-on-edit="false" />
          <div class="flex justify-end gap-1 border-t border-gray-200 pt-2">
            <ion-button
              fill="clear"
              class="min-h-11 font-semibold"
              @click="appendFirstLineToRename"
              >填入</ion-button
            >
            <ion-button
              fill="clear"
              class="min-h-11 font-semibold"
              @click="renameModalOpen = false"
              >取消</ion-button
            >
            <ion-button
              fill="clear"
              color="primary"
              class="min-h-11 font-semibold"
              @click="confirmRename"
              >确定</ion-button
            >
          </div>
        </div>
      </div>
    </ion-modal>
  </ion-segment-content>
</template>

<script setup lang="ts">
import {
  IonBadge,
  IonRefresher,
  IonRefresherContent,
  IonSegmentContent,
  alertController,
  loadingController,
} from "@ionic/vue";
import { add, checkmarkCircleOutline } from "ionicons/icons";
import { computed, onUnmounted, ref, watch } from "vue";
import FabButton from "@/components/FabButton.vue";
import EventBus, { C_EVENT } from "@/types/event-bus";
import {
  createTtsTask,
  getTtsTask,
  getTtsTaskList,
  updateTtsTask,
  type TtsTaskItem,
} from "@/api/api-tts";
import type { RefresherCustomEvent } from "@ionic/vue";
import TtsTaskDialog from "./dialogs/TtsTask.vue";

// ==================== Props ====================
const props = withDefaults(
  defineProps<{
    /** 仅在此页签激活时显示 FabButton */
    active?: boolean;
  }>(),
  { active: false }
);

// ==================== Constants ====================
const STATUS_LABELS: Record<string, string> = {
  pending: "等待",
  processing: "处理",
  success: "成功",
  failed: "失败",
  uploaded: "已上传",
};

const ADD_COOL_DOWN_MS = 1500;
const PROCESSING_POLL_MS = 3000;
const LIST_REFRESH_MS = 5000;

// ==================== State ====================
const tasks = ref<TtsTaskItem[]>([]);
const loading = ref(false);
const error = ref("");
const selectedTask = ref<TtsTaskItem | null>(null);

/** 添加按钮防短时间多点 */
const addButtonCooling = ref(false);

/** 改名弹窗 */
const renameModalOpen = ref(false);
const renameInputValue = ref("");

/** TTS 任务对话框引用 */
const ttsTaskDialogRef = ref<InstanceType<typeof TtsTaskDialog> | null>(null);

/** 定时器 */
let processingPollTimer: ReturnType<typeof setInterval> | null = null;
let listRefreshTimer: ReturnType<typeof setInterval> | null = null;
// ==================== Computed ====================
const currentIndex = computed(() => {
  if (!selectedTask.value || tasks.value.length === 0) return -1;
  return tasks.value.findIndex((t) => t.task_id === selectedTask.value!.task_id);
});

const canGoPrev = computed(() => currentIndex.value > 0);

const canGoNext = computed(
  () => currentIndex.value >= 0 && currentIndex.value < tasks.value.length - 1
);

// ==================== Detail Modal Operations ====================
async function openDetail(task: TtsTaskItem) {
  const loading = await loadingController.create({ message: "Loading..." });
  loading.present();
  
  try {
    const full = await getTtsTask(task.task_id);
    selectedTask.value = full;
  } catch (e: any) {
    EventBus.$emit(C_EVENT.TOAST, e?.message ?? "加载任务详情失败");
    selectedTask.value = task;
  } finally {
    loading.dismiss();
  }
}

function closeDetailModal() {
  stopProcessingPoll();
  selectedTask.value = null;
}

async function goPrev() {
  if (!canGoPrev.value) return;
  await navigateToTask(currentIndex.value - 1);
}

async function goNext() {
  if (!canGoNext.value) return;
  await navigateToTask(currentIndex.value + 1);
}

async function navigateToTask(index: number) {
  const task = tasks.value[index];
  const loading = await loadingController.create({ message: "Loading..." });
  loading.present();
  
  try {
    selectedTask.value = await getTtsTask(task.task_id);
  } catch {
    selectedTask.value = task;
  } finally {
    loading.dismiss();
  }
}

// ==================== Utility Functions ====================
function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

function statusColor(status: string): string {
  switch (status) {
    case "success":
      return "success";
    case "processing":
      return "warning";
    case "failed":
      return "danger";
    default:
      return "light";
  }
}

function formatTime(ts: number): string {
  if (!ts) return "";
  const d = new Date(ts * 1000);
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

// ==================== Task List Operations ====================
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

/** 点击添加按钮：创建新 TTS 任务并打开其详情弹窗 */
async function createAndOpenTask() {
  if (addButtonCooling.value) return;
  
  addButtonCooling.value = true;
  const loading = await loadingController.create({ message: "Loading..." });
  loading.present();
  
  try {
    const { task_id } = await createTtsTask({ text: "" });
    await loadTasks();
    
    const task = tasks.value.find((t) => t.task_id === task_id);
    if (task) {
      try {
        selectedTask.value = await getTtsTask(task_id);
      } catch {
        selectedTask.value = task;
      }
    } else {
      EventBus.$emit(C_EVENT.TOAST, "已创建，请从列表打开");
    }
  } catch (e: any) {
    EventBus.$emit(C_EVENT.TOAST, e?.message ?? "创建失败");
  } finally {
    loading.dismiss();
    setTimeout(() => {
      addButtonCooling.value = false;
    }, ADD_COOL_DOWN_MS);
  }
}

// ==================== Task Update Handlers ====================
async function handleTaskUpdated(updatedTask: TtsTaskItem) {
  selectedTask.value = updatedTask;
  const idx = tasks.value.findIndex((t) => t.task_id === updatedTask.task_id);
  if (idx >= 0) {
    tasks.value[idx] = updatedTask;
  } else {
    tasks.value.unshift(updatedTask);
  }
}

function handleTaskDeleted(taskId: string) {
  const idx = tasks.value.findIndex((t) => t.task_id === taskId);
  if (idx >= 0) {
    tasks.value.splice(idx, 1);
  }
  selectedTask.value = null;
}

// ==================== Rename Operations ====================
function openRenameDialog() {
  const task = selectedTask.value;
  if (!task) return;
  renameInputValue.value = task.name || task.task_id || "";
  renameModalOpen.value = true;
}

function appendFirstLineToRename() {
  const text = ttsTaskDialogRef.value?.editText ?? selectedTask.value?.text ?? "";
  const firstLine = text.split(/\r?\n/)[0]?.trim() ?? "";
  renameInputValue.value = (renameInputValue.value ?? "") + firstLine;
}

async function confirmRename() {
  const task = selectedTask.value;
  if (!task) return;
  
  const newName = (renameInputValue.value ?? "").trim();
  if (!newName) {
    EventBus.$emit(C_EVENT.TOAST, "名称不能为空");
    return;
  }
  
  try {
    await updateTtsTask(task.task_id, { name: newName });
    const t = tasks.value.find((x) => x.task_id === task.task_id);
    if (t) t.name = newName;
    if (selectedTask.value?.task_id === task.task_id) {
      selectedTask.value = { ...selectedTask.value, name: newName };
    }
    EventBus.$emit(C_EVENT.TOAST, "已改名");
    renameModalOpen.value = false;
  } catch (e: any) {
    EventBus.$emit(C_EVENT.TOAST, e?.message ?? "改名失败");
  }
}

// ==================== Polling Management ====================
function startProcessingPoll(taskId: string) {
  stopProcessingPoll();
  
  const poll = async () => {
    if (!selectedTask.value || selectedTask.value.status !== "processing") return;
    
    try {
      const updated = await getTtsTask(taskId);
      if (selectedTask.value?.task_id === taskId) {
        selectedTask.value = updated;
      }
      const idx = tasks.value.findIndex((t) => t.task_id === taskId);
      if (idx >= 0) tasks.value[idx] = updated;
    } catch {
      // 忽略单次刷新失败
    }
  };
  
  poll();
  processingPollTimer = setInterval(poll, PROCESSING_POLL_MS);
}

function stopProcessingPoll() {
  if (processingPollTimer) {
    clearInterval(processingPollTimer);
    processingPollTimer = null;
  }
}

// ==================== Lifecycle & Watchers ====================
/** 详情页打开且任务状态为「处理中」时定时刷新当前任务信息 */
watch(
  () => ({ task: selectedTask.value, status: selectedTask.value?.status }),
  ({ task, status }) => {
    if (task && status === "processing") {
      startProcessingPoll(task.task_id);
    } else {
      stopProcessingPoll();
    }
  },
  { immediate: true }
);

/** TTS 页签激活时自动刷新列表，并定时刷新 */
watch(
  () => props.active,
  (isActive) => {
    if (listRefreshTimer) {
      clearInterval(listRefreshTimer);
      listRefreshTimer = null;
    }
    if (isActive) {
      loadTasks();
      listRefreshTimer = setInterval(loadTasks, LIST_REFRESH_MS);
    }
  }
);

onUnmounted(() => {
  stopProcessingPoll();
  if (listRefreshTimer) {
    clearInterval(listRefreshTimer);
    listRefreshTimer = null;
  }
});

// 初始化加载
loadTasks();
</script>

<style scoped>
/* 此文件无需额外样式 */
</style>
