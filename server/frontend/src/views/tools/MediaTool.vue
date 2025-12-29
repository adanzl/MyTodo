<template>
  <div class="flex gap-4 h-full">
    <!-- 左侧：任务列表 -->
    <div class="w-64 border rounded p-3 flex flex-col">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-base font-semibold">任务列表</h3>
        <div class="flex items-center gap-1">
          <el-button
            type="info"
            v-bind="smallIconButtonProps"
            @click="loadMediaTaskList"
            :loading="mediaLoading"
          >
            <el-icon v-if="!mediaLoading"><Refresh /></el-icon>
          </el-button>
          <el-button
            type="success"
            v-bind="smallIconButtonProps"
            @click="handleMediaCreateTask"
            :loading="mediaLoading"
          >
            <el-icon><Plus /></el-icon>
          </el-button>
        </div>
      </div>
      <div
        v-if="mediaTaskList && mediaTaskList.length > 0"
        class="flex-1 overflow-y-auto space-y-2 pr-1 min-h-[400px]"
      >
        <div
          v-for="task in mediaTaskList"
          :key="task.task_id"
          class="border rounded px-3 py-2 cursor-pointer hover:bg-gray-50 group min-h-[60px] flex flex-col justify-between"
          :class="{
            'border-blue-500 bg-blue-50':
              mediaCurrentTask && task.task_id === mediaCurrentTask.task_id,
          }"
          @click="handleMediaViewTask(task.task_id)"
        >
          <!-- 第一行：名称、文件数量 -->
          <div class="flex items-center justify-between gap-2">
            <div class="text-sm font-medium truncate flex-1 min-w-0">{{ task.name }}</div>
            <span
              class="text-xs text-gray-500 whitespace-nowrap flex items-center gap-1 flex-shrink-0"
            >
              <el-icon><Document class="!w-3 !h-3" /></el-icon>
              <span class="whitespace-nowrap w-5 flex items-center justify-center">{{
                task.files ? task.files.length : 0
              }}</span>
            </span>
          </div>
          <!-- 第二行：状态、下载按钮、删除按钮 -->
          <div class="flex items-center justify-between gap-2 min-h-[20px]">
            <el-tag
              :type="getMediaStatusTagType(task.status)"
              size="small"
              class="!h-5 !text-xs w-16 text-center"
            >
              {{ getMediaStatusText(task.status) }}
            </el-tag>
            <div class="flex items-center gap-1 flex-shrink-0">
              <el-button
                v-if="task.status === 'success' && task.result_file"
                type="primary"
                v-bind="smallTextButtonProps"
                @click.stop="handleMediaDownloadResultFromList(task)"
              >
                下载
              </el-button>
              <el-button
                type="danger"
                v-bind="smallTextButtonProps"
                @click.stop="handleMediaDeleteTask(task.task_id)"
                :disabled="task.status === 'processing'"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="flex-1 flex items-center justify-center text-sm text-gray-400">
        暂无任务，请点击"新建"创建
      </div>
    </div>

    <!-- 右侧：任务详情 -->
    <div class="flex-1 border rounded p-3 flex flex-col max-w-2xl" v-if="mediaCurrentTask">
      <div class="flex items-center justify-between mb-3 flex-shrink-0">
        <h3 class="text-base font-semibold">任务详情: {{ mediaCurrentTask.name }}</h3>
        <span class="text-sm text-gray-500"> 共 {{ filesCount }} 个文件 </span>
      </div>

      <div class="flex-1 overflow-auto flex flex-col gap-3">
        <!-- 任务信息 -->
        <div class="flex items-center justify-between gap-4 flex-shrink-0">
          <div class="flex items-center gap-4">
            <el-tag
              :type="getMediaStatusTagType(mediaCurrentTask.status)"
              size="small"
              class="w-16 text-center"
            >
              {{ getMediaStatusText(mediaCurrentTask.status) }}
            </el-tag>
            <MediaComponent
              v-if="resultFile"
              :file="resultFileObject"
              :player="mediaPlayer"
              :disabled="mediaFilesDragMode"
              @play="handleMediaTogglePlayResult"
              @seek="handleResultFileSeek"
            />
            <el-button
              type="primary"
              v-bind="mediumTextButtonProps"
              @click="handleMediaDownloadResult"
              :disabled="isResultActionDisabled"
            >
              下载
            </el-button>
            <el-button
              type="success"
              v-bind="mediumTextButtonProps"
              @click="handleMediaSaveResult"
              :disabled="isResultActionDisabled"
            >
              转存
            </el-button>
            <span v-if="mediaCurrentTask.error_message" class="text-red-500 text-xs">
              错误: {{ mediaCurrentTask.error_message }}
            </span>
          </div>
          <div class="flex items-center gap-2">
            <el-button
              type="success"
              v-bind="mediumTextButtonProps"
              @click="handleMediaStartMerge"
              :disabled="isStartMergeDisabled"
              :loading="isTaskProcessing"
            >
              开始合成
            </el-button>
          </div>
        </div>

        <!-- 文件列表 -->
        <div class="border rounded p-2 flex-1 flex flex-col overflow-hidden">
          <div class="flex items-center justify-between mb-2 flex-shrink-0">
            <h4 class="text-sm font-semibold">文件列表</h4>
            <div class="flex items-center gap-1 pr-1">
              <el-button
                type="primary"
                v-bind="smallTextButtonProps"
                :disabled="isFileOperationDisabled"
                @click="handleMediaOpenFileBrowser"
              >
                +
              </el-button>
              <el-button
                :type="mediaFilesDragMode ? 'success' : 'default'"
                v-bind="smallIconButtonProps"
                @click="handleMediaToggleFilesDragMode"
                :disabled="isDragModeButtonDisabled"
                :title="dragModeButtonTitle"
              >
                <el-icon v-if="mediaFilesDragMode"><Check /></el-icon>
                <i-ion-chevron-expand-sharp
                  v-else
                  class="!w-3.5 !h-3.5"
                ></i-ion-chevron-expand-sharp>
              </el-button>
            </div>
          </div>
          <div class="flex-1 overflow-auto">
            <div v-if="hasFiles">
              <div
                v-for="(file, index) in mediaCurrentTask.files"
                :key="index"
                class="flex items-center gap-2 p-1 hover:bg-gray-100 rounded"
                :class="{
                  'cursor-move': mediaFilesDragMode,
                  'cursor-default': !mediaFilesDragMode,
                  'select-none': true,
                }"
                :draggable="mediaFilesDragMode"
                @dragstart="handleMediaFileDragStart($event, Number(index))"
                @dragend="handleMediaFileDragEnd($event)"
                @dragover.prevent="handleMediaFileDragOver($event)"
                @dragleave="handleMediaFileDragLeave"
                @drop.prevent="handleMediaFileDrop($event, Number(index))"
              >
                <span class="text-xs text-gray-500 w-8">{{ Number(index) + 1 }}</span>
                <span class="flex-1 text-sm truncate" :title="file.path || file.name">
                  {{ file.name }}
                </span>
                <span
                  v-if="file.size"
                  class="text-xs text-gray-500 whitespace-nowrap w-20 text-right"
                >
                  {{ formatMediaFileSize(file.size) }}
                </span>
                <div v-else class="w-20"></div>
                <div class="flex items-center gap-1 flex-shrink-0" @mousedown.stop @click.stop>
                  <MediaComponent
                    :file="file"
                    :player="mediaPlayer"
                    :disabled="isFileOperationDisabled"
                    @play="() => handleMediaTogglePlayFile(Number(index))"
                    @seek="handleSeekFile"
                  />
                  <el-button
                    type="info"
                    size="small"
                    plain
                    circle
                    @click.stop="handleMediaRemoveFile(Number(index))"
                    :disabled="isFileOperationDisabled"
                    class="!h-6 !text-xs"
                  >
                    <el-icon><Minus /></el-icon>
                  </el-button>
                </div>
              </div>
            </div>
            <div v-else class="text-sm text-gray-400 text-center py-1">文件列表为空</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧：空状态 -->
    <div class="flex-1 border rounded p-3 flex flex-col max-w-2xl" v-else>
      <div class="flex items-center justify-between mb-3 flex-shrink-0">
        <h3 class="text-base font-semibold">任务详情</h3>
      </div>
      <div class="flex-1 flex items-center justify-center text-sm text-gray-400">
        请从左侧选择一个任务查看详情
      </div>
    </div>

    <!-- 文件对话框 -->
    <FileDialog
      :visible="mediaFileBrowserDialogVisible"
      @update:visible="mediaFileBrowserDialogVisible = $event"
      title="选择文件添加到任务"
      confirm-button-text="添加"
      :confirm-loading="mediaLoading"
      @confirm="handleMediaFileBrowserConfirm"
      @close="handleMediaCloseFileBrowser"
    >
    </FileDialog>

    <!-- 转存对话框 -->
    <FileDialog
      :visible="mediaSaveResultDialogVisible"
      @update:visible="mediaSaveResultDialogVisible = $event"
      title="选择转存目录"
      confirm-button-text="转存"
      mode="directory"
      :confirm-loading="mediaLoading"
      @confirm="handleMediaSaveResultConfirm"
      @close="mediaSaveResultDialogVisible = false"
    >
    </FileDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh, Plus, Document, Delete, Check, Minus } from "@element-plus/icons-vue";
