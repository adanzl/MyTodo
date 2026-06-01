<!-- MaterialPreviewDialog.vue - 素材预览全屏弹窗 -->
<template>
  <el-dialog
    v-model="visible"
    fullscreen
    :show-close="false"
    destroy-on-close
    class="m-0! p-0! [&_.el-dialog__header]:hidden [&_.el-dialog__body]:p-0! [&_.el-dialog__body]:h-screen [&_.el-dialog__body]:overflow-hidden"
    @close="handleClose"
  >
    <div
      v-loading="loading"
      element-loading-text="加载中..."
      element-loading-background="rgba(0, 0, 0, 0.8)"
      class="relative flex h-full w-full flex-col overflow-hidden bg-black"
    >
      <!-- PDF 双页 -->
      <div
        v-if="materialData?.type === 0"
        class="relative flex min-h-0 flex-1 items-center justify-center overflow-hidden bg-black"
      >
        <div class="flex h-full w-full max-w-full">
          <!-- 左页 -->
          <div class="relative flex flex-1 items-center justify-center overflow-hidden border-r border-black bg-[#e8e0f0]">
            <div v-if="leftPage" class="relative flex h-full w-full items-center justify-center">
              <el-image
                :src="leftPage.thumbnail"
                fit="contain"
                class="h-full w-full max-h-full max-w-full object-contain"
              >
                <template #error>
                  <div class="flex h-24 flex-col items-center justify-center gap-2.5 text-gray-500">
                    <el-icon :size="60"><Picture /></el-icon>
                    <p>图片加载失败</p>
                  </div>
                </template>
              </el-image>
              <div class="absolute bottom-5 left-7.5 text-sm font-medium text-gray-800">
                {{ currentPage * 2 - 1 }}
              </div>
            </div>
            <div v-else class="flex h-full items-center justify-center text-gray-400">
              <el-icon :size="80"><Picture /></el-icon>
            </div>
          </div>

          <!-- 右页 -->
          <div class="relative flex flex-1 items-center justify-center overflow-hidden bg-[#e8e0f0]">
            <div v-if="rightPage" class="relative flex h-full w-full items-center justify-center">
              <el-image
                :src="rightPage.thumbnail"
                fit="contain"
                class="h-full w-full max-h-full max-w-full object-contain"
              >
                <template #error>
                  <div class="flex h-24 flex-col items-center justify-center gap-2.5 text-gray-500">
                    <el-icon :size="60"><Picture /></el-icon>
                    <p>图片加载失败</p>
                  </div>
                </template>
              </el-image>
              <div class="absolute bottom-5 right-7.5 text-sm font-medium text-gray-800">
                {{ currentPage * 2 }}
              </div>
            </div>
          </div>
        </div>

        <el-button
          circle
          class="absolute left-5 top-5 z-100 h-10 w-10 border-none! bg-black/60! text-white! backdrop-blur-md hover:bg-black/80!"
          @click="goBack"
        >
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
      </div>

      <!-- 视频 -->
      <div
        v-else-if="materialData?.type === 1"
        class="relative flex min-h-0 flex-1 items-center justify-center overflow-hidden bg-black"
      >
        <video
          v-if="videoUrl"
          ref="videoPlayerRef"
          :src="videoUrl"
          controls
          preload="metadata"
          class="h-full w-full max-h-full max-w-full object-contain [&::cue]:bg-black/65 [&::cue]:text-base [&::cue]:leading-snug [&::cue]:text-white"
          @ended="handleVideoEnded"
          @loadedmetadata="syncSubtitleTracks"
          @error="handleVideoError"
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
        <div v-else class="flex h-full flex-col items-center justify-center gap-2 text-gray-400">
          <el-icon :size="80"><Picture /></el-icon>
          <p>视频加载失败</p>
        </div>

        <el-button
          circle
          class="absolute left-5 top-5 z-100 h-10 w-10 border-none! bg-black/60! text-white! backdrop-blur-md hover:bg-black/80!"
          @click="goBack"
        >
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
      </div>

      <!-- PDF 底部栏 -->
      <div
        v-if="materialData?.type === 0"
        class="flex h-20 min-h-20 shrink-0 items-center justify-between border-t border-gray-200 bg-white px-7 py-3"
      >
        <div class="flex min-w-37.5 flex-1 items-center gap-4">
          <MediaComponent
            v-if="currentAudio"
            :file="currentAudio"
            :player="audioPlayer"
            width-class="w-64"
            :show-play-button="false"
          />
          <div v-else class="text-sm text-gray-400">暂无音频</div>
          <div v-if="linkedAudios.length > 0" class="text-sm text-gray-500">
            {{ currentPlayingIndex + 1 }} / {{ linkedAudios.length }}
          </div>
        </div>

        <div class="flex items-center gap-4">
          <el-button
            link
            :disabled="currentPage === 1"
            class="flex h-12 w-12 items-center justify-center p-0! text-gray-700 hover:text-blue-500! disabled:cursor-not-allowed! disabled:text-gray-300!"
            @click="prevPage"
          >
            <el-icon :size="32"><DArrowLeft /></el-icon>
          </el-button>

          <el-button
            circle
            :disabled="linkedAudios.length === 0"
            class="h-14 w-14 border-none! bg-blue-500! hover:bg-blue-400! disabled:cursor-not-allowed! disabled:opacity-50"
            @click="togglePlayAll"
          >
            <el-icon :size="40" class="text-white!">
              <VideoPause v-if="isPlaying" />
              <VideoPlay v-else />
            </el-icon>
          </el-button>

          <el-button
            link
            :disabled="isLastPage"
            class="flex h-12 w-12 items-center justify-center p-0! text-gray-700 hover:text-blue-500! disabled:cursor-not-allowed! disabled:text-gray-300!"
            @click="nextPage"
          >
            <el-icon :size="32"><DArrowRight /></el-icon>
          </el-button>
        </div>

        <div class="flex min-w-37.5 flex-1 items-center justify-end">
          <span class="max-w-50 truncate text-sm font-medium text-gray-800">
            {{ materialData?.name || '素材预览' }}
          </span>
        </div>
      </div>

      <!-- 视频底部栏 -->
      <div
        v-else-if="materialData?.type === 1"
        class="flex h-20 min-h-20 shrink-0 items-center justify-between border-t border-gray-200 bg-white px-7 py-3"
      >
        <div class="flex min-w-0 flex-1 items-center gap-2">
          <el-button
            v-if="subtitleTracks.length"
            :type="activeSubtitleIndex >= 0 ? 'primary' : 'default'"
            plain
            @click="toggleSubtitle"
          >
            字幕
          </el-button>
          <span
            v-if="subtitleTracks.length && activeSubtitleIndex >= 0"
            class="max-w-40 truncate text-xs text-gray-500"
          >
            {{ subtitleTracks[activeSubtitleIndex]?.label }}
          </span>
        </div>
        <span class="max-w-[50%] truncate text-sm font-medium text-gray-800">
          {{ materialData?.name || '素材预览' }}
        </span>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onUnmounted } from 'vue'
