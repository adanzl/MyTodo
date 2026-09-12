<template>
  <div class="p-2">
    <!-- 筛选区域 -->
    <div class="h-10 flex items-center gap-2 mb-2">
      <el-button :icon="Refresh" plain type="primary" size="small" :loading="loading" @click="refreshData" />
      <el-button type="primary" size="small" :icon="Plus" @click="handleAdd">添加日程</el-button>
      <el-radio-group v-model="selectedUserId" size="small" class="ml-2" @change="onUserChange">
        <el-radio-button :value="3">灿灿</el-radio-button>
        <el-radio-button :value="4">昭昭</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 日程列表 -->
    <el-table :data="scheduleList" v-loading="loading" stripe border max-height="calc(100vh - 240px)">
      <el-table-column label="ID" prop="id" width="60" />
      <el-table-column label="名称" prop="title" min-width="180" />
      <el-table-column label="用户" width="80" align="center">
        <template #default="{ row }">
          <el-tag
            v-if="row.userId === 3"
            size="small"
            effect="light"
            class="border-pink-200! bg-pink-100! text-pink-600!"
          >
            灿灿
          </el-tag>
          <el-tag
            v-else-if="row.userId === 4"
            size="small"
            effect="light"
            class="border-blue-200! bg-blue-100! text-blue-600!"
          >
            昭昭
          </el-tag>
          <span v-else>{{ row.userId ?? selectedUserId }}</span>
        </template>
      </el-table-column>
      <el-table-column label="分类" width="90" align="center">
        <template #default="{ row }">
          <el-tag size="small" effect="light" :type="getGroupTagType(row.groupId)">
            {{ getGroupLabel(row.groupId) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="优先级" width="80" align="center">
        <template #default="{ row }">
          {{ getPriorityLabel(row.priority) }}
        </template>
      </el-table-column>
      <el-table-column label="颜色" width="60" align="center">
        <template #default="{ row }">
          <div class="flex items-center justify-center">
            <span
              class="inline-block w-5 h-5 rounded border border-gray-300"
              :style="{ backgroundColor: resolveColor(row.color).hex }"
              :title="resolveColor(row.color).name"
            />
          </div>
        </template>
      </el-table-column>
      <el-table-column label="奖励" width="60" align="center">
        <template #default="{ row }">
          {{ row.score ?? "-" }}
        </template>
      </el-table-column>
      <el-table-column label="子任务" width="80" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.subtasks && row.subtasks.length > 0" type="info" size="small">
            {{ row.subtasks.length }} 个
          </el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="开始时间" width="120" align="center">
        <template #default="{ row }">
          {{ formatTime(row.startTs) }}
        </template>
      </el-table-column>
      <el-table-column label="重复结束" width="120" align="center">
        <template #default="{ row }">
          {{ formatTime(row.repeatEndTs) }}
        </template>
      </el-table-column>
      <el-table-column label="重复规则" min-width="160">
        <template #default="{ row }">
          {{ getRepeatRuleText(row.repeat, row.repeatData) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" align="center" fixed="right">
        <template #default="{ row }">
          <el-button
            type="primary"
            size="small"
            :icon="Edit"
            circle
            @click="handleEdit(row)"
          />
          <el-button
            type="danger"
            size="small"
            :icon="Delete"
            circle
            @click="handleDelete(row)"
          />
        </template>
      </el-table-column>
    </el-table>

    <!-- 空状态 -->
    <el-empty v-if="!loading && scheduleList.length === 0" description="暂无日程数据" />

    <!-- 分页 -->
    <el-pagination
      v-if="total > 0"
      layout="sizes, prev, pager, next"
      :total="total"
      :page-size="pageSize"
      :page-sizes="[15, 20, 50]"
      :current-page="pageNum"
      class="mt-2"
      background
      @size-change="handleSizeChange"
      @current-change="handlePageChange"
    />

    <!-- 编辑对话框 -->
    <TodoDialog
      v-model:visible="dialogVisible"
      :todo-data="currentTodo"
      :is-edit="isEditMode"
      :user-id="selectedUserId"
      @success="refreshData"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh, Delete, Edit, Plus } from "@element-plus/icons-vue";
import dayjs from "dayjs";
import { getTodoList, deleteTodo } from "@/api/api-todo";
import type { ScheduleData } from "@/api/api-todo";
import { getList } from "@/api/api-common";
import { getGroupOptions, getRepeatRuleText } from "@/utils/schedule";
import TodoDialog from "./dialogs/TodoDialog.vue";

interface ColorItem {
  id: number;
  name?: string;
  color?: string;
}

const FALLBACK_COLOR = { name: "None", hex: "#f8fafc" };
const PAGE_STORAGE_KEY = "schedule-manage-pagination";
const PAGE_SIZES = [15, 20, 50] as const;

const loadPagination = () => {
  try {
    const raw = localStorage.getItem(PAGE_STORAGE_KEY);
    if (!raw) return { pageNum: 1, pageSize: 15 };
    const saved = JSON.parse(raw) as { pageNum?: number; pageSize?: number };
    const size = PAGE_SIZES.includes(saved.pageSize as (typeof PAGE_SIZES)[number])
      ? (saved.pageSize as number)
      : 15;
    const num = Number(saved.pageNum);
    return {
      pageNum: Number.isFinite(num) && num > 0 ? num : 1,
      pageSize: size,
    };
  } catch {
    return { pageNum: 1, pageSize: 15 };
  }
};

const savePagination = () => {
  localStorage.setItem(
    PAGE_STORAGE_KEY,
    JSON.stringify({ pageNum: pageNum.value, pageSize: pageSize.value })
  );
};

const initialPagination = loadPagination();

const loading = ref(false);
const selectedUserId = ref<number>(3);
const scheduleList = ref<ScheduleData[]>([]);
const pageNum = ref(initialPagination.pageNum);
const pageSize = ref(initialPagination.pageSize);
const total = ref(0);
const dialogVisible = ref(false);
const currentTodo = ref<ScheduleData | null>(null);
const isEditMode = ref(false);
const colorMap = ref<Map<number, { name: string; hex: string }>>(new Map());

const resolveColor = (colorId?: number) => {
  if (colorId == null) return FALLBACK_COLOR;
  return colorMap.value.get(colorId) ?? FALLBACK_COLOR;
};

const getGroupLabel = (groupId?: number) => {
  if (groupId === undefined || groupId === null || groupId < 0) {
    return getGroupOptions(0).label;
  }
  return getGroupOptions(groupId).label;
};

const getGroupTagType = (groupId?: number): "info" | "danger" | "warning" => {
  const id = groupId === undefined || groupId === null || groupId < 0 ? 0 : groupId;
  if (id === 1) return "danger";
  if (id === 2) return "warning";
  return "info";
};

const getPriorityLabel = (priority?: number) => {
  if (priority === 0 || priority === -1) return "Ⅰ";
  if (priority === 1) return "Ⅱ";
  if (priority === 2) return "Ⅲ";
  if (priority === 3) return "Ⅳ";
  return "-";
};

const formatTime = (time?: string) => {
  if (!time) return "-";
  return dayjs(time).format("YYYY-MM-DD");
};

const fetchColors = async () => {
  try {
    const response = await getList<ColorItem>("t_colors", undefined, 1, 100);
    const list = response.data?.data || [];
    const map = new Map<number, { name: string; hex: string }>();
    for (const item of list) {
      map.set(item.id, {
        name: item.name || String(item.id),
        hex: item.color || FALLBACK_COLOR.hex,
      });
    }
    colorMap.value = map;
  } catch (err) {
    console.error("获取颜色列表失败:", err);
  }
};

const fetchScheduleList = async (userId: number, page: number = 1, size: number = 15) => {
  loading.value = true;
  try {
    const response = await getTodoList(userId, page, size);
    scheduleList.value = response.data || [];
    total.value = response.totalCount || 0;
    pageNum.value = page;
    pageSize.value = size;
    savePagination();
  } catch (err) {
    console.error("获取日程失败:", err);
    ElMessage.error("获取日程失败");
    scheduleList.value = [];
  } finally {
    loading.value = false;
  }
};

const onUserChange = () => {
  pageNum.value = 1;
  fetchScheduleList(selectedUserId.value, 1, pageSize.value);
};

const refreshData = () => {
  fetchScheduleList(selectedUserId.value, pageNum.value, pageSize.value);
};

const handleSizeChange = (size: number) => {
  fetchScheduleList(selectedUserId.value, 1, size);
};

const handlePageChange = (page: number) => {
  fetchScheduleList(selectedUserId.value, page, pageSize.value);
};

const handleDelete = async (row: ScheduleData) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除日程「${row.title}」吗？`,
      "删除确认",
      {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      }
    );

    await deleteTodo(row.id);
    ElMessage.success("删除成功");
    refreshData();
  } catch (err) {
    if (err !== "cancel") {
      console.error("删除日程失败:", err);
      ElMessage.error("删除日程失败");
    }
  }
};

const handleEdit = (row: ScheduleData) => {
  currentTodo.value = row;
  isEditMode.value = true;
  dialogVisible.value = true;
};

const handleAdd = () => {
  currentTodo.value = null;
  isEditMode.value = false;
  dialogVisible.value = true;
};

const handleRefresh = () => {
  refreshData();
};

onMounted(async () => {
  await fetchColors();
  fetchScheduleList(selectedUserId.value, pageNum.value, pageSize.value);
  window.addEventListener("refresh-schedule-manage-tab", handleRefresh);
});

onUnmounted(() => {
  window.removeEventListener("refresh-schedule-manage-tab", handleRefresh);
});
</script>