import FileDialog from "@/components/dialogs/FileDialog.vue";
import MediaComponent from "@/components/common/MediaComponent.vue";
import { formatSize } from "@/utils/format";
import { getMediaFileUrl } from "@/utils/file";
import { logAndNoticeError } from "@/utils/error";
import { useAudioPlayer } from "@/composables/useAudioPlayer";
import { useControllableInterval } from "@/composables/useInterval";
import { MEDIA_TASK_POLLING_INTERVAL } from "@/constants/media";
import type { MediaTaskDetail, MediaFile } from "@/types/tools";
import {
  getMediaTaskList,
  createMediaTask,
  getMediaTask,
  deleteMediaTask,
  addFileToMediaTask,
  deleteFileFromMediaTask,
  startMediaTask,
  reorderMediaTaskFiles,
  getMediaTaskDownloadUrl,
  saveMediaTaskResult,
  type MediaTask,
} from "@/api/media";

// 音频合成相关状态
const mediaLoading = ref(false);
const mediaTaskList = ref<MediaTask[]>([]);
const mediaCurrentTask = ref<MediaTaskDetail | null>(null);
const mediaFileBrowserDialogVisible = ref(false);
const mediaSaveResultDialogVisible = ref(false);
const mediaFilesDragMode = ref(false);
const mediaFilesOriginalOrder = ref<MediaFile[] | null>(null);

