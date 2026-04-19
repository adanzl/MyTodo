<template>
  <div class="task-settings-page">
    <!-- 顶部导航栏 -->
    <div class="top-navbar">
      <div class="navbar-left">
        <el-button link @click="goBack" class="back-btn">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <h1 class="page-title">布置打卡活动</h1>
      </div>
      <div class="navbar-right">
        <el-button
          type="primary"
          :disabled="!canPublish"
          @click="publishActivity"
          class="publish-btn"
        >
          布置
        </el-button>
      </div>
    </div>

    <!-- 表单内容区 -->
    <el-card class="form-card">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <!-- 第1行：任务名称 -->
        <el-form-item label="任务名称" prop="name">
          <el-input
            v-model="form.name"
            placeholder="请输入"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>

        <!-- 第2行：打卡天数 -->
        <el-form-item label="打卡天数" prop="days">
          <el-input-number
            v-model="form.days"
            :min="1"
            :max="365"
            :precision="0"
            placeholder="请输入"
            @change="updateEndTime"
          />
        </el-form-item>

        <!-- 第3行：开始时间 -->
        <el-form-item label="开始时间">
          <div class="start-time-wrapper">
            <el-radio-group v-model="form.startTimeType" @change="handleStartTimeChange">
              <el-radio value="immediate">立即开始</el-radio>
              <el-radio value="custom">自定义开始时间</el-radio>
            </el-radio-group>
            <div class="time-display" v-if="form.startTimeType === 'immediate'">
              <span class="time-text">{{ formatDateTime(form.startTime) }}</span>
              <span class="duration-text">
                （持续{{ form.days }}天，至{{ formatDateTime(form.endTime) }}）
              </span>
            </div>
          </div>
          <el-date-picker
            v-if="form.startTimeType === 'custom'"
            v-model="form.customStartTime"
            type="datetime"
            placeholder="选择开始时间"
            format="YYYY/MM/DD HH:mm"
            value-format="YYYY-MM-DD HH:mm:ss"
            @change="handleCustomTimeChange"
            style="margin-top: 12px; width: 100%;"
          />
        </el-form-item>

        <!-- 第4行：布置对象 -->
        <el-form-item label="布置对象" prop="targets">
          <el-checkbox-group v-model="form.targets">
            <el-checkbox value="Elio">Elio</el-checkbox>
            <el-checkbox value="Claire">Claire</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <!-- 第5行：任务内容 -->
        <el-form-item label="任务内容">
          <el-button
            v-if="addedTasks.length === 0"
            type="primary"
            plain
            @click="showTaskTypeDialog = true"
          >
            选择课件
          </el-button>
          <div v-else class="selected-task-content">
            <el-tag type="success" class="task-count-tag">
              已添加{{ addedTasks.length }}个任务
            </el-tag>
            <el-button link type="primary" @click="showTaskTypeDialog = true">
              继续添加
            </el-button>
          </div>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 任务类型选择弹窗 -->
    <el-dialog
      v-model="showTaskTypeDialog"
      title="请选择任务类型"
      width="500px"
      :close-on-click-modal="true"
      class="task-type-dialog"
    >
      <div class="task-type-grid">
        <div
          v-for="type in taskTypes"
          :key="type.value"
          class="task-type-item"
          @click="handleTaskTypeSelect(type.value)"
        >
          <div class="type-icon" :style="{ background: type.color }">
            <el-icon :size="32" color="#fff">
              <component :is="type.icon" />
            </el-icon>
          </div>
          <div class="type-label">{{ type.label }}</div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import {
  ArrowLeft
} from '@element-plus/icons-vue'

const router = useRouter()
const formRef = ref<FormInstance>()
const showTaskTypeDialog = ref(false)

// 任务类型列表（只保留3种）
const taskTypes = [
  { value: 'reading', label: '阅读', icon: 'Reading', color: '#FF6B6B' },
  { value: 'audio', label: '听力', icon: 'Headset', color: '#45B7D1' },
  { value: 'video', label: '看视频', icon: 'VideoCamera', color: '#4ECDC4' }
]

interface TaskForm {
  name: string
  days: number
  startTime: Date
  endTime: Date
  startTimeType: 'immediate' | 'custom'
  customStartTime: string
  targets: string[]
}

interface AddedTask {
  id: string
  name: string
  type: string
  cover?: string
  completeCount: number
}

const form = reactive<TaskForm>({
  name: '',
  days: 1,
  startTime: new Date(),
  endTime: new Date(),
  startTimeType: 'immediate',
  customStartTime: '',
  targets: ['Elio']
})

// 已添加的任务列表
const addedTasks = ref<AddedTask[]>([])

