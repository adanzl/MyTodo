<template>
  <div class="p-2">
    <div class="flex flex-wrap items-center gap-5 h-10 mb-2">
      <el-button
        size="small"
        type="primary"
        plain
        @click="handleRefresh"
        :icon="Refresh"
      />
      <el-radio-group v-model="selectedRecordType" size="default" @change="onRecordTypeChange">
        <el-radio-button value="all">全部</el-radio-button>
        <el-radio-button value="lottery">抽奖</el-radio-button>
        <el-radio-button value="exchange">兑换</el-radio-button>
      </el-radio-group>
      <el-select
        v-model="selectedPoolId"
        placeholder="选择奖池"
        :disabled="selectedRecordType !== 'lottery'"
        clearable
        style="width: 160px"
        @change="onPoolChange"
      >
        <el-option label="全部奖池" :value="0" />
        <el-option v-for="pool in poolList" :key="pool.id" :label="pool.name" :value="pool.id" />
      </el-select>
      <el-checkbox v-model="onlyWish" @change="onWishChange" size="large">心愿单</el-checkbox>
      <el-radio-group size="default" v-model="selectedUserId" @change="onUserChange">
        <el-radio-button v-for="item in userList" :key="item.id" :value="item.id">
          {{ item.name }}
        </el-radio-button>
      </el-radio-group>
    </div>

    <el-table
      :data="recordList.data"
      v-loading="loading"
      stripe
      :grid="true"
      :cell-style="{ padding: '8px' }"
      :max-height="tableMaxHeight"
      @row-click="onRowClick"
    >
      <el-table-column label="ID" prop="id" width="60" align="center" />
      <el-table-column label="用户" width="70" align="center">
        <template #default="{ row }">
          <span>{{ row.user?.name ?? row.user_id }}</span>
        </template>
      </el-table-column>
      <el-table-column label="类型" width="60" align="center">
        <template #default="{ row }">
          <div class="flex items-center justify-center">
            <el-tag :type="isExchange(row.gitf_pool_id) ? 'warning' : 'primary'" size="small">
              {{ getRecordTypeLabel(row.gitf_pool_id) }}
            </el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="礼物" min-width="100" prop="gitf_name" show-overflow-tooltip />
      <el-table-column label="分类" width="90">
        <template #default="{ row }">
          {{ getCateLabel(row.gift_cate_id) }}
        </template>
      </el-table-column>
      <el-table-column label="心愿" width="60" align="center">
        <template #default="{ row }">
          <div class="flex items-center justify-center">
            <el-icon v-if="row.wish === 1" class="w-5!" color="#67C23A">
              <SuccessFilled />
            </el-icon>
            <span v-else>-</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="奖池" width="110">
        <template #default="{ row }">
          {{ getPoolLabel(row.gitf_pool_id) }}
        </template>
      </el-table-column>
      <el-table-column label="时间" prop="dt" width="180" />
      <el-table-column label="备注" prop="msg" min-width="180" show-overflow-tooltip />
      <el-table-column label="核销" width="60" align="center">
        <template #default="{ row }">
          <el-icon
            :size="20"
            class="cursor-pointer"
            :color="row.status === 1 ? '#F56C6C' : '#67C23A'"
            @click.stop="onToggleVerify(row)"
          >
            <SuccessFilled v-if="row.status === 2" />
            <Present v-else />
          </el-icon>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      v-model="giftDialogVisible"
      title="奖品详情"
      width="800px"
      align-center
      @close="giftDialogData = null"
    >
      <div v-if="giftDialogData" class="flex flex-col items-center gap-4 py-2">
        <el-image
          :src="getPicDisplayUrl(giftDialogData.image)"
          class="w-48 h-48 object-contain rounded"
          fit="contain"
        >
          <template #error>
            <div class="w-48 h-48 flex items-center justify-center bg-gray-100 rounded">
              <el-icon :size="48" color="#909399"><Present /></el-icon>
            </div>
          </template>
        </el-image>
        <div class="font-medium text-base text-center">{{ giftDialogData.name || "-" }}</div>
        <div v-if="giftDialogData.cost != null" class="text-sm text-gray-500">
          价值: {{ giftDialogData.cost }}
        </div>
      </div>
      <div v-else class="text-center py-8 text-gray-500">暂无奖品信息</div>
    </el-dialog>

    <el-pagination
      layout="sizes, prev, pager, next"
      :total="recordList.totalCount"
      :page-size="recordList.pageSize"
      :page-sizes="[15, 20, 50]"
      :current-page="recordList.pageNum"
      class="mt-2"
      background
      @size-change="(size: number) => handlePageChange(recordList.pageNum, size)"
      @current-change="(page: number) => handlePageChange(page, recordList.pageSize)"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from "vue";
