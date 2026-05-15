<template>
  <div class="schedule-container">
    <!-- 筛选区域 -->
    <div class="filter-bar">
      <el-button :icon="Refresh" plain type="primary" @click="refreshData" :loading="loading" />
      <el-button type="primary" :icon="Plus" @click="handleAdd">添加日程</el-button>
      <el-radio-group v-model="selectedUserId" @change="onUserChange">
        <el-radio-button :value="3">灿灿</el-radio-button>
        <el-radio-button :value="4">昭昭</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 日程列表 -->
    <el-table :data="scheduleList" v-loading="loading" stripe border max-height="calc(100vh - 200px)">
      <el-table-column label="ID" prop="id" width="60" />
      <el-table-column label="标题" prop="title" min-width="200" />
      <el-table-column label="开始时间" prop="startTs" width="180">
        <template #default="{ row }">
          {{ formatTime(row.startTs) }}
        </template>
      </el-table-column>
      <el-table-column label="结束时间" prop="endTs" width="180">
        <template #default="{ row }">
          {{ formatTime(row.endTs) }}
        </template>
      </el-table-column>
      <el-table-column label="重复" width="100" align="center">
        <template #default="{ row }">
          <el-tooltip v-if="row.repeat === 999 && row.repeatData" :content="getRepeatDataText(row.repeatData)" placement="top">
            <el-tag type="primary" size="small">自定义</el-tag>
          </el-tooltip>
          <el-tag v-else-if="row.repeat" type="primary" size="small">{{ getRepeatText(row.repeat) }}</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="重复结束" prop="repeatEndTs" width="180">
        <template #default="{ row }">
          {{ formatTime(row.repeatEndTs) }}
        </template>
      </el-table-column>
      <el-table-column label="子任务" width="100" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.subtasks && row.subtasks.length > 0" type="info" size="small">
            {{ row.subtasks.length }} 个
          </el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="分数" width="60" align="center">
        <template #default="{ row }">
          <span>{{ row.score ?? '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" align="center" fixed="right">
        <template #default="{ row }">
          <el-button
            type="primary"
            size="small"
            :icon="Edit"
            @click="handleEdit(row)"
            circle
          />
          <el-button
            type="danger"
            size="small"
            :icon="Delete"
            @click="handleDelete(row)"
            circle
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
      class="pagination"
      background
      @size-change="handleSizeChange"
      @current-change="handlePageChange"
    />

    <!-- 编辑对话框 -->
    <TodoDialog
      v-model:visible="dialogVisible"
      :todo-data="currentTodo"
      :is-edit="isEditMode"
      @success="refreshData"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh, Delete, Edit, Plus } from "@element-plus/icons-vue";
import dayjs from "dayjs";
import { getTodoList, deleteTodo } from "@/api/api-todo";
import type { ScheduleData } from "@/api/api-todo";
import TodoDialog from "./dialogs/TodoDialog.vue";

const loading = ref(false);
const selectedUserId = ref<number>(3); // 默认选中灿灿
const scheduleList = ref<ScheduleData[]>([]);
const pageNum = ref(1);
const pageSize = ref(15);
const total = ref(0);
const dialogVisible = ref(false);
const currentTodo = ref<ScheduleData | null>(null);
const isEditMode = ref(false);

const fetchScheduleList = async (userId: number, page: number = 1, size: number = 15) => {
  loading.value = true;
  try {
    const response = await getTodoList(userId, page, size);
    scheduleList.value = response.data || [];
    total.value = response.totalCount || 0;
    pageNum.value = page;
    pageSize.value = size;
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

const getRepeatText = (repeat: number | string): string => {
  const repeatMap: Record<number, string> = {
    0: '无',
    1: '每天',
    2: '每星期',
    3: '每月',
    4: '每年',
    5: '工作日',
    6: '每周末',
    999: '自定义'
  };
  return repeatMap[Number(repeat)] || String(repeat);
};

const getRepeatDataText = (repeatData: any): string => {
  if (!repeatData) return '';
  try {
    const data = typeof repeatData === 'string' ? JSON.parse(repeatData) : repeatData;
    const parts: string[] = [];
    if (data.interval) parts.push(`每${data.interval}次`);
    if (data.weekdays && Array.isArray(data.weekdays)) {
      const dayNames = ['日', '一', '二', '三', '四', '五', '六'];
      const days = data.weekdays.map((d: number) => `周${dayNames[d]}`).join('、');
      parts.push(days);
    }
    if (data.monthDays && Array.isArray(data.monthDays)) {
      parts.push(`每月${data.monthDays.join('、')}日`);
    }
    return parts.join('，') || JSON.stringify(data);
  } catch {
    return String(repeatData);
  }
};

const formatTime = (time: string): string => {
  if (!time) return '-';
  return dayjs(time).format('YYYY-MM-DD');
};

const handleDelete = async (row: ScheduleData) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除日程「${row.title}」吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );

    await deleteTodo(row.id);
    ElMessage.success('删除成功');
    refreshData();
  } catch (err) {
    if (err !== 'cancel') {
      console.error('删除日程失败:', err);
      ElMessage.error('删除日程失败');
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

onMounted(() => {
  fetchScheduleList(selectedUserId.value);
});
</script>

<style scoped>
.schedule-container {
  padding: 16px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  height: 40px;
  margin-bottom: 16px;
}

.pagination {
  margin-top: 16px;
}
</style>
