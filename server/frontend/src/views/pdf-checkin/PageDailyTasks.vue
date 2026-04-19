<template>
  <div class="daily-tasks-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1>每日阅读打卡</h1>
      <el-button type="primary" @click="showFilter = !showFilter">
        <el-icon><Filter /></el-icon>
        筛选
      </el-button>
    </div>

    <!-- 筛选区域 -->
    <el-collapse-transition>
      <div v-show="showFilter" class="filter-section">
        <el-date-picker
          v-model="filterDate"
          type="date"
          placeholder="选择任务日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
        />
        <el-button type="primary" @click="loadTasks">查询</el-button>
        <el-button @click="resetFilter">重置</el-button>
      </div>
    </el-collapse-transition>

    <!-- 任务列表 -->
    <div v-if="tasks.length > 0" class="task-list">
      <el-card
        v-for="task in tasks"
        :key="task.id"
        class="task-card"
        :class="{ 'completed': task.status === 'completed' }"
      >
        <div class="task-content">
          <div class="task-info">
            <h3 class="task-name">{{ task.name }}</h3>
            <p class="courseware-name">PDF标题：{{ task.coursewareName }}</p>
            <p class="task-date">任务日期：{{ task.date }}</p>
            <el-tag :type="task.status === 'completed' ? 'success' : 'danger'">
              {{ task.status === 'completed' ? '已完成' : '未完成' }}
            </el-tag>
          </div>
          <el-button
            type="primary"
            @click="startReading(task)"
          >
            {{ task.status === 'completed' ? '继续阅读' : '开始阅读' }}
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- 空状态 -->
    <el-empty v-else description="今日暂无阅读任务，可查看过往任务">
      <el-button type="primary" @click="viewPastTasks">查看过往任务</el-button>
    </el-empty>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

interface Task {
  id: string
  name: string
  coursewareName: string
  date: string
  status: 'pending' | 'completed'
}

const router = useRouter()
const showFilter = ref(false)
const filterDate = ref('')
const tasks = ref<Task[]>([])

// 加载任务列表
const loadTasks = () => {
  // TODO: 调用API获取任务列表
  // 模拟数据
  tasks.value = [
    {
      id: '1',
      name: '语文课文阅读',
      coursewareName: '春',
      date: '2024-01-15',
      status: 'pending'
    },
    {
      id: '2',
      name: '英语绘本阅读',
      coursewareName: 'The Cat in the Hat',
      date: '2024-01-15',
      status: 'completed'
    }
  ]
}

// 开始阅读
const startReading = (task: Task) => {
  router.push({
    path: '/pdf-reader',
    query: { taskId: task.id }
  })
}

// 重置筛选
const resetFilter = () => {
  filterDate.value = ''
  loadTasks()
}

// 查看过往任务
const viewPastTasks = () => {
  showFilter.value = true
  ElMessage.info('请选择日期查看过往任务')
}

onMounted(() => {
  loadTasks()
})
</script>

<style scoped>
.daily-tasks-page {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.filter-section {
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
  margin-bottom: 20px;
  display: flex;
  gap: 10px;
  align-items: center;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.task-card {
  width: 80%;
  margin: 0 auto;
  transition: all 0.3s;
}

.task-card:hover {
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.task-card.completed {
  border-left: 4px solid #67c23a;
}

.task-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.task-info {
  flex: 1;
}

.task-name {
  margin: 0 0 8px 0;
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}

.courseware-name,
.task-date {
  margin: 5px 0;
  color: #606266;
  font-size: 14px;
}
</style>
