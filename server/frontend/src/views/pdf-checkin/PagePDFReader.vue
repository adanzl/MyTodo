<template>
  <div class="pdf-reader-page">
    <!-- 双页展示区 -->
    <div class="reader-body">
      <div class="spread-container">
        <!-- 左页 -->
        <div class="page-spread left-page">
          <div class="page-content" v-if="leftPage">
            <el-image
              :src="leftPage.thumbnail"
              fit="contain"
              class="page-image"
            >
              <template #error>
                <div class="image-error">
                  <el-icon :size="60"><Picture /></el-icon>
                  <p>图片加载失败</p>
                </div>
              </template>
            </el-image>
            <div class="page-number">{{ currentPage * 2 - 1 }}</div>
          </div>
          <div v-else class="page-empty">
            <el-icon :size="80"><Picture /></el-icon>
          </div>
        </div>

        <!-- 右页 -->
        <div class="page-spread right-page">
          <div class="page-content" v-if="rightPage">
            <el-image
              :src="rightPage.thumbnail"
              fit="contain"
              class="page-image"
            >
              <template #error>
                <div class="image-error">
                  <el-icon :size="60"><Picture /></el-icon>
                  <p>图片加载失败</p>
                </div>
              </template>
            </el-image>
            <div class="page-number">{{ currentPage * 2 }}</div>
          </div>
          <div v-else class="page-empty">
            <!-- 单数页面时，最后一页不显示右侧页面 -->
          </div>
        </div>
      </div>
      
      <!-- 返回按钮（悬浮） -->
      <el-button circle class="back-btn" @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
      </el-button>
    </div>

    <!-- 底部控制栏 -->
    <div class="reader-footer">
      <!-- 左侧：音频时长 -->
      <div class="footer-left">
        <el-icon :size="24" class="refresh-icon"><RefreshRight /></el-icon>
        <span class="audio-time">{{ currentTime }} / {{ totalTime }}</span>
      </div>

      <!-- 中间：上一页 | 播放/暂停 | 下一页 -->
      <div class="footer-center">
        <el-button 
          link 
          @click="prevPage"
          :disabled="currentPage === 1"
          class="page-nav-btn"
        >
          <el-icon :size="32"><DArrowLeft /></el-icon>
        </el-button>
        
        <el-button
          circle
          @click="togglePlayAll"
          :disabled="linkedAudios.length === 0"
          class="play-btn"
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
          class="page-nav-btn"
        >
          <el-icon :size="32"><DArrowRight /></el-icon>
        </el-button>
      </div>

      <!-- 右侧：完成/再次查看/返回按钮 -->
      <div class="footer-right">
        <el-button
          v-if="isLastPage && !isTaskCompleted && !fromAdmin"
          type="danger"
          size="large"
          @click="showCheckinConfirm"
          class="finish-btn"
        >
          阅读完成
        </el-button>
        <el-button
          v-if="isTaskCompleted"
          type="success"
          size="large"
          @click="replayTask"
          class="replay-btn"
        >
          再次查看
        </el-button>
        <el-button
          v-if="fromAdmin"
          type="primary"
          size="large"
          @click="goBack"
          class="return-btn"
        >
          返回
        </el-button>
      </div>
    </div>

    <!-- 打卡确认对话框 -->
    <el-dialog
      v-model="checkinDialogVisible"
      title="确认完成阅读"
      width="500px"
    >
      <div class="checkin-summary">
        <div class="summary-icon">🎉</div>
        <h3>恭喜您完成阅读！</h3>
        <div class="summary-stats">
          <div class="stat-item">
            <span class="stat-label">阅读页数</span>
            <span class="stat-value">{{ totalPages }} 页</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">用时</span>
            <span class="stat-value">{{ readingTime }}</span>
          </div>
        </div>
        <p class="encouragement-text">{{ encouragementText }}</p>
      </div>
      <template #footer>
        <el-button @click="checkinDialogVisible = false">稍后再说</el-button>
        <el-button type="primary" @click="confirmCheckin">确认打卡</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
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

