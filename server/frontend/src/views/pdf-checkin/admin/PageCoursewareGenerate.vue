<template>
  <div class="courseware-generate-page">
    <el-card class="main-card">
      <!-- 基本信息区域 -->
      <div class="info-section">
        <el-form :model="coursewareForm" label-width="100px" :rules="rules" ref="formRef">
          <el-form-item label="* 课文名称：" prop="name">
            <el-input
              v-model="coursewareForm.name"
              placeholder="请输入课文名称（默认文件名）"
              style="width: 400px"
              maxlength="100"
            />
          </el-form-item>
        </el-form>
      </div>

      <!-- 操作栏 -->
      <div class="action-bar">
        <span class="required-label">* 添加课文内容</span>
        <el-tooltip content="从本地上传PDF、音频或视频文件">
          <el-button type="primary" @click="showUploadDialog">
            <el-icon><Upload /></el-icon>
            本地上传
          </el-button>
        </el-tooltip>
        <el-tooltip content="从云端服务器选择文件">
          <el-button type="success" @click="showCloudFileDialog">
            <el-icon><FolderOpened /></el-icon>
            云端选择
          </el-button>
        </el-tooltip>
        <el-button @click="batchDeletePages" :disabled="selectedAudios.length === 0">
          批量删除
        </el-button>
        <span class="action-tip">注：请按照绘本内容完成排序</span>
      </div>

      <!-- 三栏布局 -->
      <div class="three-columns">
        <!-- 左侧：图片列表 -->
        <div class="column image-column">
          <div class="column-header">
            <span>图片列表 ({{ pdfPages.length }})</span>
          </div>
          <div class="column-body">
            <div
              v-for="(page, index) in pdfPages"
              :key="page.id"
              class="page-row"
            >
              <div class="page-info">
                <div class="page-index">{{ index + 1 }}</div>
                <div class="page-thumbnail-wrapper">
                  <el-image
                    :src="page.thumbnail"
                    fit="cover"
                    class="page-thumbnail"
                  >
                    <template #error>
                      <div class="image-placeholder">
                        <el-icon><Picture /></el-icon>
                      </div>
                    </template>
                  </el-image>
                </div>
                <span class="page-name">{{ page.name }}</span>
              </div>
              <div class="action-col">
                <el-button
                  link
                  type="warning"
                  size="small"
                  @click="movePageUp(index)"
                  :disabled="index === 0"
                >
                  <el-icon><ArrowUp /></el-icon>
                </el-button>
                <el-button
                  link
                  type="warning"
                  size="small"
                  @click="movePageDown(index)"
                  :disabled="index === pdfPages.length - 1"
                >
                  <el-icon><ArrowDown /></el-icon>
                </el-button>
                <el-button link type="primary" size="small" @click="editPageAudio(page)">
                  编辑音频
                </el-button>
              </div>
            </div>
            <el-empty v-if="pdfPages.length === 0" description="暂无图片，请上传PDF" />
          </div>
        </div>

        <!-- 中间：音频列表 -->
        <div class="column audio-column">
          <div class="column-header">
            <el-checkbox
              v-model="selectAllAudios"
              @change="handleSelectAllAudios"
            />
            <span>音频列表 ({{ allAudios.length }})</span>
          </div>
          <div class="column-body">
            <div
              v-for="audio in allAudios"
              :key="audio.id"
              class="audio-row"
              :class="{ 'selected': audio.selected }"
            >
              <el-checkbox
                v-model="audio.selected"
                @change="handleAudioSelect(audio)"
              />
              <div class="audio-info">
                <el-icon><Headset /></el-icon>
                <span class="audio-name">{{ audio.name }}</span>
                <span class="audio-duration">{{ audio.duration }}</span>
              </div>
              <div class="action-col">
                <el-button link type="primary" size="small" @click="playPageAudio(audio)">
                  <el-icon><VideoPlay /></el-icon>
                </el-button>
                <el-button link type="danger" size="small" @click="removePageAudio(audio)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
            <el-empty v-if="allAudios.length === 0" description="暂无音频，请上传音频文件" />
          </div>
        </div>

        <!-- 右侧：视频列表 -->
        <div class="column video-column">
          <div class="column-header">
            <span>视频列表</span>
            <span class="action-col">操作</span>
          </div>
          <div class="column-body">
            <el-empty description="暂无视频" />
          </div>
        </div>
      </div>

      <!-- 备注信息 -->
      <div class="remark-section">
        <h4>备注信息</h4>
        <el-input
          v-model="coursewareForm.remark"
          type="textarea"
          :rows="3"
          placeholder="请输入备注"
        />
      </div>

      <!-- 底部按钮 -->
      <div class="bottom-actions">
        <el-button type="primary" size="large" @click="saveCourseware" :loading="saving">
          保存课件
        </el-button>
        <el-button size="large" @click="cancel">取消</el-button>
      </div>
    </el-card>

    <!-- 本地上传对话框 -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="本地上传"
      width="500px"
    >
      <el-tabs v-model="uploadTab">
        <el-tab-pane label="PDF文件" name="pdf">
          <el-upload
            class="upload-demo"
            drag
            :auto-upload="false"
            :on-change="handlePdfChange"
            :limit="1"
            accept=".pdf"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将PDF文件拖到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                只能上传PDF文件，上传后将自动转换为图片
              </div>
            </template>
          </el-upload>
        </el-tab-pane>
        <el-tab-pane label="音频文件" name="audio">
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
        </el-tab-pane>
        <el-tab-pane label="视频文件" name="video">
          <el-upload
            class="upload-demo"
            drag
            :auto-upload="false"
            :on-change="handleVideoFileChange"
            :multiple="true"
            accept=".mp4,.avi,.mov"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将视频文件拖到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 mp4, avi, mov 格式
              </div>
            </template>
          </el-upload>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmUpload" :loading="uploading">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 云端文件选择对话框 -->
    <FileDialog
      v-model:visible="cloudFileDialogVisible"
      :title="cloudFileDialogTitle"
      :extensions="cloudFileExtensions"
      mode="file"
      @confirm="handleCloudFileConfirm"
    />
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  Delete,
  Upload,
  FolderOpened,
  Picture,
  ArrowDown,
  ArrowUp,
  Headset,
  VideoPlay,
  UploadFilled,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import FileDialog from '@/views/dialogs/FileDialog.vue'

