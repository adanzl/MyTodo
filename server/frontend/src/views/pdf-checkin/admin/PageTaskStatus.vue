<template>
  <div class="task-status-page">
    <h1 class="page-title">任务完成状态查看</h1>

    <!-- 筛选区域 -->
    <el-card class="filter-card">
      <div class="filter-row">
        <el-form :inline="true" :model="filterForm">
          <el-form-item label="任务日期">
            <el-date-picker
              v-model="filterForm.date"
              type="date"
              placeholder="选择日期"
              value-format="YYYY-MM-DD"
              clearable
            />
          </el-form-item>
          <el-form-item label="课件">
            <el-select
              v-model="filterForm.coursewareId"
              placeholder="选择课件"
              clearable
              filterable
              style="width: 200px"
            >
              <el-option
                v-for="courseware in coursewareList"
                :key="courseware.id"
                :label="courseware.name"
                :value="courseware.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="用户账户">
            <el-select
              v-model="filterForm.userId"
              placeholder="选择用户"
              clearable
              filterable
              style="width: 200px"
            >
              <el-option
                v-for="user in userList"
                :key="user.id"
                :label="`${user.username} (${user.account})`"
                :value="user.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="loadTaskList">查询</el-button>
            <el-button @click="resetFilter">重置筛选</el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-card>

    <!-- 任务状态列表 -->
    <el-card class="table-card">
      <el-table
        :data="taskList"
        border
        stripe
        v-loading="loading"
        style="width: 100%"
      >
        <el-table-column prop="taskName" label="任务名称" min-width="150" />
        <el-table-column prop="coursewareName" label="课件名称" min-width="150" />
        <el-table-column prop="userName" label="分配用户" width="120" />
        <el-table-column prop="taskDate" label="任务日期" width="120" />
        <el-table-column prop="status" label="完成状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : 'danger'">
              {{ row.status === 'completed' ? '已完成' : '未完成' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="completeTime" label="完成时间" width="180">
          <template #default="{ row }">
            {{ row.completeTime || '无' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="viewDetail(row)">
              查看详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 数据统计模块 -->
    <el-card class="stats-card">
      <div class="stats-row">
        <el-statistic title="总任务数" :value="stats.totalTasks">
          <template #prefix>
            <el-icon><Document /></el-icon>
          </template>
        </el-statistic>
        <el-statistic title="已完成任务数" :value="stats.completedTasks">
          <template #prefix>
            <el-icon><CircleCheck /></el-icon>
          </template>
        </el-statistic>
        <el-statistic title="完成率" :value="stats.completionRate" suffix="%">
          <template #prefix>
            <el-icon><TrendCharts /></el-icon>
          </template>
        </el-statistic>
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="任务详情"
      width="700px"
    >
      <div v-if="selectedTask" class="task-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="任务名称">
            {{ selectedTask.taskName }}
          </el-descriptions-item>
          <el-descriptions-item label="课件名称">
            {{ selectedTask.coursewareName }}
          </el-descriptions-item>
          <el-descriptions-item label="分配用户">
            {{ selectedTask.userName }}
          </el-descriptions-item>
          <el-descriptions-item label="任务日期">
            {{ selectedTask.taskDate }}
          </el-descriptions-item>
          <el-descriptions-item label="完成状态">
            <el-tag :type="selectedTask.status === 'completed' ? 'success' : 'danger'">
              {{ selectedTask.status === 'completed' ? '已完成' : '未完成' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="完成时间">
            {{ selectedTask.completeTime || '无' }}
          </el-descriptions-item>
        </el-descriptions>

        <div v-if="selectedTask.status === 'completed'" class="checkin-detail">
          <h4>打卡明细</h4>
          <el-table :data="selectedTask.checkinRecords" border size="small">
            <el-table-column prop="page" label="阅读页码" width="100" />
            <el-table-column prop="audioPlayed" label="播放音频" min-width="150" />
            <el-table-column prop="readTime" label="阅读时长" width="120" />
            <el-table-column prop="timestamp" label="时间戳" width="180" />
          </el-table>
        </div>
      </div>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { Document, CircleCheck, TrendCharts } from '@element-plus/icons-vue'

interface Courseware {
  id: string
  name: string
}

interface User {
  id: string
  username: string
  account: string
}

interface CheckinRecord {
  page: number
  audioPlayed: string
  readTime: string
  timestamp: string
}

interface TaskItem {
  id: string
  taskName: string
  coursewareName: string
  userName: string
  taskDate: string
  status: 'pending' | 'completed'
  completeTime?: string
  checkinRecords?: CheckinRecord[]
}

const loading = ref(false)

// 筛选表单
const filterForm = reactive({
  date: '',
  coursewareId: '',
  userId: ''
})

// 课件列表
const coursewareList = ref<Courseware[]>([
  { id: '1', name: '语文课件1' },
  { id: '2', name: '英语课件1' }
])

// 用户列表
const userList = ref<User[]>([
  { id: 'u1', username: '张三', account: 'zhangsan' },
  { id: 'u2', username: '李四', account: 'lisi' }
])

// 任务列表
const taskList = ref<TaskItem[]>([])

// 分页
const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

// 统计数据
const stats = reactive({
  totalTasks: 0,
  completedTasks: 0,
  completionRate: 0
})

// 详情对话框
const detailDialogVisible = ref(false)
const selectedTask = ref<TaskItem | null>(null)

// 加载任务列表
const loadTaskList = () => {
  loading.value = true
  
  // TODO: 调用API获取任务列表
  setTimeout(() => {
    taskList.value = [
      {
        id: 't1',
        taskName: '语文课文阅读',
        coursewareName: '春',
        userName: '张三',
        taskDate: '2024-01-15',
        status: 'completed',
        completeTime: '2024-01-15 18:30:00',
        checkinRecords: [
          { page: 1, audioPlayed: '朗读版本1', readTime: '2分30秒', timestamp: '2024-01-15 18:00:00' },
          { page: 2, audioPlayed: '朗读版本2', readTime: '3分15秒', timestamp: '2024-01-15 18:05:00' }
        ]
      },
      {
        id: 't2',
        taskName: '英语绘本阅读',
        coursewareName: 'The Cat in the Hat',
        userName: '李四',
        taskDate: '2024-01-15',
        status: 'pending',
        completeTime: undefined
      }
    ]
    
    pagination.total = 2
    updateStats()
    loading.value = false
  }, 500)
}

// 更新统计数据
const updateStats = () => {
  stats.totalTasks = taskList.value.length
  stats.completedTasks = taskList.value.filter(t => t.status === 'completed').length
  stats.completionRate = stats.totalTasks > 0
    ? Math.round((stats.completedTasks / stats.totalTasks) * 100)
    : 0
}

// 重置筛选
const resetFilter = () => {
  filterForm.date = ''
  filterForm.coursewareId = ''
  filterForm.userId = ''
  loadTaskList()
}

// 查看详情
const viewDetail = (task: TaskItem) => {
  selectedTask.value = task
  detailDialogVisible.value = true
}

// 分页大小变化
const handleSizeChange = (size: number) => {
  pagination.pageSize = size
  loadTaskList()
}

// 页码变化
const handlePageChange = (page: number) => {
  pagination.page = page
  loadTaskList()
}

onMounted(() => {
  loadTaskList()
})
</script>

<style scoped>
.task-status-page {
  padding: 20px;
}

.page-title {
  margin: 0 0 20px 0;
  font-size: 24px;
  color: #303133;
}

.filter-card {
  margin-bottom: 20px;
}

.filter-row {
  display: flex;
  justify-content: center;
}

.table-card {
  margin-bottom: 20px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.stats-card {
  background: #f5f7fa;
}

.stats-row {
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 20px 0;
}

.task-detail {
  max-height: 600px;
  overflow-y: auto;
}

.checkin-detail {
  margin-top: 20px;
}

.checkin-detail h4 {
  margin: 0 0 10px 0;
  color: #303133;
}
</style>
