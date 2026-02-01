<template>
  <ion-segment-content id="ttsTasks">
    <ion-content class="">
      <ion-refresher slot="fixed" @ionRefresh="onRefresh">
        <ion-refresher-content></ion-refresher-content>
      </ion-refresher>
      <div class="flex flex-col h-full p-2 border-t-1 border-gray-300">
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
          <div v-for="task in tasks" :key="task.task_id"
            class="rounded-lg border border-gray-300 bg-white p-3 shadow-sm cursor-pointer active:opacity-80"
            @click="openDetail(task)">
            <div class="flex items-center justify-between gap-2">
              <span class="font-medium text-gray-800 flex-1 truncate">{{ task.name || task.task_id }}</span>
              <ion-icon v-if="task.analysis" :icon="checkmarkCircleOutline" class="w-4 h-4"></ion-icon>
              <ion-badge :color="statusColor(task.status)" class="p-1 w-14">{{
                statusLabel(task.status)
              }}</ion-badge>
            </div>
            <div v-if="task.text" class="mt-1 line-clamp-2 text-sm text-gray-600">
              {{ task.text.slice(0, 80) }}{{ task.text.length > 80 ? "…" : "" }}
            </div>
            <div class="mt-2 flex items-center gap-3 text-xs text-gray-400">
              <span v-if="task.total_chars != null">字数 {{ task.total_chars }}</span>
              <span v-if="task.duration != null">时长 {{ formatDuration(task.duration) }}</span>
              <span class="flex-1 text-right">{{ formatTime(task.update_time) }}</span>
            </div>
          </div>
        </div>
      </div>
    </ion-content>
    <!-- 添加按钮 -->
    <FabButton v-if="active" :disabled="addButtonCooling" @click="createAndOpenTask" class="right-[5%] bottom-[1%]"
      bottom="1%" right="5%" :hasBar="true">
      <ion-icon :icon="add" size="large"></ion-icon>
    </FabButton>
    <!-- 全屏详情弹窗 -->
    <ion-modal :is-open="!!selectedTask" class="ion-modal-fullscreen" :initial-breakpoint="1" :breakpoints="[0, 1]"
      @didDismiss="closeDetailModal">
      <ion-header>
        <ion-toolbar>
          <ion-buttons slot="start">
            <ion-button @click="closeDetailModal">
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
              <div class="flex items-center gap-2 flex-shrink-0">
                <ion-button size="small" fill="outline" class="" @click.stop="openRenameDialog" shape="round">
                  <ion-icon :icon="createOutline" slot="icon-only" />
                </ion-button>
                <ion-badge :color="statusColor(selectedTask.status)" class="p-2 text-[10px]">
                  {{ statusLabel(selectedTask.status) }}
                </ion-badge>
                <ion-button size="small" color="primary"
                  :disabled="isTaskBusy || selectedTask.status === 'processing' || generateVoiceLock || !(selectedTask.text || '').trim()"
                  @click.stop="handleStartTask">
                  生成语音
                </ion-button>
              </div>
              <span class="text-sm text-gray-500 flex-1 truncate">
                {{ (selectedTask.error_message || "").slice(0, 80) }}
                {{ (selectedTask.error_message || "").length > 80 ? "…" : "" }}
              </span>
            </div>

            <!-- 识别（仿 server/frontend TTS.vue：选择图片后 OCR 结果追加到任务文本） -->
            <div class="rounded-lg border border-gray-300 px-3 py-2 flex items-center gap-3">
              <!-- 已选图片与添加按钮同一行，点击图片可预览 -->
              <div class="flex items-center gap-2 flex-1 min-w-0">
                <ion-button size="small" fill="clear"
                  class="flex items-center justify-center w-10 h-14 rounded-lg border-2 border-dashed border-gray-300 text-gray-400 hover:border-primary hover:text-primary"
                  @click="pickImages">
                  <ion-icon :icon="imageOutline" slot="icon-only" class="text-2xl" />
                  <div class="absolute top-0.5 !p-0 !overflow-hidden items-center justify-center">
                    <span class="text-xs">{{ selectedImages.length }}</span>
                  </div>
                </ion-button>
                <!-- ocr 图片列表 -->
                <div class="ocr-image-list flex flex-1 items-center gap-2 mr-2 overflow-x-auto">
                  <input ref="imageInputRef" type="file" accept="image/*" multiple class="hidden"
                    @change="onImageFileChange" />
                  <div v-for="(file, idx) in selectedImages" :key="idx"
                    class="relative w-14 h-14 flex-shrink-0 cursor-pointer active:opacity-80"
                    @click="openOcrPreview(idx)">
                    <div class="absolute inset-0 rounded-lg overflow-hidden border border-gray-200">
                      <img :src="getOcrImageUrl(idx)" :alt="file.name" class="w-full h-full object-cover" />
                    </div>
                    <ion-button size="small" fill="solid" color="dark"
                      class="absolute -top-0 -right-0 !min-w-0 !min-h-0 !w-6 !h-6 !max-w-6 !max-h-6 !p-0 !aspect-square !rounded-full !overflow-hidden !flex !items-center !justify-center shadow [--color:white] [--border-radius:50%]"
                      sharp="round" @click.stop="removeOcrImage(idx)">
                      <ion-icon :icon="closeCircleOutline" slot="icon-only" class="!w-5 !h-5 block shrink-0" />
                    </ion-button>
                  </div>
                </div>
              </div>
              <div class="flex items-center flex-shrink-0">
                <ion-button size="small" color="primary"
                  :disabled="isTaskBusy || selectedImages.length === 0 || ocrLoading" class="!w-10 !h-12 !p-0"
                  style="--padding-start: 0; --padding-end: 0" @click="runOcr">
                  {{ ocrLoading ? "识别中…" : "识别" }}
                </ion-button>
              </div>
            </div>

            <!-- 图片预览弹窗 -->
            <ion-modal :is-open="previewOcrIndex >= 0" class="ion-modal-fullscreen" :initial-breakpoint="1"
              :breakpoints="[0, 1]" @didDismiss="previewOcrIndex = -1">
              <ion-header>
                <ion-toolbar>
                  <ion-buttons slot="start">
                    <ion-button @click="previewOcrIndex = -1">
                      <ion-icon :icon="closeOutline" />
                    </ion-button>
                  </ion-buttons>
                  <ion-title>{{ selectedImages[previewOcrIndex]?.name || "图片预览" }}</ion-title>
                  <ion-buttons slot="end" class="mr-2">
                    <ion-button color="danger" fill="clear" @click="removeOcrImageInPreview">
                      移除
                    </ion-button>
                    <ion-button :disabled="previewOcrIndex <= 0" @click="previewOcrPrev">
                      <ion-icon :icon="arrowUpOutline" />
                    </ion-button>
                    <ion-button :disabled="previewOcrIndex < 0 || previewOcrIndex >= selectedImages.length - 1
                      " @click="previewOcrNext">
                      <ion-icon :icon="arrowDownOutline" />
                    </ion-button>
                  </ion-buttons>
                </ion-toolbar>
              </ion-header>
              <ion-content class="ion-padding">
                <div v-if="previewOcrIndex >= 0 && selectedImages[previewOcrIndex]"
                  class="flex items-center justify-center min-h-full">
                  <img :src="getOcrImageUrl(previewOcrIndex)" :alt="selectedImages[previewOcrIndex].name"
                    class="max-w-full max-h-[85vh] object-contain" />
                </div>
              </ion-content>
            </ion-modal>
            <div v-if="selectedTask.ocr_running || selectedTask.analysis_running"
              class="flex gap-2 text-sm text-amber-600">
              <span v-if="selectedTask.ocr_running">OCR 进行中</span>
              <span v-if="selectedTask.analysis_running">解析进行中</span>
            </div>
            <!-- 音频 -->
            <div v-if="selectedTask.status === 'success'" class="flex gap-2">
              <AudioPreview :src="getTtsDownloadUrl(selectedTask.task_id)"
                :duration-seconds="selectedTask.duration ?? undefined" class="flex-1" />
              <ion-button size="small" color="primary" fill="clear" :disabled="downloadButtonLock"
                @click="handleDownloadTtsAudio">
                下载
              </ion-button>
            </div>

            <div class="rounded-lg bg-gray-100 p-2">
              <ion-textarea v-model="editText" placeholder="请输入要转换为语音的文本" :disabled="isTaskBusy"
                class="text-gray-800 rounded-lg min-h-[100px] [--padding-start:8px] [--padding-end:8px] [--padding-top:1px] [--padding-bottom:8px]"
                :auto-grow="true" :rows="4" />
            </div>

            <!-- 分析内容（参考 server/frontend TTS.vue） -->
            <div ref="analysisSectionRef"
              class="rounded-lg border border-gray-300 px-3 flex flex-col gap-1 min-h-[120px]">
              <div class="flex items-center justify-between">
                <h4 class="text-sm font-semibold text-gray-700">分析内容</h4>
                <ion-button size="small" color="primary" :disabled="!editText.trim() || isTaskBusy"
                  @click="runAnalysis">
                  分析
                </ion-button>
              </div>
              <template v-if="!selectedTask.analysis">
                <div class="text-xs text-gray-400">
                  暂无分析结果，可在服务端对该任务执行「分析」后刷新查看。
                </div>
              </template>
              <template v-else>
                <div class="space-y-3 text-xs pr-1 py-1">
                  <!-- 美词 -->
                  <div v-if="selectedTask.analysis.words?.length" class="flex gap-3">
                    <div
                      class="w-10 h-6 rounded-md bg-blue-50 border border-blue-300 flex items-center justify-center flex-shrink-0">
                      <span class="text-[11px] leading-tight text-blue-700 text-center">美词</span>
                    </div>
                    <div class="flex-1 flex flex-wrap gap-1 items-start">
                      <span v-for="(w, idx) in selectedTask.analysis.words" :key="idx"
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
                      <p v-for="(s, idx) in selectedTask.analysis.sentence" :key="idx"
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
            <div class="rounded bg-gray-50 p-2 text-[12px] flex items-center gap-2">
              <span class="text-gray-500 shrink-0 w-10">音色</span>
              <ion-select v-model="editRole" placeholder="请选择音色（可选）" :disabled="isTaskBusy" interface="popover"
                class="min-h-8 flex-1 min-w-0">
                <ion-select-option value="">无</ion-select-option>
                <ion-select-option value="cosyvoice-v3-plus-leo-34ba9eaebae44039a4a9426af6389dcd">
                  灿灿
                </ion-select-option>
              </ion-select>
            </div>
            <div class="grid grid-cols-2 gap-3 text-sm">
              <div v-if="selectedTask.total_chars != null" class="rounded bg-gray-50 p-2">
                <span class="text-gray-500">字数</span>
                <div>{{ selectedTask.total_chars }}</div>
              </div>
              <div class="rounded bg-gray-50 p-2">
                <span class="text-gray-500">时长</span>
                <div>{{ formatDuration(selectedTask.duration) }}</div>
              </div>
              <div class="rounded bg-gray-50 p-2">
                <span class="text-gray-500">语速</span>
                <div class="flex items-center gap-2 mt-1">
                  <ion-button size="small" fill="clear"
                    @click="editSpeed = Math.max(0.5, Math.round((editSpeed - 0.1) * 10) / 10)">−</ion-button>
                  <span class="min-w-[2.5rem] text-center">{{ editSpeed }}</span>
                  <ion-button size="small" fill="clear"
                    @click="editSpeed = Math.min(2, Math.round((editSpeed + 0.1) * 10) / 10)">+</ion-button>
                </div>
              </div>
              <div class="rounded bg-gray-50 p-2">
                <span class="text-gray-500">音量</span>
                <div class="flex items-center gap-2 mt-1">
                  <ion-button size="small" fill="clear" @click="editVol = Math.max(0, editVol - 10)">−</ion-button>
                  <span class="min-w-[2.5rem] text-center">{{ editVol }}</span>
                  <ion-button size="small" fill="clear" @click="editVol = Math.min(100, editVol + 10)">+</ion-button>
                </div>
              </div>
            </div>



            <div class="ion-padding-top ion-padding-bottom flex items-center gap-2">
              <ion-button expand="block" @click="saveAndClose" class="flex-1">确定</ion-button>
              <ion-button color="danger" @click="confirmDelete">
                <ion-icon :icon="trashOutline" />
              </ion-button>
            </div>
          </div>
        </template>
      </ion-content>
    </ion-modal>
    <!-- 改名弹窗（样式类似 alert，Tailwind 实现） -->
    <ion-modal :is-open="renameModalOpen"
      class="[--width:100%] [--height:100%] [--border-radius:0] [--box-shadow:none] [--backdrop-opacity:0] [--background:transparent]"
      @didDismiss="renameModalOpen = false">
      <div class="fixed inset-0 z-[1] flex items-center justify-center bg-black/50 p-5"
        @click.self="renameModalOpen = false">
        <div class="w-full max-w-[400px] min-w-[260px] rounded-2xl bg-white p-4 shadow-xl">
          <h2 class="mb-3 text-center text-lg font-semibold text-gray-900">任务改名</h2>
          <ion-input v-model="renameInputValue" placeholder="任务名称"
            class="mb-3 rounded-lg border border-gray-300 text-base !px-2" :clear-input="true" :clear-on-edit="false" />
          <div class="flex justify-end gap-1 border-t border-gray-200 pt-2">
            <ion-button fill="clear" class="min-h-[44px] font-semibold" @click="appendFirstLineToRename">填入</ion-button>
            <ion-button fill="clear" class="min-h-[44px] font-semibold" @click="renameModalOpen = false">取消</ion-button>
            <ion-button fill="clear" color="primary" class="min-h-[44px] font-semibold"
              @click="confirmRename">确定</ion-button>
          </div>
        </div>
      </div>
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
  IonInput,
  IonModal,
  IonRefresher,
  IonRefresherContent,
  IonSegmentContent,
  IonSelect,
  IonSelectOption,
  IonTextarea,
  IonTitle,
  IonToolbar,
  alertController,
} from "@ionic/vue";
import {
  arrowDownOutline,
  arrowUpOutline,
  closeOutline,
  add,
  trashOutline,
  closeCircleOutline,
  imageOutline,
  createOutline,
  checkmarkCircleOutline,
} from "ionicons/icons";
import { computed, onUnmounted, ref, watch } from "vue";
import AudioPreview from "@/components/AudioPreview.vue";
import FabButton from "@/components/FabButton.vue";
import EventBus, { C_EVENT } from "@/types/EventBus";
import { resizeImageToFile } from "@/utils/ImgMgr";
import {
  createTtsTask,
  deleteTtsTask,
  downloadTtsAudio,
  getTtsTask,
  getTtsDownloadUrl,
  getTtsTaskList,
  ocrTtsTask,
  startTtsAnalysis,
  startTtsTask,
  updateTtsTask,
  type TtsTaskItem,
} from "@/utils/NetUtil";
import type { RefresherCustomEvent } from "@ionic/vue";

