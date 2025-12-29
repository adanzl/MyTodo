<template>
  <div class="border rounded p-2 mb-2">
    <!-- 第一行：标题和星期选择按钮 -->
    <div class="flex items-center justify-between mb-2">
      <div class="text-xs font-semibold text-gray-600 w-39">前置文件（播放时优先播放）</div>
      <div class="flex items-center gap-1">
        <!-- 星期选择按钮 -->
        <div class="flex items-center gap-1">
          <el-button
            v-for="(day, index) in ['周一', '周二', '周三', '周四', '周五', '周六', '周日']"
            :key="index"
            :type="
              selectedWeekdayIndex === index ||
              (selectedWeekdayIndex === null && getWeekdayIndex() === index)
                ? 'primary'
                : 'default'
            "
            size="small"
            plain
            @click="$emit('select-weekday', index)"
            :title="day"
            class="!w-16 !h-6 !p-0 text-xs"
          >
            {{ day }}<span class="text-[10px]">[{{ getPreFilesCountForWeekday(index) }}]</span>
          </el-button>
        </div>
      </div>
    </div>
    <!-- 第二行：统计信息和操作按钮 -->
    <div class="flex items-center justify-between text-xs text-gray-500 mb-2 pr-2.5">
      <div class="flex items-center">
        <span v-if="getPreFilesTotalDuration() > 0">
          总时长：{{ formatDuration(getPreFilesTotalDuration()) }}
        </span>
        <span
          v-if="getCurrentPreFiles() && getCurrentPreFiles().length > 0"
          :class="getPreFilesTotalDuration() > 0 ? 'ml-2' : ''"
        >
          共 {{ getCurrentPreFiles().length }} 首， 当前:
          {{
            playlistStatus?.pre_index !== undefined &&
            playlistStatus.pre_index !== null &&
            playlistStatus.pre_index >= 0
              ? playlistStatus.pre_index + 1
              : "-"
          }}
          / {{ getCurrentPreFiles().length }}
        </span>
        <el-tag
          v-if="playlistStatus?.isPlaying && playlistStatus.in_pre_files === true"
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
          size="small"
          plain
          @click="$emit('open-file-browser')"
          :disabled="!playlistStatus || preFilesDragMode || preFilesBatchDeleteMode"
        >
          +
        </el-button>
        <el-button
          :type="preFilesDragMode ? 'success' : 'default'"
          size="small"
          plain
          class="!w-8 !h-6"
          @click="$emit('toggle-drag-mode')"
          :disabled="
            !playlistStatus ||
            !getCurrentPreFiles() ||
            getCurrentPreFiles().length === 0 ||
            preFilesBatchDeleteMode
          "
          :title="preFilesDragMode ? '点击退出拖拽排序模式' : '点击进入拖拽排序模式'"
        >
          <el-icon v-if="preFilesDragMode"><Check /></el-icon>
          <el-icon v-else><Menu /></el-icon>
        </el-button>
        <el-button
          :type="preFilesBatchDeleteMode ? 'success' : 'default'"
          size="small"
          plain
          class="!w-8 !h-6"
          @click="$emit('toggle-batch-delete-mode')"
          :disabled="
            !playlistStatus ||
            !getCurrentPreFiles() ||
            getCurrentPreFiles().length === 0 ||
            preFilesDragMode
          "
          :title="preFilesBatchDeleteMode ? '点击退出批量删除模式' : '点击进入批量删除模式'"
        >
          <el-icon v-if="preFilesBatchDeleteMode"><Check /></el-icon>
          <el-icon v-else><Delete /></el-icon>
        </el-button>
        <el-button
          v-show="preFilesBatchDeleteMode"
          type="danger"
          size="small"
          plain
          class="!w-8 !h-6"
          @click="$emit('batch-delete')"
          :disabled="playlistLoading || selectedPreFileIndices.length === 0"
          :title="`删除选中的 ${selectedPreFileIndices.length} 项`"
        >
          <el-icon><Delete /></el-icon>
        </el-button>
        <el-button
          type="default"
          size="small"
          plain
          class="!w-8 !h-6"
          v-show="showMoreActions && !preFilesBatchDeleteMode"
          @click="$emit('clear')"
          :disabled="
            !playlistStatus ||
            !getCurrentPreFiles() ||
            getCurrentPreFiles().length === 0 ||
            playlistLoading ||
            preFilesDragMode
          "
          title="清空列表"
        >
          <el-icon><Delete /></el-icon>
        </el-button>
      </div>
    </div>
    <!-- 前置文件列表 -->
    <div
      v-if="getCurrentPreFiles() && getCurrentPreFiles().length > 0"
      class="overflow-y-scroll scrollbar-overlay"
      :class="{ 'max-h-[192px]': !preFilesExpanded }"
    >
      <div
        v-for="(file, index) in getCurrentPreFiles()"
        :key="'pre-' + index"
        class="flex items-center gap-2 p-1 hover:bg-gray-100 rounded"
        :class="{
          'bg-blue-50': Number(playlistStatus?.pre_index) === index,
          'bg-blue-100': preFilesBatchDeleteMode && selectedPreFileIndices.includes(Number(index)),
          'cursor-move': preFilesDragMode,
          'cursor-pointer': preFilesBatchDeleteMode && !preFilesDragMode,
          'cursor-default': !preFilesDragMode && !preFilesBatchDeleteMode,
          'select-none': true,
        }"
        :draggable="preFilesDragMode"
        @click="
          preFilesBatchDeleteMode && !preFilesDragMode
            ? $emit('toggle-selection', Number(index))
            : null
        "
        @dragstart="(e: DragEvent) => $emit('drag-start', e, Number(index))"
        @dragend="(e: DragEvent) => $emit('drag-end', e)"
        @dragover.prevent="(e: DragEvent) => $emit('drag-over', e)"
        @dragleave="
          (e: DragEvent) => {
            const target = e.currentTarget as HTMLElement | null;
            if (target) {
              target.classList.remove('bg-gray-100', 'border-t-2', 'border-b-2', 'border-blue-500');
            }
          }
        "
        @drop.prevent="(e: DragEvent) => $emit('drop', e, Number(index))"
      >
        <span class="text-xs text-gray-500 w-8">{{ Number(index) + 1 }}</span>
        <span
          class="flex-1 text-sm truncate"
          :class="{ 'text-blue-600': Number(playlistStatus?.pre_index) === index }"
          :title="file.uri || ''"
        >
          {{ file.uri ? file.uri.split("/").pop() : "" }}
        </span>
        <div class="flex items-center gap-1 flex-shrink-0" @mousedown.stop @click.stop>
          <MediaComponent
            v-show="!preFilesBatchDeleteMode"
            :file="file"
            :player="audioPlayer"
            :disabled="playlistLoading"
            @play="$emit('play-file', file)"
            @seek="(file, val) => $emit('seek-file', file, val)"
          />
          <el-checkbox
            v-show="preFilesBatchDeleteMode"
            class="!h-6"
            :model-value="selectedPreFileIndices.includes(Number(index))"
            @change="$emit('toggle-selection', Number(index))"
            @click.stop
          >
          </el-checkbox>
          <el-button
            v-show="showMoreActions && !preFilesDragMode && !preFilesBatchDeleteMode"
            type="default"
            size="small"
            plain
            circle
            @click.stop="$emit('move-up', Number(index))"
            :disabled="Number(index) === 0 || playlistLoading"
            title="上移"
          >
            ↑
          </el-button>
          <el-button
            v-show="showMoreActions && !preFilesDragMode && !preFilesBatchDeleteMode"
            type="default"
            size="small"
            plain
            circle
            @click.stop="$emit('move-down', Number(index))"
            :disabled="Number(index) === getCurrentPreFiles().length - 1 || playlistLoading"
            title="下移"
          >
            ↓
          </el-button>
          <el-button
            v-show="showMoreActions && !preFilesDragMode && !preFilesBatchDeleteMode"
            type="default"
            size="small"
            plain
            circle
            @click.stop="$emit('replace', Number(index))"
            :disabled="playlistLoading"
            title="替换"
          >
            <el-icon><Refresh /></el-icon>
          </el-button>
          <el-button
            v-show="!preFilesBatchDeleteMode && !preFilesDragMode"
            type="info"
            size="small"
            plain
            circle
            @click.stop="$emit('open-playlist-selector', file)"
            :disabled="playlistLoading"
            title="应用到列表"
          >
            <el-icon><DocumentCopy /></el-icon>
          </el-button>
          <el-button
            v-show="!preFilesBatchDeleteMode"
            type="default"
            size="small"
            plain
            circle
            @click.stop="$emit('delete', Number(index))"
            :disabled="playlistLoading || preFilesDragMode"
            title="删除"
          >
            <el-icon><Minus /></el-icon>
          </el-button>
        </div>
      </div>
    </div>
    <div
      v-if="getCurrentPreFiles() && getCurrentPreFiles().length > 0"
      class="w-full border-t border-gray-200"
    >
      <el-button
        type="default"
        size="small"
        plain
        class="!w-full !h-4 !p-0 !text-xs"
        @click="$emit('toggle-expand')"
        :title="preFilesExpanded ? '折叠' : '展开'"
      >
        <el-icon v-if="preFilesExpanded"><ArrowUp /></el-icon>
        <el-icon v-else><ArrowDown /></el-icon>
      </el-button>
    </div>
    <div v-else class="text-sm text-gray-400 text-center py-1">前置文件列表为空</div>
  </div>
