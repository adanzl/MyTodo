<template>
  <div class="flex-1 border rounded p-3 flex flex-col ">
    <div class="flex items-center justify-between mb-3">
      <div class="flex-1">
        <div v-if="playlistStatus" class="flex items-center gap-2 mb-1">
          <div class="flex items-center gap-2 flex-1">
            <h3 class="text-lg font-semibold truncate">{{ playlistStatus.name }}</h3>
            <el-button
              type="default"
              size="small"
              plain
              circle
              @click="$emit('start-edit-name', activePlaylistId)"
              title="编辑名称"
            >
              <el-icon><Edit /></el-icon>
            </el-button>
          </div>
        </div>
        <div v-else>
          <h3 class="text-lg font-semibold">播放列表文件</h3>
        </div>
        <div class="text-sm text-gray-500" v-if="playlistStatus">
          <span v-if="getPlaylistTotalDuration() > 0" class="mr-2">
            总时长：{{ formatDuration(getPlaylistTotalDuration()) }}
          </span>
          <template v-if="playlistStatus">
            <template
              v-if="
                (getCurrentPreFiles()?.length || 0) + (playlistStatus.playlist?.length || 0) > 0
              "
            >
              共
              {{ (getCurrentPreFiles()?.length || 0) + (playlistStatus.playlist?.length || 0) }}
              首， 当前:
              <template
                v-if="
                  playlistStatus.pre_index !== undefined &&
                  playlistStatus.pre_index !== null &&
                  playlistStatus.pre_index >= 0
                "
              >
                {{ playlistStatus.pre_index + 1 }}
              </template>
              <template
                v-else-if="
                  playlistStatus.current_index !== undefined &&
                  playlistStatus.current_index !== null &&
                  playlistStatus.current_index >= 0
                "
              >
                {{ (getCurrentPreFiles()?.length || 0) + playlistStatus.current_index + 1 }}
              </template>
              <template v-else> - </template>
              / {{ (getCurrentPreFiles()?.length || 0) + (playlistStatus.playlist?.length || 0) }}
            </template>
            <template v-else> 共 0 首， 当前: - / 0 </template>
          </template>
        </div>
      </div>
      <div class="flex flex-wrap gap-2">
        <el-button
          type="default"
          size="small"
          plain
          circle
          @click="$emit('open-batch-drawer')"
          title="批量模式"
        >
          <el-icon><Collection /></el-icon>
        </el-button>
        <el-button
          type="default"
          size="small"
          plain
          circle
          @click="$emit('play')"
          class="items-center justify-center"
          :disabled="
            !playlistStatus ||
            !playlistStatus.playlist ||
            playlistStatus.playlist.length === 0 ||
            !!playlistStatus.isPlaying
          "
          title="播放"
        >
          <el-icon v-if="playing" size="12" class="animate-spin"><Loading /></el-icon>
          <span v-else>▶</span>
        </el-button>
        <el-button
          type="default"
          size="small"
          plain
          circle
          @click="$emit('play-pre')"
          :disabled="
            !playlistStatus ||
            ((!getCurrentPreFiles() || getCurrentPreFiles().length === 0) &&
              (!playlistStatus.playlist || playlistStatus.playlist.length === 0))
          "
          title="上一首"
        >
          <el-icon v-if="playing" size="12" class="animate-spin"><Loading /></el-icon>
          <span v-else>⏮</span>
        </el-button>
        <el-button
          type="default"
          size="small"
          plain
          circle
          @click="$emit('play-next')"
          :disabled="
            !playlistStatus ||
            ((!getCurrentPreFiles() || getCurrentPreFiles().length === 0) &&
              (!playlistStatus.playlist || playlistStatus.playlist.length === 0))
          "
          title="下一首"
        >
          <el-icon v-if="playing" size="12" class="animate-spin"><Loading /></el-icon>
          <span v-else>⏭</span>
        </el-button>
        <el-button type="default" size="small" plain circle @click="$emit('stop')" title="停止">
          <el-icon v-if="stopping" size="12" class="animate-spin"><Loading /></el-icon>
          <span v-else>⏹</span>
        </el-button>
        <el-button
          v-show="showMoreActions"
          type="default"
          size="small"
          plain
          circle
          @click="$emit('clear')"
          :disabled="
            !playlistStatus ||
            ((!getCurrentPreFiles() || getCurrentPreFiles().length === 0) &&
              (!playlistStatus.playlist || playlistStatus.playlist.length === 0)) ||
            playlistLoading
          "
          title="清空列表（包括前置文件和正式文件）"
        >
          <el-icon><Delete /></el-icon>
        </el-button>
        <el-button
          type="default"
          size="small"
          plain
          circle
          @click="$emit('toggle-more-actions')"
          title="更多"
        >
          <el-icon><Menu /></el-icon>
        </el-button>
      </div>
    </div>

    <div v-if="playlistStatus" class="flex-1 overflow-y-scroll scrollbar-overlay">
      <PreFilesList
        :playlist-status="playlistStatus"
        :selected-weekday-index="selectedWeekdayIndex"
        :pre-files-drag-mode="preFilesDragMode"
        :pre-files-batch-delete-mode="preFilesBatchDeleteMode"
        :selected-pre-file-indices="selectedPreFileIndices"
        :pre-files-expanded="preFilesExpanded"
        :playlist-loading="playlistLoading"
        :show-more-actions="showMoreActions"
        :is-file-playing="isFilePlaying"
        :get-file-play-progress="getFilePlayProgress"
        :get-file-duration="getFileDuration"
        @select-weekday="$emit('select-weekday', $event)"
        @open-file-browser="$emit('open-file-browser-for-pre-files')"
        @toggle-drag-mode="$emit('toggle-pre-files-drag-mode')"
        @toggle-batch-delete-mode="$emit('toggle-pre-files-batch-delete-mode')"
        @batch-delete="$emit('batch-delete-pre-files')"
        @clear="$emit('clear-pre-files')"
        @toggle-expand="$emit('toggle-pre-files-expand')"
        @toggle-selection="$emit('toggle-pre-file-selection', $event)"
        @drag-start="(event, index) => $emit('pre-file-drag-start', event, index)"
        @drag-end="event => $emit('pre-file-drag-end', event)"
        @drag-over="event => $emit('pre-file-drag-over', event)"
        @drop="(event, index) => $emit('pre-file-drop', event, index)"
        @play-file="$emit('play-file', $event)"
        @seek-file="(file, percentage) => $emit('seek-file', file, percentage)"
        @move-up="index => $emit('move-pre-file-up', index)"
        @move-down="index => $emit('move-pre-file-down', index)"
        @replace="index => $emit('replace-pre-file', index)"
        @open-playlist-selector="file => $emit('open-playlist-selector-for-pre-file', file)"
        @delete="index => $emit('delete-pre-file', index)"
      >
      </PreFilesList>

      <FilesList
        :playlist-status="playlistStatus"
        :files-drag-mode="filesDragMode"
        :files-batch-delete-mode="filesBatchDeleteMode"
        :selected-file-indices="selectedFileIndices"
        :playlist-loading="playlistLoading"
        :show-more-actions="showMoreActions"
        :is-file-playing="isFilePlaying"
        :get-file-play-progress="getFilePlayProgress"
        :get-file-duration="getFileDuration"
        @open-file-browser="$emit('open-file-browser')"
        @toggle-drag-mode="$emit('toggle-files-drag-mode')"
        @toggle-batch-delete-mode="$emit('toggle-files-batch-delete-mode')"
        @batch-delete="$emit('batch-delete-files')"
        @clear="$emit('clear-files')"
        @toggle-selection="$emit('toggle-file-selection', $event)"
        @drag-start="(event, index) => $emit('file-drag-start', event, index)"
        @drag-end="event => $emit('file-drag-end', event)"
        @drag-over="event => $emit('file-drag-over', event)"
        @drop="(event, index) => $emit('file-drop', event, index)"
        @play-file="$emit('play-file', $event)"
        @seek-file="(file, percentage) => $emit('seek-file', file, percentage)"
        @move-up="index => $emit('move-file-up', index)"
        @move-down="index => $emit('move-file-down', index)"
        @replace="index => $emit('replace-file', index)"
        @open-playlist-selector="file => $emit('open-playlist-selector-for-file', file)"
        @delete="index => $emit('delete-file', index)"
      >
      </FilesList>

      <div
        v-if="
          (!getCurrentPreFiles() || getCurrentPreFiles().length === 0) &&
          (!playlistStatus?.playlist || playlistStatus.playlist.length === 0)
        "
        class="text-sm text-gray-400 text-center py-8"
      >
        当前播放列表为空，点击"添加文件"开始构建播放列表
      </div>
    </div>
    <div v-else class="flex-1 flex items-center justify-center text-sm text-gray-400">
      请先在左侧选择一个播放列表查看详情
    </div>
  </div>
