<template>
  <div class="textbook-select-page">
    <!-- 顶部导航 -->
    <div class="page-header">
      <div class="header-left">
        <el-button link @click="goBack" class="back-btn">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <h2 class="page-title">选择课件</h2>
        <el-tag :type="taskType === 'reading' ? 'danger' : 'primary'" class="task-type-tag">
          {{ taskType === 'reading' ? '阅读' : '听力' }}
        </el-tag>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="confirmSelection" :disabled="selectedItems.length === 0">
          确定添加 ({{ selectedItems.length }})
        </el-button>
      </div>
    </div>

    <!-- 内容区 -->
    <div class="content-container">
      <!-- 文件夹列表 -->
      <el-card class="section-card">
        <div class="section-title">
          <el-icon><Folder /></el-icon>
          <span>文件夹</span>
        </div>
        
        <el-table :data="folders" border stripe>
          <el-table-column label="文件夹名称" min-width="250">
            <template #default="{ row }">
              <div class="folder-name-link" @click="enterFolder(row)">
                <el-icon style="margin-right: 8px; vertical-align: middle;"><Folder /></el-icon>
                {{ row.name }}
              </div>
            </template>
          </el-table-column>
        </el-table>

        <el-empty v-if="folders.length === 0" description="暂无文件夹" />
      </el-card>

      <!-- 文件列表 -->
      <el-card class="section-card">
        <div class="section-title">
          <el-icon><Document /></el-icon>
          <span>课件</span>
        </div>
        
        <el-table
          :data="files"
          border
          stripe
          @selection-change="handleFileSelectionChange"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="name" label="课件名称" min-width="200">
            <template #default="{ row }">
              <div class="item-name">
                <el-icon v-if="taskType === 'reading'" style="margin-right: 8px; vertical-align: middle;"><Document /></el-icon>
                <el-icon v-else style="margin-right: 8px; vertical-align: middle;"><Headset /></el-icon>
                {{ row.name }}
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="type" label="类型" width="120" />
          <el-table-column prop="totalPages" label="页数" width="80" v-if="taskType === 'reading'" />
          <el-table-column prop="duration" label="时长" width="100" v-if="taskType === 'audio'" />
        </el-table>

        <el-empty v-if="files.length === 0" description="暂无课件" />
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Folder, Document, Headset } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()

interface FolderItem {
  id: string
  name: string
  fileCount: number
}

interface FileItem {
  id: string
  name: string
  type: string
  totalPages?: number
  duration?: string
  folderId?: string
}

const taskType = ref('')
const folders = ref<FolderItem[]>([])
const files = ref<FileItem[]>([])
const selectedItems = ref<string[]>([])

// 样例数据 - 文件夹
const sampleFolders: FolderItem[] = [
  { id: 'folder-1', name: '语文课文', fileCount: 5 },
  { id: 'folder-2', name: '英语绘本', fileCount: 8 },
  { id: 'folder-3', name: 'Reading AtoZ', fileCount: 12 }
]

// 样例数据 - 课件
const sampleFiles: FileItem[] = [
  { id: 'file-1', name: '春 - 朱自清', type: '语文', totalPages: 10, folderId: 'folder-1' },
  { id: 'file-2', name: 'The Cat in the Hat', type: '英语', totalPages: 15, folderId: 'folder-2' },
  { id: 'file-3', name: 'Reading AtoZ-M Level 1', type: '英语阅读', totalPages: 1, folderId: 'folder-3' },
  { id: 'file-4', name: 'Reading AtoZ-M Level 2', type: '英语阅读', totalPages: 1, folderId: 'folder-3' },
  { id: 'file-5', name: 'Reading AtoZ-M Level 3', type: '英语阅读', totalPages: 1, folderId: 'folder-3' },
  { id: 'file-6', name: 'Thinking 2 B1 Unit 1', type: '英语', totalPages: 20, folderId: 'folder-2' },
  { id: 'file-7', name: 'Wonders Reader G1', type: '英语', totalPages: 30, folderId: 'folder-2' }
]

// 加载数据
const loadData = () => {
  // 优先使用 localStorage 数据，否则使用样例数据
  const savedData = localStorage.getItem('materialFolders')
  if (savedData) {
    try {
      const data = JSON.parse(savedData)
      const folderType = taskType.value === 'audio' ? 'audio' : 'pdf'
      const fileType = taskType.value === 'audio' ? 'audioFiles' : 'pdfFiles'
      
      folders.value = data[folderType] || sampleFolders
      files.value = data[fileType] || sampleFiles
    } catch (e) {
      console.error('加载数据失败，使用样例数据', e)
      folders.value = sampleFolders
      files.value = sampleFiles
    }
  } else {
    // 使用样例数据
    folders.value = sampleFolders
    files.value = sampleFiles
  }
}

// 进入文件夹
const enterFolder = (folder: FolderItem) => {
  // 跳转到文件夹详情页
  router.push({
    path: '/admin/folder-detail',
    query: {
      folderId: folder.id,
      folderName: folder.name,
      type: taskType.value === 'audio' ? 'audio' : 'pdf',
      fromSelect: 'true', // 标记从选择课件页面进入
      taskType: taskType.value
    }
  })
}

// 处理文件选择变化
const handleFileSelectionChange = (selection: Array<{ id: string }>) => {
  // 合并文件夹和文件的选择
  const folderSelection = selectedItems.value.filter(id => id.startsWith('folder-'))
  const fileSelection = selection.map(item => item.id)
  selectedItems.value = [...folderSelection, ...fileSelection]
}

// 确认选择
const confirmSelection = () => {
  if (selectedItems.value.length === 0) {
    ElMessage.warning('请至少选择一个课件或文件夹')
    return
  }

  // 保存选中的项目到临时存储
  const selectedData = {
    taskType: taskType.value,
    itemIds: selectedItems.value,
    folders: folders.value.filter(f => selectedItems.value.includes(f.id)),
    files: files.value.filter(f => selectedItems.value.includes(f.id))
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

// 返回
const goBack = () => {
  router.back()
}

onMounted(() => {
  taskType.value = (route.query.taskType as string) || ''
  loadData()
})
</script>

<style scoped>
.textbook-select-page {
  padding: 20px;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

.page-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-btn {
  font-size: 20px;
  color: #606266;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.task-type-tag {
  font-size: 14px;
}

.content-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section-card {
  padding: 24px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.folder-name-link {
  color: #409eff;
  cursor: pointer;
  transition: all 0.3s;
  display: inline-flex;
  align-items: center;
  font-weight: 500;
}

.folder-name-link:hover {
  color: #66b1ff;
  text-decoration: underline;
}

:deep(.el-table) {
  font-size: 14px;
}

:deep(.el-table th) {
  background-color: #f5f7fa;
  color: #606266;
  font-weight: 600;
}

:deep(.el-card) {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}
</style>
