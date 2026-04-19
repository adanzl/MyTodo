<template>
  <div class="lesson-select-page">
    <!-- 顶部导航 -->
    <div class="page-header">
      <div class="header-left">
        <el-button link @click="goBack" class="back-btn">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <h2 class="page-title">{{ folderName }}</h2>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="confirmSelection" :disabled="selectedLessons.length === 0">
          确定添加 ({{ selectedLessons.length }})
        </el-button>
      </div>
    </div>

    <!-- 课件列表 -->
    <div class="content-container">
      <el-card class="lesson-card">
        <el-table
          :data="lessons"
          border
          stripe
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="55" />
          <el-table-column prop="name" label="课件名称" min-width="200">
            <template #default="{ row }">
              <el-icon v-if="taskType === 'reading'" style="margin-right: 8px; vertical-align: middle;"><Document /></el-icon>
              <el-icon v-else-if="taskType === 'audio'" style="margin-right: 8px; vertical-align: middle;"><Headset /></el-icon>
              {{ row.name }}
            </template>
          </el-table-column>
          <el-table-column prop="type" label="类型" width="120" />
          <el-table-column prop="totalPages" label="页数" width="80" v-if="taskType === 'reading'" />
          <el-table-column prop="duration" label="时长" width="100" v-if="taskType === 'audio'" />
        </el-table>

        <el-empty v-if="lessons.length === 0" description="暂无课件" />
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Document, Headset } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()

interface LessonItem {
  id: string
  name: string
  type: string
  totalPages?: number
  duration?: string
}

const folderName = ref('')
const taskType = ref('')
const lessons = ref<LessonItem[]>([])
const selectedLessons = ref<LessonItem[]>([])

// 加载课件数据
const loadLessons = () => {
  const savedData = localStorage.getItem('materialFolders')
  if (savedData) {
    try {
      const data = JSON.parse(savedData)
      const folderType = taskType.value === 'audio' ? 'audioFiles' : 'pdfFiles'
      // TODO: 根据folderId过滤文件，暂时显示所有文件
      lessons.value = data[folderType] || []
    } catch (e) {
      console.error('加载课件数据失败', e)
    }
  }
}

// 处理表格选择变化
const handleSelectionChange = (selection: LessonItem[]) => {
  selectedLessons.value = selection
}

// 确认选择
const confirmSelection = () => {
  if (selectedLessons.value.length === 0) {
    ElMessage.warning('请至少选择一个课件')
    return
  }

  // 保存选中的课件到临时存储
  const selectedData = {
    folderName: folderName.value,
    taskType: taskType.value,
    lessons: selectedLessons.value
  }
  localStorage.setItem('selectedLessons', JSON.stringify(selectedData))

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
  folderName.value = (route.query.folderName as string) || ''
  taskType.value = (route.query.taskType as string) || ''
  loadLessons()
})
</script>

<style scoped>
.lesson-select-page {
  padding: 20px;
  height: calc(100vh - 60px);
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

.content-container {
  flex: 1;
  overflow-y: auto;
}

.lesson-card {
  padding: 24px;
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