const rules: FormRules = {
  name: [
    { required: true, message: '请输入任务名称', trigger: 'blur' },
    { min: 1, max: 50, message: '长度在 1 到 50 个字符', trigger: 'blur' }
  ],
  days: [
    { required: true, message: '请填写打卡天数', trigger: 'blur' },
    { type: 'number', min: 1, max: 365, message: '天数范围 1-365', trigger: 'blur' }
  ],
  targets: [
    {
      type: 'array',
      required: true,
      message: '请至少选择1名学员',
      trigger: 'change'
    }
  ]
}

// 是否可以发布
const canPublish = computed(() => {
  return form.name && form.days && form.targets.length > 0 && addedTasks.value.length > 0
})

// 更新结束时间
const updateEndTime = () => {
  const start = form.startTimeType === 'immediate' ? new Date() : (form.customStartTime ? new Date(form.customStartTime) : form.startTime)
  const end = new Date(start)
  end.setDate(end.getDate() + form.days - 1)
  end.setHours(23, 59, 59, 999)
  form.endTime = end
}

// 格式化时间
const formatDateTime = (date: Date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hours = String(date.getHours()).padStart(2, '0')
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${year}/${month}/${day} ${hours}:${minutes}`
}

// 处理开始时间类型切换
const handleStartTimeChange = (value: 'immediate' | 'custom') => {
  if (value === 'immediate') {
    form.startTime = new Date()
    form.customStartTime = ''
    updateEndTime()
  }
}

// 处理自定义时间变化
const handleCustomTimeChange = (value: string) => {
  if (value) {
    form.startTime = new Date(value)
    updateEndTime()
  }
}

// 选择任务类型（直接跳转）
const handleTaskTypeSelect = (type: string) => {
  showTaskTypeDialog.value = false
  
  // 保存任务数据到本地存储
  const taskData = {
    ...form,
    startTime: form.startTime.toISOString(),
    endTime: form.endTime.toISOString()
  }
  localStorage.setItem('tempTaskData', JSON.stringify(taskData))
  
  // 根据任务类型跳转到不同页面
  if (type === 'video') {
    // 视频任务：跳转到视频上传页面
    router.push({
      path: '/admin/video-upload',
      query: { taskType: type }
    })
  } else {
    // 阅读/听力任务：跳转到教材选择页面
    router.push({
      path: '/admin/textbook-select',
      query: { taskType: type }
    })
  }
}

// 返回
const goBack = () => {
  router.back()
}

// 发布活动
const publishActivity = async () => {
  await formRef.value?.validate((valid) => {
    if (valid) {
      if (addedTasks.value.length === 0) {
        ElMessage.warning('请先添加打卡任务')
        return
      }
      
      // TODO: 调用后端API发布活动
      const activityData = {
        ...form,
        startTime: form.startTime.toISOString(),
        endTime: form.endTime.toISOString(),
        tasks: addedTasks.value
      }
      
      console.log('发布活动:', activityData)
      ElMessage.success('打卡活动发布成功')
      
      // 清除临时数据
      localStorage.removeItem('tempTaskData')
      
      // 跳转到任务状态页面
      router.push('/admin/task-status')
    }
  })
}

// 恢复未保存的数据
const restoreTempData = () => {
  const tempData = localStorage.getItem('tempTaskData')
  if (tempData) {
    try {
      const data = JSON.parse(tempData)
      Object.assign(form, {
        ...data,
        startTime: new Date(data.startTime),
        endTime: new Date(data.endTime)
      })
    } catch (e) {
      console.error('恢复临时数据失败', e)
    }
  }
}

onMounted(() => {
  restoreTempData()
  updateEndTime()
})
</script>

<style scoped>
.task-settings-page {
  padding: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

/* 顶部导航栏 */
.top-navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.navbar-left {
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

.navbar-right {
  display: flex;
  gap: 12px;
}

.publish-btn {
  font-weight: 600;
}

/* 表单内容区 */
.form-card {
  flex: 1;
  margin: 20px;
  overflow-y: auto;
}

.start-time-wrapper {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.time-display {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
}

.time-text {
  font-size: 14px;
}

.duration-text {
  font-size: 13px;
  color: #909399;
}

.selected-task-content {
  display: flex;
  align-items: center;
  gap: 12px;
}

.task-count-tag {
  font-size: 14px;
  padding: 8px 16px;
}

/* 任务类型网格 */
.task-type-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  padding: 20px;
}

.task-type-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 24px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
  border: 2px solid transparent;
  background: #f5f7fa;
}

.task-type-item:hover {
  background: #ecf5ff;
  border-color: #409eff;
  transform: translateY(-2px);
}

.type-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.type-label {
  font-size: 14px;
  color: #303133;
  text-align: center;
}

:deep(.el-dialog__header) {
  border-bottom: 1px solid #e4e7ed;
  padding-bottom: 16px;
}

:deep(.el-dialog__body) {
  padding: 20px;
}
</style>