import {
  ArrowLeft,
  VideoPlay,
  VideoPause,
  Picture,
  DArrowLeft,
  DArrowRight
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { Material } from '@/api/api-task'
import type { MaterialDetail, AudioFile, Page } from '@/types/tasks/materialDetail'
import { getMediaFileUrl } from '@/utils/file'
import { loadPdfDocument, renderPdfPageToDataUrl } from '@/utils/pdf-lib'
import {
  applySubtitleTrack,
  hideAllSubtitleTracks,
  resolveSubtitleTracks,
  revokeSubtitleTracks,
  type ResolvedSubtitleTrack,
} from '@/utils/subtitle'
import { useAudioPlayer } from '@/composables/useAudioPlayer'
import MediaComponent from '@/components/MediaComponent.vue'
import { formatTime } from '@/utils/date'

interface Props {
  modelValue: boolean
  materialId?: number | null
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  materialId: null,
})

const emit = defineEmits<Emits>()

const visible = ref(false)
const loading = ref(false)

interface PdfPage extends Page {
  id: string
  name: string
  thumbnail: string
}

// 素材相关
const materialData = ref<Material | null>(null)
const materialDetail = ref<MaterialDetail | null>(null)

// PDF相关
const currentPage = ref(1)
const totalPages = ref(0)
const pdfPages = ref<PdfPage[]>([])
const allAudios = ref<AudioFile[]>([])

// 视频相关
const videoUrl = ref<string>('')
const videoPlayerRef = ref<HTMLVideoElement | null>(null)
const subtitleTracks = ref<ResolvedSubtitleTrack[]>([])
const activeSubtitleIndex = ref(-1)
let subtitleLoadToken = 0

// 当前双页
const leftPage = computed(() => {
  const pageIndex = (currentPage.value - 1) * 2
  return pdfPages.value[pageIndex] || null
})

