<template>
  <div class="audio-edit-page">
    <!-- 顶部导航栏 -->
    <div class="page-header">
      <el-button @click="goBack">
        <el-icon><ArrowLeft /></el-icon>
        返回课件生成
      </el-button>
      <h2 class="page-title">编辑音频 - {{ coursewareName }}</h2>
      <el-button type="primary" @click="saveAndBack">
        保存并返回
      </el-button>
    </div>

    <!-- 三栏布局 -->
    <div class="three-columns">
      <!-- 左侧：图片列表 -->
      <div class="column image-list-column">
        <div class="column-header">
          <span>图片列表</span>
          <span class="count-badge">{{ pdfPages.length }}</span>
        </div>
        <div class="column-body">
          <div
            v-for="(page, index) in pdfPages"
            :key="page.id"
            class="page-item"
            :class="{ 'active': currentPageId === page.id }"
            @click="selectPage(page)"
          >
            <div class="page-thumb">
              <el-image
                :src="page.thumbnail"
                fit="cover"
                class="thumb-image"
              >
                <template #error>
                  <div class="thumb-placeholder">
                    <el-icon><Picture /></el-icon>
                  </div>
                </template>
              </el-image>
            </div>
            <div class="page-info">
              <span class="page-name">{{ page.name }}</span>
              <span class="audio-count">音频：{{ getLinkedAudios(page).length }}</span>
            </div>
            <div class="page-index">{{ index + 1 }}</div>
          </div>
          <el-empty v-if="pdfPages.length === 0" description="暂无图片" />
        </div>
      </div>

      <!-- 中间：图片预览 -->
      <div class="column image-preview-column">
        <div class="column-header">
          <span>图片预览</span>
        </div>
        <div class="column-body preview-body">
          <div v-if="currentPage" class="preview-container">
            <el-image
              :src="currentPage.thumbnail"
              fit="contain"
              class="preview-image"
            >
              <template #error>
                <div class="preview-placeholder">
                  <el-icon :size="80"><Picture /></el-icon>
                  <span>暂无图片</span>
                </div>
              </template>
            </el-image>
            <div class="preview-info">
              <h3>{{ currentPage.name }}</h3>
              <p>已关联 {{ getLinkedAudios(currentPage).length }} 个音频</p>
            </div>
          </div>
          <el-empty v-else description="请选择图片" />
        </div>
      </div>

      <!-- 右侧：音频列表 -->
      <div class="column audio-list-column">
        <div class="column-header">
          <span>音频列表</span>
          <div class="header-actions">
            <el-button size="small" type="primary" @click="addAudioFromCloud">
              <el-icon><FolderOpened /></el-icon>
              云端添加
            </el-button>
            <el-button size="small" type="success" @click="addAudioFromLocal">
              <el-icon><Upload /></el-icon>
              本地添加
            </el-button>
          </div>
        </div>
        <div class="column-body">
          <div class="audio-list">
            <div class="current-page-hint">
              当前编辑：{{ currentPage?.name || '未选择图片' }}
            </div>
            <div
              v-for="(audio, index) in allAudios"
              :key="audio.id"
              class="audio-item"
              :class="{ 
                'playing': playingAudioId === audio.id,
                'linked': isAudioLinkedToCurrentPage(audio.id)
              }"
            >
              <el-checkbox 
                :model-value="isAudioLinkedToCurrentPage(audio.id)"
                @change="toggleAudioLink(audio)"
              />
              <div class="audio-index">{{ index + 1 }}</div>
              <div class="audio-info">
                <el-icon><Headset /></el-icon>
                <div class="audio-details">
                  <span class="audio-name">{{ audio.name }}</span>
                  <span class="audio-duration">{{ audio.duration }}</span>
                </div>
                <el-tag v-if="audio.cloudPath" size="small" type="info">云端</el-tag>
              </div>
              <div class="audio-actions">
                <el-button
                  link
                  type="warning"
                  size="small"
                  @click="moveAudioUp(index)"
                  :disabled="index === 0"
                >
                  <el-icon><ArrowUp /></el-icon>
                </el-button>
                <el-button
                  link
                  type="warning"
                  size="small"
                  @click="moveAudioDown(index)"
                  :disabled="index === allAudios.length - 1"
                >
                  <el-icon><ArrowDown /></el-icon>
                </el-button>
                <el-button
                  link
                  type="primary"
                  size="small"
                  @click="togglePlayAudio(audio)"
                >
                  <el-icon>
                    <VideoPlay v-if="playingAudioId !== audio.id" />
                    <VideoPause v-else />
                  </el-icon>
                </el-button>
                <el-button
                  link
                  type="danger"
                  size="small"
                  @click="removeAudio(audio)"
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
            <el-empty v-if="allAudios.length === 0" description="暂无音频，请添加" />
          </div>
        </div>
      </div>
    </div>

    <!-- 云端文件选择对话框 -->
    <FileDialog
      v-model:visible="cloudFileDialogVisible"
      title="选择音频文件"
      extensions="audio"
      mode="file"
      @confirm="handleCloudFileConfirm"
    />

    <!-- 本地上传对话框 -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="上传音频文件"
      width="500px"
    >
      <el-upload
        class="upload-demo"
        drag
        :auto-upload="false"
        :on-change="handleAudioFileChange"
        :multiple="true"
        accept=".mp3,.wav,.m4a"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          将音频文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 mp3, wav, m4a 格式
          </div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmAudioUpload">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowLeft,
  Picture,
  FolderOpened,
  Upload,
  Headset,
  VideoPlay,
  VideoPause,
  Delete,
  UploadFilled,
  ArrowUp,
  ArrowDown,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import FileDialog from '@/views/dialogs/FileDialog.vue'

