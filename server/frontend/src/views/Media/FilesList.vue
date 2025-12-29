<template>
  <div v-if="playlistStatus?.playlist" class="border rounded p-2">
    <div class="flex items-center justify-between mb-2 pr-2.5">
      <div class="text-xs font-semibold text-gray-600">
        正式文件（播放时记录进度）
        <span v-if="filesTotalDuration > 0" class="ml-2 text-gray-500">
          总时长：{{ formatDuration(filesTotalDuration) }}
        </span>
        <span v-if="hasFiles" class="ml-2 text-gray-500">
          共 {{ playlistLength }} 首， 当前: {{ currentIndexDisplay }} / {{ playlistLength }}
        </span>
        <el-tag v-if="isPlaying" type="success" size="small" class="ml-2"> 播放中 </el-tag>
      </div>
      <div class="flex items-center gap-1">
        <el-button
          type="primary"
          v-bind="buttonBaseProps"
          @click="emit('open-file-browser')"
          :disabled="isAddButtonDisabled"
        >
          +
        </el-button>
        <el-button
          :type="filesDragMode ? 'success' : 'default'"
          v-bind="buttonBaseProps"
          @click="emit('toggle-drag-mode')"
          :disabled="isDragButtonDisabled"
          :title="filesDragMode ? '点击退出拖拽排序模式' : '点击进入拖拽排序模式'"
        >
          <el-icon v-if="filesDragMode"><Check /></el-icon>
          <el-icon v-else><Menu /></el-icon>
        </el-button>
        <el-button
          :type="filesBatchDeleteMode ? 'success' : 'default'"
          v-bind="buttonBaseProps"
          @click="emit('toggle-batch-delete-mode')"
          :disabled="isBatchDeleteButtonDisabled"
          :title="filesBatchDeleteMode ? '点击退出批量删除模式' : '点击进入批量删除模式'"
        >
          <el-icon v-if="filesBatchDeleteMode"><Check /></el-icon>
          <el-icon v-else><Delete /></el-icon>
        </el-button>
        <el-button
          v-show="filesBatchDeleteMode"
          type="danger"
          v-bind="buttonBaseProps"
          @click="emit('batch-delete')"
          :disabled="isBatchDeleteDisabled"
          :title="batchDeleteTitle"
        >
          <el-icon><Delete /></el-icon>
        </el-button>
        <el-button
          v-show="showClearButton"
          type="default"
          v-bind="buttonBaseProps"
          @click="emit('clear')"
          :disabled="isClearButtonDisabled"
          title="清空正式文件列表"
        >
          <el-icon><Delete /></el-icon>
        </el-button>
      </div>
    </div>
    <div v-if="hasFiles" class="overflow-y-scroll scrollbar-overlay">
      <div
        v-for="(file, index) in playlist"
        :key="file.uri || index"
        class="flex items-center gap-2 p-1 hover:bg-gray-100 rounded select-none"
        :class="getFileItemClass(index)"
        :draggable="filesDragMode"
        @click="handleFileItemClick(index)"
        @dragstart="handleDragStart($event, index)"
        @dragend="handleDragEnd"
        @dragover.prevent="handleDragOver"
        @dragleave="handleDragLeave"
        @drop.prevent="handleDrop($event, index)"
      >
        <span class="text-xs text-gray-500 w-8">{{ index + 1 }}</span>
        <span
          class="flex-1 text-sm truncate"
          :class="{ 'text-blue-600': isCurrent(index) }"
          :title="file.uri || ''"
        >
          {{ getFileName(file.uri) }}
        </span>
        <div class="flex items-center gap-1 flex-shrink-0" @mousedown.stop @click.stop>
          <MediaComponent
            v-show="!filesBatchDeleteMode"
            :file="file"
            :player="audioPlayer"
            :disabled="playlistLoading"
            @play="emit('play-file', file)"
            @seek="handleSeek"
          />
          <el-checkbox
            v-show="filesBatchDeleteMode"
            class="!h-6"
            :model-value="isSelected(index)"
            @change="emit('toggle-selection', index)"
            @click.stop
          />
          <el-button
            v-show="showMoreButtons"
            v-bind="circleButtonProps"
            @click.stop="emit('move-up', index)"
            :disabled="index === 0 || playlistLoading"
            title="上移"
          >
            ↑
          </el-button>
          <el-button
            v-show="showMoreButtons"
            v-bind="circleButtonProps"
            @click.stop="emit('move-down', index)"
            :disabled="index === playlistLength - 1 || playlistLoading"
            title="下移"
          >
            ↓
          </el-button>
          <el-button
            v-show="showMoreButtons"
            v-bind="circleButtonProps"
            @click.stop="emit('replace', index)"
            :disabled="playlistLoading"
            title="替换"
          >
            <el-icon><Refresh /></el-icon>
          </el-button>
          <el-button
            v-show="showPlaylistSelectorButton"
            type="info"
            size="small"
            plain
            circle
            @click.stop="emit('open-playlist-selector', file)"
            :disabled="playlistLoading"
            title="应用到列表"
          >
            <el-icon><DocumentCopy /></el-icon>
          </el-button>
          <el-button
            v-show="!filesBatchDeleteMode"
            v-bind="circleButtonProps"
            @click.stop="emit('delete', index)"
            :disabled="isDeleteButtonDisabled"
            title="删除"
          >
            <el-icon><Minus /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
    <div v-else class="text-sm text-gray-400 text-center py-1">正式文件列表为空</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Check, Delete, Menu, Refresh, DocumentCopy, Minus } from "@element-plus/icons-vue";