</template>

<script setup lang="ts">
import {
  Check,
  Delete,
  Menu,
  Refresh,
  DocumentCopy,
  Minus,
  ArrowUp,
  ArrowDown,
} from "@element-plus/icons-vue";
import { formatDuration } from "@/utils/format";
import { getWeekdayIndex } from "@/utils/date";
import { calculateFilesTotalDuration } from "@/utils/file";
import type { MediaFile } from "@/types/tools";
import type { PlaylistStatus } from "@/types/playlist";
import MediaComponent from "@/components/MediaComponent.vue";

interface Props {
  playlistStatus: PlaylistStatus | null;
  selectedWeekdayIndex: number | null;
  preFilesDragMode: boolean;
  preFilesBatchDeleteMode: boolean;
  selectedPreFileIndices: number[];
  preFilesExpanded: boolean;
  playlistLoading: boolean;
  showMoreActions: boolean;
  audioPlayer: ReturnType<typeof import("@/composables/useAudioPlayer").useAudioPlayer>;
}

const props = defineProps<Props>();

defineEmits<{
  "select-weekday": [index: number];
  "open-file-browser": [];
  "toggle-drag-mode": [];
  "toggle-batch-delete-mode": [];
  "batch-delete": [];
  clear: [];
  "toggle-expand": [];
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

const getPreFilesCountForWeekday = (weekdayIndex: number) => {
  const status = props.playlistStatus;
  if (!status || !status.pre_lists) return 0;
  if (!Array.isArray(status.pre_lists) || status.pre_lists.length !== 7) return 0;
  const preList = status.pre_lists[weekdayIndex];
  return Array.isArray(preList) ? preList.length : 0;
};

const getPreFilesTotalDuration = () => {
  const preFiles = getCurrentPreFiles();
  return calculateFilesTotalDuration(preFiles);
};
</script>
