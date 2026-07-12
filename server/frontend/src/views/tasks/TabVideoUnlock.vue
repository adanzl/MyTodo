<template>
  <div class="p-2">
    <!-- 工具栏 -->
    <div class="flex items-center h-10 mb-2">
      <div class="flex flex-1 items-center gap-4">
        <el-button type="primary" plain size="small" @click="fetchList" :icon="Refresh" />
        <span class="text-sm text-gray-500">共 {{ applicationList.length }} 条 待审批</span>
        <div class="flex-1" />
        <el-button size="small" type="success" :disabled="!selectedIds.length" @click="handleApprove">通过 ({{
          selectedIds.length }})</el-button>
        <el-button size="small" type="danger" :disabled="!selectedIds.length" @click="handleDeny">拒绝 ({{
          selectedIds.length }})</el-button>
      </div>
    </div>

    <!-- 表格 -->
    <el-table :data="applicationList" v-loading="loading" stripe border style="width: 100%" :max-height="tableMaxHeight"
      @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="45" />
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column label="任务ID" width="80" align="center">
        <template #default="{ row }">
          {{ row.task_id ?? '-' }}
        </template>
      </el-table-column>
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
      <el-table-column label="审批类型" width="100" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.lock_code === 1" type="warning" size="small">任务禁用</el-tag>
          <el-tag v-else-if="row.lock_code === 2" type="warning" size="small">全局禁用</el-tag>
          <el-tag v-else-if="row.lock_code === 3" type="info" size="small">时长超限</el-tag>
          <span v-else>未知({{ row.lock_code }})</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="申请时间" width="170">
        <template #default="{ row }">
          {{ row.created_at ? dayjs(row.created_at).format('YYYY-MM-DD HH:mm:ss') : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="170" align="center">
        <template #default="{ row }">
          <div class="flex gap-1 justify-center">
            <el-button size="small" type="primary" @click="handleApproveSingle(row)">通过</el-button>
            <el-button size="small" type="danger" @click="handleDenySingle(row)">拒绝</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 生效中列表 -->
    <div class="mt-6">
      <div class="flex items-center h-8 mb-2">
        <el-button type="primary" plain size="small" class="ml-2" @click="fetchActiveList" :icon="Refresh" />
        <span class="text-sm text-gray-400 ml-2">共 {{ activeList.length }} 条 生效中</span>
      </div>
      <el-table :data="activeList" v-loading="activeLoading" stripe border style="width: 100%"
        :max-height="tableMaxHeight">
        <el-table-column width="45">
          <template #default="{ row }">
            <el-button size="small" circle type="danger" plain @click="handleRevoke(row)">x</el-button>
          </template>
        </el-table-column>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="任务ID" width="80" align="center">
          <template #default="{ row }">
            {{ row.task_id ?? '-' }}
          </template>
        </el-table-column>
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
        <el-table-column label="审批类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.lock_code === 1" type="warning" size="small">任务禁用</el-tag>
            <el-tag v-else-if="row.lock_code === 2" type="danger" size="small">全局禁用</el-tag>
            <el-tag v-else-if="row.lock_code === 3" type="info" size="small">时长超限</el-tag>
            <span v-else>未知({{ row.lock_code }})</span>
          </template>
        </el-table-column>
        <el-table-column label="申请时间" width="170">
          <template #default="{ row }">
            {{ row.created_at ? dayjs(row.created_at).format('YYYY-MM-DD HH:mm:ss') : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="过期时间" width="170">
          <template #default="{ row }">
            <span v-if="row.expires_at" :class="{ 'text-red-500': dayjs(row.expires_at).isBefore(dayjs()) }">
              {{ dayjs(row.expires_at).format('YYYY-MM-DD HH:mm:ss') }}
            </span>
            <span v-else class="text-gray-400">永久</span>
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { getUnlimitList, approveUnlimit, denyUnlimit, revokeUnlimit, getMaterialListByIds, type UnlimitApplication } from "@/api/api-task";
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
const activeLoading = ref(false);
const activeList = ref<UnlimitApplication[]>([]);
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
    await refreshMaterialNames();
  } catch (error: any) {
    ElMessage.error(error.message || "获取申请列表失败");
  } finally {
    loading.value = false;
  }
};

const fetchActiveList = async () => {
  activeLoading.value = true;
  try {
    activeList.value = await getUnlimitList('approved', dayjs().format('YYYY-MM-DDTHH:mm:ss+08:00'));
    await refreshMaterialNames();
  } catch (error: any) {
    ElMessage.error(error.message || "获取生效中列表失败");
  } finally {
    activeLoading.value = false;
  }
};

const refreshMaterialNames = async () => {
  const allMaterialIds = [
    ...applicationList.value.map((a) => a.material_id),
    ...activeList.value.map((a) => a.material_id),
  ];
  await fetchMaterialNames(allMaterialIds);
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
    fetchActiveList();
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error(error.message || "审批失败");
    }
  }
};

const handleApproveSingle = async (row: UnlimitApplication) => {
  try {
    const { value: durationStr } = await ElMessageBox.prompt(
      `确定要通过该不限时申请吗？请输入认证分钟数：`,
      "提示",
      {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "info",
        inputValue: String(row.duration),
        inputPlaceholder: "认证分钟数",
        inputValidator: (val: string) => {
          const num = Number(val);
          if (!Number.isInteger(num) || num <= 0) return '请输入大于 0 的整数';
          return true;
        },
        inputErrorMessage: '无效的分钟数',
      }
    );
    await approveUnlimit([row.id], parseInt(durationStr, 10));
    ElMessage.success(`已通过申请 #${row.id}`);
    fetchList();
    fetchActiveList();
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error(error.message || "审批失败");
    }
  }
};

const handleDenySingle = async (row: UnlimitApplication) => {
  try {
    await ElMessageBox.confirm(
      `确定要拒绝该不限时申请吗？`,
      "提示",
      { confirmButtonText: "确定", cancelButtonText: "取消", type: "warning" }
    );
    await denyUnlimit([row.id]);
    ElMessage.success(`已拒绝申请 #${row.id}`);
    fetchList();
    fetchActiveList();
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error(error.message || "拒绝失败");
    }
  }
};

const handleRevoke = async (row: UnlimitApplication) => {
  try {
    await ElMessageBox.confirm(
      `确定要撤销申请 #${row.id}（${getMaterialName(row.material_id) || `素材#${row.material_id}`}）使其立即失效吗？`,
      "提示",
      { confirmButtonText: "确定", cancelButtonText: "取消", type: "warning" }
    );
    await revokeUnlimit(row.id);
    ElMessage.success(`已撤销申请 #${row.id}`);
    fetchActiveList();
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error(error.message || "操作失败");
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
    fetchActiveList();
  } catch (error: any) {
    if (error !== "cancel") {
      ElMessage.error(error.message || "拒绝失败");
    }
  }
};

// 初始化
onMounted(() => {
  fetchList();
  fetchActiveList();
  calculateTableHeight();
  window.addEventListener("resize", calculateTableHeight);

  const handleRefresh = () => {
    fetchList();
    fetchActiveList();
  };
  window.addEventListener("refresh-video-unlock-tab", handleRefresh);

  onUnmounted(() => {
    window.removeEventListener("resize", calculateTableHeight);
    window.removeEventListener("refresh-video-unlock-tab", handleRefresh);
  });
});
</script>
