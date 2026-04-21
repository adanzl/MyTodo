<template>
  <div class="p-2">
    <!-- 日期选择器 -->
    <div class="mb-4 flex items-center gap-4">
      <span class="text-gray-700 font-medium">快速定位日期：</span>
      <el-date-picker
        v-model="startDate"
        type="date"
        placeholder="选择开始日期"
        class="w-35!"
        @change="handleDateChange"
      />
      <span class="text-gray-700 font-medium">显示天数：</span>
      <el-input-number
        v-model="dayCount"
        :min="1"
        :max="30"
        :step="1"
        class="w-28!"
      />
      <span class="text-gray-700 font-medium">布置对象：</span>
      <el-radio-group v-model="selectedUserId" @change="handleUserChange">
        <el-radio :value="0">全部</el-radio>
        <el-radio :value="3">灿灿</el-radio>
        <el-radio :value="4">昭昭</el-radio>
      </el-radio-group>
    </div>

    <!-- 任务列表 -->
    <el-table :data="taskList" v-loading="loading" stripe border style="width: 100%">
      <el-table-column prop="name" label="任务名称" min-width="150" fixed />

      <!-- 动态生成10天的列 -->
      <el-table-column
        v-for="(date, index) in weekDates"
        :key="index"
        width="120"
        align="center"
      >
        <template #header>
          <div class="text-sm font-medium">
            {{ formatDateShort(date) }}
          </div>
          <div class="text-xs text-gray-500">
            {{ getWeekDay(date) }}
          </div>
        </template>
        <template #default="{ row }">
          <div class="text-sm">
            {{ getTaskProgress(row, date) }}
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <el-pagination
      layout="sizes, prev, pager, next"
      :total="totalCount"
      v-model:page-size="pageSize"
      :page-sizes="[10, 20, 50]"
      :current-page="pageNum"
      class="mt-2"
      background
      @size-change="handleSizeChange"
      @current-change="handlePageChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { ElMessage } from "element-plus";
import { getTaskList, type Task } from "@/api/api-task";

// 状态管理
const loading = ref(false);
const taskList = ref<Task[]>([]);
const startDate = ref(new Date());
const totalCount = ref(0);
const pageNum = ref(1);
const pageSize = ref(20);
const selectedUserId = ref<number>(0);

// 从 localStorage 获取显示天数，默认 8
const STORAGE_KEY_DAY_COUNT = "task_calendar_day_count";
const getSavedDayCount = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY_DAY_COUNT);
    return saved ? parseInt(saved) : 8;
  } catch {
    return 8;
  }
};
const dayCount = ref(getSavedDayCount());

// 保存显示天数到 localStorage
const saveDayCount = (count: number) => {
  try {
    localStorage.setItem(STORAGE_KEY_DAY_COUNT, String(count));
  } catch (error) {
    console.warn("Failed to save day count:", error);
  }
};

// 计算动态天数日期
const weekDates = computed(() => {
  const dates = [];
  for (let i = 0; i < dayCount.value; i++) {
    const date = new Date(startDate.value);
    date.setDate(date.getDate() + i);
    dates.push(date);
  }
  return dates;
});

// 监听显示天数变化，保存到 localStorage
watch(dayCount, (newVal) => {
  saveDayCount(newVal);
});

// 获取任务列表
const fetchTaskList = async () => {
  loading.value = true;
  try {
    const res = await getTaskList(selectedUserId.value, pageNum.value, pageSize.value);
    if (res.code === 0 && res.data) {
      taskList.value = res.data.data || [];
      totalCount.value = res.data.totalCount || 0;
    }
  } catch (error: any) {
    ElMessage.error(error.message || "获取任务列表失败");
  } finally {
    loading.value = false;
  }
};

// 分页变化
const handlePageChange = (page: number) => {
  pageNum.value = page;
  fetchTaskList();
};

const handleSizeChange = (size: number) => {
  pageSize.value = size;
  pageNum.value = 1;
  fetchTaskList();
};

// 日期变化
const handleDateChange = () => {
  // 可以在这里添加额外的逻辑
};

// 用户选择变化
const handleUserChange = () => {
  pageNum.value = 1;
  fetchTaskList();
};

// 格式化日期（简短）
const formatDateShort = (date: Date) => {
  const month = date.getMonth() + 1;
  const day = date.getDate();
  return `${month}/${day}`;
};

// 获取星期
const getWeekDay = (date: Date) => {
  const weekDays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
  return weekDays[date.getDay()];
};

// 获取任务在指定日期的进度
const getTaskProgress = (task: Task, date: Date) => {
  try {
    // 解析 data 字段
    const taskData = typeof task.data === "string" ? JSON.parse(task.data) : task.data;
    const dailyMaterials = taskData.dailyMaterials || {};

    // 计算这是任务的第几天
    const taskStartDate = new Date(task.start_date);
    const diffTime = date.getTime() - taskStartDate.getTime();
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));

    // 如果日期在任务开始前或结束后，显示 "-"
    if (diffDays < 0 || diffDays >= task.duration) {
      return "-";
    }

    // 获取该天的素材列表
    const dayNumber = diffDays + 1;
    const materials = dailyMaterials[dayNumber] || [];
    const totalMaterials = materials.length;

    // TODO: 这里需要从后端获取实际的完成情况
    // 目前暂时显示 0/总数
    const completedCount = 0;

    return `${completedCount}/${totalMaterials}`;
  } catch (error) {
    return "-";
  }
};

// 初始化
onMounted(() => {
  fetchTaskList();
});
</script>
