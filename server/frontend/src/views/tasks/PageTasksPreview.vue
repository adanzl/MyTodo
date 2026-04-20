<template>
  <div class="relative w-full h-screen flex flex-col bg-black overflow-hidden">
    <!-- 双页展示区 -->
    <div class="flex-1 flex justify-center items-center p-0 bg-black overflow-hidden relative min-h-0">
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

    <!-- 底部控制栏 -->
    <div class="flex items-center justify-between px-7 py-3 bg-[#2c2c2c] border-t border-[#3a3a3a] h-20 min-h-20">
      <!-- 左侧：音频时长 -->
      <div class="flex items-center gap-2 min-w-37.5">
        <el-icon :size="24" class="text-gray-400"><RefreshRight /></el-icon>
        <span class="text-sm text-white font-mono tabular-nums">{{ currentTime }} / {{ totalTime }}</span>
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
            <CaretRight v-else :size="40" />
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
      <div class="flex items-center justify-end min-w-37.5">
        <span class="text-sm text-white max-w-50 overflow-hidden text-ellipsis whitespace-nowrap">{{ materialData?.name || '素材预览' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  ArrowLeft,
  CaretRight,
  VideoPause,
  Picture,
  DArrowLeft,
  DArrowRight,
  RefreshRight
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getMaterial } from '@/api/api-task'
import type { Material } from '@/api/api-task'
import type { TaskDetail, AudioFile, Page } from '@/types/tasks/taskDetail'
import * as pdfjsLib from 'pdfjs-dist'
import { getMediaFileUrl } from '@/utils/file'

// 设置 PDF.js worker
import pdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorker

interface PdfPage extends Page {
  id: string
  name: string
  thumbnail: string
}

const router = useRouter()
const route = useRoute()

// 素材相关
const materialData = ref<Material | null>(null)
const taskDetail = ref<TaskDetail | null>(null)

// PDF相关
const currentPage = ref(1)
const totalPages = ref(0)
const pdfPages = ref<PdfPage[]>([])
const allAudios = ref<AudioFile[]>([])

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

// 音频播放
const isPlaying = ref(false)
const currentPlayingIndex = ref(-1)
const currentTime = ref('0:00')
const totalTime = ref('0:00')
const audioElement = ref<HTMLAudioElement | null>(null)

// 返回
const goBack = () => {
  if (audioElement.value) {
    audioElement.value.pause()
  }
  router.back()
}

// 上一页
const prevPage = () => {
  if (currentPage.value > 1) {
    stopAllAudio()
    currentPage.value--
  } else {
    ElMessage.info('已是首页')
  }
}

// 下一页
const nextPage = () => {
  if (!isLastPage.value) {
    stopAllAudio()
    currentPage.value++
  } else {
    ElMessage.info('已是末页')
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

  if (!audio) {
    playAudioSequence(startIndex + 1)
    return
  }

  playSingleAudio(audio, startIndex)
}

// 播放单个音频
const playSingleAudio = (audio: AudioFile, index: number) => {
  if (!audio.path) {
    ElMessage.warning('音频文件路径无效')
    playAudioSequence(index + 1)
    return
  }

  if (audioElement.value) {
    audioElement.value.pause()
  }

  const mediaUrl = getMediaFileUrl(audio.path)

  if (!mediaUrl) {
    ElMessage.error('无法生成音频URL')
    playAudioSequence(index + 1)
    return
  }

  const newAudio = new Audio(mediaUrl)
  audioElement.value = newAudio
  newAudio.addEventListener('timeupdate', updateProgress)
  newAudio.addEventListener('loadedmetadata', () => {
    if (audioElement.value) {
      totalTime.value = formatTime(audioElement.value.duration)
    }
  })
  newAudio.addEventListener('ended', () => {
    playAudioSequence(index + 1)
  })
  newAudio.addEventListener('error', (err: Event) => {
    console.error('Audio play error:', err)
    ElMessage.error(`音频播放失败：${audio.name}`)
    playAudioSequence(index + 1)
  })

  newAudio.play().then(() => {
    isPlaying.value = true
  }).catch((err: any) => {
    console.error('Audio play error:', err)
    ElMessage.error(`音频播放失败：${audio.name}`)
    playAudioSequence(index + 1)
  })
}

// 暂停音频
const pauseAudio = () => {
  if (audioElement.value) {
    audioElement.value.pause()
    isPlaying.value = false
  }
}

// 停止所有音频
const stopAllAudio = () => {
  if (audioElement.value) {
    audioElement.value.pause()
    audioElement.value.currentTime = 0
    audioElement.value = null
  }
  isPlaying.value = false
  currentPlayingIndex.value = -1
  currentTime.value = '0:00'
  totalTime.value = '0:00'
}

// 更新进度
const updateProgress = () => {
  if (audioElement.value && audioElement.value.duration) {
    currentTime.value = formatTime(audioElement.value.currentTime)
  }
}

// 格式化时间
const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
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

// 加载素材
const loadMaterial = async () => {
  console.log('=== loadMaterial 被调用 ===')
  console.log('route.query:', route.query)
  const materialId = route.query.materialId
  console.log('materialId:', materialId)

  if (!materialId) {
    ElMessage.warning('未指定素材ID')
    return
  }

  try {
    // 尝试从 sessionStorage 获取素材数据
    const cachedMaterial = sessionStorage.getItem('previewMaterial')
    let material: Material | null = null

    if (cachedMaterial) {
      try {
        material = JSON.parse(cachedMaterial)
        console.log('从缓存获取素材:', material)
        // 清除缓存
        sessionStorage.removeItem('previewMaterial')
      } catch (e) {
        console.error('解析缓存素材失败:', e)
      }
    }

    // 如果缓存中没有，则从 API 获取
    if (!material) {
      console.log('从 API 获取素材，ID:', Number(materialId))
      // 使用 fields='*' 获取所有字段
      material = await getMaterial(Number(materialId), '*')
      console.log('从 API 获取素材:', material)
    }

    if (!material) {
      ElMessage.error('获取素材数据失败')
      return
    }

    materialData.value = material

    // 解析 data 字段
    let detail: TaskDetail | null = null
    if (typeof material.data === 'string') {
      try {
        detail = JSON.parse(material.data)
      } catch (e) {
        console.error('解析 data 失败:', e)
      }
    } else {
      detail = material.data || null
    }
    taskDetail.value = detail

    // 如果是 PDF，加载缩略图
    if (material.type === 0 && material.path) {
      await loadPdfPages(material.path, detail)
    }
  } catch (error: any) {
    console.error('加载素材失败:', error)
    ElMessage.error(error.message || '加载素材失败')
  }
}

// 加载 PDF 缩略图
const loadPdfPages = async (pdfPath: string, detail: TaskDetail | null) => {
  try {
    console.log('=== PDF 加载调试信息 ===')
    console.log('原始路径:', pdfPath)

    const pdfUrl = getMediaFileUrl(pdfPath)
    console.log('生成的 PDF URL:', pdfUrl)
    console.log('========================')

    if (!pdfUrl) {
      console.error('无法生成 PDF URL')
      ElMessage.error('无法加载 PDF：路径无效')
      return
    }

    const loadingTask = pdfjsLib.getDocument({
      url: pdfUrl,
      cMapUrl: '//cdnjs.cloudflare.com/ajax/libs/pdf.js/' + pdfjsLib.version + '/cmaps/',
      cMapPacked: true,
    })

    const pdf = await loadingTask.promise
    console.log('PDF 加载成功，页数:', pdf.numPages)

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
    console.log('PDF 页面加载完成，共', pages.length, '页')

    // 加载音频列表
    allAudios.value = detail?.audioList || []

    ElMessage.success(`已加载素材：${materialData.value?.name}`)
  } catch (error) {
    console.error('加载 PDF 失败:', error)
    ElMessage.error('加载 PDF 失败')
  }
}

// 监听路由参数变化
watch(
  () => route.query.materialId,
  (newMaterialId) => {
    console.log('路由参数变化:', newMaterialId)
    if (newMaterialId) {
      loadMaterial()
    }
  }
)

onMounted(() => {
  console.log('PageTasksPreview mounted')
  loadMaterial()
  // 添加键盘监听
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  stopAllAudio()
  window.removeEventListener('keydown', handleKeyDown)
})
</script>

<style scoped>
/* 使用 Tailwind CSS，无需额外样式 */
</style>
