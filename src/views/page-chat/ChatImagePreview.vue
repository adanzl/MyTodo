<template>
  <ion-modal
    :is-open="isOpen"
    class="[--width:100%] [--height:100%] [--border-radius:0] [--box-shadow:none]"
    :initial-breakpoint="1"
    :breakpoints="[0, 1]"
    @didDismiss="close">
    <ion-header>
      <ion-toolbar>
        <ion-buttons slot="start">
          <ion-button @click="close" aria-label="关闭预览">
            <ion-icon :icon="closeOutline" class="h-6 w-6" />
          </ion-button>
        </ion-buttons>
        <ion-title class="text-sm truncate">{{ current?.alt || "图片预览" }}</ion-title>
        <ion-buttons v-if="images.length > 1" slot="end" class="mr-2">
          <ion-button :disabled="index <= 0" @click="prev" aria-label="上一张">
            <ion-icon :icon="arrowBackOutline" class="h-6 w-6" />
          </ion-button>
          <span class="text-xs opacity-70 self-center">{{ index + 1 }}/{{ images.length }}</span>
          <ion-button
            :disabled="index >= images.length - 1"
            @click="next"
            aria-label="下一张">
            <ion-icon :icon="arrowForwardOutline" class="h-6 w-6" />
          </ion-button>
        </ion-buttons>
      </ion-toolbar>
    </ion-header>
    <ion-content class="[--background:#000]">
      <div
        class="flex items-center justify-center min-h-full p-2"
        data-testid="image-preview-body"
        @click="close">
        <img
          v-if="current"
          :src="current.src"
          :alt="current.alt"
          class="max-w-full max-h-[85vh] object-contain"
          data-testid="image-preview-img"
          @click.stop />
      </div>
    </ion-content>
  </ion-modal>
</template>

<script setup lang="ts">
import {
  IonButton,
  IonButtons,
  IonContent,
  IonHeader,
  IonModal,
  IonTitle,
  IonToolbar,
} from "@ionic/vue";
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
 * 此时索引会越界并停在空白弹窗上，所以自动关闭。
 * `immediate` 是为了让"初始就是空列表"也不会打开一个空白弹窗。
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