interface AudioItem {
  id: string
  name: string
  duration: string
  url: string
  cloudPath?: string
}

interface PdfPage {
  id: string
  name: string
  thumbnail: string
  linkedAudioIds: string[]  // 关联的音频ID列表
}

const router = useRouter()

// 课件名称
const coursewareName = ref('')

// 图片列表
const pdfPages = ref<PdfPage[]>([])
const currentPageId = ref('')

const currentPage = computed(() => {
  return pdfPages.value.find(p => p.id === currentPageId.value) || null
})

// 所有音频列表
const allAudios = ref<AudioItem[]>([])

// 获取指定图片关联的音频
const getLinkedAudios = (page: PdfPage) => {
  return allAudios.value.filter(audio => page.linkedAudioIds.includes(audio.id))
}

// 检查音频是否关联到当前图片
const isAudioLinkedToCurrentPage = (audioId: string) => {
  if (!currentPage.value) return false
  return currentPage.value.linkedAudioIds.includes(audioId)
}

// 切换音频关联状态
const toggleAudioLink = (audio: AudioItem) => {
  if (!currentPage.value) {
    ElMessage.warning('请先选择图片')
    return
  }
  
  const index = currentPage.value.linkedAudioIds.indexOf(audio.id)
  if (index > -1) {
    currentPage.value.linkedAudioIds.splice(index, 1)
    ElMessage.success(`已取消关联：${audio.name}`)
  } else {
    currentPage.value.linkedAudioIds.push(audio.id)
    ElMessage.success(`已关联：${audio.name}`)
  }
}

// 音频播放
const playingAudioId = ref('')
const audioPlayer = ref<HTMLAudioElement | null>(null)

// 云端文件选择
const cloudFileDialogVisible = ref(false)
const addAudioFromCloud = () => {
  if (!currentPage.value) {
    ElMessage.warning('请先选择图片')
    return
  }
  cloudFileDialogVisible.value = true
}

const handleCloudFileConfirm = (filePaths: string[]) => {
  if (filePaths.length === 0) return
  
  const filePath = filePaths[0]
  const fileName = filePath.split('/').pop() || ''
  
  const newAudio: AudioItem = {
    id: `audio-${Date.now()}`,
    name: fileName,
    duration: '00:00',
    url: '',
    cloudPath: filePath
  }
  
  allAudios.value.push(newAudio)
  
  // 如果当前有选中的图片，自动关联
  if (currentPage.value) {
    currentPage.value.linkedAudioIds.push(newAudio.id)
  }
  
  ElMessage.success(`已添加音频：${fileName}`)
}

// 本地上传
const uploadDialogVisible = ref(false)
interface TempAudioFile {
  uid: number | string
  name: string
  status?: string
  raw?: File
}
const tempAudioFiles = ref<TempAudioFile[]>([])

const addAudioFromLocal = () => {
  if (!currentPage.value) {
    ElMessage.warning('请先选择图片')
    return
  }
  tempAudioFiles.value = []
  uploadDialogVisible.value = true
}

