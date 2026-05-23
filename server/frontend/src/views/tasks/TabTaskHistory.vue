<template>
  <div class="p-2">
    <!-- 工具栏 -->
    <div class="flex items-center h-10 mb-2">
      <div class="flex flex-1 items-center gap-4">
        <el-button type="primary" plain size="small" @click="fetchHistoryList" :icon="Refresh"/>
        <el-radio-group v-model="filterUserId" @change="handleFilterChange">
          <el-radio :value="0">全部</el-radio>
          <el-radio :value="3">灿灿</el-radio>
          <el-radio :value="4">昭昭</el-radio>
        </el-radio-group>
        <el-select v-model="filterTaskId" placeholder="选择任务" clearable style="width: 200px" @change="handleFilterChange">
          <el-option
            v-for="task in taskList"
            :key="task.id"
            :label="task.name"
            :value="task.id"
          />
        </el-select>
      </div>
    </div>

    <!-- 表格 -->
    <el-table :data="historyList" v-loading="loading" stripe border style="width: 100%" :max-height="tableMaxHeight">
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="date_str" label="日期" width="110" />
      <el-table-column prop="user_id" label="用户" width="60" align="center">
        <template #default="{ row }">
          {{ getUserName(row.user_id) }}
        </template>
      </el-table-column>
      <el-table-column prop="task_id" label="任务" min-width="100">
        <template #default="{ row }">
          {{ getTaskName(row.task_id) }}
        </template>
      </el-table-column>
      <el-table-column prop="task_type" label="任务类型" width="90" align="center">
        <template #default="{ row }">
          {{ getTaskType(row.task_id) }}
        </template>
      </el-table-column>
      <el-table-column prop="material_id" label="素材" min-width="200">
        <template #default="{ row }">
          {{ getMaterialName(row.material_id) }}
        </template>
      </el-table-column>
      <el-table-column prop="material_type" label="素材类型" width="90" align="center">
        <template #default="{ row }">
          {{ getMaterialType(row.material_id) }}
        </template>
      </el-table-column>
      <el-table-column prop="state" label="状态" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="row.state === 1 ? 'success' : 'info'">
            {{ row.state === 1 ? '已完成' : '未完成' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="dt" label="操作时间" width="170">
        <template #default="{ row }">
          {{ row.dt ? dayjs(row.dt).format('YYYY-MM-DD HH:mm:ss') : '-' }}
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
import { getTaskHistoryList, getTaskList, getMaterialListByIds, type TaskHistory, type Task } from "@/api/api-task";
import { Refresh } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { onMounted, ref, onUnmounted, nextTick } from "vue";
import dayjs from "dayjs";

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
const historyList = ref<TaskHistory[]>([]);
const totalCount = ref(0);
const pageNum = ref(1);
const pageSize = ref(20);

// 筛选条件（0 表示全部用户）
const filterUserId = ref(0);
const filterTaskId = ref<number | undefined>(undefined);
const taskList = ref<Task[]>([]);
const materialMap = ref<Map<number, { name: string; type: number }>>(new Map());

// 获取任务列表（用于下拉框）
const fetchTaskList = async () => {
  try {
    const res = await getTaskList(undefined, 1, 1000);
    if (res.code === 0 && res.data) {
      taskList.value = res.data.data || [];
    }
  } catch (error: any) {
    console.error("获取任务列表失败:", error);
  }
};

// 获取任务历史记录
const fetchHistoryList = async () => {
  loading.value = true;
  try {
    const userId = filterUserId.value === 0 ? undefined : filterUserId.value;
    const res = await getTaskHistoryList(
      userId,
      filterTaskId.value,
      pageNum.value,
      pageSize.value
    );
    if (res.code === 0 && res.data) {
      historyList.value = res.data.data || [];
      totalCount.value = res.data.totalCount || 0;

      // 批量获取素材名称
      const materialIds = [...new Set(historyList.value.map(h => h.material_id))];
      if (materialIds.length > 0) {
        await fetchMaterialNames(materialIds);
      }
    }
  } catch (error: any) {
    ElMessage.error(error.message || "获取任务历史记录失败");
  } finally {
    loading.value = false;
  }
};

// 筛选条件变化
const handleFilterChange = () => {
  pageNum.value = 1;
  fetchHistoryList();
};

// 分页变化
const handlePageChange = (page: number) => {
  pageNum.value = page;
  fetchHistoryList();
};

const handleSizeChange = (size: number) => {
  pageSize.value = size;
  pageNum.value = 1;
  fetchHistoryList();
};

// 获取用户名称
const getUserName = (userId: number) => {
  if (userId === 3) return "灿灿";
  if (userId === 4) return "昭昭";
  return `用户${userId}`;
};

// 获取任务名称
const getTaskName = (taskId: number) => {
  const task = taskList.value.find(t => t.id === taskId);
  return task ? task.name : `任务${taskId}`;
};

// 获取任务类型
const getTaskType = (taskId: number) => {
  const task = taskList.value.find(t => t.id === taskId);
  if (!task) return '-';
  return task.type === 1 ? '持续任务' : '每日任务';
};

// 批量获取素材名称
const fetchMaterialNames = async (materialIds: number[]) => {
  try {
    const materials = await getMaterialListByIds(materialIds);
    materials.forEach(material => {
      materialMap.value.set(material.id, { name: material.name, type: material.type });
    });
  } catch (error: any) {
    console.error("批量获取素材失败:", error);
  }
};

// 获取素材名称
const getMaterialName = (materialId: number) => {
  return materialMap.value.get(materialId)?.name || `素材${materialId}`;
};

// 获取素材类型
const getMaterialType = (materialId: number) => {
  const type = materialMap.value.get(materialId)?.type;
  if (type === undefined) return '-';
  const typeMap: Record<number, string> = {
    0: 'PDF',
    1: '视频',
    2: '音频'
  };
  return typeMap[type] || `未知_${type}`;
};

// 初始化
onMounted(() => {
  fetchTaskList();
  fetchHistoryList();
  calculateTableHeight();
  window.addEventListener('resize', calculateTableHeight);

  // 监听刷新事件
  const handleRefresh = () => {
    fetchHistoryList();
  };
  window.addEventListener('refresh-history-tab', handleRefresh);

  onUnmounted(() => {
    window.removeEventListener('resize', calculateTableHeight);
    window.removeEventListener('refresh-history-tab', handleRefresh);
  });
});
</script>
