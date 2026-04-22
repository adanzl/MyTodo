<template>
  <div class="p-2">
    <!-- 日期选择器 -->
    <div class="mb-4 flex items-center gap-4">
      <el-button type="primary" size="small" @click="refreshTasks" :icon="Refresh" />
      <el-radio-group v-model="selectedUserId" @change="handleUserChange">
        <el-radio :value="0">全部</el-radio>
        <el-radio :value="3">灿灿</el-radio>
        <el-radio :value="4">昭昭</el-radio>
      </el-radio-group>
      <div class="ml-auto flex items-center">
        <el-switch v-model="showDetail" @change="handleDetailChange" :active-text="''" :inactive-text="'详情'" class="mr-2" />
        <el-button size="small" :icon="ArrowLeft" @click="decreaseDays" class="mr-1" />
        <el-date-picker
          v-model="startDate"
          type="date"
          placeholder="选择开始日期"
          class="w-35! mr-1"
          size="small"
          @change="handleDateChange"
        />
        <el-button size="small" @click="setToday" class="w-4 mr-1">今</el-button>
        <el-button size="small" :icon="ArrowRight" @click="increaseDays" class="ml-0! mr-2" />
        <span class="text-gray-700 mr-1 text-sm">显示天数</span>
        <el-input-number
          v-model="dayCount"
          :min="1"
          :max="30"
          :step="1"
          class="w-20!"
          size="small"
        />
      </div>
    </div>

    <!-- 任务列表 -->
    <el-table
      :data="displayData"
      v-loading="loading"
      border
      style="width: 100%"
      row-key="id"
      :row-class-name="getRowClassName"
    >
      <el-table-column prop="name" label="任务名称" min-width="150" fixed>
        <template #default="{ row }">
          <div :class="row.isTask === false ? 'pl-6' : ''">
            {{ row.name }}
          </div>
        </template>
      </el-table-column>

      <!-- 动态生成10天的列 -->
      <el-table-column
        v-for="date in weekDates"
        :key="date.getTime()"
        width="110"
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
            <span v-if="row.isTask !== false">
              {{ getTaskProgress(row, date) }}
            </span>
            <span v-else>
              {{ getMaterialStatus(row, date) }}
            </span>
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
import { Refresh, ArrowLeft, ArrowRight } from "@element-plus/icons-vue";
import { getTaskList, type Task } from "@/api/api-task";
import { formatDateShort, getWeekDay, getDaysDiff, generateDateRange } from "@/utils/date";
import dayjs from "dayjs";
import { TaskDetail } from "@/types/tasks/taskDetail";

// 状态管理
const loading = ref(false);
const taskList = ref<Task[]>([]);
const startDate = ref(new Date());
const totalCount = ref(0);
const pageNum = ref(1);
const pageSize = ref(20);
const selectedUserId = ref<number>(0);
const showDetail = ref(false);

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
  return generateDateRange(startDate.value, dayCount.value);
});

// 监听显示天数变化，保存到 localStorage
watch(dayCount, (newVal) => {
  saveDayCount(newVal);
});

// 计算显示数据（包含任务和素材）
const displayData = computed(() => {
  if (!showDetail.value) {
    return taskList.value;
  }

  const result: any[] = [];
  taskList.value.forEach((task) => {
    // 添加任务行
    result.push({ ...task, isTask: true });

    // 添加素材行
    try {
      const taskData = typeof task.data === "string" ? JSON.parse(task.data) : task.data;
      const dailyMaterials = taskData.dailyMaterials || {};

      // 收集所有素材
      const allMaterials: Record<string, any> = {};
      (Object.values(dailyMaterials) as any[][]).forEach((materials) => {
        materials.forEach((m) => {
          if (!allMaterials[m.id]) {
            allMaterials[m.id] = { ...m, taskId: task.id };
          }
        });
      });

      // 添加素材行
      Object.values(allMaterials).forEach((material: any) => {
        result.push({
          id: `task_${task.id}_material_${material.id}`,
          name: `${material.name}`,
          type: material.type,
          taskId: task.id,
          isTask: false,
        });
      });
    } catch (error) {
      console.error("解析任务数据失败:", error);
    }
  });

  return result;
});

// 获取素材状态
const getMaterialStatus = (row: any, date: Date) => {
  const taskId = row.taskId;
  if (!taskId) return "";

  try {
    const task = taskList.value.find((t) => t.id === taskId);
    if (!task) return "";

    const taskData: TaskDetail = typeof task.data === "string" ? JSON.parse(task.data) : task.data;
    const dailyMaterials = taskData.dailyMaterials || {};

    // 计算这是任务的第几天
    const diffDays = getDaysDiff(task.start_date, date);

    if (diffDays < 0 || diffDays >= task.duration) {
      return "";
    }

    // 获取该天的素材列表（使用0-based索引）
    const materials = dailyMaterials[diffDays] || [];

    // 找到当前素材
    const material = materials.find((m: any) => m.name === row.name);
    if (!material) return "";

    // 检查是否完成
    if (material.status === 1) {
      return "✅";
    }
    return "❌";
  } catch (error) {
    return "";
  }
};

// 详情开关变化
const handleDetailChange = () => {
  // 可以在这里添加额外的逻辑
};

// 获取行类名
const getRowClassName = ({ row }: { row: any }) => {
  return showDetail.value && row.isTask !== false ? 'bg-gray-50' : '';
};

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
  fetchTaskList();
};

// 用户选择变化
const handleUserChange = () => {
  pageNum.value = 1;
  fetchTaskList();
};

// 刷新任务列表
const refreshTasks = () => {
  fetchTaskList();
};

// 设置为今天
const setToday = () => {
  startDate.value = new Date();
  fetchTaskList();
};

// 减少显示天数
const decreaseDays = () => {
  startDate.value = dayjs(startDate.value).subtract(dayCount.value, 'day').toDate();
  fetchTaskList();
};

// 增加显示天数
const increaseDays = () => {
  startDate.value = dayjs(startDate.value).add(dayCount.value, 'day').toDate();
  fetchTaskList();
};

// 获取任务在指定日期的进度
const getTaskProgress = (task: Task, date: Date) => {
  try {
    const taskData = typeof task.data === "string" ? JSON.parse(task.data) : task.data;
    const dailyMaterials = taskData.dailyMaterials || {};

    // 计算这是任务的第几天
    const diffDays = getDaysDiff(task.start_date, date);

    // 如果日期在任务开始前或结束后，显示 "-"
    if (diffDays < 0 || diffDays >= task.duration) {
      return "-";
    }

    // 获取该天的素材列表（使用0-based索引）
    const materials = dailyMaterials[diffDays] || [];
    const totalMaterials = materials.length;

    // 统计完成数
    const completedCount = materials.filter((m: any) => m.status === 1).length;

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