withDefaults(
  defineProps<{
    /** 仅在此页签激活时显示 FabButton */
    active?: boolean;
  }>(),
  { active: false }
);

const tasks = ref<TtsTaskItem[]>([]);
const loading = ref(false);
const error = ref("");
const selectedTask = ref<TtsTaskItem | null>(null);
const analysisSectionRef = ref<HTMLElement | null>(null);
/** 弹窗内可编辑的语速、音量、文本、角色（确定时提交），仿 server/frontend TTS.vue */
const editSpeed = ref<number>(1);
const editVol = ref<number>(50);
const editText = ref<string>("");
const editRole = ref<string>("");
/** 识别：已选图片、预览 URL 缓存、隐藏 input、加载态 */
const selectedImages = ref<File[]>([]);
const ocrImageUrls = ref<string[]>([]);
const imageInputRef = ref<HTMLInputElement | null>(null);
const ocrLoading = ref(false);
/** 当前预览的图片下标，-1 表示未打开 */
const previewOcrIndex = ref(-1);
/** 添加按钮防短时间多点：创建中或冷却期内为 true */
const addButtonCooling = ref(false);
const ADD_COOLDOWN_MS = 1500;
/** 下载按钮点击后锁住 1s */
const downloadButtonLock = ref(false);
const DOWNLOAD_LOCK_MS = 1000;
/** 生成语音按钮点击后禁用 1s */
const generateVoiceLock = ref(false);
const GENERATE_VOICE_LOCK_MS = 1000;
/** 改名弹窗 */
const renameModalOpen = ref(false);
const renameInputValue = ref("");
/** 详情页「处理中」时定时刷新当前任务的定时器 */
let processingPollTimer: ReturnType<typeof setInterval> | null = null;
const PROCESSING_POLL_MS = 3000;

