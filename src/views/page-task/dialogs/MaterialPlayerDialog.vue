<template>
  <ion-modal
    :is-open="isOpen"
    @did-dismiss="handleDismiss"
    class="[--width:100%] [--height:100%] [--border-radius:0] [--box-shadow:none]"
  >
    <ion-content class="p-0 h-full [--overflow:hidden] [--padding-top:0] overflow-hidden" :scroll-y="false">
      <!-- 浮动关闭按钮 + 标题（仅浮层偏移，不占用内容区高度） -->
      <div
        class="absolute inset-x-0 top-0 z-50 flex items-start gap-3 px-4 pt-3 max-md:pt-[max(0.75rem,env(safe-area-inset-top,0px),28px)] pointer-events-none"
      >
        <div class="pointer-events-auto flex items-start gap-3 min-w-0 max-w-full">
          <ion-button
            @click="handleDismiss"
            fill="clear"
            color="light"
            size="small"
            class="bg-gray-500/90 rounded-full shrink-0 m-0 w-8 h-8 min-h-8 [--padding-start:0] [--padding-end:0]"
          >
            <ion-icon :icon="closeOutline" class="text-lg" />
          </ion-button>
          <span
            v-if="!isLandscape"
            class="text-gray-500 text-lg font-bold truncate drop-shadow-sm min-w-0 flex-1 max-w-[calc(100vw-5rem)]"
            :title="material?.name"
          >{{ displayMaterialName }}</span>
        </div>
      </div>

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
          
          <div class="flex-1 flex justify-end items-center gap-2 min-w-0">
            <span
              v-if="isLandscape"
              class="text-gray-500 text-sm font-bold truncate min-w-0 max-w-40"
              :title="material?.name"
            >{{ displayMaterialName }}</span>
            <ion-button v-if="isAdmin || currentPage >= getLastPagePosition" color="success" :disabled="isMaterialCompleted || submitting" @click="completeReading">
              完成
            </ion-button>
          </div>
        </div>
      </div>

      <!-- 视频播放器 -->
      <div v-else-if="material?.type === 1" class="flex flex-col h-full">
        <div class="flex-1 relative overflow-hidden bg-black">
          <video
            v-if="videoReady"
            ref="videoRef"
            :src="getMediaFileUrl(material.path || '')"
            controls
            autoplay
            preload="metadata"
            playsinline
            webkit-playsinline="true"
            x5-playsinline="true"
            x5-video-player-type="h5-page"
            controlslist="nodownload nofullscreen noremoteplayback"
            disablePictureInPicture
            class="w-full h-full object-contain [&::cue]:bg-black/65 [&::cue]:text-white [&::cue]:text-base [&::cue]:leading-snug"
            @ended="handleVideoEnded"
            @play="isVideoPlaying = true"
            @pause="isVideoPlaying = false"
            @loadedmetadata="syncSubtitleTracks"
          >
            <track
              v-for="(track, index) in subtitleTracks"
              :key="`${track.src}-${index}`"
              kind="subtitles"
              :src="track.src"
              :srclang="track.lang"
              :label="track.label"
            />
          </video>
          <div v-if="loading" class="absolute inset-0 flex justify-center items-center bg-black bg-opacity-80">
            <ion-spinner name="crescent" class="text-white text-4xl"></ion-spinner>
          </div>
          <div v-if="videoLocked" class="absolute inset-0 z-10 flex flex-col justify-center items-center bg-black/80">
            <div class="text-white/90 text-lg mb-2">{{ lockReason || '视频观看超时' }}</div>
            <div class="text-gray-400 text-sm mb-4">已达到观看时长限制</div>
            <ion-button
              fill="outline"
              color="warning"
              size="small"
              :disabled="unlocking"
              @click="showUnlockAlert"
            >
              {{ unlocking ? '申请中...' : '申请解锁' }}
            </ion-button>
          </div>
        </div>
        
        <!-- 操作区 -->
        <div class="flex justify-between items-center p-4 border-t bg-white">
          <div class="flex-1 flex items-center gap-2 min-w-0">
            <ion-button
              @click="handleDismiss"
              fill="clear"
              color="medium"
              class="shrink-0 m-0 w-8 h-8 min-h-8 [--padding-start:0] [--padding-end:0]"
            >
              <ion-icon :icon="closeOutline" />
            </ion-button>
            <ion-button
              :disabled="!subtitleTracks.length"
              fill="outline"
              :color="activeSubtitleIndex >= 0 ? 'primary' : 'medium'"
              @click="toggleSubtitle"
            >
              字幕
            </ion-button>
          </div>
          
          <div class="flex-1 flex justify-end items-center gap-2 min-w-0">
            <span
              v-if="isLandscape"
              class="text-gray-500 text-sm font-bold truncate min-w-0 max-w-40"
              :title="material?.name"
            >{{ displayMaterialName }}</span>
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
import { addUsage, type AddUsageBody, USAGE_TYPE_PDF, USAGE_TYPE_VIDEO } from '@/api';
import { finishMaterial, requestUnlockMaterial } from '@/api/api-task';
import { apiClient } from '@/api/api-client';
import AudioPreview from '@/components/AudioPreview.vue';
import EventBus, { C_EVENT } from '@/types/event-bus';
import { getMediaFileUrl } from '@/utils/file';
import { getPDFPage, loadPDF, renderPDFPageToCanvas } from '@/utils/pdf-lib';
import {
    applySubtitleTrack,
    hideAllSubtitleTracks,
    resolveSubtitleTracks,
    revokeSubtitleTracks,
    type ResolvedSubtitleTrack,
} from '@/utils/subtitle';
import {
    IonButton,
    IonContent,
    IonIcon,
    IonModal,
    IonSpinner,
    alertController,
} from '@ionic/vue';
import { chevronBackOutline, chevronForwardOutline, closeOutline, pauseOutline, playOutline } from 'ionicons/icons';
import { computed, inject, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';

const globalVar: any = inject('globalVar');

// 是否为 admin
const isAdmin = computed(() => {
    return globalVar?.user?.admin === 1;
});

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
const subtitleTracks = ref<ResolvedSubtitleTrack[]>([]);
const activeSubtitleIndex = ref(-1);
let subtitleLoadToken = 0;

// 音频信息
const audioInfo = ref('');
const currentAudioSrcLst = ref<string[]>([]);
const audioPreviewRef = ref<any>(null);

// 使用统计相关
let usageTimer: number | null = null;
let usageStartTime: number = 0;
let isTrackingActive: boolean = false; // 追踪是否活跃（页面可见且视频播放中）

// 视频锁定轮询（播放过程中每分钟检查一次）
const VIDEO_LOCK_POLL_MS = 60_000;
let videoLockPollTimer: number | null = null;
const videoLocked = ref(false);
const lockReason = ref('');
const lockCode = ref(0);
const unlocking = ref(false);
const videoReady = ref(false);

// 监听 AudioPreview 的播放状态
const isAudioPlaying = computed(() => {
    return audioPreviewRef.value?.isPlaying || false;
});

// 监听当前播放索引
const audioIdx = computed(() => {
    return audioPreviewRef.value?.playIdx || 0;
});

const MATERIAL_NAME_MAX_LEN = 24;

const displayMaterialName = computed(() => {
    const name = props.material?.name?.trim() || '';
    if (name.length <= MATERIAL_NAME_MAX_LEN) return name;
    return `${name.slice(0, MATERIAL_NAME_MAX_LEN)}…`;
});

// Canvas 样式（由 flex 容器约束尺寸，避免 vh 在 UC 等浏览器下计算不准）
const canvasStyle = computed(() => {
    if (isLandscape.value) {
        return {
            maxWidth: '46vw',
            maxHeight: '100%',
            width: 'auto',
            height: 'auto',
        };
    }
    return {
        maxWidth: '100%',
        maxHeight: '100%',
        width: 'auto',
        height: 'auto',
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

// 关闭弹窗（先关 UI，统计上报放后台，避免等网络）
const clearSubtitleTracks = () => {
    hideAllSubtitleTracks(videoRef.value);
    revokeSubtitleTracks(subtitleTracks.value);
    subtitleTracks.value = [];
    activeSubtitleIndex.value = -1;
};

const loadVideoSubtitles = async (videoPath: string) => {
    const token = ++subtitleLoadToken;
    clearSubtitleTracks();

    const tracks = await resolveSubtitleTracks(videoPath);
    if (token !== subtitleLoadToken) {
        revokeSubtitleTracks(tracks);
        return;
    }

    subtitleTracks.value = tracks;
    activeSubtitleIndex.value = -1;
    await nextTick();
    syncSubtitleTracks();
};

const syncSubtitleTracks = () => {
    if (activeSubtitleIndex.value >= 0) {
        applySubtitleTrack(videoRef.value, activeSubtitleIndex.value);
    } else {
        hideAllSubtitleTracks(videoRef.value);
    }
};

const toggleSubtitle = () => {
    if (!subtitleTracks.value.length || !videoRef.value) return;

    if (activeSubtitleIndex.value < 0) {
        activeSubtitleIndex.value = 0;
    } else {
        const next = activeSubtitleIndex.value + 1;
        activeSubtitleIndex.value = next >= subtitleTracks.value.length ? -1 : next;
    }

    if (activeSubtitleIndex.value >= 0) {
        applySubtitleTrack(videoRef.value, activeSubtitleIndex.value);
    } else {
        hideAllSubtitleTracks(videoRef.value);
    }
};

const handleDismiss = () => {
    if (!props.isOpen) return;
    stopVideoLockPolling();
    emit('update:isOpen', false);
    stopAudio();
    void stopUsageTracking();
    pauseVideo();
    clearSubtitleTracks();
};

const checkVideoLock = async (): Promise<{ locked: boolean; reason: string; lockCode: number }> => {
    const userId = props.userId;
    const materialId = props.material?.id;
    const taskId = props.task?.id;
    if (!userId || !materialId) return { locked: false, reason: '', lockCode: 0 };

    try {
        const params: any = { userId, materialId };
        if (taskId) {
            params.taskId = taskId;
        }
        const rsp = await apiClient.get<{ code: number; data?: { lock?: number; reason?: string; duration?: number } }>(
            '/material/status',
            { params }
        );
        const data = rsp.data.data;
        if (rsp.data.code === 0 && data?.lock && data.lock > 0) {
            return { locked: true, reason: data?.reason || '已禁用', lockCode: data.lock };
        }
        return { locked: false, reason: '', lockCode: 0 };
    } catch (error: unknown) {
        console.error('获取素材状态失败:', error);
        return { locked: false, reason: '', lockCode: 0 };
    }
};

const stopVideoLockPolling = () => {
    if (videoLockPollTimer !== null) {
        clearInterval(videoLockPollTimer);
        videoLockPollTimer = null;
    }
};

const setVideoLocked = (reason: string, code: number = 0) => {
    if (videoLocked.value) return;
    videoLocked.value = true;
    lockReason.value = reason || '视频观看超时';
    lockCode.value = code;
    stopVideoLockPolling();
    pauseVideo();
};

/** 弹出申请解锁时长选择 */
const showUnlockAlert = async () => {
    const alert = await alertController.create({
        header: '申请解锁',
        message: '选择申请解锁时长：',
        buttons: [
            {
                text: '取消',
                role: 'cancel',
            },
            {
                text: '申请',
                handler: async () => {
                    await doRequestUnlock(60);
                },
            },
        ],
    });
    await alert.present();
};

/** 执行申请解锁请求 */
const doRequestUnlock = async (duration: number) => {
    const userId = props.userId;
    const materialId = props.material?.id;
    if (!userId || !materialId || !props.task?.id) return;

    unlocking.value = true;
    try {
        const res = await requestUnlockMaterial(materialId, userId, props.task?.id, duration, lockCode.value);
        // 申请已提交/更新，提示等待审批
        const successAlert = await alertController.create({
            header: res.replaced ? '申请已更新' : '申请已提交',
            message: res.replaced
                ? '已有待审批申请，已更新为最新提交，等待管理员审批后生效'
                : '不限时申请已提交，等待管理员审批后生效',
            buttons: ['确定'],
        });
        await successAlert.present();
    } catch (e: any) {
        console.error('申请解锁失败:', e);
        const errAlert = await alertController.create({
            header: '申请失败',
            message: e?.message || '请稍后重试',
            buttons: ['确定'],
        });
        await errAlert.present();
    } finally {
        unlocking.value = false;
    }
};

const pollVideoLockStatus = async () => {
    if (!props.isOpen || props.material?.type !== 1 || videoLocked.value) return;
    const result = await checkVideoLock();
    if (result.locked) {
        setVideoLocked(result.reason, result.lockCode);
    }
};

const startVideoLockPolling = () => {
    if (props.material?.type !== 1) return;
    stopVideoLockPolling();
    videoLockPollTimer = window.setInterval(() => {
        void pollVideoLockStatus();
    }, VIDEO_LOCK_POLL_MS);
};

const pauseVideo = () => {
    if (!videoRef.value) return;
    try {
        videoRef.value.pause();
        isVideoPlaying.value = false;
    } catch (e) {
        console.warn('Error pausing video:', e);
    }
};

/** UC / 微信 X5 内核：同层播放，避免全屏原生控件盖住页面关闭按钮 */
const applyVideoCompat = () => {
    const el = videoRef.value;
    if (!el) return;
    el.setAttribute('playsinline', 'true');
    el.setAttribute('webkit-playsinline', 'true');
    el.setAttribute('x5-playsinline', 'true');
    el.setAttribute('x5-video-player-type', 'h5-page');
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
    
    const userId = props.userId || globalVar?.user?.id;
    if (!userId) {
        console.warn('无法获取 userId，跳过使用统计');
        return;
    }
    
    // 清除之前的定时器
    if (usageTimer !== null) {
        clearInterval(usageTimer);
        usageTimer = null;
    }
    
    usageStartTime = Date.now();
    isTrackingActive = true;
    
    usageTimer = window.setInterval(() => {
        if (isTrackingActive) {
            reportUsageAndReset();
        }
    }, 30000);
};

// 停止使用统计追踪
const stopUsageTracking = (shouldReport: boolean = true) => {
    if (!isTrackingActive && usageStartTime === 0) {
        return;
    }

    if (usageTimer !== null) {
        clearInterval(usageTimer);
        usageTimer = null;
    }

    const capturedStartTime = usageStartTime;
    const wasActive = isTrackingActive;
    isTrackingActive = false;
    usageStartTime = 0;

    if (shouldReport && wasActive && capturedStartTime > 0) {
        const duration = Math.floor((Date.now() - capturedStartTime) / 1000);
        if (duration > 0) {
            void reportUsage(duration, capturedStartTime, true);
        }
    }
};

// 上报使用记录并重置计时器
const reportUsageAndReset = async () => {
    if (!props.material || usageStartTime === 0) return;
    
    const now = Date.now();
    const duration = Math.floor((now - usageStartTime) / 1000);
    
    if (duration <= 0) return;
    
    await reportUsage(duration);
    usageStartTime = now;
};

// 上报使用记录（isFinalReport：关闭弹窗时的末次上报，不要求视频仍在播放）
const reportUsage = async (duration: number, startTime?: number, isFinalReport = false) => {
    if (!props.material) return;

    const userId = props.userId || globalVar?.user?.id;
    if (!userId) {
        console.warn('无法获取 userId，跳过上报');
        return;
    }

    if (!isFinalReport && props.material.type === 1 && !isVideoPlaying.value) {
        return;
    }

    if (duration <= 0) return;

    const usageStart = startTime ?? usageStartTime;
    if (!usageStart) return;

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
            start_time: new Date(usageStart).toISOString(),
            duration: duration,
            user_id: userId,
            out_key: props.material.id,
        };

        await addUsage(usageData);
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
    } catch (error: any) {
        console.error('保存失败:', error);
        EventBus.$emit(C_EVENT.TOAST, error?.message || '完成失败，请稍后重试');
    } finally {
        submitting.value = false;
    }
};

// 监听弹窗打开和素材变化
watch(
    () => [props.isOpen, props.material] as const,
    async ([isOpen, material]) => {
        if (isOpen && material) {
            if (material.type === 1) {
                const lockResult = await checkVideoLock();
                if (lockResult.locked) {
                    setVideoLocked(lockResult.reason, lockResult.lockCode);
                    return;
                }
            }

            loading.value = true;
            
            setTimeout(async () => {
                if (material.type === 0 && material.path) {
                    if (!pdfCanvasLeft.value) {
                        loading.value = false;
                        return;
                    }
                    renderPDF(getMediaFileUrl(material.path));
                    startUsageTracking();
                } else if (material.type === 1 && material.path) {
                    videoReady.value = true;
                    await nextTick();
                    loading.value = false;
                    applyVideoCompat();
                    void loadVideoSubtitles(material.path);
                    startUsageTracking();
                    startVideoLockPolling();
                } else {
                    loading.value = false;
                }
            }, 300);
        } else {
            loading.value = false;
            stopVideoLockPolling();
            videoLocked.value = false;
            lockReason.value = '';
            lockCode.value = 0;
            videoReady.value = false;
            clearSubtitleTracks();
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
        isTrackingActive = false;
    } else {
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
                    }
                }
            }
        }
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
    stopVideoLockPolling();
    window.removeEventListener('resize', checkOrientation);
    document.removeEventListener('visibilitychange', handleVisibilityChange);
    window.removeEventListener('beforeunload', handleBeforeUnload);
    clearSubtitleTracks();
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
});
</script>
