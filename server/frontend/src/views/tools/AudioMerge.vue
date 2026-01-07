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
            @click="loadAudioMergeTaskList"
            :loading="audioMergeLoading"
          >
            <el-icon v-if="!audioMergeLoading"><Refresh /></el-icon>
          </el-button>
          <el-button
            type="success"
            v-bind="smallIconButtonProps"
            @click="handleAudioMergeCreateTask"
            :loading="audioMergeLoading"
          >
            <el-icon><Plus /></el-icon>
          </el-button>
        </div>
      </div>
      <div
        v-if="audioMergeTaskList && audioMergeTaskList.length > 0"
        class="flex-1 overflow-y-auto space-y-2 pr-1 min-h-[400px]"
      >
        <div
          v-for="task in audioMergeTaskList"
          :key="task.task_id"
          class="border rounded px-3 py-2 cursor-pointer hover:bg-gray-50 group min-h-[60px] flex flex-col justify-between"
          :class="{
            'border-blue-500 bg-blue-50':
              audioMergeCurrentTask && task.task_id === audioMergeCurrentTask.task_id,
          }"
          @click="handleAudioMergeViewTask(task.task_id)"
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
              :type="getAudioMergeStatusTagType(task.status)"
              size="small"
              class="!h-5 !text-xs w-16 text-center"
            >
              {{ getAudioMergeStatusText(task.status) }}
            </el-tag>
            <div class="flex items-center gap-1 flex-shrink-0">
              <el-button
                v-if="task.status === 'success' && task.result_file"
                type="primary"
                v-bind="smallTextButtonProps"
                @click.stop="handleAudioMergeDownloadResultFromList(task)"
              >
                下载
              </el-button>
              <el-button
                type="danger"
                v-bind="smallTextButtonProps"
                @click.stop="handleAudioMergeDeleteTask(task.task_id)"
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
    <div class="flex-1 border rounded p-3 flex flex-col max-w-2xl" v-if="audioMergeCurrentTask">
      <div class="flex items-center justify-between mb-3 flex-shrink-0">
        <h3 class="text-base font-semibold">任务详情: {{ audioMergeCurrentTask.name }}</h3>
        <span class="text-sm text-gray-500"> 共 {{ filesCount }} 个文件 </span>
      </div>

      <div class="flex-1 overflow-auto flex flex-col gap-3">
        <!-- 任务信息 -->
        <div class="flex items-center justify-between gap-4 flex-shrink-0">
          <div class="flex items-center gap-4">
            <el-tag
              :type="getAudioMergeStatusTagType(audioMergeCurrentTask.status)"
              size="small"
              class="w-16 text-center"
            >
              {{ getAudioMergeStatusText(audioMergeCurrentTask.status) }}
            </el-tag>
            <MediaComponent
              v-if="resultFile"
              :file="resultFileObject"
              :player="audioMergePlayer"
              :disabled="audioMergeFilesDragMode"
              @play="handleAudioMergeTogglePlayResult"
              @seek="handleResultFileSeek"
            />
            <el-button
              type="primary"
              v-bind="mediumTextButtonProps"
              @click="handleAudioMergeDownloadResult"
              :disabled="isResultActionDisabled"
            >
              下载
            </el-button>
            <el-button
              type="success"
              v-bind="mediumTextButtonProps"
              @click="handleAudioMergeSaveResult"
              :disabled="isResultActionDisabled"
            >
              转存
            </el-button>
            <span v-if="audioMergeCurrentTask.error_message" class="text-red-500 text-xs">
              错误: {{ audioMergeCurrentTask.error_message }}
            </span>
          </div>
          <div class="flex items-center gap-2">
            <el-button
              type="success"
              v-bind="mediumTextButtonProps"
              @click="handleAudioMergeStartMerge"
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
                @click="handleAudioMergeOpenFileBrowser"
              >
                +
              </el-button>
              <el-button
                :type="audioMergeFilesDragMode ? 'success' : 'default'"
                v-bind="smallIconButtonProps"
                @click="handleAudioMergeToggleFilesDragMode"
                :disabled="isDragModeButtonDisabled"
                :title="dragModeButtonTitle"
              >
                <el-icon v-if="audioMergeFilesDragMode"><Check /></el-icon>
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
                v-for="(file, index) in audioMergeCurrentTask.files"
                :key="index"
                class="flex items-center gap-2 p-1 hover:bg-gray-100 rounded"
                :class="{
                  'cursor-move': audioMergeFilesDragMode,
                  'cursor-default': !audioMergeFilesDragMode,
                  'select-none': true,
                }"
                :draggable="audioMergeFilesDragMode"
                @dragstart="handleAudioMergeFileDragStart($event, Number(index))"
                @dragend="handleAudioMergeFileDragEnd($event)"
                @dragover.prevent="handleAudioMergeFileDragOver($event)"
                @dragleave="handleAudioMergeFileDragLeave"
                @drop.prevent="handleAudioMergeFileDrop($event, Number(index))"
              >
                <span class="text-xs text-gray-500 w-8">{{ Number(index) + 1 }}</span>
                <span class="flex-1 text-sm truncate" :title="file.path || file.name">
                  {{ file.name }}
                </span>
                <span
                  v-if="file.size"
                  class="text-xs text-gray-500 whitespace-nowrap w-20 text-right"
                >
                  {{ formatAudioMergeFileSize(file.size) }}
                </span>
                <div v-else class="w-20"></div>
                <div class="flex items-center gap-1 flex-shrink-0" @mousedown.stop @click.stop>
                  <MediaComponent
                    :file="file"
                    :player="audioMergePlayer"
                    :disabled="isFileOperationDisabled"
                    @play="() => handleAudioMergeTogglePlayFile(Number(index))"
                    @seek="handleSeekFile"
                  />
                  <el-button
                    type="info"
                    size="small"
                    plain
                    circle
                    @click.stop="handleAudioMergeRemoveFile(Number(index))"
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
      :visible="audioMergeFileBrowserDialogVisible"
      @update:visible="audioMergeFileBrowserDialogVisible = $event"
      title="选择文件添加到任务"
      confirm-button-text="添加"
      :confirm-loading="audioMergeLoading"
      @confirm="handleAudioMergeFileBrowserConfirm"
      @close="handleAudioMergeCloseFileBrowser"
    >
    </FileDialog>

    <!-- 转存对话框 -->
    <FileDialog
      :visible="audioMergeSaveResultDialogVisible"
      @update:visible="audioMergeSaveResultDialogVisible = $event"
      title="选择转存目录"
      confirm-button-text="转存"
      mode="directory"
      :confirm-loading="audioMergeLoading"
      @confirm="handleAudioMergeSaveResultConfirm"
      @close="audioMergeSaveResultDialogVisible = false"
    >
    </FileDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh, Plus, Document, Delete, Check, Minus } from "@element-plus/icons-vue";
