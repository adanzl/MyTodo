<template>
  <div class="folder-detail-page">
    <!-- 面包屑导航 -->
    <el-breadcrumb separator="/" class="breadcrumb">
      <el-breadcrumb-item :to="fromSelect ? '/admin/textbook-select' : '/admin/material-library'">
        {{ fromSelect ? '选择课件' : '资料库管理' }}
      </el-breadcrumb-item>
      <el-breadcrumb-item>{{ folderName }}</el-breadcrumb-item>
    </el-breadcrumb>

    <!-- 页面标题和操作栏 -->
    <div class="page-header">
      <div class="header-left">
        <el-icon class="folder-icon"><Folder /></el-icon>
        <h2>{{ folderName }}</h2>
        <el-tag v-if="fileCount > 0" type="info">{{ fileCount }} 个文件</el-tag>
      </div>
      <div class="header-right">
        <el-button
          v-if="fromSelect"
          type="primary"
          @click="confirmSelection"
          :disabled="selectedFiles.length === 0"
        >
          确定添加 ({{ selectedFiles.length }})
        </el-button>
        <el-button v-else type="primary" @click="showUploadDialog">
          <el-icon><Upload /></el-icon>
          新建课件
        </el-button>
        <el-button @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
      </div>
    </div>

    <!-- 文件列表 -->
    <el-card class="file-list-card">
      <el-table
        v-if="fileList.length > 0"
        :data="fileList"
        border
        stripe
        @selection-change="handleSelectionChange"
      >
        <el-table-column v-if="fromSelect" type="selection" width="55" />
        <el-table-column prop="name" label="文件名称" min-width="250">
          <template #default="{ row }">
            <el-icon style="margin-right: 8px; vertical-align: middle;">
              <component :is="folderType === 'pdf' ? Document : Headset" />
            </el-icon>
            {{ row.name }}
          </template>
        </el-table-column>
        <el-table-column prop="size" label="文件大小" width="120">
          <template #default="{ row }">
            {{ formatFileSize(row.size) }}
          </template>
        </el-table-column>
        <el-table-column prop="uploadTime" label="上传时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">
              编辑
            </el-button>
            <el-button link type="primary" @click="handleView(row)">
              查看
            </el-button>
            <el-button link type="danger" @click="handleRemoveFromFolder(row)">
              移出文件夹
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <el-empty
        v-else
        description="该文件夹内暂无文件"
        :image-size="200"
      >
        <el-button type="primary" @click="showUploadDialog">
          <el-icon><Upload /></el-icon>
          新建课件
        </el-button>
      </el-empty>
    </el-card>

    <!-- 上传对话框 -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="上传PDF课件"
      width="500px"
    >
      <el-form :model="uploadForm" label-width="80px">
        <!-- 上传方式选择 -->
        <el-form-item label="上传方式">
          <el-radio-group v-model="uploadMode">
            <el-radio value="local">本地上传</el-radio>
            <el-radio value="cloud">云端选择</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 本地上传 -->
        <el-form-item v-if="uploadMode === 'local'" label="选择文件">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :on-change="handleFileChange"
            :limit="1"
            accept=".pdf"
          >
            <el-button type="primary">选择文件</el-button>
            <template #tip>
              <div class="el-upload__tip">
                只能上传PDF文件
              </div>
            </template>
          </el-upload>
        </el-form-item>

        <!-- 云端选择 -->
        <el-form-item v-if="uploadMode === 'cloud'" label="选择文件">
          <el-button type="primary" @click="openCloudFileDialog">
            <el-icon><FolderOpened /></el-icon>
            从云端选择
          </el-button>
          <div v-if="uploadForm.cloudPath" class="text-sm text-gray-600 mt-2">
            已选择：{{ uploadForm.cloudPath }}
          </div>
        </el-form-item>

        <el-form-item label="文件名称">
          <el-input v-model="uploadForm.name" placeholder="请输入文件名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="uploadForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入文件描述"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmUpload">确认上传</el-button>
      </template>
    </el-dialog>

    <!-- 云端文件选择对话框 -->
    <FileDialog
      v-model:visible="cloudFileDialogVisible"
      title="选择PDF文件"
      extensions=".pdf"
      mode="file"
      @confirm="handleCloudFileConfirm"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Folder, ArrowLeft, Document, Headset, Upload, FolderOpened } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import FileDialog from '@/views/dialogs/FileDialog.vue'

interface FileItem {
  id: string
  name: string
  size: number
  uploadTime: string
  description?: string
  relatedPdf?: string
  cloudPath?: string
  folderId?: string
}

const router = useRouter()
const route = useRoute()

// 从路由参数获取文件夹信息
const folderId = computed(() => route.query.folderId as string)
const folderType = computed(() => (route.query.type as 'pdf' | 'audio') || 'pdf')
const fromSelect = computed(() => route.query.fromSelect === 'true')
const taskType = computed(() => (route.query.taskType as string) || 'reading')
const folderName = ref('')
const fileList = ref<FileItem[]>([])
const selectedFiles = ref<FileItem[]>([])

// 计算文件数量
const fileCount = computed(() => fileList.value.length)

// 上传相关
const uploadDialogVisible = ref(false)
const uploadMode = ref<'local' | 'cloud'>('local')
const uploadForm = reactive({
  name: '',
  description: '',
  file: null as File | null,
  cloudPath: ''
})

// 云端文件选择
const cloudFileDialogVisible = ref(false)

// 格式化文件大小
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
}

// 处理表格选择变化
const handleSelectionChange = (selection: FileItem[]) => {
  selectedFiles.value = selection
}

