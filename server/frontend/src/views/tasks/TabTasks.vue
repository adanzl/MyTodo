<template>
  <div class="p-2">
    <!-- 工具栏 -->
    <div class="flex items-center h-10 mb-2">
      <div class="flex flex-1 items-center justify-end gap-2">
        <el-button type="primary" size="small" @click="refreshTasks" :icon="Refresh"/>
        <el-button type="primary" size="small" @click="handleAddTask">新建任务</el-button>
      </div>
    </div>

    <!-- 表格 -->
    <el-table :data="taskList" v-loading="loading" stripe border style="width: 100%">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="任务名称" min-width="200" />
      <el-table-column prop="start_date" label="开始日期" width="120" />
      <el-table-column prop="duration" label="天数" width="80" />
      <el-table-column prop="user_id" label="布置对象" width="150">
        <template #default="{ row }">
          {{ getUserName(row.user_id) }}
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="handleEditTask(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDeleteTask(row)">删除</el-button>
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
  </div>
</template>

<script setup lang="ts">
import {
  deleteTask,
  getTaskList,
  type Task,
} from "@/api/api-task";
import { Refresh } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { onMounted, ref } from "vue";
import TaskDialog from "./dialogs/TaskDialog.vue";

// 状态管理
const loading = ref(false);
const taskList = ref<Task[]>([]);
const totalCount = ref(0);
const pageNum = ref(1);
const pageSize = ref(20);

// 对话框
const dialogVisible = ref(false);
const isEdit = ref(false);
const currentTaskData = ref<Partial<Task>>({});

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

// 获取状态文本
const getStatusText = (status?: number) => {
  const statusMap: Record<number, string> = {
    "-1": "未开启",
    0: "未开始",
    1: "进行中",
    2: "已结束",
  };
  return statusMap[status ?? 1] || "进行中";
};

// 获取状态类型
const getStatusType = (status?: number) => {
  const typeMap: Record<number, any> = {
    "-1": "info",
    0: "info",
    1: "success",
    2: "warning",
  };
  return typeMap[status ?? 1] || "success";
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
});
</script>