import { formatDuration } from "@/utils/format";
import { calculateFilesTotalDuration } from "@/utils/file";
import type { MediaFile } from "@/types/tools";
import type { PlaylistStatus } from "@/types/playlist";
import MediaComponent from "@/components/common/MediaComponent.vue";

interface Props {
  playlistStatus: PlaylistStatus | null;
  filesDragMode: boolean;
  filesBatchDeleteMode: boolean;
  selectedFileIndices: number[];
  playlistLoading: boolean;
  showMoreActions: boolean;
  audioPlayer: ReturnType<typeof import("@/composables/useAudioPlayer").useAudioPlayer>;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  "open-file-browser": [];
  "toggle-drag-mode": [];
  "toggle-batch-delete-mode": [];
  "batch-delete": [];
  clear: [];
  "toggle-selection": [index: number];
  "drag-start": [event: DragEvent, index: number];
  "drag-end": [event: DragEvent];
  "drag-over": [event: DragEvent];
  drop: [event: DragEvent, index: number];
  "play-file": [file: MediaFile];
  "seek-file": [file: MediaFile, percentage: number];
  "move-up": [index: number];
  "move-down": [index: number];
  replace: [index: number];
  "open-playlist-selector": [file: MediaFile];
  delete: [index: number];
}>();

// 按钮公共属性
const buttonBaseProps = { plain: true, size: "small" as const, class: "!w-8 !h-6" };
const circleButtonProps = {
  type: "default" as const,
  size: "small" as const,
  plain: true,
  circle: true,
};

// 计算属性
const playlist = computed(() => props.playlistStatus?.playlist || []);
const playlistLength = computed(() => playlist.value.length);
const currentIndex = computed(() => props.playlistStatus?.current_index ?? -1);
const currentIndexDisplay = computed(() =>
  currentIndex.value >= 0 ? currentIndex.value + 1 : "-"
);
const isPlaying = computed(
  () => props.playlistStatus?.isPlaying && !props.playlistStatus.in_pre_files
);
const hasFiles = computed(() => playlistLength.value > 0);
const filesTotalDuration = computed(() => {
  if (!hasFiles.value) return 0;
  return calculateFilesTotalDuration(playlist.value);
});

const canBatchDelete = computed(
  () => props.filesBatchDeleteMode && hasFiles.value && !props.filesDragMode
);
const showMoreButtons = computed(
  () => props.showMoreActions && !props.filesDragMode && !props.filesBatchDeleteMode
);
const showClearButton = computed(() => props.showMoreActions && !props.filesBatchDeleteMode);
const showPlaylistSelectorButton = computed(
  () => !props.filesBatchDeleteMode && !props.filesDragMode
);

// 按钮禁用状态
const isAddButtonDisabled = computed(
  () => !props.playlistStatus || props.filesDragMode || props.filesBatchDeleteMode
);
const isDragButtonDisabled = computed(() => !hasFiles.value || props.filesBatchDeleteMode);
const isBatchDeleteButtonDisabled = computed(() => !hasFiles.value || props.filesDragMode);
const isBatchDeleteDisabled = computed(
  () => props.playlistLoading || props.selectedFileIndices.length === 0
);
const batchDeleteTitle = computed(() => `删除选中的 ${props.selectedFileIndices.length} 项`);
const isClearButtonDisabled = computed(
  () => !hasFiles.value || props.playlistLoading || props.filesDragMode
);

// 辅助函数
const getFileName = (uri?: string) => (uri ? uri.split("/").pop() : "");
const isSelected = (index: number) => props.selectedFileIndices.includes(index);
const isCurrent = (index: number) => index === currentIndex.value;

const getFileItemClass = (index: number) => {
  return {
    "bg-blue-50": isCurrent(index),
    "bg-blue-100": canBatchDelete.value && isSelected(index),
    "cursor-move": props.filesDragMode,
    "cursor-pointer": canBatchDelete.value,
    "cursor-default": !props.filesDragMode && !props.filesBatchDeleteMode,
  };
};

const isDeleteButtonDisabled = computed(() => props.playlistLoading || props.filesDragMode);

// 事件处理函数
const handleFileItemClick = (index: number) => {
  if (canBatchDelete.value) {
    emit("toggle-selection", index);
  }
};

const handleDragStart = (e: DragEvent, index: number) => {
  emit("drag-start", e, index);
};

const handleDragEnd = (e: DragEvent) => {
  emit("drag-end", e);
};

const handleDragOver = (e: DragEvent) => {
  emit("drag-over", e);
};

const handleDragLeave = (e: DragEvent) => {
  const target = e.currentTarget as HTMLElement | null;
  if (target?.classList) {
    target.classList.remove("bg-gray-100", "border-t-2", "border-b-2", "border-blue-500");
  }
};

const handleDrop = (e: DragEvent, index: number) => {
  emit("drop", e, index);
};

const handleSeek = (file: MediaFile, percentage: number) => {
  emit("seek-file", file, percentage);
};
</script>
