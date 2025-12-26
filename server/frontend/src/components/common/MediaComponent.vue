<template>
  <div
    class="flex items-center gap-1.5 bg-gray-50 rounded border-gray-500 pr-1"
    :class="widthClass">
    <el-button
      type="plain"
      size="small"
      circle
      @click.stop="handlePlayClick"
      :disabled="disabled"
      class="!w-6 !h-6 !p-0 flex-shrink-0 mr-1">
      <span v-if="isPlaying">⏹</span>
      <el-icon v-else class="!w-3 !h-3"><Headset /></el-icon>
    </el-button>
    <el-slider
      :model-value="progress"
      :min="0"
      :max="100"
      :step="0.1"
      size="small"
      class="flex-1 min-width-[10px] player-slider"
      :show-tooltip="false"
      :disabled="!isPlaying || disabled"
      @change="handleSeek"
      @input="handleSeek"
      @click.stop>
    </el-slider>
    <span class="text-xs text-gray-600 flex-shrink-0 min-width-[35px]">
      {{ formattedDuration }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Headset } from "@element-plus/icons-vue";
import { formatDuration } from "@/utils/format";

interface FileItem {
  uri?: string;
  [key: string]: any;
}

interface Props {
  file: FileItem;
  isPlaying?: boolean;
  progress?: number;
  duration?: number;
  disabled?: boolean;
  widthClass?: string;
}

const props = withDefaults(defineProps<Props>(), {
  isPlaying: false,
  progress: 0,
  duration: 0,
  disabled: false,
  widthClass: "w-32",
});

const emit = defineEmits<{
  play: [file: FileItem];
  seek: [file: FileItem, value: number];
}>();

// 格式化时长显示
const formattedDuration = computed(() => {
  return formatDuration(props.duration);
});

// 处理播放按钮点击
const handlePlayClick = () => {
  if (!props.disabled) {
    emit("play", props.file);
  }
};

// 处理进度条变化
const handleSeek = (value: number) => {
  if (!props.disabled && props.isPlaying) {
    emit("seek", props.file, value);
  }
};
</script>