interface AudioItem {
  id: string
  name: string
  url: string
  played?: boolean
}

interface PdfPage {
  id: string
  name: string
  thumbnail: string
  linkedAudioIds: string[]
}

const router = useRouter()
const route = useRoute()

// PDF相关
const pdfTitle = ref('')
const currentPage = ref(1)
const totalPages = ref(0)
const pdfPages = ref<PdfPage[]>([])
const allAudios = ref<AudioItem[]>([])

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
const linkedAudios = ref<AudioItem[]>([])

// 音频播放
const isPlaying = ref(false)
const audioProgress = ref(0)
const currentPlayingIndex = ref(-1)
const currentTime = ref('0:00')
const totalTime = ref('0:00')
const audioElement = ref<HTMLAudioElement | null>(null)

// 打卡对话框
const checkinDialogVisible = ref(false)

// 任务状态
const isTaskCompleted = ref(false) // 是否已完成任务（打卡后显示再次查看按钮）
const fromAdmin = ref(false) // 是否从管理员预览模式进入

// 阅读统计
const startTime = ref(Date.now())

const readingTime = computed(() => {
  const elapsed = Math.floor((Date.now() - startTime.value) / 1000)
  const hours = Math.floor(elapsed / 3600)
  const minutes = Math.floor((elapsed % 3600) / 60)
  const seconds = elapsed % 60
  
  if (hours > 0) {
    return `${hours}小时${minutes}分钟`
  } else if (minutes > 0) {
    return `${minutes}分钟${seconds}秒`
  } else {
    return `${seconds}秒`
  }
})

const encouragementText = computed(() => {
  const texts = [
    '坚持就是胜利！每一次阅读都是成长的积累！',
    '太棒了！你已经迈出了学习的重要一步！',
    '优秀！继续保持这份学习热情！',
    '了不起！知识的力量正在改变你！',
    '加油！今天的努力是明天的成功！'
  ]
  return texts[Math.floor(Math.random() * texts.length)]
})

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
    loadCurrentPageAudios()
  } else {
    ElMessage.info('已是首页')
  }
}

// 下一页
const nextPage = () => {
  if (!isLastPage.value) {
    stopAllAudio()
    currentPage.value++
    loadCurrentPageAudios()
  } else {
    ElMessage.info('已是末页')
  }
}