</template>

<script setup lang="ts">
import { Edit, Collection, Loading, Delete, Menu } from "@element-plus/icons-vue";
import { formatDuration } from "@/utils/format";
import { getWeekdayIndex } from "@/utils/date";
import { calculateFilesTotalDuration } from "@/utils/file";
import type { MediaFile } from "@/types/tools";
import type { PlaylistStatus } from "@/types/playlist";
import PreFilesList from "./PreFilesList.vue";
import FilesList from "./FilesList.vue";

interface Props {
  playlistStatus: PlaylistStatus | null;
  activePlaylistId: string;
  editingPlaylistId: string | null;
  editingPlaylistName: string;
  selectedWeekdayIndex: number | null;
  preFilesDragMode: boolean;
  preFilesBatchDeleteMode: boolean;
  selectedPreFileIndices: number[];
  preFilesExpanded: boolean;
  filesDragMode: boolean;
  filesBatchDeleteMode: boolean;
  selectedFileIndices: number[];
  playlistLoading: boolean;
  playing: boolean;
  stopping: boolean;
  showMoreActions: boolean;
  isFilePlaying: (file: MediaFile) => boolean;
  getFilePlayProgress: (file: MediaFile) => number;
  getFileDuration: (file: MediaFile) => number;
}

const props = defineProps<Props>();

