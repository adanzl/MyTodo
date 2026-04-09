<template>
  <div class="p-5" v-loading="loading" element-loading-text="加载中..." element-loading-background="rgba(255, 255, 255, 0.8)">
    <el-card class="mb-5">
      <el-form :inline="true" class="flex flex-wrap gap-2.5">
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            unlink-panels
            :shortcuts="shortcuts"
            @change="handleDateChange"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="refreshStatistics">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-row :gutter="20" class="mt-5">
      <!-- 左边：昭昭 -->
      <el-col :span="12">
        <div class="h-full">
          <h2 class="text-2xl font-bold text-white mb-5 text-center p-2.5 bg-linear-to-br from-[#667eea] to-[#764ba2] rounded-lg">昭昭</h2>

          <!-- 任务统计 -->
          <el-row :gutter="15" class="mb-5">
            <el-col :span="12">
              <el-card class="h-24">
                <div class="flex items-center gap-3.75">
                  <div class="w-12 h-12 rounded-[10px] flex items-center justify-center text-2xl text-white bg-linear-to-br from-[#4facfe] to-[#00f2fe]">
                    <el-icon><CircleCheck /></el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-2xl font-bold text-[#303133] mb-1">{{ zhaozhaoStats.taskCount }}</div>
                    <div class="text-xs text-[#909399]">完成任务数</div>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card class="h-24">
                <div class="flex items-center gap-3.75">
                  <div class="w-12 h-12 rounded-[10px] flex items-center justify-center text-2xl text-white bg-linear-to-br from-[#43e97b] to-[#38f9d7]">
                    <el-icon><Coin /></el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-2xl font-bold text-[#303133] mb-1">{{ zhaozhaoStats.taskIncome }}</div>
                    <div class="text-xs text-[#909399]">任务收益</div>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <!-- 抽奖统计 -->
          <el-row :gutter="15" class="mb-5">
            <el-col :span="12">
              <el-card class="h-24">
                <div class="flex items-center gap-3.75">
                  <div class="w-12 h-12 rounded-[10px] flex items-center justify-center text-2xl text-white bg-linear-to-br from-[#667eea] to-[#764ba2]">
                    <el-icon><Present /></el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-2xl font-bold text-[#303133] mb-1">{{ zhaozhaoStats.lotteryCount }}</div>
                    <div class="text-xs text-[#909399]">抽奖次数</div>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card class="h-24">
                <div class="flex items-center gap-3.75">
                  <div class="w-12 h-12 rounded-[10px] flex items-center justify-center text-2xl text-white bg-linear-to-br from-[#f093fb] to-[#f5576c]">
                    <el-icon><Money /></el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-2xl font-bold text-[#303133] mb-1">{{ zhaozhaoStats.lotteryCost }}</div>
                    <div class="text-xs text-[#909399]">抽奖花费</div>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <!-- 后台操作统计 -->
          <el-row :gutter="15" class="mb-5">
            <el-col :span="12">
              <el-card class="h-24">
                <div class="flex items-center gap-3.75">
                  <div class="w-12 h-12 rounded-[10px] flex items-center justify-center text-2xl text-white bg-linear-to-br from-[#fa709a] to-[#fee140]">
                    <el-icon><Setting /></el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-2xl font-bold text-[#303133] mb-1">{{ appAdminStats.taskCount }}</div>
                    <div class="text-xs text-[#909399]">后台操作数</div>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card class="h-24">
                <div class="flex items-center gap-3.75">
                  <div class="w-12 h-12 rounded-[10px] flex items-center justify-center text-2xl text-white bg-linear-to-br from-[#30cfd0] to-[#330867]">
                    <el-icon><TrendCharts /></el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-2xl font-bold text-[#303133] mb-1">{{ appAdminStats.taskIncome }}</div>
                    <div class="text-xs text-[#909399]">操作汇总</div>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <el-card class="mt-5">
            <template #header>
              <div class="text-base font-bold">
                <span>各分类中奖统计</span>
              </div>
            </template>
            <el-table :data="zhaozhaoCategoryStats" stripe style="width: 100%">
              <el-table-column prop="cate_name" label="分类名称" />
              <el-table-column prop="win_count" label="中奖次数" width="120" align="center" />
            </el-table>
          </el-card>
        </div>
      </el-col>

      <!-- 右边：灿灿 -->
      <el-col :span="12">
        <div class="h-full">
          <h2 class="text-2xl font-bold mb-5 text-center p-2.5 bg-linear-to-br from-[#667eea] to-[#764ba2] text-white rounded-lg">灿灿</h2>

          <!-- 任务统计 -->
          <el-row :gutter="15" class="mb-5">
            <el-col :span="12">
              <el-card class="h-24">
                <div class="flex items-center gap-3.75">
                  <div class="w-12 h-12 rounded-[10px] flex items-center justify-center text-2xl text-white bg-linear-to-br from-[#4facfe] to-[#00f2fe]">
                    <el-icon><CircleCheck /></el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-2xl font-bold text-[#303133] mb-1">{{ cancanStats.taskCount }}</div>
                    <div class="text-xs text-[#909399]">完成任务数</div>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card class="h-24">
                <div class="flex items-center gap-3.75">
                  <div class="w-12 h-12 rounded-[10px] flex items-center justify-center text-2xl text-white bg-linear-to-br from-[#43e97b] to-[#38f9d7]">
                    <el-icon><Coin /></el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-2xl font-bold text-[#303133] mb-1">{{ cancanStats.taskIncome }}</div>
                    <div class="text-xs text-[#909399]">任务收益</div>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <!-- 抽奖统计 -->
          <el-row :gutter="15" class="mb-5">
            <el-col :span="12">
              <el-card class="h-24">
                <div class="flex items-center gap-3.75">
                  <div class="w-12 h-12 rounded-[10px] flex items-center justify-center text-2xl text-white bg-linear-to-br from-[#667eea] to-[#764ba2]">
                    <el-icon><Present /></el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-2xl font-bold text-[#303133] mb-1">{{ cancanStats.lotteryCount }}</div>
                    <div class="text-xs text-[#909399]">抽奖次数</div>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card class="h-24">
                <div class="flex items-center gap-3.75">
                  <div class="w-12 h-12 rounded-[10px] flex items-center justify-center text-2xl text-white bg-linear-to-br from-[#f093fb] to-[#f5576c]">
                    <el-icon><Money /></el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-2xl font-bold text-[#303133] mb-1">{{ cancanStats.lotteryCost }}</div>
                    <div class="text-xs text-[#909399]">抽奖花费</div>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <!-- 后台操作统计（与昭昭共用） -->
          <el-row :gutter="15" class="mb-5">
            <el-col :span="12">
              <el-card class="h-24">
                <div class="flex items-center gap-3.75">
                  <div class="w-12 h-12 rounded-[10px] flex items-center justify-center text-2xl text-white bg-linear-to-br from-[#fa709a] to-[#fee140]">
                    <el-icon><Setting /></el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-2xl font-bold text-[#303133] mb-1">{{ appAdminStats.taskCount }}</div>
                    <div class="text-xs text-[#909399]">后台操作数</div>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card class="h-24">
                <div class="flex items-center gap-3.75">
                  <div class="w-12 h-12 rounded-[10px] flex items-center justify-center text-2xl text-white bg-linear-to-br from-[#30cfd0] to-[#330867]">
                    <el-icon><TrendCharts /></el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-2xl font-bold text-[#303133] mb-1">{{ appAdminStats.taskIncome }}</div>
                    <div class="text-xs text-[#909399]">操作汇总</div>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <el-card class="mt-5">
            <template #header>
              <div class="text-base font-bold">
                <span>各分类中奖统计</span>
              </div>
            </template>
            <el-table :data="cancanCategoryStats" stripe style="width: 100%">
              <el-table-column prop="cate_name" label="分类名称" />
              <el-table-column prop="win_count" label="中奖次数" width="120" align="center" />
            </el-table>
          </el-card>
        </div>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Present, Money, CircleCheck, Coin, Setting, TrendCharts } from "@element-plus/icons-vue";
import { getList } from "@/api/api-common";
import type { ScoreHistory } from "@/api/api-score";
import { ElMessage } from "element-plus";
import dayjs from "dayjs";

interface CategoryStat {
  cate_id: number | null;
  cate_name: string;
  win_count: number;
  total_cost: number;
}

// 日期快捷选项
const shortcuts = [
  {
    text: '最近一周',
    value: () => {
      const end = new Date();
      const start = new Date();
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 7);
      return [start, end];
    },
  },
  {
    text: '最近二周',
    value: () => {
      const end = new Date();
      const start = new Date();
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 14);
      return [start, end];
    },
  },
  {
    text: '最近一个月',
    value: () => {
      const end = new Date();
      const start = new Date();
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 30);
      return [start, end];
    },
  },
  {
    text: '最近三个月',
    value: () => {
      const end = new Date();
      const start = new Date();
      start.setTime(start.getTime() - 3600 * 1000 * 24 * 90);
      return [start, end];
    },
  },
];

// 默认日期范围：最近一周
const endDate = dayjs().format("YYYY-MM-DD");
const startDate = dayjs().subtract(30, "day").format("YYYY-MM-DD");
const dateRange = ref<[string, string]>([startDate, endDate]);
const loading = ref(false);

// 昭昭的统计数据
const ZHAOZHAO_USER_ID = 4;
const zhaozhaoStats = ref({
  lotteryCount: 0,
  lotteryCost: 0,
  taskCount: 0,
  taskIncome: 0,
});
const zhaozhaoCategoryStats = ref<CategoryStat[]>([]);

// 灿灿的统计数据
const CANCAN_USER_ID = 3;
const cancanStats = ref({
  lotteryCount: 0,
  lotteryCost: 0,
  taskCount: 0,
  taskIncome: 0,
});
const cancanCategoryStats = ref<CategoryStat[]>([]);

// appAdmin 的统计数据
const APPADMIN_USER_ID = 1;
const appAdminStats = ref({
  taskCount: 0,
  taskIncome: 0,
});

// 处理日期变化
const handleDateChange = () => {
  // 日期变化时自动刷新统计
  refreshStatistics();
};

// 重置筛选条件
const resetFilters = () => {
  const endDate = dayjs().format("YYYY-MM-DD");
  const startDate = dayjs().subtract(7, "day").format("YYYY-MM-DD");
  dateRange.value = [startDate, endDate];
  refreshStatistics();
};

// 获取所有积分历史记录
const fetchScoreHistory = async (userId: number): Promise<ScoreHistory[]> => {
  const conditions: Record<string, any> = {
    user_id: userId,
  };

  // 日期筛选（后端过滤）
  if (dateRange.value && dateRange.value.length === 2) {
    const startDate = dateRange.value[0];
    const endDate = dateRange.value[1] + " 23:59:59";
    conditions.dt = { ">=": startDate, "<=": endDate };
  }

  try {
    const response = await getList<ScoreHistory>("t_score_history", conditions, 1, 10000);
    if (response.code === 0) {
      return response.data.data || [];
    } else {
      ElMessage.error(response.msg || "获取数据失败");
      return [];
    }
  } catch (error) {
    console.error("获取积分历史失败:", error);
    ElMessage.error("获取数据失败");
    return [];
  }
};

// 获取礼物信息映射
const fetchGiftMap = async (): Promise<Map<number, { name: string; cate_id: number; cate_name: string }>> => {
  try {
    const response = await getList<any>("t_gift", undefined, 1, 10000);
    if (response.code === 0) {
      const gifts = response.data.data || [];
      const giftMap = new Map();

      // 同时获取分类信息
      const cateResponse = await getList<any>("t_gift_category", undefined, 1, 1000);
      const cateMap = new Map();
      if (cateResponse.code === 0) {
        const categories = cateResponse.data.data || [];
        categories.forEach((cate: any) => {
          cateMap.set(cate.id, cate.name);
        });
      }

      gifts.forEach((gift: any) => {
        giftMap.set(gift.id, {
          name: gift.name,
          cate_id: gift.cate_id,
          cate_name: cateMap.get(gift.cate_id) || `分类${gift.cate_id}`,
        });
      });

      return giftMap;
    }
  } catch (error) {
    console.error("获取礼物信息失败:", error);
  }
  return new Map();
};

// 统计单个用户的数据
const calculateUserStats = (
  historyList: ScoreHistory[],
  giftMap: Map<number, { name: string; cate_id: number; cate_name: string }>
) => {
  let lotteryCount = 0;
  let lotteryCost = 0;
  let taskCount = 0;
  let taskIncome = 0;
  const categoryWinMap = new Map<number | null, { win_count: number; total_cost: number; cate_name: string }>();

  // 遍历历史记录进行统计
  historyList.forEach((record) => {
    const action = record.action;
    const value = record.value;

    // 统计抽奖
    if (action === "lottery") {
      lotteryCount++;
      lotteryCost += Math.abs(value); // value是负数，取绝对值

      // 统计各分类中奖次数
      if (record.out_key) {
        const giftIds = record.out_key.split(",").map((id) => parseInt(id.trim())).filter((id) => !isNaN(id));
        giftIds.forEach((giftId) => {
          const giftInfo = giftMap.get(giftId);
          if (giftInfo) {
            const cateId = giftInfo.cate_id;
            if (!categoryWinMap.has(cateId)) {
              categoryWinMap.set(cateId, {
                win_count: 0,
                total_cost: 0,
                cate_name: giftInfo.cate_name,
              });
            }
            const stat = categoryWinMap.get(cateId)!;
            stat.win_count++;
            stat.total_cost += Math.abs(value / giftIds.length); // 按比例分配花费
          }
        });
      }
    }

    // 统计兑换
    if (action === "exchange") {
      lotteryCount++;
      lotteryCost += Math.abs(value);

      // 统计各分类中奖次数
      if (record.out_key) {
        const giftId = parseInt(record.out_key);
        if (!isNaN(giftId)) {
          const giftInfo = giftMap.get(giftId);
          if (giftInfo) {
            const cateId = giftInfo.cate_id;
            if (!categoryWinMap.has(cateId)) {
              categoryWinMap.set(cateId, {
                win_count: 0,
                total_cost: 0,
                cate_name: giftInfo.cate_name,
              });
            }
            const stat = categoryWinMap.get(cateId)!;
            stat.win_count++;
            stat.total_cost += Math.abs(value);
          }
        }
      }
    }

    // 统计任务
    if (action === "schedule") {
      if (value > 0) {
        taskCount++;
        taskIncome += value;
      }
    }
  });

  // 更新分类统计
  const categoryStats = Array.from(categoryWinMap.entries())
    .map(([cateId, stat]) => ({
      cate_id: cateId,
      cate_name: stat.cate_name,
      win_count: stat.win_count,
      total_cost: Math.round(stat.total_cost * 100) / 100,
    }))
    .sort((a, b) => b.win_count - a.win_count);

  return {
    stats: {
      lotteryCount,
      lotteryCost,
      taskCount,
      taskIncome,
    },
    categoryStats,
  };
};

// 刷新统计数据
const refreshStatistics = async () => {
  loading.value = true;
  try {
    const giftMap = await fetchGiftMap();

    // 并行获取三个用户的数据
    const [zhaozhaoHistory, cancanHistory, appAdminHistory] = await Promise.all([
      fetchScoreHistory(ZHAOZHAO_USER_ID),
      fetchScoreHistory(CANCAN_USER_ID),
      fetchScoreHistory(APPADMIN_USER_ID),
    ]);

    // 计算昭昭的统计
    const zhaozhaoResult = calculateUserStats(zhaozhaoHistory, giftMap);
    zhaozhaoStats.value = zhaozhaoResult.stats;
    zhaozhaoCategoryStats.value = zhaozhaoResult.categoryStats;

    // 计算灿灿的统计
    const cancanResult = calculateUserStats(cancanHistory, giftMap);
    cancanStats.value = cancanResult.stats;
    cancanCategoryStats.value = cancanResult.categoryStats;

    // 计算 appAdmin 的统计（只统计任务）
    let appAdminTaskCount = 0;
    let appAdminTaskIncome = 0;
    appAdminHistory.forEach((record) => {
      if (record.action === "schedule" && record.value > 0) {
        appAdminTaskCount++;
        appAdminTaskIncome += record.value;
      }
    });
    appAdminStats.value = {
      taskCount: appAdminTaskCount,
      taskIncome: appAdminTaskIncome,
    };
  } catch (error) {
    console.error("统计失败:", error);
    ElMessage.error("统计失败");
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  refreshStatistics();
});
</script>