const router = useRouter()
const route = useRoute()
const formRef = ref()

// 课件表单
const coursewareForm = reactive({
  name: '',
  coverUrl: '',
  remark: ''
})

// 表单验证
const rules = {
  name: [
    { required: true, message: '请输入课文名称', trigger: 'blur' },
    { min: 1, max: 100, message: '长度在 1 到 100 个字符', trigger: 'blur' }
  ]
}

// PDF页面列表
interface PdfPage {
  id: string
  name: string
  thumbnail: string
  linkedAudioIds: string[]  // 关联的音频ID
}

interface AudioItem {
  id: string
  name: string
  duration: string
  url: string
  selected: boolean  // 用于多选删除
  cloudPath?: string
}

const pdfPages = ref<PdfPage[]>([])

// 所有音频列表（不绑定到具体页面）
const allAudios = ref<AudioItem[]>([])
const currentEditingPage = ref<PdfPage | null>(null)
const selectAllAudios = ref(false)
const selectedAudios = computed(() => allAudios.value.filter(a => a.selected))

// 对话框状态
const uploadDialogVisible = ref(false)
const uploading = ref(false)
const saving = ref(false)

// 云端文件选择
const cloudFileDialogVisible = ref(false)
const cloudFileMode = ref<'pdf' | 'audio'>('pdf')

const cloudFileDialogTitle = computed(() => {
  if (cloudFileMode.value === 'pdf') return '选择PDF文件'
  return '选择音频文件'
})

const cloudFileExtensions = computed(() => {
  if (cloudFileMode.value === 'pdf') return '.pdf'
  return 'audio'
})

const showCloudFileDialog = (mode: 'pdf' | 'audio' = 'pdf') => {
  cloudFileMode.value = mode
  cloudFileDialogVisible.value = true
}

