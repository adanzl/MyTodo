<template>
  <ion-modal :is-open="isOpen" @did-dismiss="handleDismiss" :presenting-element="$parent.$el"
  class="[--width:100%] [--height:100%] [--border-radius:0] [--box-shadow:none]"
  >
    <ion-header>
      <ion-toolbar>
        <ion-buttons slot="start">
          <ion-button @click="handleDismiss">
            <ion-icon :icon="closeOutline" />
          </ion-button>
        </ion-buttons>
        <ion-title>{{ material?.name }}</ion-title>
      </ion-toolbar>
    </ion-header>

    <ion-content class="p-0">
      <!-- PDF 播放器 -->
      <div class="flex justify-center items-center min-h-full">
        <canvas ref="pdfCanvas" class="max-w-full h-auto shadow-md"></canvas>
      </div>

    </ion-content>
  </ion-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import {
    IonModal,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonButtons,
    IonButton,
    IonContent,
    IonIcon,
} from '@ionic/vue';
import { closeOutline } from 'ionicons/icons';
import { loadPDF, getPDFPage, renderPDFPageToCanvas } from '@/utils/pdf-lib';

interface Material {
    id: number;
    name: string;
    type: number; // 0: PDF, 1: Audio, 2: Video
    url?: string;
}

const props = defineProps<{
    isOpen: boolean;
    material: Material | null;
}>();

const emit = defineEmits<{
    (e: 'update:isOpen', value: boolean): void;
}>();

const pdfCanvas = ref<HTMLCanvasElement | null>(null);
const audioPlayer = ref<HTMLAudioElement | null>(null);
const videoPlayer = ref<HTMLVideoElement | null>(null);

// 关闭弹窗
const handleDismiss = () => {
    emit('update:isOpen', false);

    // 停止播放
    if (audioPlayer.value) {
        audioPlayer.value.pause();
    }
    if (videoPlayer.value) {
        videoPlayer.value.pause();
    }
};


// 渲染 PDF
const renderPDF = async (url: string) => {
    if (!pdfCanvas.value) return;

    try {
        const pdf = await loadPDF(url);
        const page = await getPDFPage(pdf, 1);
        await renderPDFPageToCanvas(page, pdfCanvas.value, 1.5);
    } catch (error) {
        console.error('PDF 渲染失败:', error);
    }
};

// 监听弹窗打开和素材变化
watch(
    () => [props.isOpen, props.material] as const,
    ([isOpen, material]) => {
        if (isOpen && material) {
            if (material.type === 0 && material.url) {
                // 延迟渲染，等待 DOM 更新
                setTimeout(() => {
                    renderPDF(material.url);
                }, 100);
            }
        }
    }
);
</script>
