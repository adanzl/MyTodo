<template>
  <div class="task-content-config-page">
    <div class="page-header">
      <div class="header-left">
        <el-button link @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
        </el-button>
        <h1>添加打卡活动内容</h1>
      </div>
      <div class="header-right">
        <el-button round>快速添加</el-button>
        <el-button round>预览</el-button>
        <el-button type="primary" round @click="saveAndReturn">保存</el-button>
      </div>
    </div>

    <div class="config-container">
      <!-- 左侧：打卡天数导航区 -->
      <div class="left-panel">
        <div class="days-list">
          <div
            v-for="day in form.days"
            :key="day"
            class="day-item"
            :class="{ active: currentDay === day, 'has-task': hasTaskForDay(day) }"
            @click="switchDay(day)"
          >
            第{{ day }}天
          </div>
        </div>

        <div class="left-footer" @click="openEditDaysDialog">
          <el-icon><EditPen /></el-icon>
          <span>共{{ form.days }}天</span>
        </div>
      </div>

      <!-- 右侧：任务配置区 -->
      <div class="right-panel">
        <!-- 任务类型筛选 -->
        <div class="filter-bar">
          <el-button
            round
            :type="!activeFilter ? 'primary' : 'default'"
            @click="activeFilter = ''"
          >
            全部({{ totalTasks }})
          </el-button>
          <el-button
            round
            :type="activeFilter === 'reading' ? 'primary' : 'default'"
            @click="activeFilter = 'reading'"
          >
            阅读({{ readingTasks.length }})
          </el-button>
          <el-button round @click="showTaskTypeDialog = true">
            <el-icon><Plus /></el-icon>
            类型
          </el-button>
        </div>

        <!-- 课程标题 -->
        <div v-if="currentCoursewareName" class="course-title">
          {{ currentCoursewareName }}
        </div>

        <!-- 任务列表 -->
        <div class="task-list">
          <div
            v-if="filteredTasks.length > 0"
            class="task-items"
          >
            <div
              v-for="(task, index) in filteredTasks"
              :key="index"
              class="task-card"
            >
              <!-- 序号 -->
              <div class="task-index">{{ index + 1 }}</div>
              
              <!-- 封面图 -->
              <div class="task-cover">
                <el-icon v-if="!task.cover" :size="40" color="#909399">
                  <Picture />
                </el-icon>
                <img v-else :src="task.cover" alt="" />
              </div>
              
              <!-- 任务信息 -->
              <div class="task-info">
                <h4 class="task-name">{{ task.name }}</h4>
                <el-tag size="small" type="danger" effect="plain">{{ getTaskTypeLabel(task.type) }}</el-tag>
              </div>
              
              <!-- 操作按钮 -->
              <div class="task-actions">
                <div class="complete-count">
                  <div class="count-box">1</div>
                  <span>完成次数</span>
                </div>
                <el-button link class="action-btn">
                  <el-icon><EditPen /></el-icon>
                  修改
                </el-button>
                <el-button link type="danger" class="action-btn" @click="removeTask(index)">
                  <el-icon><Delete /></el-icon>
                  删除
                </el-button>
              </div>
            </div>
          </div>

          <!-- 空状态 -->
          <el-empty
            v-else
            description="暂无任务，请点击下方按钮添加"
            :image-size="100"
          />
        </div>

        <!-- 底部操作按钮 -->
        <div class="footer-actions">
          <el-button link type="primary">同步内容</el-button>
          <el-button type="primary" round @click="showAddTaskDialog = true">
            <el-icon><Plus /></el-icon>
            继续添加
          </el-button>
          <el-button link>批量操作</el-button>
        </div>
      </div>
    </div>

    <!-- 任务类型选择弹窗 -->
    <el-dialog
      v-model="showTaskTypeDialog"
      title="请选择任务类型"
      width="700px"
      class="task-type-dialog"
    >
      <div class="task-type-grid">
        <div
          v-for="type in taskTypes"
          :key="type.value"
          class="task-type-item"
          :class="{ active: selectedTaskTypes.includes(type.value) }"
          @click="toggleTaskType(type.value)"
        >
          <div class="type-icon" :style="{ background: type.color }">
            <el-icon :size="32" color="#fff">
              <component :is="type.icon" />
            </el-icon>
          </div>
          <div class="type-label">{{ type.label }}</div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showTaskTypeDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmTaskTypes">确定</el-button>
      </template>
    </el-dialog>

    <!-- 添加任务弹窗 -->
    <el-dialog
      v-model="showAddTaskDialog"
      title="请选择课文"
      width="1000px"
      class="courseware-dialog"
    >
      <div class="add-task-container">
        <!-- 左侧：分页选择 -->
        <div class="page-selector">
          <div class="page-item" :class="{ active: !pageRange }" @click="pageRange = ''">全部</div>
          <div
            v-for="range in pageRanges"
            :key="range"
            class="page-item"
            :class="{ active: pageRange === range }"
            @click="pageRange = range"
          >
            {{ range }}
          </div>
        </div>

        <!-- 右侧：课件列表 -->
        <div class="courseware-list">
          <div class="list-header">
            <span class="title">{{ pageRange || '全部' }}</span>
            <el-checkbox v-model="selectAll" @change="handleSelectAll">全选</el-checkbox>
          </div>
          <div class="courseware-grid">
            <div
              v-for="item in filteredCoursewareList"
              :key="item.id"
              class="courseware-card"
              :class="{ selected: isCoursewareSelected(item.id) }"
              @click="toggleCoursewareSelection(item)"
            >
              <div class="card-cover">
                <el-icon v-if="!item.cover" :size="48" color="#909399">
                  <Picture />
                </el-icon>
                <img v-else :src="item.cover" alt="" />
                <div class="badge" v-if="item.canTest">可测评</div>
                <div v-if="isCoursewareSelected(item.id)" class="check-badge">
                  <el-icon :size="20" color="#fff"><Check /></el-icon>
                </div>
              </div>
              <div class="card-info">
                <div class="card-title">{{ item.pdfTitle }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button round @click="showAddTaskDialog = false">取消</el-button>
          <div>
            <el-button round>选择分页</el-button>
            <el-button type="primary" round @click="confirmAddTasks">确定添加</el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- 编辑天数弹窗 -->
    <el-dialog
      v-model="showEditDaysDialog"
      title="编辑天数"
      width="400px"
    >
      <el-form label-width="80px">
        <el-form-item label="总天数">
          <el-input-number
            v-model="editDays"
            :min="1"
            :max="365"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button round @click="showEditDaysDialog = false">取消</el-button>
        <el-button type="primary" round @click="confirmEditDays">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  ArrowLeft,
  Delete,
  Plus,
  EditPen,
  Picture,
  Check,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

interface TaskItem {
  name: string
  type: string
  cover?: string
  resourceId?: string
}

interface CoursewareItem {
  id: string
  name: string
  pdfTitle: string
  type: string
  cover?: string
  canTest?: boolean
  page: number
}

interface TaskForm {
  days: number
  taskData: Record<number, TaskItem[]>
}

const router = useRouter()

// 弹窗状态
const showAddTaskDialog = ref(false)
const showTaskTypeDialog = ref(false)
const showEditDaysDialog = ref(false)
const editDays = ref(1)
const selectedCourseware = ref<CoursewareItem[]>([])
const selectedTaskTypes = ref(['reading'])
const activeFilter = ref('')
const pageRange = ref('')
const selectAll = ref(false)

// 当前选中的天数
const currentDay = ref(1)

// 分页范围
const pageRanges = ['1-10', '11-20', '21-30', '31-40', '41-52']

// 任务类型列表
const taskTypes = [
  { value: 'reading', label: '阅读', icon: 'Reading', color: '#FF6B6B' },
  { value: 'video', label: '视频', icon: 'VideoCamera', color: '#4ECDC4' },
  { value: 'audio', label: '听力', icon: 'Headset', color: '#45B7D1' }
]

// 表单数据
const form = reactive<TaskForm>({
  days: 1,
  taskData: {}
})

// 模拟课件数据
const allCourseware: CoursewareItem[] = [
  { id: '1', name: 'A Man of Vision', pdfTitle: '01-A Man of Vision', type: 'reading', canTest: true, page: 1 },
  { id: '2', name: 'A Prairie Dog\'s Life', pdfTitle: '02-A Prairie Dog\'s Life', type: 'reading', canTest: true, page: 2 },
  { id: '3', name: 'Aesop\'s Fables', pdfTitle: '03-Aesop\'s Fables', type: 'reading', canTest: true, page: 3 },
  { id: '4', name: 'ART Around Us', pdfTitle: '04-ART Around Us', type: 'reading', canTest: true, page: 4 },
  { id: '5', name: 'Arthur\'s Bad-News Day', pdfTitle: '05-Arthur\'s Bad-News Day', type: 'reading', canTest: true, page: 5 }
]

// 过滤课件列表
const filteredCoursewareList = computed(() => {
  if (!pageRange.value) return allCourseware
  
  const [start, end] = pageRange.value.split('-').map(Number)
  return allCourseware.filter(c => c.page >= start && c.page <= end)
})

// 当前天数的任务列表
const currentDayTasks = computed(() => {
  return form.taskData[currentDay.value] || []
})

// 根据类型筛选任务
const readingTasks = computed(() => {
  return currentDayTasks.value.filter(t => t.type === 'reading')
})

const totalTasks = computed(() => {
  return currentDayTasks.value.length
})

// 过滤后的任务列表
const filteredTasks = computed(() => {
  if (!activeFilter.value) return currentDayTasks.value
  return currentDayTasks.value.filter(t => t.type === activeFilter.value)
})

// 当前课件名称
const currentCoursewareName = computed(() => {
  return 'Reading AtoZ-M'
})

// 判断某天是否有任务
const hasTaskForDay = (day: number) => {
  const tasks = form.taskData[day]
  return tasks && tasks.length > 0
}

// 获取任务类型标签
const getTaskTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    reading: '阅读',
    video: '看视频',
    audio: '听力'
  }
  return labels[type] || type
}

