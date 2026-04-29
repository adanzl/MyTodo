<!-- MaterialPreviewDialog.vue - 素材预览全屏弹窗 -->
<template>
  <el-dialog
    v-model="visible"
    fullscreen
    :show-close="false"
    destroy-on-close
    @close="handleClose"
    class="preview-fullscreen-dialog"
  >
    <div v-loading="loading" element-loading-text="加载中..." element-loading-background="rgba(0, 0, 0, 0.8)" class="relative w-full h-full flex flex-col bg-black overflow-hidden">
      <!-- PDF双页展示区 -->
      <div v-if="materialData?.type === 0" class="flex-1 flex justify-center items-center p-0 bg-black overflow-hidden relative min-h-0">
        <div class="flex gap-0 w-full h-full max-w-full relative [&_.page-spread:last-child]:after:hidden">
          <!-- 左页 -->
          <div class="flex-1 bg-[#e8e0f0] relative flex items-center justify-center overflow-hidden page-spread after:content-[''] after:absolute after:right-0 after:top-0 after:bottom-0 after:w-0.5 after:bg-black left-page">
            <div class="w-full h-full relative flex items-center justify-center" v-if="leftPage">
              <el-image
                :src="leftPage.thumbnail"
                fit="contain"
                class="max-w-full max-h-full w-full h-full object-contain"
              >
                <template #error>
                  <div class="flex flex-col items-center justify-center h-100 text-gray-500 gap-2.5">
                    <el-icon :size="60"><Picture /></el-icon>
                    <p>图片加载失败</p>
                  </div>
                </template>
              </el-image>
              <div class="absolute bottom-5 text-sm text-gray-800 font-medium left-7.5">{{ currentPage * 2 - 1 }}</div>
            </div>
            <div v-else class="flex items-center justify-center h-full text-gray-400">
              <el-icon :size="80"><Picture /></el-icon>
            </div>
          </div>

          <!-- 右页 -->
          <div class="flex-1 bg-[#e8e0f0] relative flex items-center justify-center overflow-hidden page-spread after:content-[''] after:absolute after:right-0 after:top-0 after:bottom-0 after:w-0.5 after:bg-black right-page">
            <div class="w-full h-full relative flex items-center justify-center" v-if="rightPage">
              <el-image
                :src="rightPage.thumbnail"
                fit="contain"
                class="max-w-full max-h-full w-full h-full object-contain"
              >
                <template #error>
                  <div class="flex flex-col items-center justify-center h-100 text-gray-500 gap-2.5">
                    <el-icon :size="60"><Picture /></el-icon>
                    <p>图片加载失败</p>
                  </div>
                </template>
              </el-image>
              <div class="absolute bottom-5 text-sm text-gray-800 font-medium right-7.5">{{ currentPage * 2 }}</div>
            </div>
            <div v-else class="flex items-center justify-center h-full text-gray-400">
              <!-- 单数页面时,最后一页不显示右侧页面 -->
            </div>
          </div>
        </div>

        <!-- 返回按钮（悬浮） -->
        <el-button circle class="absolute top-5 left-5 z-100 bg-black/60 border-none text-white w-10 h-10 backdrop-blur-md hover:bg-black/80" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
      </div>

      <!-- 视频播放区 -->
      <div v-else-if="materialData?.type === 1" class="flex-1 flex justify-center items-center p-0 bg-black overflow-hidden relative min-h-0">
        <video
          v-if="videoUrl"
          ref="videoPlayerRef"
          :src="videoUrl"
          controls
          preload="metadata"
          class="max-w-full max-h-full w-full h-full object-contain"
          @ended="handleVideoEnded"
        ></video>
        <div v-else class="flex items-center justify-center h-full text-gray-400">
          <el-icon :size="80"><Picture /></el-icon>
          <p>视频加载失败</p>
        </div>

        <!-- 返回按钮（悬浮） -->
        <el-button circle class="absolute top-5 left-5 z-100 bg-black/60 border-none text-white w-10 h-10 backdrop-blur-md hover:bg-black/80" @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
      </div>

      <!-- 底部控制栏（仅PDF显示） -->
      <div v-if="materialData?.type === 0" class="flex items-center justify-between px-7 py-3 bg-white border-t border-[#3a3a3a] h-20 min-h-20">
        <!-- 左侧：音频播放器 -->
        <div class="flex items-center gap-4 min-w-37.5 flex-1">
          <MediaComponent
            v-if="currentAudio"
            :file="currentAudio"
            :player="audioPlayer"
            width-class="w-64"
            :show-play-button="false"
          />
          <div v-else class="text-sm text-gray-400">暂无音频</div>
          <div v-if="linkedAudios.length > 0" class="text-sm text-gray-400">
            {{ currentPlayingIndex + 1 }} / {{ linkedAudios.length }}
          </div>
        </div>

        <!-- 中间：上一页 | 播放/暂停 | 下一页 -->
        <div class="flex items-center gap-4">
          <el-button
            link
            @click="prevPage"
            :disabled="currentPage === 1"
            class="text-white p-0 w-12 h-12 flex items-center justify-center hover:text-blue-500 disabled:text-gray-600 disabled:cursor-not-allowed"
          >
            <el-icon :size="32"><DArrowLeft /></el-icon>
          </el-button>

          <el-button
            circle
            @click="togglePlayAll"
            :disabled="linkedAudios.length === 0"
            class="w-14 h-14 bg-blue-500 border-none hover:bg-blue-400 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <el-icon :size="40">
              <VideoPause v-if="isPlaying" />
              <VideoPlay v-else :size="40" />
            </el-icon>
          </el-button>

          <el-button
            link
            @click="nextPage"
            :disabled="isLastPage"
            class="text-white p-0 w-12 h-12 flex items-center justify-center hover:text-blue-500 disabled:text-gray-600 disabled:cursor-not-allowed"
          >
            <el-icon :size="32"><DArrowRight /></el-icon>
          </el-button>
        </div>

        <!-- 右侧：素材名称 -->
        <div class="flex items-center justify-end min-w-37.5 flex-1">
          <span class="text-sm text-gray-800 max-w-50 overflow-hidden text-ellipsis whitespace-nowrap">{{ materialData?.name || '素材预览' }}</span>
        </div>
      </div>

      <!-- 底部控制栏（视频显示素材名称） -->
      <div v-else-if="materialData?.type === 1" class="flex items-center justify-center px-7 py-3 bg-white border-t border-[#3a3a3a] h-20 min-h-20">
        <span class="text-sm text-gray-800">{{ materialData?.name || '素材预览' }}</span>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
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
import * as pdfjsLib from 'pdfjs-dist'
import { getMediaFileUrl } from '@/utils/file'
import { useAudioPlayer } from '@/composables/useAudioPlayer'
import MediaComponent from '@/components/MediaComponent.vue'
import { formatTime } from '@/utils/date'