const handleAudioFileChange = (file: TempAudioFile) => {
  if (file.status === 'removed') {
    tempAudioFiles.value = tempAudioFiles.value.filter(f => f.uid !== file.uid)
  } else {
    tempAudioFiles.value.push(file)
  }
}

const confirmAudioUpload = () => {
  if (tempAudioFiles.value.length === 0) {
    ElMessage.warning('请选择音频文件')
    return
  }
  
  const newAudioIds: string[] = []
  
  tempAudioFiles.value.forEach((file, index) => {
    const newAudio: AudioItem = {
      id: `audio-${Date.now()}-${index}`,
      name: file.name,
      duration: '00:00',
      url: ''
    }
    allAudios.value.push(newAudio)
    newAudioIds.push(newAudio.id)
  })
  
  // 如果当前有选中的图片，自动关联
  if (currentPage.value) {
    currentPage.value.linkedAudioIds.push(...newAudioIds)
  }
  
  ElMessage.success(`已添加 ${tempAudioFiles.value.length} 个音频文件`)
  uploadDialogVisible.value = false
  tempAudioFiles.value = []
}

// 选择图片
const selectPage = (page: PdfPage) => {
  currentPageId.value = page.id
}

// 播放音频
const togglePlayAudio = (audio: AudioItem) => {
  if (playingAudioId.value === audio.id) {
    // 暂停播放
    if (audioPlayer.value) {
      audioPlayer.value.pause()
      audioPlayer.value = null
    }
    playingAudioId.value = ''
  } else {
    // 播放音频
    if (audioPlayer.value) {
      audioPlayer.value.pause()
    }
    
    // 创建新的音频播放器
    const player = new Audio(audio.url || '')
    player.play().catch(() => {
      ElMessage.info('音频播放（模拟）')
    })
    
    player.onended = () => {
      playingAudioId.value = ''
      audioPlayer.value = null
    }
    
    audioPlayer.value = player
    playingAudioId.value = audio.id
  }
}

// 删除音频
const removeAudio = (audio: AudioItem) => {
  const audioIndex = allAudios.value.findIndex(a => a.id === audio.id)
  if (audioIndex > -1) {
    allAudios.value.splice(audioIndex, 1)
    
    // 从所有图片的关联中移除
    pdfPages.value.forEach(page => {
      const idx = page.linkedAudioIds.indexOf(audio.id)
      if (idx > -1) {
        page.linkedAudioIds.splice(idx, 1)
      }
    })
    
    // 如果删除的是正在播放的音频，停止播放
    if (playingAudioId.value === audio.id) {
      if (audioPlayer.value) {
        audioPlayer.value.pause()
        audioPlayer.value = null
      }
      playingAudioId.value = ''
    }
    
    ElMessage.success('音频已删除')
  }
}

// 音频上移
const moveAudioUp = (index: number) => {
  if (index > 0) {
    const temp = allAudios.value[index]
    allAudios.value[index] = allAudios.value[index - 1]
    allAudios.value[index - 1] = temp
    ElMessage.success('音频已上移')
  }
}

// 音频下移
const moveAudioDown = (index: number) => {
  if (index < allAudios.value.length - 1) {
    const temp = allAudios.value[index]
    allAudios.value[index] = allAudios.value[index + 1]
    allAudios.value[index + 1] = temp
    ElMessage.success('音频已下移')
  }
}

// 返回
const goBack = () => {
  router.back()
}

// 保存并返回
const saveAndBack = () => {
  ElMessage.success('音频编辑已保存')
  router.back()
}

