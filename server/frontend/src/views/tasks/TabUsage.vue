<template>
  <div class="p-2">
    <!-- 工具栏 -->
    <div class="flex items-center h-10 mb-2 gap-2">

      <div class="flex">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          size="small"
          class="w-55! mr-3"
        />
        <el-button type="primary" size="small" @click="handleQuery" :disabled="loading">
          查询
        </el-button>
        <el-button size="small" @click="handleReset">重置</el-button>
      </div>
      <el-switch
        v-model="showDetail"
        active-text="详情"
        inactive-text=""
        @change="handleQuery"
      />
    </div>

    <!-- 统计摘要卡片 -->
    <el-card v-if="rawData && Object.keys(rawData).length > 0" class="mb-4" shadow="hover">
      <template #header>
        <div class="font-bold">使用统计摘要</div>
      </template>

      <!-- 动态表格 -->
      <el-table :data="tableData" border stripe v-loading="loading">
        <el-table-column prop="user_id" label="用户" width="80" fixed>
          <template #default="{ row }">
            {{ getUserName(row.user_id) }}
          </template>
        </el-table-column>

        <!-- 动态日期列 -->
        <el-table-column
          v-for="date in dateColumns"
          :key="date"
          :label="date"
          align="center"
        >
          <el-table-column
            v-for="subItem in getSubItems(date)"
            :key="`${date}-${subItem.key}`"
            :label="subItem.label"
            align="center"
            min-width="70"
          >
            <template #default="{ row }">
              <span class="text-[12px]">{{ getCellValue(row.user_id, date, subItem.key) || '-' }}</span>
            </template>
          </el-table-column>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 空状态 -->
    <el-empty v-if="!loading && (!rawData || Object.keys(rawData).length === 0)" description="请选择日期范围后查询" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
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

// 是否显示详情
const showDetail = ref(false);

// 原始数据
const rawData = ref<any>(null);

// 获取所有用户ID
const userIds = computed(() => {
  if (!rawData.value) return [];
  return Object.keys(rawData.value).sort((a, b) => Number(a) - Number(b));
});

// 获取所有日期 - 基于选择的日期范围生成
const dateColumns = computed(() => {
  if (!dateRange.value || dateRange.value.length !== 2) return [];

  const dates: string[] = [];
  const start = dayjs(dateRange.value[0]);
  const end = dayjs(dateRange.value[1]);

  let current = start;
  while (current.isBefore(end) || current.isSame(end, 'day')) {
    dates.push(current.format('YYYY-MM-DD'));
    current = current.add(1, 'day');
  }

  return dates;
});

// 获取用户名
const getUserName = (userId: string): string => {
  const userMap: Record<string, string> = {
    '1': 'Leo',
    '2': '紫夜',
    '3': '灿灿',
    '4': '昭昭'
  };
  return userMap[userId] || userId;
};

// 构建表格数据
const tableData = computed(() => {
  return userIds.value.map(userId => ({
    user_id: userId
  }));
});

// 获取指定日期的子项（type 或 out_key）
const getSubItems = (date: string) => {
  if (!rawData.value) return [];

  if (!showDetail.value) {
    // detail=0: 固定两列 PDF 和 VIDEO
    return [
      { key: 'matPdf', label: 'PDF' },
      { key: 'matVideo', label: 'VIDEO' }
    ];
  }

  // detail=1: 按 out_key 分
  const items = new Set<string>();
  userIds.value.forEach(userId => {
    const userData = rawData.value[userId];
    if (userData && userData[date]) {
      const typeData = userData[date];
      Object.values(typeData).forEach((outKeys: any) => {
        if (typeof outKeys === 'object') {
          Object.keys(outKeys).forEach(key => items.add(key));
        }
      });
    }
  });

  return Array.from(items).map(key => ({
    key,
    label: key
  }));
};

// 获取单元格值
const getCellValue = (userId: string, date: string, subKey: string) => {
  if (!rawData.value) return null;

  const userData = rawData.value[userId];
  if (!userData || !userData[date]) return null;

  const typeData = userData[date];

  if (showDetail.value) {
    // detail=1: 查找包含该 out_key 的 type
    for (const type of Object.keys(typeData)) {
      const outKeys = typeData[type];
      if (typeof outKeys === 'object' && outKeys[subKey] !== undefined) {
        return formatDurationToMinutes(outKeys[subKey]);
      }
    }
  } else {
    // detail=0: 直接按 type 查找
    if (typeData[subKey] !== undefined) {
      return formatDurationToMinutes(typeData[subKey]);
    }
  }

  return null;
};

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

    // 查询摘要
    const result = await getUsageAbstract(startTime, endTime, showDetail.value ? 1 : 0);
    rawData.value = result.data || {};

  } catch (error: any) {
    console.error("查询失败:", error);
    ElMessage.error(error.message || "查询失败");
  } finally {
    loading.value = false;
  }
};

// 重置
const handleReset = () => {
  dateRange.value = [
    dayjs().subtract(7, 'day').toDate(),
    dayjs().toDate()
  ];
  rawData.value = null;
  showDetail.value = false;
};

// 格式化时长为 MM:SS 格式
const formatDurationToMinutes = (seconds: number): string => {
  if (!seconds || seconds === 0) return "00:00";

  const minutes = Math.floor(seconds / 60);
  const secs = seconds % 60;

  return `${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
};

// 组件挂载时自动查询
onMounted(() => {
  handleQuery();

  // 监听刷新事件
  const handleRefresh = () => {
    handleQuery();
  };
  window.addEventListener('refresh-usage-tab', handleRefresh);

  onUnmounted(() => {
    window.removeEventListener('refresh-usage-tab', handleRefresh);
  });
});
</script>

<style scoped>
/* 使用 Tailwind CSS，无需额外样式 */
</style>