// 切换天数
const switchDay = (day: number) => {
  currentDay.value = day
}

// 切换任务类型
const toggleTaskType = (type: string) => {
  const index = selectedTaskTypes.value.indexOf(type)
  if (index > -1) {
    selectedTaskTypes.value.splice(index, 1)
  } else {
    selectedTaskTypes.value.push(type)
  }
}

// 确认任务类型
const confirmTaskTypes = () => {
  if (selectedTaskTypes.value.length === 0) {
    ElMessage.warning('请至少选择一种任务类型')
    return
  }
  showTaskTypeDialog.value = false
  ElMessage.success('任务类型已更新')
}

// 判断课件是否已选中
const isCoursewareSelected = (id: string) => {
  return selectedCourseware.value.some(item => item.id === id)
}

// 切换课件选中状态
const toggleCoursewareSelection = (item: CoursewareItem) => {
  const index = selectedCourseware.value.findIndex(c => c.id === item.id)
  if (index > -1) {
    selectedCourseware.value.splice(index, 1)
  } else {
    selectedCourseware.value.push(item)
  }
  selectAll.value = selectedCourseware.value.length === filteredCoursewareList.value.length
}

// 全选处理
const handleSelectAll = (value: boolean) => {
  if (value) {
    selectedCourseware.value = [...filteredCoursewareList.value]
  } else {
    selectedCourseware.value = []
  }
}

