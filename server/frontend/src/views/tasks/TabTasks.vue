<template>
  <div class="p-2">
    <!-- 工具栏 -->
    <div class="flex items-center min-h-10 mb-2">
      <div class="flex flex-1 flex-wrap items-center gap-1">
        <el-button type="primary" plain size="small" @click="refreshTasks" :icon="Refresh"/>
        <el-button type="primary" size="small" @click="handleAddTask">新建任务</el-button>
        <div
          class="flex flex-wrap items-center gap-1 ml-1 px-2 min-h-7 py-1 rounded border border-dashed border-gray-300 cursor-pointer"
          @click="blockTimeDialogVisible = true"
        >
          <span class="text-xs text-gray-500 shrink-0">全局禁用</span>
          <BlockTimeDisplay :block-time="globalBlockTime" :wrap="false" />
        </div>
      </div>
    </div>

    <!-- 表格 -->
    <el-table :data="taskList" v-loading="loading" stripe border style="width: 100%" :max-height="tableMaxHeight">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="任务名称" min-width="200" />
      <el-table-column prop="priority" label="优先级" width="70" align="center" />
      <el-table-column prop="type" label="类型" width="60" align="center">
        <template #default="{ row }">
          <el-tag :type="row.type === 1 ? 'success' : 'primary'" size="small">{{ row.type === 1 ? '持续' : '每日' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="start_date" label="开始日期" width="110" />
      <el-table-column prop="duration" label="天数" width="70" align="center" />
      <el-table-column prop="user_id" label="布置对象" width="100">
        <template #default="{ row }">
          {{ getUserName(row.user_id) }}
        </template>
      </el-table-column>
      <el-table-column label="前置日程" width="90" align="center">
        <template #default="{ row }">
          {{ getPreTodoCounts(row) }}
        </template>
      </el-table-column>
      <el-table-column label="前置任务" width="90" align="center">
        <template #default="{ row }">
          {{ getPreTaskCount(row) }}
        </template>
      </el-table-column>
      <!-- 休息日 -->
      <el-table-column label="休息日" width="110">
        <template #default="{ row }">
          <el-tooltip
            v-if="restDaysText(row)"
            :content="restDaysText(row)"
            placement="top"
            :show-after="300"
          >
            <span class="text-xs text-gray-700 cursor-default block truncate max-w-25">
              {{ restDaysText(row) }}
            </span>
          </el-tooltip>
          <span v-else class="text-gray-400">-</span>
        </template>
      </el-table-column>
      <el-table-column label="禁用时段" width="230">
        <template #default="{ row }">
          <BlockTimeDisplay :block-time="row.block_time" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" :icon="Edit" @click="handleEditTask(row)" />
          <el-button size="small" :icon="CopyDocument" @click="handleCopyTask(row)" />
          <el-button size="small" type="danger" :icon="Delete" @click="handleDeleteTask(row)" />
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

    <!-- 任务编辑对话框 -->
    <TaskDialog
      v-model="dialogVisible"
      :is-edit="isEdit"
      :task-data="currentTaskData"
      @success="fetchTaskList"
    />

    <BlockTimeDialog v-model="blockTimeDialogVisible" @success="fetchGlobalBlockTime" />
  </div>
</template>

<script setup lang="ts">
import {
  addTask,
  deleteTask,
  getGlobalBlockTime,
  getTaskList,
  parsePreTask,
  type Task,
  type BlockTimeConfig,
} from "@/api/api-task";
import { Refresh, Edit, CopyDocument, Delete } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { onMounted, ref, onUnmounted, nextTick } from "vue";
import BlockTimeDisplay from "./components/BlockTimeDisplay.vue";
import TaskDialog from "./dialogs/TaskDialog.vue";
import BlockTimeDialog from "./dialogs/BlockTimeDialog.vue";
import { formatRestDaysFullText } from "@/utils/date";


const restDaysText = (task: Task) => formatRestDaysFullText(task.rest_days);

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
const totalCount = ref(0);
const pageNum = ref(1);
const pageSize = ref(20);

// 对话框
const dialogVisible = ref(false);
const blockTimeDialogVisible = ref(false);
const globalBlockTime = ref<BlockTimeConfig>();
const isEdit = ref(false);
const currentTaskData = ref<Partial<Task>>({});

// 获取全局禁用时段
const fetchGlobalBlockTime = async () => {
  try {
    globalBlockTime.value = await getGlobalBlockTime();
  } catch (error: any) {
    ElMessage.error(error.message || "获取全局禁用时段失败");
  }
};

// 获取任务列表
const fetchTaskList = async () => {
  loading.value = true;
  try {
    const res = await getTaskList(undefined, pageNum.value, pageSize.value);
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

// 刷新任务列表
const refreshTasks = () => {
  fetchTaskList();
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

// 获取用户名称
const getUserName = (userId?: number) => {
  if (!userId) return "-";
  const userIds = String(userId).split(",").map(Number);
  const names: string[] = [];
  if (userIds.includes(3)) names.push("灿灿");
  if (userIds.includes(4)) names.push("昭昭");
  return names.join(", ") || "-";
};

// 获取布置对象对应的前置任务个数，顺序与布置对象一致
const getPreTodoCounts = (task: Task): string => {
  const userIds = String(task.user_id || "").split(",").map(Number);
  const assignedUsers: number[] = [];
  if (userIds.includes(3)) assignedUsers.push(3);
  if (userIds.includes(4)) assignedUsers.push(4);
  if (assignedUsers.length === 0) return "-";

  let preTodoData: Record<string, number[]> = {};
  if (task.pre_todo) {
    try {
      preTodoData = typeof task.pre_todo === "string" ? JSON.parse(task.pre_todo) : task.pre_todo;
    } catch {
      preTodoData = {};
    }
  }

  return assignedUsers
    .map((id) => {
      const ids = preTodoData[String(id)];
      return Array.isArray(ids) ? ids.length : 0;
    })
    .join(", ");
};

const getPreTaskCount = (task: Task): string => {
  const count = parsePreTask(task.pre_task).length;
  return count > 0 ? String(count) : "-";
};

// 新建任务
const handleAddTask = () => {
  isEdit.value = false;
  currentTaskData.value = {};
  dialogVisible.value = true;
};

// 编辑任务
const handleEditTask = (row: Task) => {
  isEdit.value = true;
  currentTaskData.value = row;
  dialogVisible.value = true;
};

// 复制任务
const handleCopyTask = async (row: Task) => {
  try {
    await ElMessageBox.confirm(`确定要复制任务「${row.name}」吗？`, "提示", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "info",
    });

    const { id: _id, lock: _lock, msg: _msg, ...rest } = row;
    await addTask({
      ...rest,
      name: `${row.name}(复制)`,
      data: typeof row.data === "string" ? row.data : JSON.stringify(row.data ?? {}),
    });
    ElMessage.success("复制成功");
    fetchTaskList();
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error(error.message || "复制失败");
    }
  }
};

// 删除任务
const handleDeleteTask = async (row: Task) => {
  try {
    await ElMessageBox.confirm("确定要删除该任务吗？", "提示", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    });

    await deleteTask(row.id!);
    ElMessage.success("删除成功");
    fetchTaskList();
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error(error.message || "删除失败");
    }
  }
};

// 初始化
onMounted(() => {
  fetchTaskList();
  fetchGlobalBlockTime();
  calculateTableHeight();
  window.addEventListener('resize', calculateTableHeight);

  // 监听刷新事件
  const handleRefresh = () => {
    fetchTaskList();
  };
  window.addEventListener('refresh-tasks-tab', handleRefresh);

  onUnmounted(() => {
    window.removeEventListener('resize', calculateTableHeight);
    window.removeEventListener('refresh-tasks-tab', handleRefresh);
  });
});
</script>