const handleCloudFileConfirm = (filePaths: string[]) => {
  if (filePaths.length === 0) return
  
  const filePath = filePaths[0]
  const fileName = filePath.split('/').pop() || ''
  
  if (cloudFileMode.value === 'pdf') {
    // 处理PDF文件
    coursewareForm.name = fileName.replace(/\.pdf$/i, '')
    pdfPages.value = [
      {
        id: '1',
        name: '第1页.jpg',
        thumbnail: `https://placehold.co/200x300/e0e0e0/666?text=${encodeURIComponent(coursewareForm.name)}+Page+1`,
        linkedAudioIds: []
      },
      {
        id: '2',
        name: '第2页.jpg',
        thumbnail: `https://placehold.co/200x300/e0e0e0/666?text=${encodeURIComponent(coursewareForm.name)}+Page+2`,
        linkedAudioIds: []
      },
      {
        id: '3',
        name: '第3页.jpg',
        thumbnail: `https://placehold.co/200x300/e0e0e0/666?text=${encodeURIComponent(coursewareForm.name)}+Page+3`,
        linkedAudioIds: []
      }
    ]
    if (pdfPages.value.length > 0) {
      currentEditingPage.value = pdfPages.value[0]
    }
    ElMessage.success(`已从云端加载PDF：${fileName}`)
  } else if (cloudFileMode.value === 'audio') {
    // 处理音频文件 - 添加到所有音频列表
    const newAudio: AudioItem = {
      id: `audio-${Date.now()}`,
      name: fileName,
      duration: '00:00',
      url: '',
      selected: false,
      cloudPath: filePath
    }
    allAudios.value.push(newAudio)
    ElMessage.success(`已从云端添加音频：${fileName}`)
  }
}


// 上传相关
const uploadTab = ref('pdf')

// 临时存储上传的文件
const uploadedPdfFile = ref<any>(null)
const tempAudioFiles = ref<any[]>([])
const tempVideoFiles = ref<any[]>([])

const showUploadDialog = () => {
  uploadTab.value = 'pdf'
  uploadedPdfFile.value = null
  tempAudioFiles.value = []
  tempVideoFiles.value = []
  uploadDialogVisible.value = true
}

const handlePdfChange = (file: any) => {
  uploadedPdfFile.value = file
}

const handleAudioFileChange = (file: any) => {
  if (file.status === 'removed') {
    tempAudioFiles.value = tempAudioFiles.value.filter(f => f.uid !== file.uid)
  } else {
    tempAudioFiles.value.push(file)
  }
}

const handleVideoFileChange = (file: any) => {
  if (file.status === 'removed') {
    tempVideoFiles.value = tempVideoFiles.value.filter(f => f.uid !== file.uid)
  } else {
    tempVideoFiles.value.push(file)
  }
}

const confirmUpload = async () => {
  uploading.value = true
  
  setTimeout(() => {
    if (uploadTab.value === 'pdf' && uploadedPdfFile.value) {
      const fileName = uploadedPdfFile.value.name
      coursewareForm.name = fileName.replace(/\.pdf$/i, '')
      pdfPages.value = [
        {
          id: '1',
          name: '第1页.jpg',
          thumbnail: `https://placehold.co/200x300/e0e0e0/666?text=${encodeURIComponent(fileName)}+Page+1`,
          linkedAudioIds: []
        },
        {
          id: '2',
          name: '第2页.jpg',
          thumbnail: `https://placehold.co/200x300/e0e0e0/666?text=${encodeURIComponent(fileName)}+Page+2`,
          linkedAudioIds: []
        },
        {
          id: '3',
          name: '第3页.jpg',
          thumbnail: `https://placehold.co/200x300/e0e0e0/666?text=${encodeURIComponent(fileName)}+Page+3`,
          linkedAudioIds: []
        }
      ]
      // 默认选中第一页
      if (pdfPages.value.length > 0) {
        currentEditingPage.value = pdfPages.value[0]
      }
      ElMessage.success(`PDF上传成功：${fileName}`)
    } else if (uploadTab.value === 'audio' && tempAudioFiles.value.length > 0) {
      // 音频添加到所有音频列表
      tempAudioFiles.value.forEach((file, index) => {
        allAudios.value.push({
          id: `audio-${Date.now()}-${index}`,
          name: file.name,
          duration: '00:00',
          url: '',
          selected: false
        })
      })
      ElMessage.success(`已添加 ${tempAudioFiles.value.length} 个音频文件`)
    } else if (uploadTab.value === 'video') {
      ElMessage.info('视频功能待实现')
    } else {
      ElMessage.warning('请选择要上传的文件')
    }
    
    uploading.value = false
    uploadDialogVisible.value = false
  }, 1000)
}

// 全选音频
const handleSelectAllAudios = (val: boolean) => {
  allAudios.value.forEach(audio => {
    audio.selected = val
  })
}

const handleAudioSelect = (_audio: AudioItem) => {
  // 单个音频选择
}

// 图片上移
const movePageUp = (index: number) => {
  if (index > 0) {
    const temp = pdfPages.value[index]
    pdfPages.value[index] = pdfPages.value[index - 1]
    pdfPages.value[index - 1] = temp
    ElMessage.success('图片已上移')
  }
}