const rightPage = computed(() => {
  const pageIndex = (currentPage.value - 1) * 2 + 1
  return pdfPages.value[pageIndex] || null
})

// 是否是最后一页
const isLastPage = computed(() => {
  return currentPage.value >= Math.ceil(totalPages.value / 2)
})

// 当前页关联的音频
const linkedAudios = computed(() => {
  const leftPageIndex = (currentPage.value - 1) * 2
  const rightPageIndex = (currentPage.value - 1) * 2 + 1

  const leftPageData = pdfPages.value[leftPageIndex]
  const rightPageData = pdfPages.value[rightPageIndex]

  // 合并左右两页的音频ID
  const audioIds = new Set<string>()
  if (leftPageData) {
    leftPageData.audioIds.forEach(id => audioIds.add(id))
  }
  if (rightPageData) {
    rightPageData.audioIds.forEach(id => audioIds.add(id))
  }

  // 返回对应的音频对象
  return allAudios.value.filter(audio => audioIds.has(audio.id))
})

// 计算总时长
const calculateTotalDuration = async () => {
  if (linkedAudios.value.length === 0) {
    totalTime.value = '0:00'
    return
  }

  let totalSeconds = 0
  for (const audio of linkedAudios.value) {
    if (audio.duration) {
      // 如果 duration 是字符串格式 "mm:ss" 或 "hh:mm:ss"
      const parts = audio.duration.split(':').map(Number)
      if (parts.length === 2) {
        totalSeconds += parts[0] * 60 + parts[1]
      } else if (parts.length === 3) {
        totalSeconds += parts[0] * 3600 + parts[1] * 60 + parts[2]
      }
    }
  }
  totalTime.value = formatTime(totalSeconds)
}

// 音频播放
const isPlaying = ref(false)
const currentPlayingIndex = ref(-1)
const totalTime = ref('0:00')

// 使用 useAudioPlayer
const audioPlayer = useAudioPlayer({
  callbacks: {
    onPlay: () => {
      isPlaying.value = true
    },
    onPause: () => {
      isPlaying.value = false
    },
    onEnded: () => {
      // 播放下一个
      playAudioSequence(currentPlayingIndex.value + 1)
    },
  },
})

// 当前播放的音频文件
const currentAudio = computed(() => {
  if (currentPlayingIndex.value >= 0 && currentPlayingIndex.value < linkedAudios.value.length) {
    const audio = linkedAudios.value[currentPlayingIndex.value]
    if (!audio) return null

    // 将 duration 从字符串转换为数字（秒）
    let durationInSeconds = 0
    if (audio.duration) {
      const parts = audio.duration.split(':').map(Number)
      if (parts.length === 2) {
        durationInSeconds = parts[0] * 60 + parts[1]
      } else if (parts.length === 3) {
        durationInSeconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
      }
    }

    return {
      ...audio,
      uri: audio.path || '',
      path: audio.path || '',
      file: audio.path || '',
      duration: durationInSeconds,
    }
  }
  return null
})

// 监听 modelValue 变化
watch(
  () => props.modelValue,
  (val) => {
    visible.value = val
    if (val && props.materialId) {
      loadMaterial()
    } else if (!val) {
      stopVideo()
    }
  }
)

// 监听 visible 变化
watch(visible, (val) => {
  emit('update:modelValue', val)
})

// 返回
const goBack = () => {
  handleClose()
}

// 上一页
const prevPage = () => {
  if (currentPage.value > 1) {
    // 翻页时停止音频
    stopAllAudio()
    currentPage.value--
    calculateTotalDuration()

    // 加载新页面的第一个音频（不播放）
    loadCurrentPageAudio()
  } else {
    ElMessage.info('已是首页')
  }
}

// 下一页
const nextPage = () => {
  if (!isLastPage.value) {
    // 翻页时停止音频
    stopAllAudio()
    currentPage.value++
    calculateTotalDuration()

    // 加载新页面的第一个音频（不播放）
    loadCurrentPageAudio()
  } else {
    ElMessage.info('已是末页')
  }
}

// 加载当前页的第一个音频（不播放）
const loadCurrentPageAudio = () => {
  if (linkedAudios.value.length > 0) {
    currentPlayingIndex.value = 0
    const audio = linkedAudios.value[0]
    if (audio && audio.path) {
      const mediaUrl = getMediaFileUrl(audio.path)
      if (mediaUrl) {
        audioPlayer.load(mediaUrl, {
          playingFilePath: audio.path,
        })
      }
    }
  }
}

