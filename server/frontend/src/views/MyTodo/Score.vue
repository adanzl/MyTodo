<template>
  <div class="">
    <div class="flex items-center">
      <el-radio-group size="large" v-model="selectedUserId" @change="onUserChange">
        <el-radio-button v-for="item in userList" :key="item.id" :value="item.id">
          {{ item.name }}
        </el-radio-button>
      </el-radio-group>
    </div>
    <el-table :data="recordList.data" v-loading="loading" stripe>
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
      <el-table-column label="Pre" prop="pre_value" width="70"> </el-table-column>
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
    </el-table>
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
import { CaretTop, CaretBottom } from "@element-plus/icons-vue";
import { getList } from "@/api/common";
import * as _ from "lodash-es";
import dayjs from "dayjs";

const PAGE_SIZE = 10;
const userList = ref<any[]>([]);
const recordList = ref({
  data: [] as any[],
  pageNum: 1,
  pageSize: 10,
  totalCount: 0,
  totalPage: 0,
});
const loading = ref(false);
const selectedUserId = ref<number>(0);
const selectedUser = computed(() => {
  return userList.value.find(item => item.id === selectedUserId.value) || userList.value[0];
});

const refreshUserList = async () => {
  try {
    const response = await getList("t_user");
    if (response && response.data) {
      // API 返回的是分页格式，用户数组在 response.data.data 中
      const users = response.data.data || response.data;
      const data = Array.isArray(users) ? users : [];
      userList.value = [...data];
      userList.value.unshift({ id: 0, name: "全部" });
      if (userList.value.length > 0) {
        selectedUserId.value = userList.value[0].id;
      }
    }
  } catch (error) {
    console.error("获取用户列表失败:", error);
  }
};

const getUserInfo = (id: number) => {
  return _.find(userList.value, item => item.id == id);
};

const refreshRecordList = async (userId: number, pageNum: number, pageSize: number) => {
  loading.value = true;
  try {
    let filter: any = undefined;
    if (userId && userId !== 0) {
      filter = { user_id: userId };
    }
    const response = await getList<{
      pageNum: number;
      pageSize: number;
      totalCount: number;
      totalPage: number;
      data: any[];
    }>("t_score_history", filter, pageNum, pageSize);
    if (response && response.data) {
      const d = response.data.data || response.data;
      console.log(response);
      recordList.value.data = [];
      recordList.value.pageNum = response.data.pageNum || pageNum;
      recordList.value.pageSize = response.data.pageSize || pageSize;
      recordList.value.totalCount = response.data.totalCount || 0;
      recordList.value.totalPage = response.data.totalPage || 0;

      _.forEach(d, (item: any) => {
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

const handlePageChange = (pageNum: any, pageSize: any) => {
  refreshRecordList(selectedUser.value.id, Number(pageNum), Number(pageSize));
};

onMounted(async () => {
  await refreshUserList();
  await refreshRecordList(0, 1, PAGE_SIZE);
});
</script>

<style scoped></style>