onMounted(() => {
  // 从 localStorage 加载课件数据
  
  // 尝试从 localStorage 读取
  const savedData = localStorage.getItem('courseware_edit_data')
  
  if (savedData) {
    try {
      const data = JSON.parse(savedData)
      coursewareName.value = data.name || ''
      pdfPages.value = data.pdfPages || []
      allAudios.value = data.allAudios || []
    } catch (e) {
      console.error('Failed to parse saved data', e)
    }
  }
  
  // 如果没有 savedData，加载样例数据
  if (pdfPages.value.length === 0) {
    coursewareName.value = '春'
    
    // 所有音频
    allAudios.value = [
      { id: 'a1-1', name: '春-第一段.mp3', duration: '00:45', url: '' },
      { id: 'a1-2', name: '春-第二段.mp3', duration: '00:38', url: '' },
      { id: 'a2-1', name: '春-第三段.mp3', duration: '00:52', url: '' }
    ]
    
    pdfPages.value = [
      {
        id: '1',
        name: '第1页.jpg',
        thumbnail: `https://placehold.co/600x800/e0e0e0/666?text=${encodeURIComponent('春')}+Page+1`,
        linkedAudioIds: ['a1-1', 'a1-2']
      },
      {
        id: '2',
        name: '第2页.jpg',
        thumbnail: `https://placehold.co/600x800/e0e0e0/666?text=${encodeURIComponent('春')}+Page+2`,
        linkedAudioIds: ['a2-1']
      },
      {
        id: '3',
        name: '第3页.jpg',
        thumbnail: `https://placehold.co/600x800/e0e0e0/666?text=${encodeURIComponent('春')}+Page+3`,
        linkedAudioIds: []
      }
    ]
  }
  
  // 默认选中第一页
  if (pdfPages.value.length > 0) {
    currentPageId.value = pdfPages.value[0].id
  }
  
  ElMessage.success(`已加载课件：${coursewareName.value}`)
})
</script>

<style scoped>
.audio-edit-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

/* 顶部导航栏 */
.page-header {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 15px 20px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.page-title {
  flex: 1;
  margin: 0;
  font-size: 20px;
  color: #303133;
}

/* 三栏布局 */
.three-columns {
  flex: 1;
  display: flex;
  gap: 15px;
  padding: 15px;
  overflow: hidden;
}

.column {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.image-list-column {
  width: 280px;
  flex-shrink: 0;
}

.image-preview-column {
  flex: 1;
  min-width: 400px;
}

.audio-list-column {
  width: 380px;
  flex-shrink: 0;
}

/* 列头部 */
.column-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 15px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.count-badge {
  background: #409eff;
  color: #fff;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
}

.header-actions {
  display: flex;
  gap: 8px;
}

/* 列主体 */
.column-body {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

/* 图片列表项 */
.page-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  margin-bottom: 8px;
  border: 2px solid #e4e7ed;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
  background: #fff;
}

.page-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.2);
}

.page-item.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.page-thumb {
  width: 60px;
  height: 60px;
  flex-shrink: 0;
  border-radius: 4px;
  overflow: hidden;
}

.thumb-image {
  width: 100%;
  height: 100%;
}

.thumb-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  font-size: 24px;
  color: #c0c4cc;
}

.page-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-name {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.audio-count {
  font-size: 12px;
  color: #909399;
}

.page-index {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #409eff;
  color: #fff;
  border-radius: 50%;
  font-size: 12px;
  font-weight: bold;
  flex-shrink: 0;
}

/* 图片预览 */
.preview-body {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
}

.preview-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  padding: 20px;
  width: 100%;
  height: 100%;
}

.preview-image {
  max-width: 100%;
  max-height: calc(100% - 100px);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.preview-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  height: 400px;
  color: #c0c4cc;
  font-size: 16px;
}

.preview-info {
  text-align: center;
}

.preview-info h3 {
  margin: 0 0 8px 0;
  font-size: 18px;
  color: #303133;
}

.preview-info p {
  margin: 0;
  font-size: 14px;
  color: #909399;
}

/* 音频列表 */
.current-page-hint {
  padding: 10px;
  margin-bottom: 10px;
  background: #ecf5ff;
  border-radius: 6px;
  color: #409eff;
  font-size: 14px;
  font-weight: 500;
}

.audio-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  margin-bottom: 8px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: #fff;
  transition: all 0.3s;
}

.audio-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
}

.audio-item.playing {
  border-color: #67c23a;
  background: #f0f9eb;
}

.audio-item.linked {
  border-color: #409eff;
  background: #ecf5ff;
}

.audio-index {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #409eff;
  color: #fff;
  border-radius: 50%;
  font-size: 12px;
  font-weight: bold;
  flex-shrink: 0;
}

.audio-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.audio-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.audio-name {
  font-size: 14px;
  color: #303133;
  font-weight: 500;
}

.audio-duration {
  font-size: 12px;
  color: #909399;
}

.audio-actions {
  display: flex;
  gap: 5px;
  flex-shrink: 0;
}

/* 上传对话框 */
.upload-demo {
  width: 100%;
}
</style>
