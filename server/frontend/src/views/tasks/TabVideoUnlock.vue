<template>
  <div class="p-2">
    <!-- 工具栏 -->
    <div class="flex items-center h-10 mb-2">
      <div class="flex flex-1 items-center gap-4">
        <el-button type="primary" plain size="small" @click="fetchList" :icon="Refresh" />
        <span class="text-sm text-gray-500">共 {{ applicationList.length }} 条待审批</span>
        <div class="flex-1" />
        <el-button
          size="small"
          type="success"
          :disabled="!selectedIds.length"
          @click="handleApprove"
        >通过 ({{ selectedIds.length }})</el-button>
        <el-button
          size="small"
          type="danger"
          :disabled="!selectedIds.length"
          @click="handleDeny"
        >拒绝 ({{ selectedIds.length }})</el-button>
      </div>
    </div>

    <!-- 表格 -->
    <el-table
      :data="applicationList"
      v-loading="loading"
      stripe border
      style="width: 100%"
      :max-height="tableMaxHeight"
      @selection-change="handleSelectionChange"
    >
      <el-table-column type="selection" width="45" />
      <el-table-column prop="id" label="ID" width="150" />
      <el-table-column label="用户" width="70" align="center">
        <template #default="{ row }">
          {{ getUserName(row.user_id) }}
        </template>
      </el-table-column>
      <el-table-column label="素材" min-width="200">
        <template #default="{ row }">
          {{ getMaterialName(row.material_id) || `素材#${row.material_id}` }}
        </template>
      </el-table-column>
      <el-table-column label="申请时长" width="100" align="center">
        <template #default="{ row }">
          {{ row.duration }} 分钟
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="申请时间" width="170">
        <template #default="{ row }">
          {{ row.created_at ? dayjs(row.created_at).format('YYYY-MM-DD HH:mm:ss') : '-' }}
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { getUnlimitList, approveUnlimit, denyUnlimit, getMaterialListByIds, type UnlimitApplication } from "@/api/api-task";
import { Refresh } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { onMounted, ref, onUnmounted, nextTick } from "vue";
import dayjs from "dayjs";

const tableMaxHeight = ref<number>(0);

const calculateTableHeight = () => {
  nextTick(() => {
    const windowHeight = window.innerHeight;
    const reservedSpace = 300;
    tableMaxHeight.value = windowHeight - reservedSpace;
  });
};

const loading = ref(false);
const applicationList = ref<UnlimitApplication[]>([]);
const selectedIds = ref<number[]>([]);
const materialNameMap = ref<Map<number, string>>(new Map());

const getUserName = (userId: number) => {
  if (userId === 3) return "灿灿";
  if (userId === 4) return "昭昭";
  return `用户${userId}`;
};

const getMaterialName = (materialId: number) => {
  return materialNameMap.value.get(materialId) || '';
};

const fetchMaterialNames = async (materialIds: number[]) => {
  const ids = [...new Set(materialIds.filter(Boolean))];
  if (!ids.length) return;
  try {
    const materials = await getMaterialListByIds(ids);
    materials.forEach((m) => {
      materialNameMap.value.set(m.id, m.name);
    });
  } catch {
    // 静默处理
  }
};

const fetchList = async () => {
  loading.value = true;
  try {
    applicationList.value = await getUnlimitList('pending');
    const materialIds = applicationList.value.map((a) => a.material_id);
    await fetchMaterialNames(materialIds);
  } catch (error: any) {
    ElMessage.error(error.message || "获取申请列表失败");
  } finally {
    loading.value = false;
  }
};

const handleSelectionChange = (rows: UnlimitApplication[]) => {
  selectedIds.value = rows.map((r) => r.id);
};

const handleApprove = async () => {
  if (!selectedIds.value.length) return;
  try {
    await ElMessageBox.confirm(
      `确定要通过选中的 ${selectedIds.value.length} 条不限时申请吗？`,
      "提示",
      { confirmButtonText: "确定", cancelButtonText: "取消", type: "info" }
    );
    await approveUnlimit(selectedIds.value);
    ElMessage.success(`已通过 ${selectedIds.value.length} 条申请`);
    selectedIds.value = [];
    fetchList();
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error(error.message || "审批失败");
    }
  }
};

const handleDeny = async () => {
  if (!selectedIds.value.length) return;
  try {
    await ElMessageBox.confirm(
      `确定要拒绝选中的 ${selectedIds.value.length} 条不限时申请吗？`,
      "提示",
      { confirmButtonText: "确定", cancelButtonText: "取消", type: "warning" }
    );
    await denyUnlimit(selectedIds.value);
    ElMessage.success(`已拒绝 ${selectedIds.value.length} 条申请`);
    selectedIds.value = [];
    fetchList();
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error(error.message || "拒绝失败");
    }
  }
};

// 初始化
onMounted(() => {
  fetchList();
  calculateTableHeight();
  window.addEventListener("resize", calculateTableHeight);

  const handleRefresh = () => {
    fetchList();
  };
  window.addEventListener("refresh-video-unlock-tab", handleRefresh);

  onUnmounted(() => {
    window.removeEventListener("resize", calculateTableHeight);
    window.removeEventListener("refresh-video-unlock-tab", handleRefresh);
  });
});
</script>
