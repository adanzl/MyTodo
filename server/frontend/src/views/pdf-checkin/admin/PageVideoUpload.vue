<template>
  <div class="video-upload-page">
    <!-- 面包屑导航 -->
    <el-breadcrumb separator="/" class="breadcrumb">
      <el-breadcrumb-item :to="{ path: '/admin/task-settings' }">任务设置</el-breadcrumb-item>
      <el-breadcrumb-item>上传视频</el-breadcrumb-item>
    </el-breadcrumb>

    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <el-icon class="video-icon"><VideoCamera /></el-icon>
        <h2>上传视频</h2>
        <el-tag type="success">视频任务</el-tag>
      </div>
      <div class="header-right">
        <el-button @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
      </div>
    </div>

    <!-- 上传方式选择 -->
    <el-card class="upload-card">
      <el-form label-width="100px">
        <!-- 上传方式 -->
        <el-form-item label="上传方式">
          <el-radio-group v-model="uploadMode">
            <el-radio value="local">本地上传</el-radio>
            <el-radio value="cloud">云端选择</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 本地上传 -->
        <div v-if="uploadMode === 'local'" class="upload-area">
          <el-upload
            ref="uploadRef"
            class="upload-dragger"
            drag
            :auto-upload="false"
            :on-change="handleFileChange"
            :limit="1"
            accept="video/*"
          >
            <el-icon class="el-icon--upload"><Upload /></el-icon>
            <div class="el-upload__text">
              将视频文件拖到此处，或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 mp4、avi、mov 等常见视频格式，单个文件不超过 500MB
              </div>
            </template>
          </el-upload>
        </div>

        <!-- 云端选择 -->
        <div v-if="uploadMode === 'cloud'" class="upload-area">
          <el-button type="primary" size="large" @click="openCloudFileDialog">
            <el-icon><FolderOpened /></el-icon>
            从云端选择视频文件
          </el-button>
          <div v-if="uploadForm.cloudPath" class="selected-file-info">
            <el-icon color="#67C23A"><CircleCheck /></el-icon>
            <span>已选择：{{ uploadForm.cloudPath }}</span>
          </div>
        </div>

        <!-- 文件信息 -->
        <div v-if="uploadForm.file || uploadForm.cloudPath" class="file-info">
          <el-divider />
          <el-form-item label="视频名称">
            <el-input v-model="uploadForm.name" placeholder="请输入视频名称" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input
              v-model="uploadForm.description"
              type="textarea"
              :rows="3"
              placeholder="请输入视频描述（可选）"
            />
          </el-form-item>
        </div>

        <!-- 操作按钮 -->
        <el-form-item class="action-buttons">
          <el-button type="primary" size="large" @click="confirmUpload" :disabled="!canUpload">
            确认上传
          </el-button>
          <el-button size="large" @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 云端文件选择对话框 -->
    <FileDialog
      v-model:visible="cloudFileDialogVisible"
      title="选择视频文件"
      extensions=".mp4,.avi,.mov,.mkv,.wmv,.flv"
      mode="file"
      @confirm="handleCloudFileConfirm"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { VideoCamera, ArrowLeft, Upload, FolderOpened, CircleCheck } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import FileDialog from '@/views/dialogs/FileDialog.vue'

const router = useRouter()

interface UploadForm {
  name: string
  description: string
  file: File | null
  cloudPath: string
}

const uploadMode = ref<'local' | 'cloud'>('local')
const uploadForm = reactive<UploadForm>({
  name: '',
  description: '',
  file: null,
  cloudPath: ''
})

const uploadRef = ref()
const cloudFileDialogVisible = ref(false)

// 是否可以上传
const canUpload = computed(() => {
  if (uploadMode.value === 'local') {
    return !!uploadForm.file && !!uploadForm.name
  }
  return !!uploadForm.cloudPath && !!uploadForm.name
})

// 打开云端文件选择
const openCloudFileDialog = () => {
  cloudFileDialogVisible.value = true
}

// 云端文件选择确认
const handleCloudFileConfirm = (filePaths: string[]) => {
  if (filePaths.length > 0) {
    uploadForm.cloudPath = filePaths[0]
    if (!uploadForm.name) {
      const fileName = filePaths[0].split('/').pop() || ''
      uploadForm.name = fileName.replace(/\.[^/.]+$/, '')
    }
    ElMessage.success('已选择云端文件')
  }
}

// 文件选择变化
const handleFileChange = (file: { status?: string; raw?: File; name: string; size: number }) => {
  if (file.status === 'removed') {
    uploadForm.file = null
    return
  }
  
  // 检查文件大小（500MB）
  const maxSize = 500 * 1024 * 1024
  if (file.size > maxSize) {
    ElMessage.error('视频文件大小不能超过 500MB')
    uploadForm.file = null
    return
  }
  
  if (file.raw) {
    uploadForm.file = file.raw
  }
  if (!uploadForm.name) {
    uploadForm.name = file.name.replace(/\.[^/.]+$/, '')
  }
}

// 确认上传
const confirmUpload = () => {
  // 根据上传方式验证
  if (uploadMode.value === 'local' && !uploadForm.file) {
    ElMessage.warning('请选择视频文件')
    return
  }
  if (uploadMode.value === 'cloud' && !uploadForm.cloudPath) {
    ElMessage.warning('请从云端选择视频文件')
    return
  }
  if (!uploadForm.name) {
    ElMessage.warning('请输入视频名称')
    return
  }

  // TODO: 实际项目中调用后端API上传文件
  const videoData = {
    name: uploadForm.name,
    description: uploadForm.description,
    cloudPath: uploadForm.cloudPath || '',
    uploadMode: uploadMode.value,
    uploadTime: new Date().toISOString()
  }

  // 保存视频信息到 localStorage（临时存储）
  const savedVideos = localStorage.getItem('uploadedVideos')
  const videos = savedVideos ? JSON.parse(savedVideos) : []
  videos.push({
    id: `video-${Date.now()}`,
    ...videoData
  })
  localStorage.setItem('uploadedVideos', JSON.stringify(videos))

  ElMessage.success(`视频"${uploadForm.name}"上传成功`)
  
  // 返回资料库管理页面
  router.push({
    path: '/admin/material-library'
  })
}

// 重置表单
const resetForm = () => {
  uploadMode.value = 'local'
  uploadForm.name = ''
  uploadForm.description = ''
  uploadForm.file = null
  uploadForm.cloudPath = ''
  uploadRef.value?.clearFiles()
}

// 返回
const goBack = () => {
  router.back()
}
</script>

<style scoped>
.video-upload-page {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.breadcrumb {
  margin-bottom: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.video-icon {
  font-size: 32px;
  color: #409eff;
}

.header-left h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.upload-card {
  padding: 32px;
}

.upload-area {
  margin: 20px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.upload-dragger {
  width: 100%;
}

.selected-file-info {
  margin-top: 16px;
  padding: 12px 16px;
  background: #f0f9ff;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #67C23A;
}

.file-info {
  margin-top: 20px;
}

.action-buttons {
  margin-top: 24px;
}
</style>