import { Present, Refresh, SuccessFilled } from "@element-plus/icons-vue";
import { getList, setData } from "@/api/api-common";
import { getPicDisplayUrl } from "@/api/api-pic";
import type { GiftHistory, GiftCategory } from "@/types/lottery";
import type { User } from "@/types/user";
import { useUserStore } from "@/stores/user";
import { ElMessage } from "element-plus";
import * as _ from "lodash-es";
import dayjs from "dayjs";

interface UserWithAll extends User {
  id: number;
  name: string;
}

interface GiftPoolItem {
  id: number;
  name: string;
}

interface GiftDetail {
  name: string;
  image: string;
  cost?: number;
}

const PAGE_SIZE = 15;

const userStore = useUserStore();
const storeUserList = computed(() => userStore.userList);

const userList = computed(() => {
  const list = [...storeUserList.value];
  list.unshift({ id: 0, name: "全部" } as UserWithAll);
  return list;
});

const recordList = ref({
  data: [] as GiftHistory[],
  pageNum: 1,
  pageSize: PAGE_SIZE,
  totalCount: 0,
  totalPage: 0,
});

const loading = ref(false);
const selectedUserId = ref<number>(0);
const selectedRecordType = ref<"all" | "lottery" | "exchange">("all");
const selectedPoolId = ref<number>(0);
const onlyWish = ref(false);
const tableMaxHeight = ref(400);
const poolList = ref<GiftPoolItem[]>([]);
const poolMap = ref<Map<number, string>>(new Map());
const cateMap = ref<Map<number, string>>(new Map());
const giftDialogVisible = ref(false);
const giftDialogData = ref<GiftDetail | null>(null);

const calculateTableHeight = () => {
  nextTick(() => {
    tableMaxHeight.value = window.innerHeight - 400;
  });
};

const getUserInfo = (id: number): UserWithAll | undefined => {
  return _.find(userList.value, item => item.id === id);
};

const isExchange = (poolId?: number) => poolId === -1;

const getRecordTypeLabel = (poolId?: number) => (isExchange(poolId) ? "兑换" : "抽奖");

const getPoolLabel = (poolId?: number) => {
  if (isExchange(poolId)) return "兑换";
  if (poolId == null) return "-";
  return poolMap.value.get(poolId) ?? `奖池${poolId}`;
};

const getCateLabel = (cateId?: number) => {
  if (cateId == null) return "-";
  return cateMap.value.get(cateId) ?? String(cateId);
};

const buildFilter = (): Record<string, unknown> => {
  const filter: Record<string, unknown> = {};
  if (selectedUserId.value && selectedUserId.value !== 0) {
    filter.user_id = selectedUserId.value;
  }
  if (selectedRecordType.value === "exchange") {
    filter.gitf_pool_id = -1;
  } else if (selectedRecordType.value === "lottery") {
    if (selectedPoolId.value > 0) {
      filter.gitf_pool_id = selectedPoolId.value;
    } else {
      filter.gitf_pool_id = { ">": -1 };
    }
  }
  if (onlyWish.value) {
    filter.wish = 1;
  }
  return filter;
};