// 统一的播放器相关状态
const mediaPlayer = useAudioPlayer({
  callbacks: {
    onPlay: () => {
      ElMessage.success("开始播放");
    },
    onError: () => {
      logAndNoticeError(new Error("音频播放失败"), "播放失败");
      clearBrowserAudioPlayer();
    },
    onEnded: () => {
      clearBrowserAudioPlayer();
    },
  },
});

// 按钮公共属性
const smallIconButtonProps = { size: "small" as const, plain: true, class: "!w-8 !h-6 !p-0" };
const smallTextButtonProps = { size: "small" as const, plain: true, class: "!h-5 !text-xs !px-2" };
const mediumTextButtonProps = { size: "small" as const, plain: true, class: "!h-7 !text-xs" };

// 拖拽样式类名常量
const DRAG_STYLE_CLASSES = ["bg-gray-100", "border-t-2", "border-b-2", "border-blue-500"];

// 清除拖拽样式
const clearDragStyles = (element: HTMLElement) => {
  if (element) {
    element.classList.remove(...DRAG_STYLE_CLASSES);
  }
};

// 清除所有拖拽项的样式
const clearAllDragStyles = (parentElement: HTMLElement | null) => {
  if (!parentElement) return;
  const allItems = parentElement.querySelectorAll('[draggable="true"]');
  allItems.forEach(item => clearDragStyles(item as HTMLElement));
};

// 处理媒体工具文件选择确认
const handleMediaFileBrowserConfirm = async (filePaths: string[]) => {
  if (!mediaCurrentTask.value) {
    return;
  }

  if (filePaths.length === 0) {
    return;
  }

  try {
    mediaLoading.value = true;
    for (const filePath of filePaths) {
      const response = await addFileToMediaTask(mediaCurrentTask.value.task_id, filePath);

      if (response.code !== 0) {
        ElMessage.error(`添加文件失败: ${response.msg || "未知错误"}`);
        break;
      }
    }

    ElMessage.success(`成功添加 ${filePaths.length} 个文件`);
    await handleMediaViewTask(mediaCurrentTask.value.task_id);
  } catch (error) {
    logAndNoticeError(error as Error, "添加文件失败");
  } finally {
    mediaLoading.value = false;
  }
};