// 设置 PDF.js worker
import pdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorker

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

// 停止视频播放
const stopVideo = () => {
  if (videoPlayerRef.value) {
    videoPlayerRef.value.pause()
    videoPlayerRef.value.src = ''
  }
  videoUrl.value = ''
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

// 加载视频
const loadVideo = (videoPath: string) => {
  videoUrl.value = getMediaFileUrl(videoPath) || ''
  if (!videoUrl.value) {
    ElMessage.error('无法加载视频：路径无效')
  }
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
      // 如果是视频，加载视频URL
      loadVideo(material.path)
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

    const loadingTask = pdfjsLib.getDocument({
      url: pdfUrl,
      cMapUrl: '//cdnjs.cloudflare.com/ajax/libs/pdf.js/' + pdfjsLib.version + '/cmaps/',
      cMapPacked: true,
    })

    const pdf = await loadingTask.promise

    const pages: PdfPage[] = []

    for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
      const page = await pdf.getPage(pageNum)
      const viewport = page.getViewport({ scale: 1.0 })
      const canvas = document.createElement('canvas')
      const context = canvas.getContext('2d')

      if (context) {
        canvas.height = viewport.height
        canvas.width = viewport.width

        await page.render({
          canvasContext: context,
          viewport: viewport,
          canvas: canvas as any,
        }).promise

        const thumbnail = canvas.toDataURL('image/jpeg', 0.9)

        // 从 pages 数据中获取绑定的音频 ID
        const pageData = detail?.pages?.[pageNum - 1]

        pages.push({
          id: String(pageNum),
          name: `第${pageNum}页`,
          thumbnail: thumbnail,
          audioIds: pageData?.audioIds || [],
        })
      }
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
  }
})
</script>

<style scoped>
/* 使用 Tailwind CSS，无需额外样式 */
</style>

<style>
/* 全局样式，用于覆盖 el-dialog 默认样式 */
.preview-fullscreen-dialog {
  margin: 0 !important;
  padding: 0 !important;
}

.preview-fullscreen-dialog .el-dialog__header {
  display: none;
}

.preview-fullscreen-dialog .el-dialog__body {
  padding: 0 !important;
  height: 100vh;
}
</style>
