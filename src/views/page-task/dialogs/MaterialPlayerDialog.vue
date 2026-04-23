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
              <!-- 右页（横屏时显示，但最后一页且总页数为奇数时不显示） -->
              <canvas v-if="isLandscape && !isLastPageOdd" ref="pdfCanvasRight" class="shadow-md bg-white object-contain" :style="canvasStyle"></canvas>
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
                {{ currentAudioSrcs.length > 1 ? `(${audioIdx + 1}/${currentAudioSrcs.length})` : '' }}
            </div>
          </div>
          
          <div class="flex gap-2">
            <ion-button fill="outline" :disabled="currentPage === 1" @click="prevPage">
              <ion-icon slot="icon-only" :icon="chevronBackOutline" />
            </ion-button>
            <ion-button fill="outline" :disabled="!currentAudioSrcs.length" @click="playAudio">
              <ion-icon slot="icon-only" :icon="isAudioPlaying ? pauseOutline : playOutline" />
            </ion-button>
            <ion-button fill="outline" :disabled="currentPage >= getLastPagePosition" @click="nextPage">
              <ion-icon slot="icon-only" :icon="chevronForwardOutline" />
            </ion-button>
          </div>
          
          <div class="flex-1 flex justify-end">
            <ion-button v-if="currentPage >= getLastPagePosition" color="success" :disabled="isMaterialCompleted" @click="completeReading">
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
import { ref, watch, computed, onMounted, onUnmounted } from 'vue';
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

// 判断是否是最后一页且总页数为奇数（横屏时只显示一页）
const isLastPageOdd = computed(() => {
    return isLandscape.value && 
           totalPages.value % 2 === 1 && 
           currentPage.value === totalPages.value;
});

// 判断当前素材是否已完成
const isMaterialCompleted = computed(() => {
    if (!props.material || !props.task) return false;
    
    const taskData = typeof props.task.data === 'string' 
        ? JSON.parse(props.task.data) 
        : props.task.data;
    
    if (taskData.dailyMaterials) {
        for (const dayKey in taskData.dailyMaterials) {
            const materials = taskData.dailyMaterials[dayKey];
            const material = materials.find((m: any) => m.id === props.material?.id);
            if (material && material.status === 1) {
                return true;
            }
        }
    }
    return false;
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

    // 渲染右页（横屏时，且不是最后一页奇数情况）
    if (isLandscape.value && pdfCanvasRight.value && !isLastPageOdd.value) {
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
        audioInfo.value = ` ${audios.length} 音频`;
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
        // 不强制放大，交给工具函数按设备能力自适应缩放，避免安卓端白屏
        await renderPDFPageToCanvas(page, canvas);
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

// 获取当前应该显示的最后一页位置（用于判断按钮禁用和完成按钮显示）
const getLastPagePosition = computed(() => {
    if (isLandscape.value && totalPages.value % 2 === 1) {
        // 横屏且总页数为奇数，最后一页单独显示
        return totalPages.value;
    }
    // 其他情况，最后一页位置是 totalPages - 1（横屏）或 totalPages（竖屏）
    return isLandscape.value ? totalPages.value - 1 : totalPages.value;
});

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
    if (typeof window !== 'undefined') {
        isLandscape.value = window.innerWidth > window.innerHeight;
    }
};

onMounted(() => {
    checkOrientation();
    window.addEventListener('resize', checkOrientation);
});

onUnmounted(() => {
    window.removeEventListener('resize', checkOrientation);
});
</script>
