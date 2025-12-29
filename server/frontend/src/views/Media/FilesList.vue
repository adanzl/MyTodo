<template>
  <div v-if="playlistStatus.playlist" class="border rounded p-2">
    <div class="flex items-center justify-between mb-2 pr-2.5">
      <div class="text-xs font-semibold text-gray-600">
        正式文件（播放时记录进度）
        <span v-if="getFilesTotalDuration() > 0" class="ml-2 text-gray-500">
          总时长：{{ formatDuration(getFilesTotalDuration()) }}
        </span>
        <span
          v-if="playlistStatus.playlist && playlistStatus.playlist.length > 0"
          class="ml-2 text-gray-500"
        >
          共 {{ playlistStatus.playlist.length }} 首， 当前:
          {{ playlistStatus.current_index !== undefined ? playlistStatus.current_index + 1 : "-" }}
          / {{ playlistStatus.playlist.length }}
        </span>
        <el-tag
          v-if="playlistStatus.isPlaying && playlistStatus.in_pre_files === false"
          type="success"
          size="small"
          class="ml-2"
        >
          播放中
        </el-tag>
      </div>
      <div class="flex items-center gap-1">
        <el-button
          type="primary"
          plain
          size="small"
          class="!w-8 !h-6"
          @click="$emit('open-file-browser')"
          :disabled="!playlistStatus || filesDragMode || filesBatchDeleteMode"
        >
          +
        </el-button>
        <el-button
          :type="filesDragMode ? 'success' : 'default'"
          plain
          size="small"
          class="!w-8 !h-6"
          @click="$emit('toggle-drag-mode')"
          :disabled="
            !playlistStatus ||
            !playlistStatus.playlist ||
            playlistStatus.playlist.length === 0 ||
            filesBatchDeleteMode
          "
          :title="filesDragMode ? '点击退出拖拽排序模式' : '点击进入拖拽排序模式'"
        >
          <el-icon v-if="filesDragMode"><Check /></el-icon>
          <el-icon v-else><Menu /></el-icon>
        </el-button>
        <el-button
          :type="filesBatchDeleteMode ? 'success' : 'default'"
          plain
          size="small"
          class="!w-8 !h-6"
          @click="$emit('toggle-batch-delete-mode')"
          :disabled="
            !playlistStatus ||
            !playlistStatus.playlist ||
            playlistStatus.playlist.length === 0 ||
            filesDragMode
          "
          :title="filesBatchDeleteMode ? '点击退出批量删除模式' : '点击进入批量删除模式'"
        >
          <el-icon v-if="filesBatchDeleteMode"><Check /></el-icon>
          <el-icon v-else><Delete /></el-icon>
        </el-button>
        <el-button
          v-show="filesBatchDeleteMode"
          type="danger"
          plain
          size="small"
          class="!w-8 !h-6"
          @click="$emit('batch-delete')"
          :disabled="playlistLoading || selectedFileIndices.length === 0"
          :title="`删除选中的 ${selectedFileIndices.length} 项`"
        >
          <el-icon><Delete /></el-icon>
        </el-button>
        <el-button
          type="default"
          plain
          size="small"
          class="!w-8 !h-6"
          v-show="showMoreActions && !filesBatchDeleteMode"
          @click="$emit('clear')"
          :disabled="
            !playlistStatus ||
            !playlistStatus.playlist ||
            playlistStatus.playlist.length === 0 ||
            playlistLoading ||
            filesDragMode
          "
          title="清空正式文件列表"
        >
          <el-icon><Delete /></el-icon>
        </el-button>
      </div>
    </div>
    <div
      v-if="playlistStatus.playlist && playlistStatus.playlist.length > 0"
      class="overflow-y-scroll scrollbar-overlay"
    >
      <div
        v-for="(file, index) in playlistStatus.playlist"
        :key="index"
        class="flex items-center gap-2 p-1 hover:bg-gray-100 rounded"
        :class="{
          'bg-blue-50': Number(index) === playlistStatus.current_index,
          'bg-blue-100': filesBatchDeleteMode && selectedFileIndices.includes(Number(index)),
          'cursor-move': filesDragMode,
          'cursor-pointer': filesBatchDeleteMode && !filesDragMode,
          'cursor-default': !filesDragMode && !filesBatchDeleteMode,
          'select-none': true,
        }"
        :draggable="filesDragMode"
        @click="
          filesBatchDeleteMode && !filesDragMode ? emit('toggle-selection', Number(index)) : null
        "
        @dragstart="(e: DragEvent) => emit('drag-start', e, Number(index))"
        @dragend="(e: DragEvent) => emit('drag-end', e)"
        @dragover.prevent="(e: DragEvent) => emit('drag-over', e)"
        @dragleave="
          (e: DragEvent) => {
            const target = e.currentTarget as HTMLElement | null;
            if (target && 'classList' in target) {
              target.classList.remove('bg-gray-100', 'border-t-2', 'border-b-2', 'border-blue-500');
            }
          }
        "
        @drop.prevent="(e: DragEvent) => emit('drop', e, Number(index))"
      >
        <span class="text-xs text-gray-500 w-8">{{ Number(index) + 1 }}</span>
        <span
          class="flex-1 text-sm truncate"
          :class="{ 'text-blue-600': Number(index) === playlistStatus.current_index }"
          :title="file.uri"
        >
          {{ file.uri.split("/").pop() }}
        </span>
        <div class="flex items-center gap-1 flex-shrink-0" @mousedown.stop @click.stop>
          <MediaComponent
            v-show="!filesBatchDeleteMode"
            :file="file"
            :is-playing="isFilePlaying(file)"
            :progress="getFilePlayProgress(file)"
            :duration="getFileDuration(file)"
            :disabled="playlistLoading"
            @play="emit('play-file', file)"
            @seek="(file, val) => emit('seek-file', file, val)"
          >
          </MediaComponent>
          <el-checkbox
            v-show="filesBatchDeleteMode"
            class="!h-6"
            :model-value="selectedFileIndices.includes(Number(index))"
            @change="emit('toggle-selection', Number(index))"
            @click.stop
          >
          </el-checkbox>
          <el-button
            v-show="showMoreActions && !filesDragMode && !filesBatchDeleteMode"
            type="default"
            size="small"
            plain
            circle
            @click.stop="emit('move-up', Number(index))"
            :disabled="Number(index) === 0 || playlistLoading"
            title="上移"
          >
            ↑
          </el-button>
          <el-button
            v-show="showMoreActions && !filesDragMode && !filesBatchDeleteMode"
            type="default"
            size="small"
            plain
            circle
            @click.stop="emit('move-down', Number(index))"
            :disabled="Number(index) === playlistStatus.playlist.length - 1 || playlistLoading"
            title="下移"
          >
            ↓
          </el-button>
          <el-button
            v-show="showMoreActions && !filesDragMode && !filesBatchDeleteMode"
            type="default"
            size="small"
            plain
            circle
            @click.stop="emit('replace', Number(index))"
            :disabled="playlistLoading"
            title="替换"
          >
            <el-icon><Refresh /></el-icon>
          </el-button>
          <el-button
            v-show="!filesBatchDeleteMode && !filesDragMode"
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
            type="default"
            size="small"
            plain
            circle
            @click.stop="emit('delete', Number(index))"
            :disabled="playlistLoading || filesDragMode"
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
  isFilePlaying: (file: MediaFile) => boolean;
  getFilePlayProgress: (file: MediaFile) => number;
  getFileDuration: (file: MediaFile) => number;
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

const getFilesTotalDuration = () => {
  const status = props.playlistStatus;
  if (!status || !status.playlist || status.playlist.length === 0) {
    return 0;
  }
  return calculateFilesTotalDuration(status.playlist);
};
</script>