defineEmits<{
  "update:editingPlaylistName": [value: string];
  "start-edit-name": [playlistId: string];
  "save-name": [playlistId: string];
  "cancel-edit-name": [];
  "open-batch-drawer": [];
  play: [];
  "play-pre": [];
  "play-next": [];
  stop: [];
  clear: [];
  "toggle-more-actions": [];
  "select-weekday": [index: number];
  "open-file-browser-for-pre-files": [];
  "toggle-pre-files-drag-mode": [];
  "toggle-pre-files-batch-delete-mode": [];
  "batch-delete-pre-files": [];
  "clear-pre-files": [];
  "toggle-pre-files-expand": [];
  "toggle-pre-file-selection": [index: number];
  "pre-file-drag-start": [event: DragEvent, index: number];
  "pre-file-drag-end": [event: DragEvent];
  "pre-file-drag-over": [event: DragEvent];
  "pre-file-drop": [event: DragEvent, index: number];
  "open-file-browser": [];
  "toggle-files-drag-mode": [];
  "toggle-files-batch-delete-mode": [];
  "batch-delete-files": [];
  "clear-files": [];
  "toggle-file-selection": [index: number];
  "file-drag-start": [event: DragEvent, index: number];
  "file-drag-end": [event: DragEvent];
  "file-drag-over": [event: DragEvent];
  "file-drop": [event: DragEvent, index: number];
  "play-file": [file: MediaFile];
  "seek-file": [file: MediaFile, percentage: number];
  "move-pre-file-up": [index: number];
  "move-pre-file-down": [index: number];
  "replace-pre-file": [index: number];
  "open-playlist-selector-for-pre-file": [file: MediaFile];
  "delete-pre-file": [index: number];
  "move-file-up": [index: number];
  "move-file-down": [index: number];
  "replace-file": [index: number];
  "open-playlist-selector-for-file": [file: MediaFile];
  "delete-file": [index: number];
}>();

const getSelectedWeekdayIndex = () => {
  return props.selectedWeekdayIndex !== null ? props.selectedWeekdayIndex : getWeekdayIndex();
};

const getCurrentPreFiles = () => {
  const status = props.playlistStatus;
  if (!status || !status.pre_lists) return [];
  const weekdayIndex = getSelectedWeekdayIndex();
  if (!Array.isArray(status.pre_lists) || status.pre_lists.length !== 7) return [];
  return status.pre_lists[weekdayIndex] || [];
};

const getPlaylistTotalDuration = () => {
  const status = props.playlistStatus;
  if (!status) return 0;
  const preFiles = getCurrentPreFiles();
  const preFilesDuration = calculateFilesTotalDuration(preFiles);
  const files = status.playlist || [];
  const filesDuration = calculateFilesTotalDuration(files);
  return preFilesDuration + filesDuration;
};
</script>