// 加载媒体任务列表
const loadMediaTaskList = async () => {
  try {
    mediaLoading.value = true;
    const response = await getMediaTaskList();
    if (response.code === 0) {
      mediaTaskList.value = response.data.tasks || [];
      if (mediaTaskList.value.length > 0 && !mediaCurrentTask.value) {
        await handleMediaViewTask(mediaTaskList.value[0].task_id);
      }
    } else {
      ElMessage.error(response.msg || "获取任务列表失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "获取任务列表失败");
  } finally {
    mediaLoading.value = false;
  }
};

// 创建媒体任务
const handleMediaCreateTask = async () => {
  try {
    mediaLoading.value = true;
    const response = await createMediaTask();

    if (response.code === 0) {
      ElMessage.success("任务创建成功");
      await loadMediaTaskList();
      handleMediaViewTask(response.data.task_id);
    } else {
      ElMessage.error(response.msg || "创建任务失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "创建任务失败");
  } finally {
    mediaLoading.value = false;
  }
};

// 查看媒体任务
const handleMediaViewTask = async (taskId: string) => {
  if (mediaCurrentTask.value && mediaCurrentTask.value.task_id !== taskId) {
    handleMediaStopPlay();
  }
  try {
    mediaLoading.value = true;
    const response = await getMediaTask(taskId);
    if (response.code === 0) {
      mediaCurrentTask.value = response.data;
    } else {
      ElMessage.error(response.msg || "获取任务信息失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "获取任务信息失败");
  } finally {
    mediaLoading.value = false;
  }
};

// 删除媒体任务
const handleMediaDeleteTask = async (taskId: string) => {
  const confirmed = await ElMessageBox.confirm("确定要删除该任务吗？", "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).catch(() => false);

  if (!confirmed) return;

  try {
    mediaLoading.value = true;
    const response = await deleteMediaTask(taskId);
    if (response.code === 0) {
      ElMessage.success("任务删除成功");
      await loadMediaTaskList();
      if (mediaCurrentTask.value && mediaCurrentTask.value.task_id === taskId) {
        if (mediaTaskList.value && mediaTaskList.value.length > 0) {
          await handleMediaViewTask(mediaTaskList.value[0].task_id);
        } else {
          mediaCurrentTask.value = null;
        }
      }
    } else {
      ElMessage.error(response.msg || "删除任务失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "删除任务失败");
  } finally {
    mediaLoading.value = false;
  }
};

// 打开媒体文件浏览器
const handleMediaOpenFileBrowser = () => {
  if (!mediaCurrentTask.value) {
    ElMessage.warning("请先创建或选择任务");
    return;
  }
  mediaFileBrowserDialogVisible.value = true;
};

// 移除媒体文件
const handleMediaRemoveFile = async (fileIndex: number) => {
  if (!mediaCurrentTask.value) {
    return;
  }

  const confirmed = await ElMessageBox.confirm("确定要删除该文件吗？", "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).catch(() => false);

  if (!confirmed) return;

  try {
    mediaLoading.value = true;
    const response = await deleteFileFromMediaTask(mediaCurrentTask.value.task_id, fileIndex);
    if (response.code === 0) {
      if (mediaPlayer.playingFileIndex.value === fileIndex) {
        handleMediaStopPlay();
      } else if (
        mediaPlayer.playingFileIndex.value !== null &&
        mediaPlayer.playingFileIndex.value > fileIndex
      ) {
        mediaPlayer.playingFileIndex.value = mediaPlayer.playingFileIndex.value - 1;
      }
      ElMessage.success("文件删除成功");
      await handleMediaViewTask(mediaCurrentTask.value.task_id);
    } else {
      ElMessage.error(response.msg || "删除文件失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "删除文件失败");
  } finally {
    mediaLoading.value = false;
  }
};

// 开始媒体合成
const handleMediaStartMerge = async () => {
  if (!mediaCurrentTask.value) {
    return;
  }

  const confirmed = await ElMessageBox.confirm(
    `确定要开始合成吗？将合并 ${filesCount.value} 个音频文件。`,
    "确认合成",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    }
  ).catch(() => false);

  if (!confirmed) return;

  try {
    mediaLoading.value = true;
    const response = await startMediaTask(mediaCurrentTask.value.task_id);
    if (response.code === 0) {
      ElMessage.success("合成任务已启动");
      await loadMediaTaskList();
      await handleMediaViewTask(mediaCurrentTask.value.task_id);
      startMediaPollingTaskStatus();
    } else {
      ElMessage.error(response.msg || "启动任务失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "启动任务失败");
  } finally {
    mediaLoading.value = false;
  }
};

// 轮询媒体任务状态
const { start: startMediaPolling, stop: stopMediaPolling } = useControllableInterval(
  async () => {
    if (!mediaCurrentTask.value || mediaCurrentTask.value.status !== "processing") {
      stopMediaPolling();
      return;
    }
    await loadMediaTaskList();
    await handleMediaViewTask(mediaCurrentTask.value.task_id);
  },
  MEDIA_TASK_POLLING_INTERVAL,
  { immediate: false }
);

const startMediaPollingTaskStatus = () => {
  startMediaPolling();
};

// 下载媒体结果（通用函数）
const downloadMediaResult = (taskId: string) => {
  if (!taskId) return;
  const url = getMediaTaskDownloadUrl(taskId);
  window.open(url, "_blank");
};

// 下载媒体结果
const handleMediaDownloadResult = () => {
  if (!mediaCurrentTask.value?.result_file) return;
  downloadMediaResult(mediaCurrentTask.value.task_id);
};

// 从任务列表下载媒体结果
const handleMediaDownloadResultFromList = (task: MediaTask) => {
  if (!task?.result_file) return;
  downloadMediaResult(task.task_id);
};

// 清理浏览器音频播放器状态（统一清理所有播放）
const clearBrowserAudioPlayer = () => {
  mediaPlayer.clear();
};

// 注意：这些函数已不再使用，因为 MediaComponent 现在直接使用 player 对象
// 保留它们是为了向后兼容，如果其他代码还在使用的话

// 处理文件进度条拖拽
const handleSeekFile = (fileItem: MediaFile, percentage: number) => {
  if (!fileItem) return;
  const filePath = fileItem?.path || fileItem?.name || "";
  mediaPlayer.seekFile(filePath, percentage);
};

// 处理结果文件进度条拖拽
const handleResultFileSeek = (_file: MediaFile, percentage: number) => {
  if (!mediaCurrentTask.value?.result_file) return;
  handleSeekFile({ path: mediaCurrentTask.value.result_file }, percentage);
};

// 播放/暂停媒体文件
const handleMediaTogglePlayFile = (index: number) => {
  if (
    !mediaCurrentTask.value ||
    !mediaCurrentTask.value.files ||
    index < 0 ||
    index >= mediaCurrentTask.value.files.length
  ) {
    return;
  }

  const file = mediaCurrentTask.value.files[index];
  const filePath = file.path || file.name || "";
  if (!filePath) {
    ElMessage.warning("文件路径不存在");
    return;
  }

  // 如果点击的是正在播放的文件，则停止播放
  if (
    mediaPlayer.playingFilePath.value === filePath &&
    mediaPlayer.audio &&
    !mediaPlayer.audio.paused
  ) {
    clearBrowserAudioPlayer();
    ElMessage.info("已停止播放");
    return;
  }

  const audioUrl = getMediaFileUrl(filePath);
  if (!audioUrl) {
    ElMessage.error("无法生成媒体文件URL");
    return;
  }

  // 加载/更换播放文件
  mediaPlayer.load(audioUrl, {
    playingFilePath: filePath,
    playingFileIndex: index,
  });

  // 开始播放
  mediaPlayer.play().catch(error => {
    logAndNoticeError(error as Error, "播放失败");
    clearBrowserAudioPlayer();
  });
};

// 停止媒体播放（统一清理所有播放）
const handleMediaStopPlay = () => {
  clearBrowserAudioPlayer();
};

// 播放/暂停媒体结果文件（使用统一的播放器）
const handleMediaTogglePlayResult = () => {
  if (!mediaCurrentTask.value || !mediaCurrentTask.value.result_file) {
    ElMessage.warning("结果文件不存在");
    return;
  }

  const resultFilePath = mediaCurrentTask.value.result_file;

  // 如果点击的是正在播放的结果文件，则停止播放
  if (
    mediaPlayer.playingFilePath.value === resultFilePath &&
    mediaPlayer.audio &&
    !mediaPlayer.audio.paused
  ) {
    clearBrowserAudioPlayer();
    ElMessage.info("已停止播放");
    return;
  }

  const audioUrl = getMediaFileUrl(resultFilePath);
  if (!audioUrl) {
    ElMessage.error("无法生成媒体文件URL");
    return;
  }

  // 加载/更换播放文件
  mediaPlayer.load(audioUrl, {
    playingFilePath: resultFilePath,
  });

  // 开始播放
  mediaPlayer.play().catch(error => {
    logAndNoticeError(error as Error, "播放失败");
    clearBrowserAudioPlayer();
  });
};

// 转存媒体结果文件
const handleMediaSaveResult = () => {
  if (!mediaCurrentTask.value || !mediaCurrentTask.value.result_file) {
    ElMessage.warning("结果文件不存在");
    return;
  }
  mediaSaveResultDialogVisible.value = true;
};

// 处理媒体转存确认
const handleMediaSaveResultConfirm = async (filePaths: string[]) => {
  if (!mediaCurrentTask.value || !mediaCurrentTask.value.result_file) {
    return;
  }

  if (filePaths.length === 0) {
    ElMessage.warning("请选择转存目录");
    return;
  }

  const targetDir = filePaths[0];

  try {
    mediaLoading.value = true;
    const response = await saveMediaTaskResult(mediaCurrentTask.value.task_id, targetDir);

    if (response.code === 0) {
      ElMessage.success("转存成功");
      mediaSaveResultDialogVisible.value = false;
    } else {
      ElMessage.error(response.msg || "转存失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "转存失败");
  } finally {
    mediaLoading.value = false;
  }
};

// 格式化媒体文件大小（使用统一的 formatSize 函数）
const formatMediaFileSize = formatSize;

// 媒体状态映射
const MEDIA_STATUS_MAP: Record<string, { tag: string; text: string }> = {
  pending: { tag: "info", text: "等待中" },
  processing: { tag: "warning", text: "处理中" },
  success: { tag: "success", text: "成功" },
  failed: { tag: "danger", text: "失败" },
};

// 获取媒体状态标签类型
const getMediaStatusTagType = (status: string): string => {
  return MEDIA_STATUS_MAP[status]?.tag || "info";
};

// 获取媒体状态文本
const getMediaStatusText = (status: string): string => {
  return MEDIA_STATUS_MAP[status]?.text || "未知";
};

// 计算属性
const isTaskProcessing = computed(() => mediaCurrentTask.value?.status === "processing");
const hasFiles = computed(() => (mediaCurrentTask.value?.files || []).length > 0);
const filesCount = computed(() => (mediaCurrentTask.value?.files || []).length);
const resultFile = computed(() => mediaCurrentTask.value?.result_file);
const isResultActionDisabled = computed(
  () =>
    !resultFile.value || mediaCurrentTask.value?.status !== "success" || mediaFilesDragMode.value
);
const isStartMergeDisabled = computed(
  () => !hasFiles.value || isTaskProcessing.value || mediaFilesDragMode.value
);
const isFileOperationDisabled = computed(() => isTaskProcessing.value || mediaFilesDragMode.value);
const isDragModeButtonDisabled = computed(
  () => !mediaCurrentTask.value || !hasFiles.value || isTaskProcessing.value
);
const dragModeButtonTitle = computed(() =>
  mediaFilesDragMode.value ? "点击退出拖拽排序模式" : "点击进入拖拽排序模式"
);
const resultFileObject = computed(() => ({ path: resultFile.value || "" }));

// 检查媒体文件顺序是否改变
const isMediaOrderChanged = (original: MediaFile[], current: MediaFile[]): boolean => {
  if (!original || !current || original.length !== current.length) {
    return true;
  }
  return original.some((item, i) => {
    const origPath = item?.path || item?.name;
    const currPath = current[i]?.path || current[i]?.name;
    return origPath !== currPath;
  });
};

// 切换媒体文件拖拽排序模式
const handleMediaToggleFilesDragMode = async () => {
  if (mediaFilesDragMode.value) {
    if (
      mediaCurrentTask.value &&
      mediaCurrentTask.value.files &&
      mediaCurrentTask.value.files.length > 0
    ) {
      const hasChanged = isMediaOrderChanged(
        mediaFilesOriginalOrder.value || [],
        mediaCurrentTask.value.files
      );
      if (hasChanged) {
        try {
          mediaLoading.value = true;
          const fileIndices = mediaCurrentTask.value.files.map((_, index: number) => index);
          const response = await reorderMediaTaskFiles(mediaCurrentTask.value.task_id, fileIndices);

          if (response.code === 0) {
            ElMessage.success("排序已保存");
            await handleMediaViewTask(mediaCurrentTask.value.task_id);
          } else {
            ElMessage.error(response.msg || "保存排序失败");
          }
        } catch (error) {
          logAndNoticeError(error as Error, "保存排序失败");
        } finally {
          mediaLoading.value = false;
        }
      }
      mediaFilesOriginalOrder.value = null;
    }
  } else {
    if (
      mediaCurrentTask.value &&
      mediaCurrentTask.value.files &&
      mediaCurrentTask.value.files.length > 0
    ) {
      mediaFilesOriginalOrder.value = [...(mediaCurrentTask.value.files || [])];
    }
  }
  mediaFilesDragMode.value = !mediaFilesDragMode.value;
};

// 处理媒体文件拖拽开始
const handleMediaFileDragStart = (event: DragEvent, index: number) => {
  if (!mediaFilesDragMode.value) {
    event.preventDefault();
    return false;
  }
  try {
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", index.toString());
    }
  } catch (e) {
    console.error("拖拽开始失败:", e);
  }
};

// 处理媒体文件拖拽结束
const handleMediaFileDragEnd = (event: DragEvent) => {
  if (event.currentTarget) {
    clearDragStyles(event.currentTarget as HTMLElement);
  }
};

// 处理媒体文件拖拽离开
const handleMediaFileDragLeave = (event: DragEvent) => {
  if (event.currentTarget) {
    clearDragStyles(event.currentTarget as HTMLElement);
  }
};

// 处理媒体文件拖拽悬停
const handleMediaFileDragOver = (event: DragEvent) => {
  if (!mediaFilesDragMode.value) {
    return;
  }
  event.preventDefault();
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = "move";
  }
  if (event.currentTarget) {
    const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
    const mouseY = event.clientY;
    const elementCenterY = rect.top + rect.height / 2;

    clearDragStyles(event.currentTarget as HTMLElement);

    if (mouseY < elementCenterY) {
      (event.currentTarget as HTMLElement).classList.add("border-t-2", "border-blue-500");
    } else {
      (event.currentTarget as HTMLElement).classList.add("border-b-2", "border-blue-500");
    }
  }
};

// 处理媒体文件拖拽放置
const handleMediaFileDrop = (event: DragEvent, targetIndex: number) => {
  if (!mediaFilesDragMode.value) {
    return;
  }
  event.preventDefault();
  if (event.currentTarget) {
    clearDragStyles(event.currentTarget as HTMLElement);
    clearAllDragStyles((event.currentTarget as HTMLElement).parentElement);
  }

  if (!event.dataTransfer) return;
  const sourceIndex = parseInt(event.dataTransfer.getData("text/plain"), 10);

  if (sourceIndex === targetIndex || isNaN(sourceIndex)) {
    return;
  }

  if (
    !mediaCurrentTask.value ||
    !mediaCurrentTask.value.files ||
    sourceIndex < 0 ||
    sourceIndex >= mediaCurrentTask.value.files.length ||
    targetIndex < 0 ||
    targetIndex >= mediaCurrentTask.value.files.length
  ) {
    return;
  }

  // 计算插入位置
  const rect = (event.currentTarget as HTMLElement)?.getBoundingClientRect();
  const mouseY = event.clientY;
  const elementCenterY = rect ? rect.top + rect.height / 2 : 0;
  const insertIndex = mouseY < elementCenterY ? targetIndex : targetIndex + 1;

  // 重新排序文件列表
  const list = [...(mediaCurrentTask.value.files || [])];
  const [removed] = list.splice(sourceIndex, 1);
  const adjustedIndex = sourceIndex < insertIndex ? insertIndex - 1 : insertIndex;
  list.splice(adjustedIndex, 0, removed);

  mediaCurrentTask.value = {
    ...mediaCurrentTask.value,
    files: list,
  };
};

// 关闭文件浏览器
const handleMediaCloseFileBrowser = () => {
  mediaFileBrowserDialogVisible.value = false;
};

onMounted(() => {
  loadMediaTaskList();
});

onUnmounted(() => {
  handleMediaStopPlay();
  // useInterval 会自动清理，但显式调用更安全
  stopMediaPolling();
});
</script>
