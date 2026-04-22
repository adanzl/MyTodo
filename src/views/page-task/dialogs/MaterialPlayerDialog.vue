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
      <div v-if="material?.type === 0" class="flex flex-col h-full">
        <div class="flex-1 relative overflow-hidden bg-gray-100">
          <div class="absolute inset-0 flex items-center justify-center p-4">
            <div class="flex gap-2 max-w-full max-h-full" :class="isLandscape ? 'flex-row' : 'flex-col'">
              <!-- 左页/单页 -->
              <canvas ref="pdfCanvasLeft" class="shadow-md bg-white object-contain" :style="canvasStyle"></canvas>
              <!-- 右页（横屏时显示） -->
              <canvas v-if="isLandscape" ref="pdfCanvasRight" class="shadow-md bg-white object-contain" :style="canvasStyle"></canvas>
            </div>
          </div>
          <div v-if="loading" class="absolute inset-0 flex justify-center items-center bg-white bg-opacity-80">
            <ion-spinner name="crescent" class="text-4xl"></ion-spinner>
          </div>
        </div>
        
        <!-- 操作区 -->
        <div class="flex justify-between items-center p-4 border-t bg-white">
          <div class="flex-1 flex items-center gap-2">
            <!-- 音频播放信息 -->
            <AudioPreview 
              ref="audioPreviewRef"
              :src="currentAudioSrcs"
              width-class="max-w-30"
              :show-progress="false"
              :show-play-button="false"
            />
            <div class="text-sm text-gray-600">
                {{ audioInfo }} {{ currentAudioSrcs.length > 1 ? `(${audioIdx + 1}/${currentAudioSrcs.length})` : '' }}
            </div>
          </div>
          
          <div class="flex gap-2">
            <ion-button fill="outline" :disabled="currentPage === 1" @click="prevPage">
              <ion-icon slot="icon-only" :icon="chevronBackOutline" />
            </ion-button>
            <ion-button fill="outline" :disabled="!currentAudioSrcs.length" @click="playAudio">
              <ion-icon slot="icon-only" :icon="isAudioPlaying ? pauseOutline : playOutline" />
            </ion-button>
            <ion-button fill="outline" :disabled="currentPage >= totalPages - (isLandscape ? 1 : 0)" @click="nextPage">
              <ion-icon slot="icon-only" :icon="chevronForwardOutline" />
            </ion-button>
          </div>
          
          <div class="flex-1 flex justify-end">
            <ion-button v-if="currentPage >= totalPages - (isLandscape ? 1 : 0)" color="success" @click="completeReading">
              完成
            </ion-button>
          </div>
        </div>
      </div>

      <!-- 未知类型 -->
      <div v-else class="text-center py-10 text-gray-500">
        <p>不支持的素材类型</p>
      </div>
    </ion-content>
  </ion-modal>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import {
    IonModal,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonButtons,
    IonButton,
    IonContent,
    IonIcon,
    IonSpinner,
} from '@ionic/vue';
import { closeOutline, chevronBackOutline, chevronForwardOutline, playOutline, pauseOutline } from 'ionicons/icons';
import { loadPDF, getPDFPage, renderPDFPageToCanvas } from '@/utils/pdf-lib';
import { getMediaFileUrl } from '@/utils/file';
import AudioPreview from '@/components/AudioPreview.vue';
import { updateTask, type Task } from '@/api/api-task';

interface Material {
    id: number;
    name: string;
    type: number; // 0: PDF, 1: Audio, 2: Video
    path?: string;
    data?: any;
}

const props = defineProps<{
    isOpen: boolean;
    material: Material | null;
    task: any | null;
}>();

const emit = defineEmits<{
    (e: 'update:isOpen', value: boolean): void;
}>();

const pdfCanvasLeft = ref<HTMLCanvasElement | null>(null);
const pdfCanvasRight = ref<HTMLCanvasElement | null>(null);
const loading = ref(false);
const currentPage = ref(1);
const totalPages = ref(0);
const isLandscape = ref(false);
let currentPdf: any = null;

// 音频信息
const audioInfo = ref('');
const currentAudioSrcs = ref<string[]>([]);
const audioPreviewRef = ref<any>(null);

// 监听 AudioPreview 的播放状态
const isAudioPlaying = computed(() => {
    return audioPreviewRef.value?.isPlaying || false;
});

// 监听当前播放索引
const audioIdx = computed(() => {
    return audioPreviewRef.value?.playIdx || 0;
});

// Canvas 样式（竖屏时限制最大宽高）
const canvasStyle = computed(() => {
    if (isLandscape.value) {
        return {
            maxWidth: '46vw',
            maxHeight: 'calc(100vh - 120px)', // 减去 header 和操作区的高度
            width: 'auto',
            height: 'auto'
        };
    }
    return {
        maxWidth: '100%',
        maxHeight: 'calc(100vh - 150px)', // 减去 header 和操作区的高度
        width: 'auto',
        height: 'auto'
    };
});

// 关闭弹窗
const handleDismiss = () => {
    stopAudio();
    emit('update:isOpen', false);
};