// 图片下移
const movePageDown = (index: number) => {
  if (index < pdfPages.value.length - 1) {
    const temp = pdfPages.value[index]
    pdfPages.value[index] = pdfPages.value[index + 1]
    pdfPages.value[index + 1] = temp
    ElMessage.success('图片已下移')
  }
}

// 批量删除音频
const batchDeletePages = () => {
  if (selectedAudios.value.length === 0) {
    ElMessage.warning('请先选择要删除的音频')
    return
  }
  
  ElMessageBox.confirm(
    `确定要删除选中的 ${selectedAudios.value.length} 个音频吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    // 获取要删除的音频ID
    const audioIdsToDelete = selectedAudios.value.map(a => a.id)
    
    // 从 allAudios 中删除
    allAudios.value = allAudios.value.filter(a => !audioIdsToDelete.includes(a.id))
    
    // 从所有页面的 linkedAudioIds 中移除
    pdfPages.value.forEach(page => {
      page.linkedAudioIds = page.linkedAudioIds.filter(id => !audioIdsToDelete.includes(id))
    })
    
    selectAllAudios.value = false
    ElMessage.success('删除成功')
  }).catch(() => {})
}

// 编辑页面音频
const editPageAudio = (_page: PdfPage) => {
  // 保存课件数据到 localStorage
  const coursewareData = {
    name: coursewareForm.name,
    pdfPages: pdfPages.value,
    allAudios: allAudios.value
  }
  localStorage.setItem('courseware_edit_data', JSON.stringify(coursewareData))
  
  // 跳转到音频编辑页面
  const pdfId = route.query.pdfId as string
  router.push({
    path: '/admin/audio-edit',
    query: { pdfId }
  })
}

// 课件生成视图中的音频操作
const playPageAudio = (audio: AudioItem) => {
  ElMessage.info(`播放音频：${audio.name}（模拟）`)
}

const removePageAudio = (audio: AudioItem) => {
  const index = allAudios.value.findIndex(a => a.id === audio.id)
  if (index > -1) {
    allAudios.value.splice(index, 1)
    ElMessage.success('音频已删除')
  }
}

// 保存课件
const saveCourseware = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid: boolean) => {
    if (valid) {
      if (pdfPages.value.length === 0) {
        ElMessage.warning('请至少添加一个页面')
        return
      }
      
      // 检查是否所有页面都添加了音频
      const uneditedPages = pdfPages.value.filter(p => p.linkedAudioIds.length === 0)
      if (uneditedPages.length > 0) {
        ElMessageBox.confirm(
          `还有 ${uneditedPages.length} 个页面未添加音频，确定要保存吗？`,
          '提示',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        ).then(() => {
          performSave()
        }).catch(() => {})
      } else {
        performSave()
      }
    }
  })
}

const performSave = () => {
  saving.value = true
  
  // 模拟保存
  setTimeout(() => {
    saving.value = false
    ElMessage.success('课件保存成功')
    router.push('/admin/material-library')
  }, 1500)
}

// 取消
const cancel = () => {
  router.back()
}


onMounted(() => {
  // 可以从路由参数获取PDF ID
  const pdfId = route.query.pdfId
  if (pdfId) {
    // 加载样例数据
    coursewareForm.name = '春'
    
    // 样例音频（全部音频，不与特定页面绑定）
    allAudios.value = [
      {
        id: 'a1-1',
        name: '春-第一段.mp3',
        duration: '00:45',
        url: '',
        selected: false
      },
      {
        id: 'a1-2',
        name: '春-第二段.mp3',
        duration: '00:38',
        url: '',
        selected: false
      },
      {
        id: 'a2-1',
        name: '春-第三段.mp3',
        duration: '00:52',
        url: '',
        selected: false
      }
    ]
    
    // 样例图片（linkedAudioIds 关联对应音频）
    pdfPages.value = [
      {
        id: '1',
        name: '第1页.jpg',
        thumbnail: `https://placehold.co/200x300/e0e0e0/666?text=${encodeURIComponent('春')}+Page+1`,
        linkedAudioIds: ['a1-1', 'a1-2']  // 关联前两个音频
      },
      {
        id: '2',
        name: '第2页.jpg',
        thumbnail: `https://placehold.co/200x300/e0e0e0/666?text=${encodeURIComponent('春')}+Page+2`,
        linkedAudioIds: ['a2-1']  // 关联第三个音频
      },
      {
        id: '3',
        name: '第3页.jpg',
        thumbnail: `https://placehold.co/200x300/e0e0e0/666?text=${encodeURIComponent('春')}+Page+3`,
        linkedAudioIds: []  // 未关联音频
      }
    ]
    
    // 默认选中第一页
    if (pdfPages.value.length > 0) {
      currentEditingPage.value = pdfPages.value[0]
    }
    
    ElMessage.success(`已加载样例课件：春`)
  }
})
</script>