// 删除任务
const removeTask = (index: number) => {
  ElMessageBox.confirm(
    '确定要删除这个任务吗？',
    '确认删除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    if (!form.taskData[currentDay.value]) {
      form.taskData[currentDay.value] = []
    }
    form.taskData[currentDay.value].splice(index, 1)
    ElMessage.success('任务已删除')
  }).catch(() => {
    // 用户取消
  })
}

// 确认添加任务
const confirmAddTasks = () => {
  if (selectedCourseware.value.length === 0) {
    ElMessage.warning('请选择课件')
    return
  }

  if (!form.taskData[currentDay.value]) {
    form.taskData[currentDay.value] = []
  }

  // 添加选中的课件
  selectedCourseware.value.forEach(item => {
    form.taskData[currentDay.value].push({
      name: item.pdfTitle,
      type: item.type,
      cover: item.cover,
      resourceId: item.id
    })
  })

  showAddTaskDialog.value = false
  selectedCourseware.value = []
  selectAll.value = false
  ElMessage.success(`已添加 ${selectedCourseware.value.length} 个任务`)
}

// 保存并返回
const saveAndReturn = () => {
  const hasTask = Object.values(form.taskData).some(
    (tasks: TaskItem[]) => tasks && tasks.length > 0
  )

  if (!hasTask) {
    ElMessage.warning('请至少为 1 天添加任务')
    return
  }

  localStorage.setItem('tempTaskConfig', JSON.stringify({
    taskType: 'reading',
    form: {
      ...form,
      taskData: form.taskData
    }
  }))

  ElMessage.success('保存成功')
  router.back()
}

