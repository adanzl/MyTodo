<template>
  <div class="m-4">
    <!-- 筛选区域 -->
    <div class="flex items-center gap-3 h-10">
      <el-button :icon="Refresh" plain type="primary" @click="refreshData" :loading="loading" />
      <el-radio-group v-model="selectedUserId" @change="onUserChange">
        <el-radio-button :value="3">灿灿</el-radio-button>
        <el-radio-button :value="4">昭昭</el-radio-button>
      </el-radio-group>
    </div>

    <!-- 日程列表  max-height="calc(100vh - 200px)-->
    <el-collapse v-loading="loading">
      <el-collapse-item v-for="item in scheduleList" :key="item.id" :title="`[${item.id}] ${item.title}`">
        <div class="space-y-2">
          <p>
            时间范围: {{ item?.startTs }} - {{ item?.endTs }} |
            全天: {{ item.allDay ? '是' : '否' }} |
            排序: {{ item.order }}
          </p>
          <p>
            提醒: {{ item.reminder }} |
            重复: {{ item.repeat }} |
            重复结束: {{ item.repeatEndTs }}
          </p>
          <div v-if="item.subtasks && item.subtasks.length > 0">
            <p class="font-medium">子任务:</p>
            <p v-for="(task, idx) in item.subtasks" :key="idx" class="ml-4">
              [{{ task.id }}] {{ task.name }}
            </p>
          </div>
        </div>
      </el-collapse-item>
    </el-collapse>

    <!-- 空状态 -->
    <el-empty v-if="!loading && scheduleList.length === 0" description="暂无日程数据" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import { getTodoList } from "@/api/api-todo";
import type { ScheduleData } from "@/api/api-todo";

const loading = ref(false);
const selectedUserId = ref<number>(3); // 默认选中灿灿
const scheduleList = ref<ScheduleData[]>([]);

const fetchScheduleList = async (userId: number) => {
  loading.value = true;
  try {
    const response = await getTodoList(userId, 1, 100);
    scheduleList.value = response.data || [];
  } catch (err) {
    console.error("获取日程失败:", err);
    ElMessage.error("获取日程失败");
    scheduleList.value = [];
  } finally {
    loading.value = false;
  }
};

const onUserChange = () => {
  fetchScheduleList(selectedUserId.value);
};

const refreshData = () => {
  fetchScheduleList(selectedUserId.value);
};

onMounted(() => {
  fetchScheduleList(selectedUserId.value);
});
</script>

<style scoped></style>