// 加载当前页关联的音频
const loadCurrentPageAudios = () => {
  const leftPageIndex = (currentPage.value - 1) * 2
  const rightPageIndex = (currentPage.value - 1) * 2 + 1
  
  const leftPageData = pdfPages.value[leftPageIndex]
  const rightPageData = pdfPages.value[rightPageIndex]
  
  // 合并左右两页的音频
  const audioIds = new Set<string>()
  if (leftPageData) {
    leftPageData.linkedAudioIds.forEach(id => audioIds.add(id))
  }
  if (rightPageData) {
    rightPageData.linkedAudioIds.forEach(id => audioIds.add(id))
  }
  
  linkedAudios.value = allAudios.value
    .filter(audio => audioIds.has(audio.id))
    .map(audio => ({ ...audio, played: false }))
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
const playSingleAudio = (audio: AudioItem, index: number) => {
  if (audioElement.value) {
    audioElement.value.pause()
  }
  
  const newAudio = new Audio(audio.url || '')
  audioElement.value = newAudio
  newAudio.addEventListener('timeupdate', updateProgress)
  newAudio.addEventListener('loadedmetadata', () => {
    if (audioElement.value) {
      totalTime.value = formatTime(audioElement.value.duration)
    }
  })
  newAudio.addEventListener('ended', () => {
    linkedAudios.value[index].played = true
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
  audioProgress.value = 0
  currentPlayingIndex.value = -1
  currentTime.value = '0:00'
  totalTime.value = '0:00'
  linkedAudios.value.forEach(audio => {
    audio.played = false
  })
}

// 更新进度
const updateProgress = () => {
  if (audioElement.value && audioElement.value.duration) {
    audioProgress.value = Math.round((audioElement.value.currentTime / audioElement.value.duration) * 100)
    currentTime.value = formatTime(audioElement.value.currentTime)
  }
}

// 格式化时间
const formatTime = (seconds: number): string => {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

// 显示打卡确认
const showCheckinConfirm = () => {
  checkinDialogVisible.value = true
}

// 再次查看
const replayTask = () => {
  isTaskCompleted.value = false
  currentPage.value = 1
  stopAllAudio()
  loadCurrentPageAudios()
  ElMessage.info('开始重新阅读')
}

// 确认打卡
const confirmCheckin = () => {
  checkinDialogVisible.value = false
  stopAllAudio()
  
  // 标记任务已完成
  isTaskCompleted.value = true
  
  // TODO: 调用API提交打卡
  ElMessage.success('打卡成功！')
  
  // 跳转到打卡成功页面
  setTimeout(() => {
    router.push('/checkin-success')
  }, 500)
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

onMounted(() => {
  fromAdmin.value = route.query.fromAdmin === 'true'
  
  // 如果是管理员从资料库管理页面进入，显示"返回"按钮而不是"阅读完成"
  if (fromAdmin.value) {
    // 管理员模式：只显示PDF预览，不显示完成按钮
  }
  
  // 从 localStorage 读取课件数据
  const savedData = localStorage.getItem('courseware_edit_data')
  
  if (savedData) {
    try {
      const data = JSON.parse(savedData)
      pdfTitle.value = data.name || '未命名课件'
      pdfPages.value = data.pdfPages || []
      allAudios.value = data.allAudios || []
      totalPages.value = pdfPages.value.length
      
      // 加载第一页的音频
      if (totalPages.value > 0) {
        loadCurrentPageAudios()
      }
      
      ElMessage.success(`已加载课件：${pdfTitle.value}`)
    } catch (e) {
      console.error('Failed to parse saved data', e)
      ElMessage.error('加载课件数据失败')
    }
  } else {
    ElMessage.warning('未找到课件数据，请先在课件生成页面创建课件')
  }
  
  // 添加键盘监听
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  stopAllAudio()
  window.removeEventListener('keydown', handleKeyDown)
})
</script>

<style scoped>
.pdf-reader-page {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  background: #000;
  overflow: hidden;
  z-index: 10000;
}
.reader-body {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 0;
  background: #000;
  overflow: hidden;
  position: relative;
  min-height: 0;
}

.spread-container {
  display: flex;
  gap: 0;
  width: 100%;
  height: 100%;
  max-width: 100%;
  position: relative;
}

.page-spread {
  flex: 1;
  background: #e8e0f0;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.page-spread::after {
  content: '';
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #000;
}

.right-page .page-spread::after,
.page-spread:last-child::after {
  display: none;
}

.page-content {
  width: 100%;
  height: 100%;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.page-image {
  max-width: 100%;
  max-height: 100%;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.page-number {
  position: absolute;
  bottom: 20px;
  font-size: 14px;
  color: #333;
  font-weight: 500;
}

.left-page .page-number {
  left: 30px;
}

.right-page .page-number {
  right: 30px;
}

.page-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #ccc;
}

.image-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400px;
  color: #999;
  gap: 10px;
}

/* 悬浮返回按钮 */
.back-btn {
  position: absolute;
  top: 20px;
  left: 20px;
  z-index: 100;
  background: rgba(0, 0, 0, 0.6);
  border: none;
  color: #fff;
  width: 40px;
  height: 40px;
  backdrop-filter: blur(10px);
}

.back-btn:hover {
  background: rgba(0, 0, 0, 0.8);
}

/* 底部控制栏 */
.reader-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 30px;
  background: #2c2c2c;
  border-top: 1px solid #3a3a3a;
  height: 80px;
  min-height: 80px;
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 150px;
}

.refresh-icon {
  color: #ccc;
}

.audio-time {
  font-size: 14px;
  color: #fff;
  font-family: 'Courier New', monospace;
  font-variant-numeric: tabular-nums;
}

.footer-center {
  display: flex;
  align-items: center;
  gap: 16px;
}

.footer-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  min-width: 150px;
}

.page-btn {
  color: #fff;
  padding: 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.page-btn:hover:not(:disabled) {
  color: #409eff;
}

.page-btn:disabled {
  color: #555;
  cursor: not-allowed;
}

.page-btn-text {
  font-size: 14px;
  font-weight: 500;
}

.page-info {
  font-size: 16px;
  color: #fff;
  font-family: 'Courier New', monospace;
  font-variant-numeric: tabular-nums;
  font-weight: 500;
}

.page-nav-btn {
  color: #fff;
  padding: 0;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.page-nav-btn:hover:not(:disabled) {
  color: #409eff;
}

.page-nav-btn:disabled {
  color: #555;
  cursor: not-allowed;
}

/* 打卡摘要对话框 */
.checkin-summary {
  text-align: center;
  padding: 20px 0;
}

.summary-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.checkin-summary h3 {
  margin: 0 0 24px 0;
  font-size: 22px;
  color: #333;
}

.summary-stats {
  display: flex;
  justify-content: center;
  gap: 40px;
  margin-bottom: 24px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-label {
  font-size: 14px;
  color: #666;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #409eff;
}

.encouragement-text {
  font-size: 16px;
  color: #67c23a;
  font-weight: 500;
  line-height: 1.6;
  margin: 0;
}

.control-btn {
  color: #fff;
  padding: 0;
  width: 40px;
  height: 40px;
}

.control-btn:hover:not(:disabled) {
  color: #409eff;
}

.control-btn:disabled {
  color: #555;
  cursor: not-allowed;
}

.play-btn {
  width: 56px;
  height: 56px;
  background: #409eff;
  border: none;
}

.play-btn:hover:not(:disabled) {
  background: #66b1ff;
}

.play-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.action-section {
  display: flex;
  align-items: center;
  gap: 15px;
  min-width: 120px;
  justify-content: flex-end;
}

.finish-btn {
  font-weight: bold;
  font-size: 15px;
  padding: 10px 24px;
  margin-left: 12px;
}

.finish-btn:hover {
  background: #f56c6c;
  opacity: 0.9;
}

.return-btn {
  font-weight: bold;
  font-size: 15px;
  padding: 10px 24px;
  margin-left: 12px;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .reader-footer {
    padding: 12px 20px;
  }
  
  .footer-left,
  .footer-right {
    min-width: 120px;
  }
}

@media (max-width: 768px) {
  .spread-container {
    flex-direction: column;
  }
  
  .page-spread::after {
    display: none;
  }
  
  .reader-footer {
    padding: 10px 15px;
    height: 70px;
    min-height: 70px;
  }
  
  .footer-left,
  .footer-right {
    min-width: 80px;
  }
  
  .footer-center {
    gap: 16px;
  }
  
  .play-btn {
    width: 48px;
    height: 48px;
  }
  
  .control-btn {
    width: 32px;
    height: 32px;
  }
  
  .page-nav-btn {
    width: 40px;
    height: 40px;
  }
  
  .page-info {
    font-size: 14px;
  }
  
  .back-btn {
    top: 10px;
    left: 10px;
    width: 36px;
    height: 36px;
  }
}

@media (max-width: 480px) {
  .reader-footer {
    padding: 8px 10px;
    height: 60px;
    min-height: 60px;
  }
  
  .footer-left,
  .footer-right {
    min-width: 60px;
  }
  
  .footer-center {
    gap: 12px;
  }
  
  .play-btn {
    width: 40px;
    height: 40px;
  }
  
  .control-btn {
    width: 28px;
    height: 28px;
  }
  
  .page-nav-btn {
    width: 36px;
    height: 36px;
  }
  
  .page-info {
    font-size: 13px;
  }
  
  .back-btn {
    width: 32px;
    height: 32px;
  }
}
</style>