<style scoped>
.courseware-generate-page {
  padding: 20px;
}

.main-card {
  padding: 20px;
}

.info-section {
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e4e7ed;
}

.cover-tip {
  margin-left: 10px;
  font-size: 12px;
  color: #909399;
}

.cover-preview {
  position: relative;
  display: inline-block;
  margin-top: 10px;
}

.cover-preview img {
  width: 120px;
  height: 90px;
  object-fit: cover;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
}

.remove-cover-btn {
  position: absolute;
  top: 5px;
  right: 5px;
}

.action-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 20px;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.required-label {
  color: #f56c6c;
  font-weight: bold;
  margin-right: 10px;
}

.action-tip {
  margin-left: auto;
  font-size: 12px;
  color: #909399;
}

/* 三栏布局 */
.three-columns {
  display: flex;
  gap: 15px;
  margin-bottom: 20px;
  height: 500px;
}

.column {
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
}

.image-column {
  flex: 2;
}

.audio-column,
.video-column {
  flex: 1;
}

.column-header {
  display: flex;
  align-items: center;
  padding: 10px 15px;
  background: #f5f7fa;
  border-bottom: 1px solid #e4e7ed;
  font-weight: bold;
  gap: 10px;
}

.column-body {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

/* 页面行 */
.page-row {
  display: flex;
  align-items: center;
  padding: 10px;
  margin-bottom: 10px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  gap: 10px;
  background: #fff;
  transition: all 0.3s;
}

.page-row:hover {
  border-color: #409eff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.page-row.selected {
  background: #ecf5ff;
  border-color: #409eff;
}

.page-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

.page-index {
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

.page-thumbnail {
  width: 80px;
  height: 60px;
  border-radius: 4px;
  background-color: #f5f7fa;
}

.page-thumbnail-wrapper {
  width: 80px;
  height: 60px;
  flex-shrink: 0;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  font-size: 24px;
  color: #c0c4cc;
}

.page-name {
  font-size: 14px;
  color: #303133;
}

.status-col {
  width: 100px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}

.status-dot.unedited {
  background: #f56c6c;
}

.status-dot.edited {
  background: #67c23a;
}

.status-text {
  font-size: 12px;
  color: #606266;
}

.action-col {
  width: 180px;
  display: flex;
  align-items: center;
  gap: 5px;
}

.sort-col {
  width: 50px;
  text-align: center;
  font-size: 12px;
  color: #909399;
}

/* 音频行 */
.current-page-info {
  padding: 10px;
  margin-bottom: 10px;
  background: #ecf5ff;
  border-radius: 4px;
  color: #409eff;
  font-size: 14px;
}

.audio-row {
  display: flex;
  align-items: center;
  padding: 10px;
  margin-bottom: 10px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  gap: 10px;
  background: #fff;
}

.audio-row.selected {
  background: #ecf5ff;
  border-color: #409eff;
}

.audio-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.audio-name {
  font-size: 14px;
  color: #303133;
}

.audio-duration {
  font-size: 12px;
  color: #909399;
}

/* 备注区域 */
.remark-section {
  margin-bottom: 20px;
}

.remark-section h4 {
  margin: 0 0 10px 0;
  font-size: 16px;
  color: #303133;
}

/* 底部按钮 */
.bottom-actions {
  display: flex;
  justify-content: center;
  gap: 20px;
  padding-top: 20px;
  border-top: 1px solid #e4e7ed;
}

/* 素材库对话框 */
.material-search {
  margin-bottom: 15px;
}

/* 音频选择对话框 */
.audio-selection {
  max-height: 500px;
  overflow-y: auto;
}

.audio-upload-section {
  margin-bottom: 20px;
}

.audio-list-section h5 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #303133;
}

.temp-audio-list {
  max-height: 200px;
  overflow-y: auto;
}

.temp-audio-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  margin-bottom: 8px;
  background: #f5f7fa;
  border-radius: 4px;
}

.audio-order {
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
}

.audio-file-name {
  flex: 1;
  font-size: 14px;
  color: #303133;
}

.courseware-generate-page {
  height: calc(100vh - 60px);
  background: #f5f7fa;
  padding: 20px;
  overflow-y: auto;
}

.main-card {
  max-width: 1400px;
  margin: 0 auto;
}
</style>
