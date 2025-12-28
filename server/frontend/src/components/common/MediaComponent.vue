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

// 加载状态：点击播放后，在媒体文件准备好之前锁定按钮
const isLoading = ref(false);

// 格式化时长显示
const formattedDuration = computed(() => {
  return formatDuration(props.duration);
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
  if (props.isPlaying) {
    emit("play", props.file);
    return;
  }

  // 开始播放：设置加载状态并锁定按钮
  isLoading.value = true;
  emit("play", props.file);
};

// 处理进度条变化
const handleSeek = (value: number) => {
  if (!props.disabled && props.isPlaying) {
    emit("seek", props.file, value);
  }
};

// 监听播放状态和时长变化，当媒体准备好时解除锁定
watch(
  [() => props.isPlaying, () => props.duration],
  ([isPlaying, duration]) => {
    // 如果正在播放且有时长（大于0），说明媒体已准备好
    if (isPlaying && duration > 0) {
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
