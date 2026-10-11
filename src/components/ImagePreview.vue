<template>
  <!--
    浮层预览：ion-modal 只作为全屏宿主，外观完全由下层的 fixed 覆盖层决定。
    参数与 src/views/page-chat/TabTtsTasks.vue 的改名浮层保持一致
    （宿主透明 + --backdrop-opacity:0，避免 Ionic 自带的背景与圆角干扰）。
  -->
  <ion-modal
    :is-open="isOpen"
    class="[--width:100%] [--height:100%] [--border-radius:0] [--box-shadow:none] [--backdrop-opacity:0] [--background:transparent]"
    @didDismiss="close">
    <div
      class="fixed inset-0 z-1 flex items-center justify-center bg-black/90"
      role="dialog"
      aria-label="图片预览"
      data-testid="image-preview-body"
      @click.self="close">
      <img
        v-if="current"
        :src="current.src"
        :alt="current.alt ?? ''"
        class="max-w-full max-h-full object-contain select-none"
        data-testid="image-preview-img" />

      <!-- 关闭：贴在右上角。用 safe-area 避开刘海/状态栏；
           写成工具类而非内联 style，因为 jsdom 会丢弃含 env() 的内联样式，
           放进样式表才能被构建产物验证到。 -->
      <button
        type="button"
        class="absolute right-4 top-[calc(env(safe-area-inset-top,0px)_+_1rem)] w-10 h-10 rounded-full bg-white/15 text-white flex items-center justify-center active:bg-white/25"
        aria-label="关闭预览"
        @click="close">
        <ion-icon :icon="closeOutline" class="w-6 h-6" />
      </button>

      <template v-if="images.length > 1">
        <button
          type="button"
          class="absolute left-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-white/15 text-white flex items-center justify-center active:bg-white/25 disabled:opacity-25"
          aria-label="上一张"
          :disabled="index <= 0"
          @click="prev">
          <ion-icon :icon="arrowBackOutline" class="w-6 h-6" />
        </button>
        <button
          type="button"
          class="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-white/15 text-white flex items-center justify-center active:bg-white/25 disabled:opacity-25"
          aria-label="下一张"
          :disabled="index >= images.length - 1"
          @click="next">
          <ion-icon :icon="arrowForwardOutline" class="w-6 h-6" />
        </button>
        <span
          class="absolute left-1/2 -translate-x-1/2 bottom-[calc(env(safe-area-inset-bottom,0px)_+_1.25rem)] rounded-full bg-white/15 px-3 py-1 text-xs text-white tabular-nums">
          {{ index + 1 }}/{{ images.length }}
        </span>
      </template>
    </div>
  </ion-modal>
</template>

<script setup lang="ts">
import { IonIcon, IonModal } from "@ionic/vue";
import { arrowBackOutline, arrowForwardOutline, closeOutline } from "ionicons/icons";
import { computed, watch } from "vue";

export interface PreviewImage {
  src: string;
  alt?: string;
}

const props = defineProps<{
  isOpen: boolean;
  images: PreviewImage[];
  /** 从第几张开始看 */
  index: number;
}>();

const emit = defineEmits<{
  (e: "update:isOpen", value: boolean): void;
  (e: "update:index", value: number): void;
}>();

const current = computed(() => props.images[props.index]);

function close() {
  emit("update:isOpen", false);
}

function prev() {
  if (props.index > 0) emit("update:index", props.index - 1);
}

function next() {
  if (props.index < props.images.length - 1) emit("update:index", props.index + 1);
}

/**
 * 图片列表可能在预览期间变短（例如发送后待发区被清空、预览图的对象 URL 同时被释放），
 * 此时索引会越界并停在空白浮层上，所以自动关闭。
 * `immediate` 是为了让"初始就是空列表"也不会打开一个空白浮层。
 */
watch(
  () => [props.isOpen, props.images.length, props.index] as const,
  ([open, len, idx]) => {
    if (!open) return;
    if (len === 0 || idx >= len) close();
  },
  { immediate: true }
);
</script>
