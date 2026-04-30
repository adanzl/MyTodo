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
      :max-height="tableMaxHeight"
      :row-class-name="getRowClassName"
      :row-style="getRowStyle"
      :span-method="getSpanMethod"
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
      v-model:current-page="pageNum"
      :page-sizes="[10, 20, 50]"
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

const tableMaxHeight = ref<number>(0);

// 计算表格最大高度
const calculateTableHeight = () => {
  nextTick(() => {
    const windowHeight = window.innerHeight;
    const reservedSpace = 300;
    tableMaxHeight.value = windowHeight - reservedSpace;
  });
};
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

      // 收集素材
      const materialsToDisplay: any[] = [];

      if (task.type === 1) {
        // type=1（持续任务）：只收集第0天的素材
        const day0Materials = dailyMaterials[0] || [];
        day0Materials.forEach((m: any) => {
          materialsToDisplay.push({
            ...m,
            taskId: task.id,
            taskType: task.type,
            taskStartDate: task.start_date,
            taskDuration: task.duration
          });
        });
      } else {
        // type=0（每日任务）：收集所有天的素材
        const allMaterials: Record<string, any> = {};
        (Object.values(dailyMaterials) as any[][]).forEach((materials) => {
          materials.forEach((m) => {
            if (!allMaterials[m.id]) {
              allMaterials[m.id] = {
                ...m,
                taskId: task.id,
                taskType: task.type,
                taskStartDate: task.start_date,
                taskDuration: task.duration
              };
            }
          });
        });
        Object.values(allMaterials).forEach((material: any) => {
          materialsToDisplay.push(material);
        });
      }

      // 添加素材行到结果
      materialsToDisplay.forEach((material: any) => {
        result.push({
          id: `task_${task.id}_material_${material.id}`,
          name: `${material.name}`,
          type: material.type,
          taskId: task.id,
          taskType: material.taskType,
          taskStartDate: material.taskStartDate,
          taskDuration: material.taskDuration,
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

    // type=1（持续任务）：只看第0天的素材
    const materialsIndex = task.type === 1 ? 0 : diffDays;
    const materials = dailyMaterials[materialsIndex] || [];

    // 找到当前素材
    const material = materials.find((m: any) => m.name === row.name);
    if (!material) return "";

    // 检查是否完成 - status 现在是 Record<user_id, status>
    // 如果 selectedUserId 为 0（全部），检查是否所有用户都完成
    if (material.status) {
      if (selectedUserId.value === 0) {
        // 全部用户：检查是否有任意用户完成
        const hasCompleted = Object.values(material.status).some(s => s === 1);
        return hasCompleted ? "✅" : "❌";
      } else {
        // 特定用户：检查该用户的状态
        const userStatus = material.status[String(selectedUserId.value)];
        return userStatus === 1 ? "✅" : "❌";
      }
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

// 设置行样式，详情模式下高亮任务行
const getRowStyle = ({ row }: { row: any }) => {
  if (showDetail.value && row.isTask !== false) {
    return { backgroundColor: '#f0f9ff' };
  }
  return {};
};

// 合并单元格方法，type=1的任务和素材行只合并任务所在天的单元格
const getSpanMethod = ({ row, columnIndex }: any) => {
  // type=1（持续任务）的任务行
  const isType1Task = row.isTask !== false && row.type === 1;
  // 详情模式下的 type=1 素材行
  const isType1Material = showDetail.value && row.isTask === false && row.taskType === 1;

  if (!(isType1Task || isType1Material) || columnIndex < 1) {
    return { rowspan: 1, colspan: 1 };
  }

  // 获取任务的开始日期和持续时间
  const taskStartDate = isType1Task ? row.start_date : row.taskStartDate;
  const taskDuration = isType1Task ? row.duration : row.taskDuration;

  if (!taskStartDate || !taskDuration) {
    return { rowspan: 1, colspan: 1 };
  }

  // 计算任务覆盖的日期范围
  const startDate = dayjs(taskStartDate).startOf('day');
  const endDate = startDate.add(taskDuration - 1, 'day').endOf('day');

  // 检查当前列的日期是否在任务范围内
  const currentDate = dayjs(weekDates.value[columnIndex - 1]).startOf('day');

  if (currentDate.isBefore(startDate) || currentDate.isAfter(endDate)) {
    return { rowspan: 1, colspan: 1 };
  }

  // 计算从当前列开始，后面还有多少列在任务范围内
  let colspan = 1;
  for (let i = columnIndex; i < weekDates.value.length; i++) {
    const nextDate = dayjs(weekDates.value[i]).startOf('day');
    if (nextDate.isBefore(endDate) || nextDate.isSame(endDate, 'day')) {
      colspan++;
    } else {
      break;
    }
  }

  // 判断当前列是否是视图中任务覆盖范围的第一列
  const prevDate = columnIndex > 1 ? dayjs(weekDates.value[columnIndex - 2]).startOf('day') : null;
  const isFirstInViewRange = columnIndex === 1 || (prevDate && prevDate.isBefore(startDate));
  return isFirstInViewRange ? { rowspan: 1, colspan } : { rowspan: 0, colspan: 0 };
};

// 获取任务列表
const fetchTaskList = async () => {
  loading.value = true;
  try {
    // 计算视图的日期范围
    const viewStartDate = weekDates.value[0];
    const viewEndDate = weekDates.value[weekDates.value.length - 1];

    const startDateStr = viewStartDate ? dayjs(viewStartDate).format('YYYY-MM-DD') : undefined;
    const endDateStr = viewEndDate ? dayjs(viewEndDate).format('YYYY-MM-DD') : undefined;

    const res = await getTaskList(
      selectedUserId.value,
      pageNum.value,
      pageSize.value,
      startDateStr,
      endDateStr
    );
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

    let materials: any[] = [];

    // type=1（持续任务）：只看第0天的素材
    if (task.type === 1) {
      materials = dailyMaterials[0] || [];
    } else {
      // type=0（每日任务）：获取该天的素材列表
      materials = dailyMaterials[diffDays] || [];
    }

    const totalMaterials = materials.length;

    // 统计完成数 - status 现在是 Record<user_id, status>
    let completedCount = 0;
    if (selectedUserId.value === 0) {
      // 全部用户：素材有任何一个用户完成就算完成
      completedCount = materials.filter((m: any) => {
        if (!m.status) return false;
        return Object.values(m.status).some((s: any) => s === 1);
      }).length;
    } else {
      // 特定用户：检查该用户的状态
      completedCount = materials.filter((m: any) => {
        if (!m.status) return false;
        return m.status[String(selectedUserId.value)] === 1;
      }).length;
    }

    return `${completedCount}/${totalMaterials}`;
  } catch (error) {
    return "-";
  }
};

// 初始化
onMounted(() => {
  fetchTaskList();
  calculateTableHeight();
  window.addEventListener('resize', calculateTableHeight);
});
</script>
