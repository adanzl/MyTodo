<template>
  <div class="p-2">
    <!-- 工具栏 -->
    <div class="flex items-center h-10 mb-2 gap-2">
      <el-date-picker
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        size="small"
        class="w-60"
      />
      <el-button type="primary" size="small" @click="handleQuery" :loading="loading">
        查询
      </el-button>
      <el-button size="small" @click="handleReset">重置</el-button>
    </div>

    <!-- 统计摘要卡片 -->
    <el-card v-if="abstractData" class="mb-4" shadow="hover">
      <template #header>
        <div class="font-bold">使用统计摘要</div>
      </template>
      <div class="grid grid-cols-4 gap-4">
        <div class="text-center">
          <div class="text-gray-500 text-sm">总次数</div>
          <div class="text-2xl font-bold text-blue-600">{{ abstractData.total_count || 0 }}</div>
        </div>
        <div class="text-center">
          <div class="text-gray-500 text-sm">总时长</div>
          <div class="text-2xl font-bold text-green-600">{{ formatDuration(abstractData.total_duration || 0) }}</div>
        </div>
        <div class="text-center">
          <div class="text-gray-500 text-sm">平均时长</div>
          <div class="text-2xl font-bold text-orange-600">{{ formatDuration(abstractData.avg_duration || 0) }}</div>
        </div>
        <div class="text-center">
          <div class="text-gray-500 text-sm">用户数</div>
          <div class="text-2xl font-bold text-purple-600">{{ abstractData.user_count || 0 }}</div>
        </div>
      </div>
    </el-card>

    <!-- 详细数据表格 -->
    <el-table
      v-if="detailData && detailData.length > 0"
      :data="detailData"
      v-loading="loading"
      stripe
      border
      style="width: 100%"
    >
      <el-table-column prop="user_id" label="用户ID" width="100" />
      <el-table-column prop="type" label="类型" width="120" />
      <el-table-column prop="count" label="次数" width="100" />
      <el-table-column prop="total_duration" label="总时长" width="120">
        <template #default="{ row }">
          {{ formatDuration(row.total_duration) }}
        </template>
      </el-table-column>
      <el-table-column prop="avg_duration" label="平均时长" width="120">
        <template #default="{ row }">
          {{ formatDuration(row.avg_duration) }}
        </template>
      </el-table-column>
    </el-table>

    <!-- 空状态 -->
    <el-empty v-if="!loading && !abstractData && !detailData?.length" description="请选择日期范围后查询" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from "vue";
import { ElMessage } from "element-plus";
import { getUsageAbstract } from "@/api/api-usage";
import dayjs from "dayjs";

// 日期范围 - 默认过去一周到今天
const dateRange = ref<[Date, Date] | null>([
  dayjs().subtract(7, 'day').toDate(),
  dayjs().toDate()
]);

// 加载状态
const loading = ref(false);

// 摘要数据
const abstractData = ref<any>(null);

// 详细数据
const detailData = ref<any[]>([]);

// 查询
const handleQuery = async () => {
  if (!dateRange.value || dateRange.value.length !== 2) {
    ElMessage.warning("请选择日期范围");
    return;
  }

  loading.value = true;
  try {
    const startTime = dayjs(dateRange.value[0]).startOf('day').format("YYYY-MM-DD HH:mm:ss");
    const endTime = dayjs(dateRange.value[1]).endOf('day').format("YYYY-MM-DD HH:mm:ss");

    // 查询摘要（不含详情）
    const result = await getUsageAbstract(startTime, endTime, 0);
    abstractData.value = result;

    // 如果需要，可以查询详细数据
    // const detailResult = await getUsageAbstract(startTime, endTime, 1);
    // detailData.value = detailResult.detail || [];

    ElMessage.success("查询成功");
  } catch (error: any) {
    console.error("查询失败:", error);
    ElMessage.error(error.message || "查询失败");
  } finally {
    loading.value = false;
  }
};

// 重置
const handleReset = () => {
  dateRange.value = null;
  abstractData.value = null;
  detailData.value = [];
};

// 格式化时长
const formatDuration = (seconds: number): string => {
  if (!seconds || seconds === 0) return "0秒";

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  const parts: string[] = [];
  if (hours > 0) parts.push(`${hours}小时`);
  if (minutes > 0) parts.push(`${minutes}分钟`);
  if (secs > 0) parts.push(`${secs}秒`);

  return parts.join("") || "0秒";
};
</script>

<style scoped>
/* 使用 Tailwind CSS，无需额外样式 */
</style>