// 播放/暂停切换
const togglePlayAll = () => {
  if (linkedAudios.value.length === 0) return

  if (isPlaying.value) {
    pauseAudio()
  } else {
    playAudioSequence()
  }
}

// 按顺序播放音频序列
const playAudioSequence = (startIndex: number = 0) => {
  if (startIndex >= linkedAudios.value.length) {
    isPlaying.value = false
    currentPlayingIndex.value = -1
    ElMessage.success('所有音频播放完毕')
    return
  }

  currentPlayingIndex.value = startIndex
  const audio = linkedAudios.value[startIndex]

  if (!audio || !audio.path) {
    playAudioSequence(startIndex + 1)
    return
  }

  playSingleAudio(audio, startIndex)
}

// 播放单个音频
const playSingleAudio = (audio: AudioFile, index: number) => {
  if (!audio.path) return

  const mediaUrl = getMediaFileUrl(audio.path)

  if (!mediaUrl) {
    ElMessage.error('无法生成音频URL')
    playAudioSequence(index + 1)
    return
  }

  // 使用 audioPlayer 播放
  audioPlayer.load(mediaUrl, {
    playingFilePath: audio.path,
  })

  audioPlayer.play().catch((error) => {
    console.error('播放失败:', error)
    ElMessage.error(`音频播放失败：${audio.name}`)
    playAudioSequence(index + 1)
  })
}

// 暂停音频
const pauseAudio = () => {
  audioPlayer.pause()
}

// 停止所有音频
const stopAllAudio = () => {
  audioPlayer.clear()
  isPlaying.value = false
  currentPlayingIndex.value = -1
}

// 键盘控制
const handleKeyDown = (e: KeyboardEvent) => {
  if (e.key === 'ArrowLeft') {
    prevPage()
  } else if (e.key === 'ArrowRight') {
    nextPage()
  } else if (e.key === ' ') {
    e.preventDefault()
    togglePlayAll()
  }
}

const clearSubtitleTracks = () => {
  hideAllSubtitleTracks(videoPlayerRef.value)
  const previous = subtitleTracks.value
  subtitleTracks.value = []
  activeSubtitleIndex.value = -1
  if (previous.length) {
    void nextTick(() => revokeSubtitleTracks(previous))
  }
}

const loadVideoSubtitles = async (videoPath: string) => {
  const token = ++subtitleLoadToken
  clearSubtitleTracks()

  const tracks = await resolveSubtitleTracks(videoPath)
  if (token !== subtitleLoadToken) {
    revokeSubtitleTracks(tracks)
    return
  }

  subtitleTracks.value = tracks
  activeSubtitleIndex.value = -1
  await nextTick()
  syncSubtitleTracks()
}

const syncSubtitleTracks = () => {
  if (activeSubtitleIndex.value >= 0) {
    applySubtitleTrack(videoPlayerRef.value, activeSubtitleIndex.value)
  } else {
    hideAllSubtitleTracks(videoPlayerRef.value)
  }
}

const toggleSubtitle = () => {
  if (!subtitleTracks.value.length || !videoPlayerRef.value) return

  if (activeSubtitleIndex.value < 0) {
    activeSubtitleIndex.value = 0
  } else {
    const next = activeSubtitleIndex.value + 1
    activeSubtitleIndex.value = next >= subtitleTracks.value.length ? -1 : next
  }

  if (activeSubtitleIndex.value >= 0) {
    applySubtitleTrack(videoPlayerRef.value, activeSubtitleIndex.value)
  } else {
    hideAllSubtitleTracks(videoPlayerRef.value)
  }
}

// 停止视频：仅清空 URL 由 v-if 卸载 <video>，避免手动 src='' 触发未捕获的 abort
const stopVideo = () => {
  if (videoPlayerRef.value) {
    try {
      videoPlayerRef.value.pause()
    } catch {
      /* ignore */
    }
  }
  videoUrl.value = ''
  clearSubtitleTracks()
}

/** 切换/关闭时浏览器会中止进行中的加载，MEDIA_ERR_ABORTED 可忽略 */
const handleVideoError = () => {
  const el = videoPlayerRef.value
  if (!el?.error) return
  if (el.error.code === MediaError.MEDIA_ERR_ABORTED) return
  console.warn('视频加载失败:', el.error.code, videoUrl.value)
}

