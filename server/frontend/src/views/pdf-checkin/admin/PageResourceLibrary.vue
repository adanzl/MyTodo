<template>
  <div class="resource-library-page">
    <div class="page-header">
      <div class="header-left">
        <el-button link @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <h1>资料库</h1>
        <el-tag :type="taskTypeTag">{{ getTaskTypeLabel(taskType) }}</el-tag>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="confirmSelection">
          确定 ({{ selectedResources.length }})
        </el-button>
      </div>
    </div>

    <el-card class="content-container">
      <!-- 搜索和筛选栏 -->
      <div class="toolbar">
        <div class="filter-controls">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索资源名称"
            clearable
            style="width: 200px"
          />
          <el-button @click="resetFilter">重置</el-button>
        </div>
      </div>

      <!-- 文件夹列表 -->
      <el-table v-if="folders.length > 0" :data="folders" border stripe style="margin-bottom: 20px">
        <el-table-column label="文件夹名称" min-width="250">
          <template #default="{ row }">
            <div class="folder-name-link" @click="viewFolder(row)">
              <el-icon style="margin-right: 8px; vertical-align: middle;"><Folder /></el-icon>
              {{ row.name }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="fileCount" label="文件数量" width="120" />
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewFolder(row)">
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 资源列表 -->
      <el-table
        :data="filteredResources"
        border
        stripe
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="name" label="资源名称" min-width="200">
          <template #default="{ row }">
            <el-icon v-if="row.taskType === 'reading'" style="margin-right: 8px; vertical-align: middle;"><Document /></el-icon>
            <el-icon v-else-if="row.taskType === 'video'" style="margin-right: 8px; vertical-align: middle;"><VideoCamera /></el-icon>
            <el-icon v-else-if="row.taskType === 'audio'" style="margin-right: 8px; vertical-align: middle;"><Headset /></el-icon>
            {{ row.name }}
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="filteredResources.length === 0" description="暂无资源" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, Folder, Document, VideoCamera, Headset } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const route = useRoute()

const taskType = ref(route.query.taskType as string || 'reading')
const searchKeyword = ref('')
const filterType = ref('all')
const selectedResources = ref<string[]>([])

// 文件夹数据
const folders = ref([
  { id: 'folder-1', name: '语文课文', fileCount: 5 },
  { id: 'folder-2', name: '英语绘本', fileCount: 8 },
  { id: 'folder-3', name: '数学练习', fileCount: 3 }
])

// 查看文件夹
const viewFolder = (folder: { id: string }) => {
  router.push({
    path: '/admin/folder-detail',
    query: {
      folderId: folder.id,
      type: taskType.value === 'reading' ? 'pdf' : 'audio'
    }
  })
}

// 重置筛选
const resetFilter = () => {
  searchKeyword.value = ''
  filterType.value = 'all'
}

// 处理表格选择变化
const handleSelectionChange = (selection: Array<{ id: string }>) => {
  selectedResources.value = selection.map(item => item.id)
}

// 任务类型标签
const taskTypeTag = computed(() => {
  const tags: Record<string, string> = {
    reading: 'primary',
    video: 'success',
    audio: 'warning'
  }
  return tags[taskType.value] || 'info'
})

// 获取任务类型标签
const getTaskTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    reading: '阅读',
    video: '看视频',
    audio: '听力'
  }
  return labels[type] || type
}

