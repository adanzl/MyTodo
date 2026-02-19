<template>
  <div class="">
    <div class="flex items-center">
      <el-radio-group size="large" v-model="selectedUserId" @change="onUserChange">
        <el-radio-button v-for="item in userList" :key="item.id" :value="item.id">
          {{ item.name }}
        </el-radio-button>
      </el-radio-group>
    </div>
    <el-table
      :data="recordList.data"
      v-loading="loading"
      stripe
      @row-click="onRowClick">
      <el-table-column label="ID" prop="id" width="60"> </el-table-column>
      <el-table-column label="user" width="60">
        <template #default="{ row }">
          <template v-if="row.user">
            <span>{{ row.user.name }}</span>
          </template>
          <template v-else>
            <span>{{ row.user_id }}</span>
          </template>
        </template>
      </el-table-column>
      <el-table-column label="Action" prop="action" width="100"> </el-table-column>
      <el-table-column label="Date" prop="dt" width="180"> </el-table-column>
      <el-table-column label="Pre" prop="pre_value" width="80"> </el-table-column>
      <el-table-column label="Value" width="70">
        <template #default="{ row }">
          <div class="flex items-center gap-1 w-full">
            <el-icon v-if="row.value > 0" color="#67C23A" :size="16"><CaretTop /></el-icon>
            <el-icon v-else color="#F56C6C" :size="16"><CaretBottom /></el-icon>
            <span class="flex-1 text-center">{{ row.value }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="Current" prop="current" width="80"> </el-table-column>
      <el-table-column label="MSG" prop="msg"> </el-table-column>
      <el-table-column label="" width="60" align="center" class-name="text-primary">
        <template #default="{ row }">
          <el-icon
            v-if="isGiftRecord(row)"
            :size="20">
            <Present />
          </el-icon>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="80" align="center" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="isGiftRecord(row)"
            type="danger"
            link
            size="small"
            @click.stop="onUndo(row)">
            撤销
          </el-button>
          <span v-else>-</span>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog
      v-model="giftDialogVisible"
      title="奖品详情"
      width="320px"
      align-center
      @close="giftDialogData = null">
      <div v-if="giftDialogData" class="flex flex-col items-center gap-3 py-2">
        <el-image
          v-if="giftDialogData.image"
          :src="getPicDisplayUrl(giftDialogData.image)"
          class="w-32 h-32 object-contain rounded"
          fit="contain" />
        <div class="font-medium text-lg">{{ giftDialogData.name || "-" }}</div>
      </div>
    </el-dialog>
    <el-pagination
      layout="sizes, prev, pager, next"
      :total="recordList.totalCount"
      :page-size="recordList.pageSize"
      :page-sizes="[10, 20, 50]"
      :current-page="recordList.pageNum"
      class="mt-2"
      background
      @size-change="(size: number) => handlePageChange(recordList.pageNum, size)"
      @current-change="(page: number) => handlePageChange(page, recordList.pageSize)"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { CaretTop, CaretBottom, Present } from "@element-plus/icons-vue";
import { getList, getData } from "@/api/common";
import { getPicDisplayUrl } from "@/api/pic";
import { undoLottery } from "@/api/user";
import { ElMessage } from "element-plus";
import * as _ from "lodash-es";
import dayjs from "dayjs";
import { useUserStore } from "@/stores/user";
import type { User } from "@/types/user";

interface ScoreHistory {
  id: number;
  user_id: number;
  value: number;
  action: string;
  pre_value: number;
  current: number;
  msg: string;
  dt: string;
  out_key?: string;
  user?: User;
}

interface UserWithAll extends User {
  id: number;
  name: string;
}

const PAGE_SIZE = 20;

// 使用 Pinia Store
const userStore = useUserStore();
const storeUserList = computed(() => userStore.userList);

// 本地用户列表（包含"全部"选项）
const userList = computed(() => {
  const list = [...storeUserList.value];
  list.unshift({ id: 0, name: "全部" } as UserWithAll);
  return list;
});

const recordList = ref<{
  data: ScoreHistory[];
  pageNum: number;
  pageSize: number;
  totalCount: number;
  totalPage: number;
}>({
  data: [],
  pageNum: 1,
  pageSize: 20,
  totalCount: 0,
  totalPage: 0,
});
const loading = ref(false);
const selectedUserId = ref<number>(0);
const selectedUser = computed(() => {
  return userList.value.find(item => item.id === selectedUserId.value) || userList.value[0];
});

const refreshUserList = async () => {
  // 使用 Pinia Store 刷新用户列表
  await userStore.refreshUserList();
  // 设置默认选中第一个用户
  if (userList.value.length > 0) {
    selectedUserId.value = userList.value[0].id;
  }
};

const getUserInfo = (id: number): UserWithAll | undefined => {
  return _.find(userList.value, item => item.id == id);
};

const refreshRecordList = async (userId: number, pageNum: number, pageSize: number) => {
  loading.value = true;
  try {
    let filter: Record<string, number> | undefined = undefined;
    if (userId && userId !== 0) {
      filter = { user_id: userId };
    }
    const response = await getList<ScoreHistory>("t_score_history", filter, pageNum, pageSize);
    if (response && response.data) {
      const d = response.data.data || [];
      recordList.value.data = [];
      recordList.value.pageNum = response.data.pageNum ?? pageNum;
      recordList.value.pageSize = response.data.pageSize ?? pageSize;
      recordList.value.totalCount = response.data.totalCount ?? 0;
      recordList.value.totalPage = response.data.totalPage ?? 0;

      _.forEach(d, (item: ScoreHistory) => {
        item.user = getUserInfo(item.user_id);
        item.dt = dayjs(item.dt).format("YYYY-MM-DD HH:mm:ss");
        recordList.value.data.push(item);
      });
    }
  } catch (error) {
    console.error("获取积分记录失败:", error);
  } finally {
    loading.value = false;
  }
};

const onUserChange = async () => {
  const user = selectedUser.value;
  console.log("onUserChange", user);
  if (user) {
    await refreshRecordList(user.id, 1, PAGE_SIZE);
  }
};

const handlePageChange = (pageNum: number, pageSize: number) => {
  refreshRecordList(selectedUser.value.id, pageNum, pageSize);
};

const giftDialogVisible = ref(false);
const giftDialogData = ref<{ name: string; image: string } | null>(null);

/** 抽奖/兑换记录（可查看奖品、可撤销） */
function isGiftRecord(row: ScoreHistory) {
  return (row.action === "lottery" || row.action === "exchange") && row.out_key;
}

function onRowClick(row: ScoreHistory) {
  if (isGiftRecord(row)) {
    onGiftClick(row);
  }
}

async function onGiftClick(row: ScoreHistory) {
  if (!isGiftRecord(row)) return;
  try {
    const gift = await getData<{ name: string; image: string }>(
      "t_gift",
      Number(row.out_key),
      "name,image"
    );
    giftDialogData.value = { name: gift?.name ?? "", image: gift?.image ?? "" };
    giftDialogVisible.value = true;
  } catch (err) {
    console.error("获取奖品详情失败:", err);
    ElMessage.error("获取奖品详情失败");
  }
}

async function onUndo(row: ScoreHistory) {
  if (!isGiftRecord(row)) return;
  try {
    await undoLottery(row.id);
    ElMessage.success("已撤销：已删除该条记录、恢复积分并补充库存");
    await refreshRecordList(selectedUserId.value, recordList.value.pageNum, recordList.value.pageSize);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "撤销失败";
    ElMessage.error(msg);
  }
}

onMounted(async () => {
  await refreshUserList();
  await refreshRecordList(0, 1, PAGE_SIZE);
});
</script>

<style scoped></style>