// 关闭对话框
const handleClose = () => {
  stopAllAudio()
  // 停止视频播放
  stopVideo()
  visible.value = false
  // 重置状态
  materialData.value = null
  materialDetail.value = null
  pdfPages.value = []
  allAudios.value = []
  currentPage.value = 1
  totalPages.value = 0
}

// 加载视频：先卸载再设新地址，避免在同一元素上改 src 中止上一次请求
const loadVideo = async (videoPath: string) => {
  clearSubtitleTracks()
  const nextUrl = getMediaFileUrl(videoPath) || ''
  if (!nextUrl) {
    videoUrl.value = ''
    ElMessage.error('无法加载视频：路径无效')
    return
  }
  if (videoUrl.value && videoUrl.value !== nextUrl) {
    videoUrl.value = ''
    await nextTick()
  }
  videoUrl.value = nextUrl
}

// 加载素材
const loadMaterial = async () => {
  if (!props.materialId) {
    ElMessage.warning('未指定素材ID')
    return
  }

  loading.value = true
  try {
    // 尝试从 sessionStorage 获取素材数据
    const cachedMaterial = sessionStorage.getItem('previewMaterial')
    let material: Material | null = null

    if (cachedMaterial) {
      try {
        material = JSON.parse(cachedMaterial)
        // 清除缓存
        sessionStorage.removeItem('previewMaterial')
      } catch (e) {
        console.error('解析缓存素材失败:', e)
      }
    }

    // 如果缓存中没有，需要从父组件传入完整数据
    // 这里简化处理，实际应该通过 props 或 API 获取
    if (!material) {
      ElMessage.warning('请通过 props 传入完整的素材数据')
      loading.value = false
      return
    }

    materialData.value = material

    // 解析 data 字段
    let detail: MaterialDetail | null = null
    if (typeof material.data === 'string') {
      try {
        detail = JSON.parse(material.data)
      } catch (e) {
        console.error('解析 data 失败:', e)
      }
    } else {
      detail = material.data || null
    }
    materialDetail.value = detail

    // 如果是 PDF，加载缩略图
    if (material.type === 0 && material.path) {
      await loadPdfPages(material.path, detail)
    } else if (material.type === 1 && material.path) {
      await loadVideo(material.path)
      await nextTick()
      void loadVideoSubtitles(material.path)
    }

    loading.value = false
  } catch (error: any) {
    console.error('加载素材失败:', error)
    ElMessage.error(error.message || '加载素材失败')
    loading.value = false
  }
}

// 加载 PDF 缩略图
const loadPdfPages = async (pdfPath: string, detail: MaterialDetail | null) => {
  try {
    const pdfUrl = getMediaFileUrl(pdfPath)

    if (!pdfUrl) {
      ElMessage.error('无法加载 PDF：路径无效')
      return
    }

    const pdf = await loadPdfDocument(pdfUrl)

    const pages: PdfPage[] = []

    for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
      const page = await pdf.getPage(pageNum)
      const thumbnail = await renderPdfPageToDataUrl(page, {
        scale: 1.0,
        mimeType: 'image/jpeg',
        quality: 0.9,
      })

      const pageData = detail?.pages?.[pageNum - 1]

      pages.push({
        id: String(pageNum),
        name: `第${pageNum}页`,
        thumbnail,
        audioIds: pageData?.audioIds || [],
      })
    }

    pdfPages.value = pages
    totalPages.value = pages.length

    // 加载音频列表
    allAudios.value = detail?.audioList || []

    // 计算总时长
    await calculateTotalDuration()

    // 自动加载第一个音频（不播放）
    if (linkedAudios.value.length > 0) {
      currentPlayingIndex.value = 0
      const audio = linkedAudios.value[0]
      if (audio && audio.path) {
        const mediaUrl = getMediaFileUrl(audio.path)
        if (mediaUrl) {
          // 只加载，不播放
          audioPlayer.load(mediaUrl, {
            playingFilePath: audio.path,
          })
        }
      }
    }

    ElMessage.success(`已加载素材：${materialData.value?.name}`)
  } catch (error) {
    console.error('加载 PDF 失败:', error)
    ElMessage.error('加载 PDF 失败')
  }
}

// 视频播放结束处理
const handleVideoEnded = () => {
  console.log('视频播放结束')
}

// 监听键盘事件
watch(visible, (val) => {
  if (val) {
    window.addEventListener('keydown', handleKeyDown)
  } else {
    window.removeEventListener('keydown', handleKeyDown)
    clearSubtitleTracks()
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown)
  stopVideo()
})
</script>