// 编辑天数弹窗 - 打开时初始化
const openEditDaysDialog = () => {
  editDays.value = form.days
  showEditDaysDialog.value = true
}

// 确认编辑天数
const confirmEditDays = () => {
  const oldDays = form.days
  const newDays = editDays.value
  
  if (newDays === oldDays) {
    showEditDaysDialog.value = false
    return
  }
  
  // 确认修改
  ElMessageBox.confirm(
    `将天数从 ${oldDays} 天调整为 ${newDays} 天？\n如果新天数少于当前天数，超出的任务将被删除。`,
    '确认修改',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    if (newDays < oldDays) {
      // 如果减少天数，删除多余天数的任务
      for (let day = newDays + 1; day <= oldDays; day++) {
        delete form.taskData[day]
      }
    }
    
    form.days = newDays
    
    // 如果当前选中的天数超出范围，切换到第1天
    if (currentDay.value > newDays) {
      currentDay.value = 1
    }
    
    showEditDaysDialog.value = false
    ElMessage.success(`天数已调整为 ${newDays} 天`)
  }).catch(() => {
    // 用户取消
  })
}

// 返回
const goBack = () => {
  ElMessageBox.confirm(
    '确定要放弃当前配置吗？未保存的数据将丢失。',
    '确认取消',
    {
      confirmButtonText: '确定',
      cancelButtonText: '继续编辑',
      type: 'warning'
    }
  ).then(() => {
    router.back()
  }).catch(() => {
    // 用户选择继续编辑
  })
}

// 恢复未保存的数据
const restoreTempData = () => {
  const tempData = localStorage.getItem('tempTaskData')
  const configData = localStorage.getItem('tempTaskConfig')
  const selectedResourcesData = localStorage.getItem('selectedResources')
  
  if (tempData) {
    try {
      const data = JSON.parse(tempData)
      form.days = data.days || 1
    } catch (e) {
      console.error('恢复临时数据失败', e)
    }
  }

  if (configData) {
    try {
      const data = JSON.parse(configData)
      if (data.form) {
        form.days = data.form.days
        form.taskData = data.form.taskData || {}
      }
    } catch (e) {
      console.error('恢复配置数据失败', e)
    }
  }
  
  // 如果从资料库选择了资源，自动添加到第一天
  if (selectedResourcesData) {
    try {
      const data = JSON.parse(selectedResourcesData)
      if (data.resources && data.resources.length > 0) {
        // 初始化第一天的任务列表
        if (!form.taskData[1]) {
          form.taskData[1] = []
        }
        
        // 添加选中的资源到第一天
        data.resources.forEach((resource: { name: string; cover?: string; id: string }) => {
          form.taskData[1].push({
            name: resource.name,
            type: data.taskType || 'reading',
            cover: resource.cover || '',
            resourceId: resource.id
          })
        })
        
        ElMessage.success(`已从资料库导入 ${data.resources.length} 个任务`)
        
        // 清除已读取的资料库数据（避免重复导入）
        localStorage.removeItem('selectedResources')
      }
    } catch (e) {
      console.error('恢复资料库数据失败', e)
    }
  }
}

