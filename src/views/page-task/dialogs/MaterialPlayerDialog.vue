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
      <!-- 全屏加载遮罩 -->
      <div v-if="submitting" class="absolute inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
        <ion-spinner name="crescent" class="text-white text-6xl"></ion-spinner>
      </div>
      
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
              :src="currentAudioSrcLst"
              width-class="max-w-30"
              :show-progress="false"
              :show-play-button="false"
            />
            <div class="text-sm text-gray-600">
                {{ currentAudioSrcLst.length > 1 ? `(${audioIdx + 1}/${currentAudioSrcLst.length})` : '' }}
            </div>
          </div>
          
          <div class="flex gap-2">
            <ion-button fill="outline" :disabled="currentPage === 1" @click="prevPage">
              <ion-icon slot="icon-only" :icon="chevronBackOutline" />
            </ion-button>
            <ion-button fill="outline" :disabled="!currentAudioSrcLst.length" @click="playAudio">
              <ion-icon slot="icon-only" :icon="isAudioPlaying ? pauseOutline : playOutline" />
            </ion-button>
            <ion-button fill="outline" :disabled="currentPage >= getLastPagePosition" @click="nextPage">
              <ion-icon slot="icon-only" :icon="chevronForwardOutline" />
            </ion-button>
          </div>
          
          <div class="flex-1 flex justify-end">
            <ion-button v-if="currentPage >= getLastPagePosition" color="success" :disabled="isMaterialCompleted || submitting" @click="completeReading">
              完成
            </ion-button>
          </div>
        </div>
      </div>

      <!-- 视频播放器 -->
      <div v-else-if="material?.type === 1" class="flex flex-col h-full">
        <div class="flex-1 relative overflow-hidden bg-black">
          <video
            ref="videoRef"
            :src="getMediaFileUrl(material.path || '')"
            controls
            autoplay
            preload="metadata"
            playsinline
            class="w-full h-full object-contain"
            @ended="handleVideoEnded"
            @play="isVideoPlaying = true"
            @pause="isVideoPlaying = false"
          />
          <div v-if="loading" class="absolute inset-0 flex justify-center items-center bg-black bg-opacity-80">
            <ion-spinner name="crescent" class="text-white text-4xl"></ion-spinner>
          </div>
        </div>
        
        <!-- 操作区 -->
        <div class="flex justify-between items-center p-4 border-t bg-white">
          <div class="flex-1"></div>
          
          <div class="flex gap-2">
            <ion-button fill="outline" @click="toggleVideoPlay">
              <ion-icon slot="icon-only" :icon="isVideoPlaying ? pauseOutline : playOutline" />
            </ion-button>
          </div>
          
          <div class="flex-1 flex justify-end">
            <ion-button color="success" :disabled="isMaterialCompleted || submitting" @click="completeReading">
              完成
            </ion-button>
          </div>
        </div>
      </div>
    </ion-content>
  </ion-modal>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted, onUnmounted, inject } from 'vue';
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
import { finishMaterial } from '@/api/api-task';
import { addUsage, type AddUsageBody, USAGE_TYPE_VIDEO, USAGE_TYPE_PDF } from '@/api';
import EventBus, { C_EVENT } from '@/types/event-bus';

const globalVar: any = inject('globalVar');

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
    userId?: number;
    date?: string; // 素材对应的日期
}>();

const emit = defineEmits<{
    (e: 'update:isOpen', value: boolean): void;
    (e: 'completed'): void; // 完成素材阅读后触发
}>();

const pdfCanvasLeft = ref<HTMLCanvasElement | null>(null);
const pdfCanvasRight = ref<HTMLCanvasElement | null>(null);
const videoRef = ref<HTMLVideoElement | null>(null);
const loading = ref(false);
const submitting = ref(false); // 提交状态
const currentPage = ref(1);
const totalPages = ref(0);
const isLandscape = ref(false);
let currentPdf: any = null;

// 视频信息
const isVideoPlaying = ref(false);

// 音频信息
const audioInfo = ref('');
const currentAudioSrcLst = ref<string[]>([]);
const audioPreviewRef = ref<any>(null);