import FileDialog from "@/views/dialogs/FileDialog.vue";
import MediaComponent from "@/components/MediaComponent.vue";
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
} from "@/api/audioMerge";

// 音频合成相关状态
const audioMergeLoading = ref(false);
const audioMergeTaskList = ref<MediaTask[]>([]);
const audioMergeCurrentTask = ref<MediaTaskDetail | null>(null);
const audioMergeFileBrowserDialogVisible = ref(false);
const audioMergeSaveResultDialogVisible = ref(false);
const audioMergeFilesDragMode = ref(false);
const audioMergeFilesOriginalOrder = ref<MediaFile[] | null>(null);

// 统一的播放器相关状态
const audioMergePlayer = useAudioPlayer({
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

// 处理音频合成文件选择确认
const handleAudioMergeFileBrowserConfirm = async (filePaths: string[]) => {
  if (!audioMergeCurrentTask.value) {
    return;
  }

  if (filePaths.length === 0) {
    return;
  }

  try {
    audioMergeLoading.value = true;
    for (const filePath of filePaths) {
      const response = await addFileToMediaTask(audioMergeCurrentTask.value.task_id, filePath);

      if (response.code !== 0) {
        ElMessage.error(`添加文件失败: ${response.msg || "未知错误"}`);
        break;
      }
    }

    ElMessage.success(`成功添加 ${filePaths.length} 个文件`);
    await handleAudioMergeViewTask(audioMergeCurrentTask.value.task_id);
  } catch (error) {
    logAndNoticeError(error as Error, "添加文件失败");
  } finally {
    audioMergeLoading.value = false;
  }
};

// 加载音频合成任务列表
const loadAudioMergeTaskList = async () => {
  try {
    audioMergeLoading.value = true;
    const response = await getMediaTaskList();
    if (response.code === 0) {
      audioMergeTaskList.value = response.data.tasks || [];
      if (audioMergeTaskList.value.length > 0 && !audioMergeCurrentTask.value) {
        await handleAudioMergeViewTask(audioMergeTaskList.value[0].task_id);
      }
    } else {
      ElMessage.error(response.msg || "获取任务列表失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "获取任务列表失败");
  } finally {
    audioMergeLoading.value = false;
  }
};

// 创建音频合成任务
const handleAudioMergeCreateTask = async () => {
  try {
    audioMergeLoading.value = true;
    const response = await createMediaTask();

    if (response.code === 0) {
      ElMessage.success("任务创建成功");
      await loadAudioMergeTaskList();
      handleAudioMergeViewTask(response.data.task_id);
    } else {
      ElMessage.error(response.msg || "创建任务失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "创建任务失败");
  } finally {
    audioMergeLoading.value = false;
  }
};

// 查看音频合成任务
const handleAudioMergeViewTask = async (taskId: string) => {
  if (audioMergeCurrentTask.value && audioMergeCurrentTask.value.task_id !== taskId) {
    handleAudioMergeStopPlay();
  }
  try {
    audioMergeLoading.value = true;
    const response = await getMediaTask(taskId);
    if (response.code === 0) {
      audioMergeCurrentTask.value = response.data;
    } else {
      ElMessage.error(response.msg || "获取任务信息失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "获取任务信息失败");
  } finally {
    audioMergeLoading.value = false;
  }
};

// 删除音频合成任务
const handleAudioMergeDeleteTask = async (taskId: string) => {
  const confirmed = await ElMessageBox.confirm("确定要删除该任务吗？", "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).catch(() => false);

  if (!confirmed) return;

  try {
    audioMergeLoading.value = true;
    const response = await deleteMediaTask(taskId);
    if (response.code === 0) {
      ElMessage.success("任务删除成功");
      await loadAudioMergeTaskList();
      if (audioMergeCurrentTask.value && audioMergeCurrentTask.value.task_id === taskId) {
        if (audioMergeTaskList.value && audioMergeTaskList.value.length > 0) {
          await handleAudioMergeViewTask(audioMergeTaskList.value[0].task_id);
        } else {
          audioMergeCurrentTask.value = null;
        }
      }
    } else {
      ElMessage.error(response.msg || "删除任务失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "删除任务失败");
  } finally {
    audioMergeLoading.value = false;
  }
};

// 打开音频合成文件浏览器
const handleAudioMergeOpenFileBrowser = () => {
  if (!audioMergeCurrentTask.value) {
    ElMessage.warning("请先创建或选择任务");
    return;
  }
  audioMergeFileBrowserDialogVisible.value = true;
};

// 移除音频合成文件
const handleAudioMergeRemoveFile = async (fileIndex: number) => {
  if (!audioMergeCurrentTask.value) {
    return;
  }

  const confirmed = await ElMessageBox.confirm("确定要删除该文件吗？", "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).catch(() => false);

  if (!confirmed) return;

  try {
    audioMergeLoading.value = true;
    const response = await deleteFileFromMediaTask(audioMergeCurrentTask.value.task_id, fileIndex);
    if (response.code === 0) {
      if (audioMergePlayer.playingFileIndex.value === fileIndex) {
        handleAudioMergeStopPlay();
      } else if (
        audioMergePlayer.playingFileIndex.value !== null &&
        audioMergePlayer.playingFileIndex.value > fileIndex
      ) {
        audioMergePlayer.playingFileIndex.value = audioMergePlayer.playingFileIndex.value - 1;
      }
      ElMessage.success("文件删除成功");
      await handleAudioMergeViewTask(audioMergeCurrentTask.value.task_id);
    } else {
      ElMessage.error(response.msg || "删除文件失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "删除文件失败");
  } finally {
    audioMergeLoading.value = false;
  }
};

// 开始音频合成
const handleAudioMergeStartMerge = async () => {
  if (!audioMergeCurrentTask.value) {
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
    audioMergeLoading.value = true;
    const response = await startMediaTask(audioMergeCurrentTask.value.task_id);
    if (response.code === 0) {
      ElMessage.success("合成任务已启动");
      await loadAudioMergeTaskList();
      await handleAudioMergeViewTask(audioMergeCurrentTask.value.task_id);
      startAudioMergePollingTaskStatus();
    } else {
      ElMessage.error(response.msg || "启动任务失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "启动任务失败");
  } finally {
    audioMergeLoading.value = false;
  }
};

// 轮询音频合成任务状态
const { start: startAudioMergePolling, stop: stopAudioMergePolling } = useControllableInterval(
  async () => {
    if (!audioMergeCurrentTask.value || audioMergeCurrentTask.value.status !== "processing") {
      stopAudioMergePolling();
      return;
    }
    await loadAudioMergeTaskList();
    await handleAudioMergeViewTask(audioMergeCurrentTask.value.task_id);
  },
  MEDIA_TASK_POLLING_INTERVAL,
  { immediate: false }
);

const startAudioMergePollingTaskStatus = () => {
  startAudioMergePolling();
};

// 下载音频合成结果（通用函数）
const downloadAudioMergeResult = (taskId: string) => {
  if (!taskId) return;
  const url = getMediaTaskDownloadUrl(taskId);
  window.open(url, "_blank");
};

// 下载音频合成结果
const handleAudioMergeDownloadResult = () => {
  if (!audioMergeCurrentTask.value?.result_file) return;
  downloadAudioMergeResult(audioMergeCurrentTask.value.task_id);
};

// 从任务列表下载音频合成结果
const handleAudioMergeDownloadResultFromList = (task: MediaTask) => {
  if (!task?.result_file) return;
  downloadAudioMergeResult(task.task_id);
};

// 清理浏览器音频播放器状态（统一清理所有播放）
const clearBrowserAudioPlayer = () => {
  audioMergePlayer.clear();
};

// 注意：这些函数已不再使用，因为 MediaComponent 现在直接使用 player 对象
// 保留它们是为了向后兼容，如果其他代码还在使用的话

// 处理文件进度条拖拽
const handleSeekFile = (fileItem: MediaFile, percentage: number) => {
  if (!fileItem) return;
  const filePath = fileItem?.path || fileItem?.name || "";
  audioMergePlayer.seekFile(filePath, percentage);
};

// 处理结果文件进度条拖拽
const handleResultFileSeek = (_file: MediaFile, percentage: number) => {
  if (!audioMergeCurrentTask.value?.result_file) return;
  handleSeekFile({ path: audioMergeCurrentTask.value.result_file }, percentage);
};

// 播放/暂停音频合成文件
const handleAudioMergeTogglePlayFile = (index: number) => {
  if (
    !audioMergeCurrentTask.value ||
    !audioMergeCurrentTask.value.files ||
    index < 0 ||
    index >= audioMergeCurrentTask.value.files.length
  ) {
    return;
  }

  const file = audioMergeCurrentTask.value.files[index];
  const filePath = file.path || file.name || "";
  if (!filePath) {
    ElMessage.warning("文件路径不存在");
    return;
  }

  // 如果点击的是正在播放的文件，则停止播放
  if (
    audioMergePlayer.playingFilePath.value === filePath &&
    audioMergePlayer.audio &&
    !audioMergePlayer.audio.paused
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
  audioMergePlayer.load(audioUrl, {
    playingFilePath: filePath,
    playingFileIndex: index,
  });

  // 开始播放
  audioMergePlayer.play().catch(error => {
    logAndNoticeError(error as Error, "播放失败");
    clearBrowserAudioPlayer();
  });
};

// 停止音频合成播放（统一清理所有播放）
const handleAudioMergeStopPlay = () => {
  clearBrowserAudioPlayer();
};

// 播放/暂停音频合成结果文件（使用统一的播放器）
const handleAudioMergeTogglePlayResult = () => {
  if (!audioMergeCurrentTask.value || !audioMergeCurrentTask.value.result_file) {
    ElMessage.warning("结果文件不存在");
    return;
  }

  const resultFilePath = audioMergeCurrentTask.value.result_file;

  // 如果点击的是正在播放的结果文件，则停止播放
  if (
    audioMergePlayer.playingFilePath.value === resultFilePath &&
    audioMergePlayer.audio &&
    !audioMergePlayer.audio.paused
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
  audioMergePlayer.load(audioUrl, {
    playingFilePath: resultFilePath,
  });

  // 开始播放
  audioMergePlayer.play().catch(error => {
    logAndNoticeError(error as Error, "播放失败");
    clearBrowserAudioPlayer();
  });
};

// 转存音频合成结果文件
const handleAudioMergeSaveResult = () => {
  if (!audioMergeCurrentTask.value || !audioMergeCurrentTask.value.result_file) {
    ElMessage.warning("结果文件不存在");
    return;
  }
  audioMergeSaveResultDialogVisible.value = true;
};

// 处理音频合成转存确认
const handleAudioMergeSaveResultConfirm = async (filePaths: string[]) => {
  if (!audioMergeCurrentTask.value || !audioMergeCurrentTask.value.result_file) {
    return;
  }

  if (filePaths.length === 0) {
    ElMessage.warning("请选择转存目录");
    return;
  }

  const targetDir = filePaths[0];

  try {
    audioMergeLoading.value = true;
    const response = await saveMediaTaskResult(audioMergeCurrentTask.value.task_id, targetDir);

    if (response.code === 0) {
      ElMessage.success("转存成功");
      audioMergeSaveResultDialogVisible.value = false;
    } else {
      ElMessage.error(response.msg || "转存失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "转存失败");
  } finally {
    audioMergeLoading.value = false;
  }
};

// 格式化音频合成文件大小（使用统一的 formatSize 函数）
const formatAudioMergeFileSize = formatSize;

// 音频合成状态映射
const AUDIO_MERGE_STATUS_MAP: Record<string, { tag: string; text: string }> = {
  pending: { tag: "info", text: "等待中" },
  processing: { tag: "warning", text: "处理中" },
  success: { tag: "success", text: "成功" },
  failed: { tag: "danger", text: "失败" },
};

// 获取音频合成状态标签类型
const getAudioMergeStatusTagType = (status: string): string => {
  return AUDIO_MERGE_STATUS_MAP[status]?.tag || "info";
};

// 获取音频合成状态文本
const getAudioMergeStatusText = (status: string): string => {
  return AUDIO_MERGE_STATUS_MAP[status]?.text || "未知";
};

// 计算属性
const isTaskProcessing = computed(() => audioMergeCurrentTask.value?.status === "processing");
const hasFiles = computed(() => (audioMergeCurrentTask.value?.files || []).length > 0);
const filesCount = computed(() => (audioMergeCurrentTask.value?.files || []).length);
const resultFile = computed(() => audioMergeCurrentTask.value?.result_file);
const isResultActionDisabled = computed(
  () =>
    !resultFile.value || audioMergeCurrentTask.value?.status !== "success" || audioMergeFilesDragMode.value
);
const isStartMergeDisabled = computed(
  () => !hasFiles.value || isTaskProcessing.value || audioMergeFilesDragMode.value
);
const isFileOperationDisabled = computed(() => isTaskProcessing.value || audioMergeFilesDragMode.value);
const isDragModeButtonDisabled = computed(
  () => !audioMergeCurrentTask.value || !hasFiles.value || isTaskProcessing.value
);
const dragModeButtonTitle = computed(() =>
  audioMergeFilesDragMode.value ? "点击退出拖拽排序模式" : "点击进入拖拽排序模式"
);
const resultFileObject = computed(() => ({ path: resultFile.value || "" }));

// 检查音频合成文件顺序是否改变
const isAudioMergeOrderChanged = (original: MediaFile[], current: MediaFile[]): boolean => {
  if (!original || !current || original.length !== current.length) {
    return true;
  }
  return original.some((item, i) => {
    const origPath = item?.path || item?.name;
    const currPath = current[i]?.path || current[i]?.name;
    return origPath !== currPath;
  });
};

// 切换音频合成文件拖拽排序模式
const handleAudioMergeToggleFilesDragMode = async () => {
  if (audioMergeFilesDragMode.value) {
    if (
      audioMergeCurrentTask.value &&
      audioMergeCurrentTask.value.files &&
      audioMergeCurrentTask.value.files.length > 0
    ) {
      const hasChanged = isAudioMergeOrderChanged(
        audioMergeFilesOriginalOrder.value || [],
        audioMergeCurrentTask.value.files
      );
      if (hasChanged) {
        try {
          audioMergeLoading.value = true;
          const fileIndices = audioMergeCurrentTask.value.files.map((_, index: number) => index);
          const response = await reorderMediaTaskFiles(audioMergeCurrentTask.value.task_id, fileIndices);

          if (response.code === 0) {
            ElMessage.success("排序已保存");
            await handleAudioMergeViewTask(audioMergeCurrentTask.value.task_id);
          } else {
            ElMessage.error(response.msg || "保存排序失败");
          }
        } catch (error) {
          logAndNoticeError(error as Error, "保存排序失败");
        } finally {
          audioMergeLoading.value = false;
        }
      }
      audioMergeFilesOriginalOrder.value = null;
    }
  } else {
    if (
      audioMergeCurrentTask.value &&
      audioMergeCurrentTask.value.files &&
      audioMergeCurrentTask.value.files.length > 0
    ) {
      audioMergeFilesOriginalOrder.value = [...(audioMergeCurrentTask.value.files || [])];
    }
  }
  audioMergeFilesDragMode.value = !audioMergeFilesDragMode.value;
};

// 处理音频合成文件拖拽开始
const handleAudioMergeFileDragStart = (event: DragEvent, index: number) => {
  if (!audioMergeFilesDragMode.value) {
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

// 处理音频合成文件拖拽结束
const handleAudioMergeFileDragEnd = (event: DragEvent) => {
  if (event.currentTarget) {
    clearDragStyles(event.currentTarget as HTMLElement);
  }
};

// 处理音频合成文件拖拽离开
const handleAudioMergeFileDragLeave = (event: DragEvent) => {
  if (event.currentTarget) {
    clearDragStyles(event.currentTarget as HTMLElement);
  }
};

// 处理音频合成文件拖拽悬停
const handleAudioMergeFileDragOver = (event: DragEvent) => {
  if (!audioMergeFilesDragMode.value) {
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

// 处理音频合成文件拖拽放置
const handleAudioMergeFileDrop = (event: DragEvent, targetIndex: number) => {
  if (!audioMergeFilesDragMode.value) {
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
    !audioMergeCurrentTask.value ||
    !audioMergeCurrentTask.value.files ||
    sourceIndex < 0 ||
    sourceIndex >= audioMergeCurrentTask.value.files.length ||
    targetIndex < 0 ||
    targetIndex >= audioMergeCurrentTask.value.files.length
  ) {
    return;
  }

  // 计算插入位置
  const rect = (event.currentTarget as HTMLElement)?.getBoundingClientRect();
  const mouseY = event.clientY;
  const elementCenterY = rect ? rect.top + rect.height / 2 : 0;
  const insertIndex = mouseY < elementCenterY ? targetIndex : targetIndex + 1;

  // 重新排序文件列表
  const list = [...(audioMergeCurrentTask.value.files || [])];
  const [removed] = list.splice(sourceIndex, 1);
  const adjustedIndex = sourceIndex < insertIndex ? insertIndex - 1 : insertIndex;
  list.splice(adjustedIndex, 0, removed);

  audioMergeCurrentTask.value = {
    ...audioMergeCurrentTask.value,
    files: list,
  };
};

// 关闭文件浏览器
const handleAudioMergeCloseFileBrowser = () => {
  audioMergeFileBrowserDialogVisible.value = false;
};

onMounted(() => {
  loadAudioMergeTaskList();
});

onUnmounted(() => {
  handleAudioMergeStopPlay();
  // useInterval 会自动清理，但显式调用更安全
  stopAudioMergePolling();
});
</script>