onMounted(() => {
  restoreTempData()
})
</script>

<style scoped>
.task-content-config-page {
  padding: 20px;
  height: calc(100vh - 80px);
  display: flex;
  flex-direction: column;
  background: #f0f5ff;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-left h1 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}

.header-right {
  display: flex;
  gap: 12px;
}

.config-container {
  display: flex;
  gap: 24px;
  flex: 1;
  overflow: hidden;
}

.left-panel {
  width: 140px;
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.days-list {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 16px;
}

.day-item {
  padding: 14px 16px;
  margin-bottom: 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  text-align: center;
  color: #606266;
  position: relative;
}

.day-item:hover {
  background: #ecf5ff;
}

.day-item.active {
  background: #e8f0ff;
  color: #409eff;
  font-weight: 600;
}

.day-item.has-task::after {
  content: '';
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 8px;
  height: 8px;
  background: #409eff;
  border-radius: 50%;
}

.left-footer {
  border-top: 1px solid #e4e7ed;
  padding-top: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: #909399;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
}

.left-footer:hover {
  color: #409eff;
}

.right-panel {
  flex: 1;
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.course-title {
  font-size: 18px;
  color: #303133;
  margin-bottom: 20px;
  font-weight: 600;
}

.task-list {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 20px;
}

.task-items {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.task-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  transition: all 0.3s;
}

.task-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.task-index {
  width: 40px;
  height: 40px;
  background: #f5f7fa;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: #606266;
  font-weight: 600;
}

.task-cover {
  width: 80px;
  height: 80px;
  border-radius: 8px;
  overflow: hidden;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.task-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.task-info {
  flex: 1;
}

.task-name {
  margin: 0 0 8px 0;
  font-size: 16px;
  color: #303133;
}

.task-actions {
  display: flex;
  align-items: center;
  gap: 20px;
}

.complete-count {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.count-box {
  width: 48px;
  height: 48px;
  background: #f5f7fa;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.complete-count span {
  font-size: 12px;
  color: #909399;
}

.action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.footer-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 20px;
  border-top: 1px solid #e4e7ed;
}

/* 任务类型弹窗 */
.task-type-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  padding: 20px;
}

.task-type-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 20px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
  border: 2px solid transparent;
  background: #f5f7fa;
}

.task-type-item:hover {
  background: #ecf5ff;
  border-color: #409eff;
}

.task-type-item.active {
  background: #ecf5ff;
  border-color: #409eff;
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

/* 课件选择弹窗 */
.add-task-container {
  display: flex;
  gap: 24px;
  min-height: 400px;
}

.page-selector {
  width: 120px;
  background: #f5f7fa;
  border-radius: 8px;
  overflow: hidden;
}

.page-item {
  padding: 14px 16px;
  cursor: pointer;
  transition: all 0.3s;
  text-align: center;
  color: #606266;
}

.page-item:hover {
  background: #ecf5ff;
}

.page-item.active {
  background: #409eff;
  color: #fff;
  font-weight: 600;
}

.courseware-list {
  flex: 1;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.list-header .title {
  font-size: 16px;
  color: #303133;
  font-weight: 600;
}

.courseware-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  max-height: 400px;
  overflow-y: auto;
}

.courseware-card {
  border: 2px solid #e4e7ed;
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.3s;
  background: #fff;
}

.courseware-card:hover {
  border-color: #409eff;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.courseware-card.selected {
  border-color: #409eff;
  background: #ecf5ff;
}

.card-cover {
  width: 100%;
  aspect-ratio: 3 / 4;
  background: #f5f7fa;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.card-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.badge {
  position: absolute;
  bottom: 8px;
  right: 8px;
  background: #409eff;
  color: #fff;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.check-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  background: #409eff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-info {
  padding: 12px;
}

.card-title {
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.dialog-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dialog-footer > div {
  display: flex;
  gap: 12px;
}
</style>