// 确认选择
const confirmSelection = () => {
  if (selectedFiles.value.length === 0) {
    ElMessage.warning('请至少选择一个课件')
    return
  }

  // 保存选中的文件到临时存储
  const selectedData = {
    taskType: taskType.value,
    files: selectedFiles.value.map(f => ({
      id: f.id,
      name: f.name,
      type: folderType.value
    }))
  }
  localStorage.setItem('selectedCourseware', JSON.stringify(selectedData))

  // 跳转到任务列表编辑页面
  router.push({
    path: '/admin/task-content-config',
    query: {
      taskType: taskType.value
    }
  })
}

// 返回上一页
const goBack = () => {
  if (fromSelect.value) {
    // 从选择课件页面进入，返回选择课件页面
    router.push({
      path: '/admin/textbook-select',
      query: {
        taskType: taskType.value
      }
    })
  } else {
    router.back()
  }
}

// 显示上传对话框
const showUploadDialog = () => {
  uploadMode.value = 'local'
  uploadForm.name = ''
  uploadForm.description = ''
  uploadForm.file = null
  uploadForm.cloudPath = ''
  uploadDialogVisible.value = true
}

// 文件选择变化
const handleFileChange = (file: { status?: string; raw?: File; name: string }) => {
  if (file.status === 'removed') {
    uploadForm.file = null
    return
  }
  if (file.raw) {
    uploadForm.file = file.raw
  }
  if (!uploadForm.name) {
    uploadForm.name = file.name.replace(/\.pdf$/i, '')
  }
}

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

// 确认上传
const confirmUpload = () => {
  // 根据上传方式验证
  if (uploadMode.value === 'local' && !uploadForm.file) {
    ElMessage.warning('请选择文件')
    return
  }
  if (uploadMode.value === 'cloud' && !uploadForm.cloudPath) {
    ElMessage.warning('请从云端选择文件')
    return
  }
  if (!uploadForm.name) {
    ElMessage.warning('请输入文件名称')
    return
  }

  const now = new Date()
  const uploadTime = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')} ${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`

  const newPdf: FileItem = {
    id: `pdf-${Date.now()}`,
    name: uploadForm.name + '.pdf',
    size: uploadForm.file ? uploadForm.file.size : 0,
    uploadTime,
    description: uploadForm.description,
    folderId: folderId.value // 设置文件夹ID
  }
  if (uploadForm.cloudPath) {
    newPdf.cloudPath = uploadForm.cloudPath
  }
  
  fileList.value.push(newPdf)
  ElMessage.success(`PDF课件 "${newPdf.name}" 上传成功`)
  
  uploadDialogVisible.value = false
  uploadForm.name = ''
  uploadForm.description = ''
  uploadForm.file = null
  uploadForm.cloudPath = ''
}

// 加载文件夹数据
const loadFolderData = () => {
  // 从 localStorage 或模拟数据中获取文件夹信息
  const savedFolders = localStorage.getItem('materialFolders')
  if (savedFolders) {
    try {
      const folders = JSON.parse(savedFolders)
      const folder = folders[folderType.value]?.find((f: any) => f.id === folderId.value)
      if (folder) {
        folderName.value = folder.name
      } else {
        folderName.value = '未知文件夹'
      }
    } catch (e) {
      console.error('加载文件夹数据失败', e)
      folderName.value = '未知文件夹'
    }
  } else {
    folderName.value = '文件夹详情'
  }

  // 加载文件列表（模拟数据）
  // TODO: 实际项目中应该从后端API获取
  const mockFiles: FileItem[] = [
    {
      id: '1',
      name: '春 - 朱自清.pdf',
      size: 2048576,
      uploadTime: '2024-01-15 10:30:00',
      folderId: folderId.value
    },
    {
      id: '2',
      name: '背影 - 朱自清.pdf',
      size: 1536000,
      uploadTime: '2024-01-16 14:20:00',
      folderId: folderId.value
    }
  ]

  fileList.value = mockFiles
}

// 编辑文件
const handleEdit = (row: FileItem) => {
  if (folderType.value === 'pdf') {
    router.push({
      path: '/admin/courseware-generate',
      query: { pdfId: row.id }
    })
  } else {
    ElMessage.info('音频编辑功能开发中')
  }
}

// 查看文件
const handleView = (row: FileItem) => {
  if (folderType.value === 'pdf') {
    // 跳转到PDF阅读器页面
    router.push({
      path: '/pdf-reader',
      query: {
        taskId: row.id,
        fromAdmin: 'true' // 标记从管理后台进入
      }
    })
  } else {
    // 播放音频
    ElMessage.info('正在播放音频...')
  }
}

// 从文件夹中移除文件
const handleRemoveFromFolder = (row: FileItem) => {
  ElMessageBox.confirm(
    `确定要将文件"${row.name}"从文件夹中移出吗？`,
    '提示',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    // 更新文件的文件夹ID
    const index = fileList.value.findIndex(f => f.id === row.id)
    if (index > -1) {
      fileList.value.splice(index, 1)
    }

    // TODO: 调用后端API更新文件
    ElMessage.success('已移出文件夹')
  }).catch(() => {})
}

onMounted(() => {
  loadFolderData()
})
</script>

<style scoped>
.folder-detail-page {
  padding: 20px;
  background-color: #f5f7fa;
  min-height: calc(100vh - 60px);
}

.breadcrumb {
  margin-bottom: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.folder-icon {
  font-size: 32px;
  color: #409eff;
}

.header-left h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.file-list-card {
  background: white;
  border-radius: 8px;
}

:deep(.el-table) {
  font-size: 14px;
}

:deep(.el-table th) {
  background-color: #f5f7fa;
  color: #606266;
  font-weight: 600;
}
</style>