// 使用统计相关
let usageTimer: number | null = null;
let usageStartTime: number = 0;
let isTrackingActive: boolean = false; // 追踪是否活跃（页面可见且视频播放中）

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
    
    const userId = props.userId;
    if (!userId) return false;
    
    const taskData = typeof props.task.data === 'string' 
        ? JSON.parse(props.task.data) 
        : props.task.data;
    
    if (taskData.dailyMaterials && props.date) {
        // 只检查当前日期下的素材状态
        const materials = taskData.dailyMaterials[props.date];
        if (materials) {
            const material = materials.find((m: any) => m.id === props.material?.id);
            // status 现在是 Record<string, number>，key 为 user_id
            if (material && material.status) {
                return material.status[String(userId)] === 1;
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
        currentAudioSrcLst.value = audios.map((audio: any) => getMediaFileUrl(audio.path));
    } else {
        audioInfo.value = '无音频';
        currentAudioSrcLst.value = [];
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
    if (!currentAudioSrcLst.value.length) return;
    audioPreviewRef.value?.togglePlay();
};

// 停止音频
const stopAudio = () => {
    currentAudioSrcLst.value = [];
};

// 开始使用统计追踪
const startUsageTracking = () => {
    if (!props.material) return;
    
    // 如果 userId 为空，尝试从全局变量获取
    const userId = props.userId || globalVar?.user?.id;
    if (!userId) {
        console.warn('无法获取 userId，跳过使用统计');
        return;
    }
    
    console.log('开始使用统计追踪，素材类型:', props.material.type, 'userId:', userId);
    
    // 记录开始时间
    usageStartTime = Date.now();
    isTrackingActive = true;
    
    // 清除之前的定时器
    stopUsageTracking(false); // 不上报
    
    // 设置定时器，每30秒上报一次
    usageTimer = window.setInterval(() => {
        if (isTrackingActive) {
            reportUsageAndReset();
        }
    }, 30000);
};

// 停止使用统计追踪
const stopUsageTracking = async (shouldReport: boolean = true) => {
    console.log('stopUsageTracking 调用, shouldReport:', shouldReport, 'isTrackingActive:', isTrackingActive, 'usageStartTime:', usageStartTime);
    
    if (usageTimer !== null) {
        clearInterval(usageTimer);
        usageTimer = null;
    }
    
    // 如果需要上报且正在追踪
    if (shouldReport && isTrackingActive && usageStartTime > 0) {
        const now = Date.now();
        const duration = Math.floor((now - usageStartTime) / 1000);
        console.log('停止追踪，计算时长:', duration, '秒');
        await reportUsage(duration);
    } else {
        console.log('不上报原因 - shouldReport:', shouldReport, 'isTrackingActive:', isTrackingActive, 'usageStartTime:', usageStartTime);
    }
    
    isTrackingActive = false;
    usageStartTime = 0;
};

// 上报使用记录并重置计时器
const reportUsageAndReset = async () => {
    if (!props.material || usageStartTime === 0) return;
    
    const now = Date.now();
    const duration = Math.floor((now - usageStartTime) / 1000);
    
    if (duration <= 0) return;
    
    console.log('定时上报，时长:', duration);
    await reportUsage(duration);
    
    // 重置开始时间，继续下一轮统计
    usageStartTime = now;
};

// 上报使用记录
const reportUsage = async (duration: number) => {
    if (!props.material) return;
    
    // 如果 userId 为空，尝试从全局变量获取
    const userId = props.userId || globalVar?.user?.id;
    if (!userId) {
        console.warn('无法获取 userId，跳过上报');
        return;
    }
    
    // 视频素材特殊规则：检查是否在播放中
    if (props.material.type === 1 && !isVideoPlaying.value) {
        console.log('视频未在播放，跳过上报');
        return;
    }
    
    if (duration <= 0) {
        console.log('使用时长为0，跳过上报');
        return;
    }
    
    console.log('准备上报使用记录:', {
        type: props.material.type,
        duration: duration,
        userId: userId,
        materialId: props.material.id
    });
    
    // 根据素材类型确定 type
    let usageType = '';
    if (props.material.type === 0) {
        usageType = USAGE_TYPE_PDF;
    } else if (props.material.type === 1) {
        usageType = USAGE_TYPE_VIDEO;
    }
    
    if (!usageType) return;
    
    try {
        const usageData: AddUsageBody = {
            type: usageType,
            start_time: new Date(usageStartTime).toISOString(),
            duration: duration,
            user_id: userId,
            out_key: props.material.id,
        };
        
        console.log('发送上报请求:', usageData);
        await addUsage(usageData);
        console.log('上报成功');
    } catch (error) {
        console.error('上报使用记录失败:', error);
    }
};

// 完成阅读
const completeReading = async () => {
    if (!props.material || !props.task || !props.date || !props.userId) return;
    
    submitting.value = true;
    try {
        const userId = props.userId;
        
        // 使用服务端接口完成素材打卡
        const result = await finishMaterial(
            props.task.id,
            props.material.id,
            props.date, // 使用传入的日期
            userId
        );
        
        // 如果获得积分，弹出奖励弹窗
        if (result.score > 0) {
            EventBus.$emit(C_EVENT.REWARD, {
                value: result.score,
                rewardType: 'points',
            });
        }
        
        // 通知父组件刷新列表
        emit('completed');
        
        console.log('完成阅读，已保存');
        handleDismiss();
    } catch (error) {
        console.error('保存失败:', error);
    } finally {
        submitting.value = false;
    }
};

// 监听弹窗打开和素材变化
watch(
    () => [props.isOpen, props.material] as const,
    ([isOpen, material]) => {
        if (isOpen && material) {
            loading.value = true;
            
            setTimeout(() => {
                if (material.type === 0 && material.path) {
                    // PDF 类型
                    if (!pdfCanvasLeft.value) {
                        loading.value = false;
                        return;
                    }
                    renderPDF(getMediaFileUrl(material.path));
                    // 开始使用统计
                    startUsageTracking();
                } else if (material.type === 1 && material.path) {
                    // 视频类型
                    loading.value = false;
                    // 视频会自动加载和播放
                    // 开始使用统计
                    startUsageTracking();
                } else {
                    loading.value = false;
                    console.log('未满足启动条件');
                }
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

// 监听页面可见性变化（锁屏/切后台时暂停统计）
const handleVisibilityChange = () => {
    if (document.hidden) {
        console.log('页面隐藏，暂停使用统计');
        isTrackingActive = false;
    } else {
        console.log('页面可见，恢复使用统计');
        // 重置开始时间为当前时间，避免计入隐藏期间的时长
        if (usageStartTime > 0) {
            usageStartTime = Date.now();
        }
        isTrackingActive = true;
    }
};

// 监听浏览器关闭事件
const handleBeforeUnload = () => {
    if (isTrackingActive && usageStartTime > 0) {
        const now = Date.now();
        const duration = Math.floor((now - usageStartTime) / 1000);
        
        if (duration > 0 && props.material) {
            const userId = props.userId || globalVar?.user?.id;
            if (userId) {
                let usageType = '';
                if (props.material.type === 0) {
                    usageType = USAGE_TYPE_PDF;
                } else if (props.material.type === 1) {
                    usageType = USAGE_TYPE_VIDEO;
                }
                
                if (usageType) {
                    // 使用 sendBeacon 确保浏览器关闭时也能发送
                    const apiUrl = window.location.origin + '/usage/add';
                    const data = JSON.stringify({
                        type: usageType,
                        start_time: new Date(usageStartTime).toISOString(),
                        duration: duration,
                        user_id: userId,
                        out_key: props.material.id,
                    });
                    
                    if (navigator.sendBeacon) {
                        navigator.sendBeacon(apiUrl, new Blob([data], { type: 'application/json' }));
                        console.log('通过 sendBeacon 上报最后时长:', duration);
                    }
                }
            }
        }
    }
};

// 切换视频播放/暂停
const toggleVideoPlay = () => {
    if (!videoRef.value) return;
    if (isVideoPlaying.value) {
        videoRef.value.pause();
    } else {
        videoRef.value.play();
    }
};

// 视频播放结束处理
const handleVideoEnded = () => {
    isVideoPlaying.value = false;
};

onMounted(() => {
    checkOrientation();
    window.addEventListener('resize', checkOrientation);
    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('beforeunload', handleBeforeUnload);
});

onUnmounted(() => {
    window.removeEventListener('resize', checkOrientation);
    document.removeEventListener('visibilitychange', handleVisibilityChange);
    window.removeEventListener('beforeunload', handleBeforeUnload);
    // 清理视频资源
    if (typeof window !== 'undefined' && videoRef.value) {
        try {
            videoRef.value.pause();
            videoRef.value.src = '';
            videoRef.value.load();
        } catch (e) {
            console.warn('Error cleaning up video element:', e);
        }
    }
    // 最后再停止统计并上报
    stopUsageTracking();
});
</script>
