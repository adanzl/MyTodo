<template>
  <div class="p-2">
    <div class="mb-2 flex items-center gap-4 h-10">
      <el-button type="primary" plain size="small" :icon="Refresh" :loading="loading" @click="refreshData" />
      <el-radio-group v-model="selectedUserId" size="small" @change="handleUserChange">
        <el-radio-button :value="0">全部</el-radio-button>
        <el-radio-button :value="3">灿灿</el-radio-button>
        <el-radio-button :value="4">昭昭</el-radio-button>
      </el-radio-group>

      <div class="ml-auto flex items-center">
        <el-button size="small" :icon="ArrowLeft" class="mr-1" @click="prevDay" />
        <el-date-picker
          v-model="selectedDate"
          type="date"
          placeholder="选择日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          class="w-35! mr-1"
          size="small"
          @change="handleDateChange"
        />
        <el-button size="small" class="w-4 mr-1" @click="setToday">今</el-button>
        <el-button size="small" :icon="ArrowRight" class="ml-0!" @click="nextDay" />
      </div>
    </div>

    <el-table
      :data="scheduleList"
      v-loading="loading"
      stripe
      border
      max-height="calc(100vh - 240px)"
    >
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
          <span v-else>{{ row.userId ?? "-" }}</span>
        </template>
      </el-table-column>
      <el-table-column label="分类" width="90" align="center">
        <template #default="{ row }">
          <el-tag
            size="small"
            effect="light"
            :type="getGroupTagType(row.groupId)"
          >
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

    <el-empty v-if="!loading && scheduleList.length === 0" description="当天暂无日程" />

    <TodoDialog
      v-model:visible="dialogVisible"
      :todo-data="currentTodo"
      :is-edit="isEditMode"
      :user-id="editUserId"
      @success="refreshData"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh, ArrowLeft, ArrowRight, Edit, Delete } from "@element-plus/icons-vue";
import dayjs from "dayjs";
import { getTodoCalendar, deleteTodo, type ScheduleData } from "@/api/api-todo";
import { getList } from "@/api/api-common";
import { getGroupOptions, getRepeatRuleText } from "@/utils/schedule";
import TodoDialog from "./dialogs/TodoDialog.vue";

interface ColorItem {
  id: number;
  name?: string;
  color?: string;
}

const ALL_USER_IDS = [3, 4] as const;
const FALLBACK_COLOR = { name: "None", hex: "#f8fafc" };

const loading = ref(false);
const selectedUserId = ref(0);
const selectedDate = ref(dayjs().format("YYYY-MM-DD"));
const scheduleList = ref<ScheduleData[]>([]);
const colorMap = ref<Map<number, { name: string; hex: string }>>(new Map());
const dialogVisible = ref(false);
const currentTodo = ref<ScheduleData | null>(null);
const isEditMode = ref(false);
const editUserId = ref(3);

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

const fetchDaySchedules = async () => {
  const dateStr = selectedDate.value;
  if (!dateStr) return;

  loading.value = true;
  try {
    const userIds =
      selectedUserId.value === 0 ? [...ALL_USER_IDS] : [selectedUserId.value];

    const results = await Promise.all(
      userIds.map((userId) => getTodoCalendar(dateStr, dateStr, userId))
    );

    const merged: ScheduleData[] = [];
    for (const calendar of results) {
      const dayItems = calendar[dateStr] || [];
      merged.push(...dayItems);
    }

    merged.sort((a, b) => (a.order ?? 0) - (b.order ?? 0) || a.id - b.id);
    scheduleList.value = merged;
  } catch (err) {
    console.error("获取日历日程失败:", err);
    ElMessage.error("获取日历日程失败");
    scheduleList.value = [];
  } finally {
    loading.value = false;
  }
};

const refreshData = () => {
  fetchDaySchedules();
};

const handleEdit = (row: ScheduleData) => {
  currentTodo.value = row;
  isEditMode.value = true;
  editUserId.value = row.userId || (selectedUserId.value === 0 ? 3 : selectedUserId.value);
  dialogVisible.value = true;
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

const handleUserChange = () => {
  fetchDaySchedules();
};

const handleDateChange = () => {
  fetchDaySchedules();
};

const prevDay = () => {
  selectedDate.value = dayjs(selectedDate.value).subtract(1, "day").format("YYYY-MM-DD");
  fetchDaySchedules();
};

const nextDay = () => {
  selectedDate.value = dayjs(selectedDate.value).add(1, "day").format("YYYY-MM-DD");
  fetchDaySchedules();
};

const setToday = () => {
  selectedDate.value = dayjs().format("YYYY-MM-DD");
  fetchDaySchedules();
};

onMounted(async () => {
  await fetchColors();
  fetchDaySchedules();
  window.addEventListener("refresh-schedule-calendar-tab", refreshData);
});

onUnmounted(() => {
  window.removeEventListener("refresh-schedule-calendar-tab", refreshData);
});
</script>