/** 任务是否忙（TTS 生成中或 OCR/分析子任务中），仿 frontend TTS.vue */
const isTaskBusy = computed(
  () =>
    !!(
      selectedTask.value?.status === "processing" ||
      selectedTask.value?.ocr_running ||
      selectedTask.value?.analysis_running
    )
);

watch(selectedTask, (t) => {
  if (t) {
    editSpeed.value = t.speed ?? 1;
    editVol.value = t.vol ?? 50;
    editText.value = t.text ?? "";
    editRole.value = t.role ?? "";
  } else {
    clearSelectedImages();
  }
});

/** 详情页打开且任务状态为「处理中」时定时刷新当前任务信息 */
watch(
  () => ({ task: selectedTask.value, status: selectedTask.value?.status }),
  ({ task, status }) => {
    if (processingPollTimer) {
      clearInterval(processingPollTimer);
      processingPollTimer = null;
    }
    if (task && status === "processing") {
      const poll = async () => {
        if (!selectedTask.value || selectedTask.value.status !== "processing") return;
        const taskId = selectedTask.value.task_id;
        try {
          const updated = await getTtsTask(taskId);
          // 仅当详情弹窗仍在该任务时更新 selectedTask，避免关闭弹窗后被轮询结果重新打开
          if (selectedTask.value?.task_id === taskId) {
            selectedTask.value = updated;
          }
          const idx = tasks.value.findIndex((t) => t.task_id === taskId);
          if (idx >= 0) tasks.value[idx] = updated;
        } catch {
          // 忽略单次刷新失败，下次轮询再试
        }
      };
      poll();
      processingPollTimer = setInterval(poll, PROCESSING_POLL_MS);
    }
  },
  { immediate: true }
);