// 模拟资源数据
// 模拟资源数据（实际应从API获取）
const allResources = ref([
  { id: '1', name: '春 - 朱自清', type: '语文', taskType: 'reading', totalPages: 10, duration: '5分钟' },
  { id: '2', name: 'The Cat in the Hat', type: '英语', taskType: 'reading', totalPages: 15, duration: '10分钟' },
  { id: '3', name: 'Reading AtoZ-M Level 1', type: '英语阅读', taskType: 'reading', totalPages: 1 },
  { id: '4', name: 'Reading AtoZ-M Level 2', type: '英语阅读', taskType: 'reading', totalPages: 1 },
  { id: '5', name: 'Reading AtoZ-M Level 3', type: '英语阅读', taskType: 'reading', totalPages: 1 },
  { id: '6', name: 'Reading AtoZ-M Level 4', type: '英语阅读', taskType: 'reading', totalPages: 1 },
  { id: '7', name: 'Reading AtoZ-M Level 5', type: '英语阅读', taskType: 'reading', totalPages: 1 },
  { id: '8', name: '自然拼读视频第1课', type: '视频', taskType: 'video', duration: '15分钟' },
  { id: '9', name: '自然拼读视频第2课', type: '视频', taskType: 'video', duration: '20分钟' },
  { id: '10', name: '英语听力练习-日常对话', type: '听力', taskType: 'audio', duration: '5分钟' },
  { id: '11', name: '英语听力练习-故事阅读', type: '听力', taskType: 'audio', duration: '8分钟' },
  { id: '12', name: 'Think 2 B1 Unit 1', type: '英语', taskType: 'reading', totalPages: 20 },
  { id: '13', name: 'Reading AtoZ-F Level 1', type: '英语阅读', taskType: 'reading', totalPages: 1 },
  { id: '14', name: 'Reading AtoZ-J Level 1', type: '英语阅读', taskType: 'reading', totalPages: 1 },
  { id: '15', name: 'Wonders Reader G1', type: '英语', taskType: 'reading', totalPages: 30 }
])

// 从 localStorage 加载文件夹数据
const loadFolderData = () => {
  const savedFolders = localStorage.getItem('materialFolders')
  if (savedFolders) {
    try {
      const foldersData = JSON.parse(savedFolders)
      const pdfFolders = foldersData.pdf || []
      const audioFolders = foldersData.audio || []
      
      // 根据任务类型选择文件夹
      const folderType = taskType.value === 'audio' ? audioFolders : pdfFolders
      folders.value = folderType.map((f: any) => ({
        id: f.id,
        name: f.name,
        fileCount: f.fileCount
      }))
    } catch (e) {
      console.error('加载文件夹数据失败', e)
    }
  }
}

// 过滤后的资源列表
const filteredResources = computed(() => {
  let resources = allResources.value
  
  // 根据任务类型过滤
  if (taskType.value) {
    resources = resources.filter(r => r.taskType === taskType.value)
  }
  
  // 搜索关键词过滤
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    resources = resources.filter(r => r.name.toLowerCase().includes(keyword))
  }
  
  return resources
})

// 确认选择
const confirmSelection = () => {
  if (selectedResources.value.length === 0) {
    ElMessage.warning('请至少选择一个资源')
    return
  }

  // 获取选中的资源详细信息
  const selectedResourceDetails = selectedResources.value
    .map(id => allResources.value.find(r => r.id === id))
    .filter(Boolean) as any[]

  // 保存选择的资源到 localStorage
  const selectedData = {
    taskType: taskType.value,
    resources: selectedResourceDetails,
    timestamp: Date.now()
  }
  localStorage.setItem('selectedResources', JSON.stringify(selectedData))

  ElMessage.success(`已选择 ${selectedResources.value.length} 个资源`)
  
  // 跳转到分日任务设置页面
  router.push({
    path: '/admin/task-content-config',
    query: { taskType: taskType.value }
  })
}

// 返回
const goBack = () => {
  if (selectedResources.value.length > 0) {
    ElMessageBox.confirm(
      '确定要放弃已选择的资源吗？',
      '提示',
      {
        confirmButtonText: '确定',
        cancelButtonText: '继续选择',
        type: 'warning'
      }
    ).then(() => {
      router.back()
    }).catch(() => {
      // 用户取消
    })
  } else {
    router.back()
  }
}

onMounted(() => {
  // 加载文件夹和文件数据
  loadFolderData()
})
</script>

<style scoped>
.resource-library-page {
  padding: 20px;
  height: calc(100vh - 80px);
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
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
  gap: 16px;
}

.header-left h1 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.content-container {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.filter-controls {
  display: flex;
  gap: 10px;
  align-items: center;
}

.folder-name-link {
  color: #409eff;
  cursor: pointer;
  transition: all 0.3s;
  display: inline-flex;
  align-items: center;
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
</style>