// 渲染 PDF
const renderPDF = async (url: string) => {
    if (!pdfCanvasLeft.value) {
        loading.value = false;
        return;
    }

    try {
        currentPdf = await loadPDF(url);
        totalPages.value = currentPdf.numPages;
        currentPage.value = 1;
        await renderPages();
    } catch (error) {
        console.error('PDF 渲染失败:', error);
    } finally {
        loading.value = false;
    }
};

// 渲染页面
const renderPages = async () => {
    if (!currentPdf) return;

    // 翻页时停止音频播放
    stopAudio();

    // 渲染左页
    if (pdfCanvasLeft.value && currentPage.value <= totalPages.value) {
        await renderPageToCanvas(currentPage.value, pdfCanvasLeft.value);
    }

    // 渲染右页（横屏时）
    if (isLandscape.value && pdfCanvasRight.value) {
        const rightPageNum = currentPage.value + 1;
        if (rightPageNum <= totalPages.value) {
            await renderPageToCanvas(rightPageNum, pdfCanvasRight.value);
        } else {
            // 清空右页
            clearCanvas(pdfCanvasRight.value);
        }
    }

    // 更新音频信息
    const audios = getCurrentPageAudios();
    if (audios.length > 0) {
        audioInfo.value = ` ${audios.length} 个音频`;
        // 自动加载所有音频
        currentAudioSrcs.value = audios.map((audio: any) => getMediaFileUrl(audio.path));
    } else {
        audioInfo.value = '无音频';
        currentAudioSrcs.value = [];
    }
};

// 渲染单页到 canvas
const renderPageToCanvas = async (pageNum: number, canvas: HTMLCanvasElement) => {
    try {
        const page = await getPDFPage(currentPdf, pageNum);
        await renderPDFPageToCanvas(page, canvas, 1.5);
    } catch (error) {
        console.error('渲染页面失败:', error);
    }
};

// 清空 canvas
const clearCanvas = (canvas: HTMLCanvasElement) => {
    const ctx = canvas.getContext('2d');
    if (ctx) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
};

// 上一页
const prevPage = () => {
    if (currentPage.value > 1) {
        currentPage.value -= isLandscape.value ? 2 : 1;
        if (currentPage.value < 1) currentPage.value = 1;
        renderPages();
    }
};

// 下一页
const nextPage = () => {
    const step = isLandscape.value ? 2 : 1;
    if (currentPage.value < totalPages.value) {
        currentPage.value += step;
        if (currentPage.value > totalPages.value) {
            currentPage.value = totalPages.value;
        }
        renderPages();
    }
};

// 获取当前页的音频列表
const getCurrentPageAudios = () => {
    if (!props.material?.data) return [];

    const data = typeof props.material.data === 'string'
        ? JSON.parse(props.material.data)
        : props.material.data;

    const pages = data.pages || [];
    const audioList = data.audioList || [];

    // 获取当前页和下一页（横屏时）的音频 ID
    const pageIndices = isLandscape.value
        ? [currentPage.value - 1, currentPage.value]
        : [currentPage.value - 1];

    const audioIds = new Set<string>();
    pageIndices.forEach(idx => {
        if (pages[idx]) {
            pages[idx].audioIds?.forEach((id: string) => audioIds.add(id));
        }
    });

    // 根据 ID 获取音频对象
    return Array.from(audioIds)
        .map(id => audioList.find((a: any) => a.id === id))
        .filter(Boolean);
};

// 播放音频
const playAudio = () => {
    if (!currentAudioSrcs.value.length) return;
    audioPreviewRef.value?.togglePlay();
};

// 停止音频
const stopAudio = () => {
    currentAudioSrcs.value = [];
};

// 完成阅读
const completeReading = async () => {
    if (!props.material || !props.task) return;
    
    try {
        // 解析 task data
        const taskData = typeof props.task.data === 'string' 
            ? JSON.parse(props.task.data) 
            : props.task.data;
        
        // 找到当前 material 在 dailyMaterials 中的位置并更新 status
        if (taskData.dailyMaterials) {
            for (const dayKey in taskData.dailyMaterials) {
                const materials = taskData.dailyMaterials[dayKey];
                const materialIndex = materials.findIndex((m: any) => m.id === props.material?.id);
                
                if (materialIndex !== -1) {
                    // 更新 status 为 1（完成）
                    materials[materialIndex].status = 1;
                    break;
                }
            }
        }
        
        // 保存任务
        await updateTask({
            ...props.task,
            data: JSON.stringify(taskData),
        } as Task);
        
        console.log('完成阅读，已保存');
        handleDismiss();
    } catch (error) {
        console.error('保存失败:', error);
    }
};

// 监听弹窗打开和素材变化
watch(
    () => [props.isOpen, props.material] as const,
    ([isOpen, material]) => {
        console.log(material)
        if (isOpen && material && material.type === 0 && material.path) {
            loading.value = true;

            setTimeout(() => {
                if (!pdfCanvasLeft.value) {
                    loading.value = false;
                    return;
                }
                renderPDF(getMediaFileUrl(material.path));
            }, 300);
        } else {
            loading.value = false;
        }
    }
);

// 监听窗口大小变化，判断横竖屏
const checkOrientation = () => {
    isLandscape.value = window.innerWidth > window.innerHeight;
};

window.addEventListener('resize', checkOrientation);
checkOrientation();
</script>