const loadPoolMap = async () => {
  try {
    const response = await getList<GiftPoolItem>("t_gift_pool", undefined, 1, 500);
    poolList.value = response.data?.data || [];
    poolMap.value = new Map(poolList.value.map(item => [item.id, item.name]));
  } catch (error) {
    console.error("获取奖池列表失败:", error);
  }
};

const loadCateMap = async () => {
  try {
    const response = await getList<GiftCategory>("t_gift_category", undefined, 1, 500);
    const categories = response.data?.data || [];
    cateMap.value = new Map(categories.map(item => [item.id, item.name]));
  } catch (error) {
    console.error("获取礼物分类失败:", error);
  }
};

const refreshRecordList = async (pageNum: number, pageSize: number) => {
  loading.value = true;
  try {
    const filter = buildFilter();
    const filterParam = Object.keys(filter).length > 0 ? filter : undefined;
    const response = await getList<GiftHistory>("t_gift_history", filterParam, pageNum, pageSize);
    if (response?.data) {
      const rows = response.data.data || [];
      recordList.value.pageNum = response.data.pageNum ?? pageNum;
      recordList.value.pageSize = response.data.pageSize ?? pageSize;
      recordList.value.totalCount = response.data.totalCount ?? 0;
      recordList.value.totalPage = response.data.totalPage ?? 0;

      recordList.value.data = rows.map(item => ({
        ...item,
        user: getUserInfo(item.user_id),
        dt: item.dt ? dayjs(item.dt).format("YYYY-MM-DD HH:mm:ss") : "-",
      }));
    }
  } catch (error) {
    console.error("获取礼物记录失败:", error);
    ElMessage.error("获取礼物记录失败");
  } finally {
    loading.value = false;
  }
};

const onRecordTypeChange = async () => {
  if (selectedRecordType.value !== "lottery") {
    selectedPoolId.value = 0;
  }
  await refreshRecordList(1, recordList.value.pageSize);
};

const onPoolChange = async () => {
  await refreshRecordList(1, recordList.value.pageSize);
};

const onWishChange = async () => {
  await refreshRecordList(1, recordList.value.pageSize);
};

const onUserChange = async () => {
  await refreshRecordList(1, recordList.value.pageSize);
};

const handlePageChange = (pageNum: number, pageSize: number) => {
  refreshRecordList(pageNum, pageSize);
};

const onToggleVerify = async (row: GiftHistory) => {
  const newStatus = row.status === 1 ? 2 : 1;
  try {
    await setData("t_gift_history", { id: row.id, status: newStatus });
    row.status = newStatus;
    ElMessage.success(newStatus === 2 ? "核销成功" : "已取消核销");
  } catch (error) {
    console.error("更新核销状态失败:", error);
    ElMessage.error("更新核销状态失败");
  }
};

const onRowClick = (row: GiftHistory) => {
  onGiftClick(row);
};

const onGiftClick = async (row: GiftHistory) => {
  loading.value = true;
  try {
    const response = await getList<GiftDetail>(
      "t_gift",
      { id: row.gitf_id },
      1,
      1
    );
    const gift = response.data?.data?.[0];
    if (gift) {
      giftDialogData.value = gift;
      giftDialogVisible.value = true;
    } else {
      ElMessage.warning("未找到奖品信息");
    }
  } catch (error) {
    console.error("获取奖品详情失败:", error);
    ElMessage.error("获取奖品详情失败");
  } finally {
    loading.value = false;
  }
};

const handleRefresh = () => {
  refreshRecordList(recordList.value.pageNum, recordList.value.pageSize);
};

onMounted(async () => {
  calculateTableHeight();
  window.addEventListener("resize", calculateTableHeight);
  window.addEventListener("refresh-lottery-history-tab", handleRefresh);

  await userStore.refreshUserList();
  if (userList.value.length > 0) {
    selectedUserId.value = userList.value[0].id;
  }
  await loadPoolMap();
  await loadCateMap();
  await refreshRecordList(1, PAGE_SIZE);
});

onUnmounted(() => {
  window.removeEventListener("resize", calculateTableHeight);
  window.removeEventListener("refresh-lottery-history-tab", handleRefresh);
});
</script>