onUnmounted(() => {
  if (processingPollTimer) clearInterval(processingPollTimer);
});

function getOcrImageUrl(index: number): string {
  return ocrImageUrls.value[index] ?? "";
}

function openOcrPreview(index: number) {
  previewOcrIndex.value = index;
}

function removeOcrImageInPreview() {
  if (previewOcrIndex.value < 0) return;
  removeOcrImage(previewOcrIndex.value);
}

function previewOcrPrev() {
  if (previewOcrIndex.value > 0) previewOcrIndex.value--;
}

function previewOcrNext() {
  if (previewOcrIndex.value < selectedImages.value.length - 1) previewOcrIndex.value++;
}

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

/** 关闭详情弹窗并停止刷新当前任务的定时器 */
function closeDetailModal() {
  if (processingPollTimer) {
    clearInterval(processingPollTimer);
    processingPollTimer = null;
  }
  selectedTask.value = null;
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

async function confirmDelete() {
  const task = selectedTask.value;
  if (!task) return;
  const alert = await alertController.create({
    header: "删除任务",
    message: `确定删除任务「${task.name || task.task_id}」吗？此操作不可恢复。`,
    buttons: [
      { text: "取消", role: "cancel" },
      {
        text: "删除",
        role: "destructive",
        handler: async () => {
          try {
            await deleteTtsTask(task.task_id);
            const idx = tasks.value.findIndex((t) => t.task_id === task.task_id);
            if (idx >= 0) tasks.value.splice(idx, 1);
            selectedTask.value = null;
            EventBus.$emit(C_EVENT.TOAST, "已删除");
          } catch (e: any) {
            EventBus.$emit(C_EVENT.TOAST, e?.message ?? "删除失败");
          }
        },
      },
    ],
  });
  await alert.present();
}

function openRenameDialog() {
  const task = selectedTask.value;
  if (!task) return;
  renameInputValue.value = task.name || task.task_id || "";
  renameModalOpen.value = true;
}

/** 把任务正文的第一行文字追加到改名输入框末尾 */
function appendFirstLineToRename() {
  const text = selectedTask.value?.text ?? "";
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

async function handleStartTask() {
  const task = selectedTask.value;
  if (!task) return;
  if (isTaskBusy.value || task.status === "processing" || generateVoiceLock.value) return;
  generateVoiceLock.value = true;
  try {
    await startTtsTask(task.task_id);
    EventBus.$emit(C_EVENT.TOAST, "任务已开始处理");
    await loadTasks();
    const updated = tasks.value.find((t) => t.task_id === task.task_id);
    if (updated) selectedTask.value = updated;
  } catch (e: any) {
    EventBus.$emit(C_EVENT.TOAST, e?.message ?? "启动任务失败");
  } finally {
    setTimeout(() => {
      generateVoiceLock.value = false;
    }, GENERATE_VOICE_LOCK_MS);
  }
}

async function runAnalysis() {
  const task = selectedTask.value;
  if (!task) return;
  try {
    await startTtsAnalysis(task.task_id);
    EventBus.$emit(C_EVENT.TOAST, "分析已启动，请稍后刷新查看结果");
  } catch (e: any) {
    EventBus.$emit(C_EVENT.TOAST, e?.message ?? "发起分析失败");
  }
}

async function handleDownloadTtsAudio() {
  if (downloadButtonLock.value) return;
  const task = selectedTask.value;
  if (!task) return;
  downloadButtonLock.value = true;
  try {
    const name = (task.name || task.task_id).replace(/[/\\?%*:|"<>]/g, "_");
    await downloadTtsAudio(task.task_id, `tts_${name}.mp3`);
    EventBus.$emit(C_EVENT.TOAST, "已开始下载");
  } catch (e: any) {
    EventBus.$emit(C_EVENT.TOAST, e?.message ?? "下载失败");
  } finally {
    setTimeout(() => {
      downloadButtonLock.value = false;
    }, DOWNLOAD_LOCK_MS);
  }
}

function pickImages() {
  imageInputRef.value?.click();
}

async function onImageFileChange(e: Event) {
  const input = e.target as HTMLInputElement;
  const files = input.files;
  if (!files?.length) {
    input.value = "";
    return;
  }
  try {
    const list = Array.from(files);
    const resized = await Promise.all(list.map((f) => resizeImageToFile(f)));
    resized.forEach((f) => {
      selectedImages.value.push(f);
      ocrImageUrls.value.push(URL.createObjectURL(f));
    });
  } catch (err: any) {
    EventBus.$emit(C_EVENT.TOAST, err?.message ?? "图片处理失败");
  } finally {
    input.value = "";
  }
}

function removeOcrImage(index: number) {
  if (ocrImageUrls.value[index]) {
    URL.revokeObjectURL(ocrImageUrls.value[index]);
  }
  ocrImageUrls.value.splice(index, 1);
  selectedImages.value.splice(index, 1);
  if (previewOcrIndex.value === index) {
    previewOcrIndex.value = -1;
  } else if (previewOcrIndex.value > index) {
    previewOcrIndex.value--;
  }
}

function clearSelectedImages() {
  ocrImageUrls.value.forEach((url) => URL.revokeObjectURL(url));
  ocrImageUrls.value = [];
  selectedImages.value = [];
  previewOcrIndex.value = -1;
  if (imageInputRef.value) imageInputRef.value.value = "";
}

async function runOcr() {
  const task = selectedTask.value;
  if (!task) return;
  if (selectedImages.value.length === 0) {
    EventBus.$emit(C_EVENT.TOAST, "请先选择图片");
    return;
  }
  if (isTaskBusy.value) {
    EventBus.$emit(C_EVENT.TOAST, "任务正在处理中或正在执行分析，无法执行识别");
    return;
  }
  try {
    ocrLoading.value = true;
    await ocrTtsTask(task.task_id, selectedImages.value);
    clearSelectedImages();
    EventBus.$emit(C_EVENT.TOAST, "识别已启动，结果将追加到任务文本，请稍后刷新");
    await loadTasks();
    const updated = tasks.value.find((t) => t.task_id === task.task_id);
    if (updated) selectedTask.value = updated;
  } catch (e: any) {
    EventBus.$emit(C_EVENT.TOAST, e?.message ?? "识别失败");
  } finally {
    ocrLoading.value = false;
  }
}

async function saveAndClose() {
  const task = selectedTask.value;
  if (!task) return;
  try {
    await updateTtsTask(task.task_id, {
      text: editText.value,
      role: editRole.value || undefined,
      speed: Number(editSpeed.value),
      vol: Number(editVol.value),
    });
    const t = tasks.value.find((x) => x.task_id === task.task_id);
    if (t) {
      t.text = editText.value;
      t.role = editRole.value || undefined;
      t.speed = Number(editSpeed.value);
      t.vol = Number(editVol.value);
    }
    if (selectedTask.value?.task_id === task.task_id) {
      selectedTask.value = {
        ...selectedTask.value,
        text: editText.value,
        role: editRole.value || undefined,
        speed: t?.speed ?? editSpeed.value,
        vol: t?.vol ?? editVol.value,
      };
    }
    EventBus.$emit(C_EVENT.TOAST, "已保存");
  } catch (e: any) {
    EventBus.$emit(C_EVENT.TOAST, e?.message ?? "保存失败");
  }
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

/** 点击添加按钮：创建新 TTS 任务并打开其详情弹窗（防短时间多点） */
async function createAndOpenTask() {
  if (addButtonCooling.value) return;
  addButtonCooling.value = true;
  try {
    const { task_id } = await createTtsTask({ text: "" });
    await loadTasks();
    const task = tasks.value.find((t) => t.task_id === task_id);
    if (task) selectedTask.value = task;
    else EventBus.$emit(C_EVENT.TOAST, "已创建，请从列表打开");
  } catch (e: any) {
    EventBus.$emit(C_EVENT.TOAST, e?.message ?? "创建失败");
  } finally {
    setTimeout(() => {
      addButtonCooling.value = false;
    }, ADD_COOLDOWN_MS);
  }
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

.ocr-image-list {
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.ocr-image-list::-webkit-scrollbar {
  display: none;
}
</style>
