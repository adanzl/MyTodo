<template>
  <div
    class="flex items-center gap-1.5 bg-gray-50 rounded border-gray-500 pr-1"
    :class="widthClass"
  >
    <el-button
      type="default"
      plain
      size="small"
      circle
      @click.stop="handlePlayClick"
      :disabled="isButtonDisabled"
      :loading="isLoading && !isPlaying"
      class="!w-6 !h-6 !p-0 flex-shrink-0 mr-1"
    >
      <span v-if="isPlaying">⏹</span>
      <el-icon v-else-if="!isLoading" class="!w-3 !h-3"><Headset /></el-icon>
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
      @click.stop
    >
    </el-slider>
    <span class="text-xs text-gray-600 flex-shrink-0 min-width-[35px]">
      {{ formattedDuration }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Headset } from "@element-plus/icons-vue";
import { formatDuration } from "@/utils/format";
import type { Ref } from "vue";

interface FileItem {
  uri?: string;
  path?: string;
  name?: string;
  duration?: number | null;
  [key: string]: unknown;
}

// useAudioPlayer 返回对象的类型
interface AudioPlayer {
  playingFilePath: Ref<string | null>;
  playProgress: Ref<number>;
  duration: Ref<number>;
  isPlaying: Ref<boolean>;
  isFilePlaying: (filePath: string) => boolean;
  getFilePlayProgress: (filePath: string) => number;
  getFileDuration: (filePath: string, fallbackDuration?: number) => number;
  seekFile: (filePath: string, percentage: number) => void;
}

interface Props {
  file: FileItem;
  // 如果提供了 player，则使用 player 的方法获取状态
  player?: AudioPlayer;
  // 如果没有提供 player，则使用这些 props（向后兼容）
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

// 从 file 对象中提取文件路径
const getFilePath = (file: FileItem): string => {
  return file?.uri || file?.path || file?.name || "";
};

// 加载状态：点击播放后，在媒体文件准备好之前锁定按钮
const isLoading = ref(false);

// 使用 player 或 props 获取播放状态
const isPlaying = computed(() => {
  if (props.player) {
    const filePath = getFilePath(props.file);
    return props.player.isFilePlaying(filePath);
  }
  return props.isPlaying;
});

// 使用 player 或 props 获取播放进度
const progress = computed(() => {
  if (props.player) {
    const filePath = getFilePath(props.file);
    return props.player.getFilePlayProgress(filePath);
  }
  return props.progress;
});

// 使用 player 或 props 获取时长
const duration = computed(() => {
  if (props.player) {
    const filePath = getFilePath(props.file);
    const fallbackDuration = props.file?.duration || props.duration;
    return props.player.getFileDuration(filePath, fallbackDuration);
  }
  return props.duration;
});

// 格式化时长显示
const formattedDuration = computed(() => {
  return formatDuration(duration.value);
});

// 计算按钮是否应该禁用
const isButtonDisabled = computed(() => {
  return props.disabled || isLoading.value;
});

// 处理播放按钮点击
const handlePlayClick = () => {
  if (isButtonDisabled.value) {
    return;
  }

  // 如果正在播放，直接停止（不需要锁定）
  if (isPlaying.value) {
    emit("play", props.file);
    return;
  }

  // 开始播放：设置加载状态并锁定按钮
  isLoading.value = true;
  emit("play", props.file);
};

// 处理进度条变化
const handleSeek = (value: number) => {
  if (!props.disabled && isPlaying.value) {
    // 如果提供了 player，直接使用 player 的 seekFile 方法
    if (props.player) {
      const filePath = getFilePath(props.file);
      props.player.seekFile(filePath, value);
    }
    emit("seek", props.file, value);
  }
};

// 监听播放状态和时长变化，当媒体准备好时解除锁定
watch(
  [isPlaying, duration],
  ([playing, dur]) => {
    // 如果正在播放且有时长（大于0），说明媒体已准备好
    if (playing && dur > 0) {
      isLoading.value = false;
    }
  },
  { immediate: true }
);

// 监听文件变化，切换文件时重置加载状态
watch(
  () => props.file,
  () => {
    isLoading.value = false;
  }
);
</script>

<style scoped>
/* 播放器滑块样式 */
.player-slider {
  --el-slider-button-size: 10px;
  --el-slider-button-wrapper-size: 20px;
  --el-slider-button-wrapper-offset: -9px;
}
</style>

