<template>
  <div class="p-5" v-loading="loading" element-loading-text="加载中..."
    element-loading-background="rgba(255, 255, 255, 0.8)">
    <el-card class="mb-0">
      <el-form :inline="true" class="flex flex-wrap gap-2">
        <el-form-item label="日期范围" class="mb-0!">
          <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期"
            end-placeholder="结束日期" value-format="YYYY-MM-DD" unlink-panels :shortcuts="shortcuts"
            @change="handleDateChange" />
        </el-form-item>
        <el-form-item class="mb-0!">
          <el-button type="primary" @click="refreshStatistics">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-row :gutter="20" class="mt-5">
      <!-- 左边：昭昭 -->
      <el-col :span="12">
        <div class="h-full">
          <h2
            class="text-2xl font-bold text-white mb-5 text-center p-2.5 bg-linear-to-br from-[#667eea] to-[#764ba2] rounded-lg">
            昭昭</h2>

          <!-- 任务统计 -->
          <el-row :gutter="15" class="mb-5">
            <el-col :span="8">
              <el-card class="h-22">
                <div class="flex items-center gap-2">
                  <div
                    class="w-8 h-8 rounded-lg flex items-center justify-center text-lg text-white bg-linear-to-br from-[#4facfe] to-[#00f2fe]">
                    <el-icon>
                      <CircleCheck />
                    </el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-lg font-bold text-[#303133] mb-0">{{ zhaozhaoStats.taskCount }}</div>
                    <div class="text-xs text-[#909399]">任务完成数</div>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card class="h-22">
                <div class="flex items-center gap-2">
                  <div
                    class="w-8 h-8 rounded-lg flex items-center justify-center text-lg text-white bg-linear-to-br from-[#43e97b] to-[#38f9d7]">
                    <el-icon>
                      <Coin />
                    </el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-lg font-bold text-[#303133] mb-0">{{ zhaozhaoStats.taskIncome }}</div>
                    <div class="text-xs text-[#909399]">获得星星</div>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card class="h-22">
                <div class="flex items-center gap-2">
                  <div
                    class="w-8 h-8 rounded-lg flex items-center justify-center text-lg text-white bg-linear-to-br from-[#667eea] to-[#764ba2]">
                    <el-icon>
                      <Present />
                    </el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-lg font-bold text-[#303133] mb-0">{{ zhaozhaoStats.lotteryCount }}</div>
                    <div class="text-xs text-[#909399]">抽奖次数</div>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <el-row :gutter="15" class="mb-5">
            <el-col :span="8">
              <el-card class="h-22">
                <div class="flex items-center gap-2">
                  <div
                    class="w-8 h-8 rounded-lg flex items-center justify-center text-lg text-white bg-linear-to-br from-[#f093fb] to-[#f5576c]">
                    <el-icon>
                      <Money />
                    </el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-lg font-bold text-[#303133] mb-0">{{ zhaozhaoStats.lotteryCost }}</div>
                    <div class="text-xs text-[#909399]">抽奖花费</div>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card class="h-22">
                <div class="flex items-center gap-2">
                  <div
                    class="w-8 h-8 rounded-lg flex items-center justify-center text-lg text-white bg-linear-to-br from-[#fa709a] to-[#fee140]">
                    <el-icon>
                      <ShoppingCart />
                    </el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-lg font-bold text-[#303133] mb-0">{{ zhaozhaoStats.exchangeCount }}</div>
                    <div class="text-xs text-[#909399]">兑换次数</div>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card class="h-22">
                <div class="flex items-center gap-2">
                  <div
                    class="w-8 h-8 rounded-lg flex items-center justify-center text-lg text-white bg-linear-to-br from-[#ffecd2] to-[#fcb69f]">
                    <el-icon>
                      <Wallet />
                    </el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-lg font-bold text-[#303133] mb-0">{{ zhaozhaoStats.exchangeCost }}</div>
                    <div class="text-xs text-[#909399]">兑换花费</div>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <el-row :gutter="15" class="mb-5">
            <el-col :span="8">
              <el-card class="h-22">
                <div class="flex items-center gap-2">
                  <div
                    class="w-8 h-8 rounded-lg flex items-center justify-center text-lg text-white bg-linear-to-br from-[#fa709a] to-[#fee140]">
                    <el-icon>
                      <Setting />
                    </el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-lg font-bold text-[#303133] mb-0">{{ zhaozhaoStats.adminCount }}</div>
                    <div class="text-xs text-[#909399]">后台操作数</div>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card class="h-22">
                <div class="flex items-center gap-2">
                  <div
                    class="w-8 h-8 rounded-lg flex items-center justify-center text-lg text-white bg-linear-to-br from-[#30cfd0] to-[#330867]">
                    <el-icon>
                      <TrendCharts />
                    </el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-lg font-bold text-[#303133] mb-0">{{ zhaozhaoStats.adminIncome }}</div>
                    <div class="text-xs text-[#909399]">操作汇总</div>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <el-card class="mt-5">
            <template #header>
              <div class="text-base font-bold">
                <span>分类中奖统计</span>
              </div>
            </template>
            <el-table :data="zhaozhaoCategoryStats" stripe style="width: 100%" @row-click="handleCategoryClick">
              <el-table-column prop="cate_name" label="分类名称" />
              <el-table-column prop="gift_types" label="礼物种类" width="120" align="center" />
              <el-table-column prop="win_count" label="中奖次数" width="120" align="center" />
              <el-table-column prop="total_exchange_price" label="兑换总价" width="140" align="center" />
            </el-table>
          </el-card>
        </div>
      </el-col>

      <!-- 右边：灿灿 -->
      <el-col :span="12">
        <div class="h-full">
          <h2
            class="text-2xl font-bold mb-5 text-center p-2.5 bg-linear-to-br from-[#667eea] to-[#764ba2] text-white rounded-lg">
            灿灿</h2>

          <!-- 任务统计 -->
          <el-row :gutter="15" class="mb-5">
            <el-col :span="8">
              <el-card class="h-22">
                <div class="flex items-center gap-2">
                  <div
                    class="w-8 h-8 rounded-lg flex items-center justify-center text-lg text-white bg-linear-to-br from-[#4facfe] to-[#00f2fe]">
                    <el-icon>
                      <CircleCheck />
                    </el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-lg font-bold text-[#303133] mb-0">{{ cancanStats.taskCount }}</div>
                    <div class="text-xs text-[#909399]">完成任务数</div>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card class="h-22">
                <div class="flex items-center gap-2">
                  <div
                    class="w-8 h-8 rounded-lg flex items-center justify-center text-lg text-white bg-linear-to-br from-[#43e97b] to-[#38f9d7]">
                    <el-icon>
                      <Coin />
                    </el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-lg font-bold text-[#303133] mb-0">{{ cancanStats.taskIncome }}</div>
                    <div class="text-xs text-[#909399]">获得星星</div>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card class="h-22">
                <div class="flex items-center gap-2">
                  <div
                    class="w-8 h-8 rounded-lg flex items-center justify-center text-lg text-white bg-linear-to-br from-[#667eea] to-[#764ba2]">
                    <el-icon>
                      <Present />
                    </el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-lg font-bold text-[#303133] mb-0">{{ cancanStats.lotteryCount }}</div>
                    <div class="text-xs text-[#909399]">抽奖次数</div>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <el-row :gutter="15" class="mb-5">
            <el-col :span="8">
              <el-card class="h-22">
                <div class="flex items-center gap-2">
                  <div
                    class="w-8 h-8 rounded-lg flex items-center justify-center text-lg text-white bg-linear-to-br from-[#f093fb] to-[#f5576c]">
                    <el-icon>
                      <Money />
                    </el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-lg font-bold text-[#303133] mb-0">{{ cancanStats.lotteryCost }}</div>
                    <div class="text-xs text-[#909399]">抽奖花费</div>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card class="h-22">
                <div class="flex items-center gap-2">
                  <div
                    class="w-8 h-8 rounded-lg flex items-center justify-center text-lg text-white bg-linear-to-br from-[#fa709a] to-[#fee140]">
                    <el-icon>
                      <ShoppingCart />
                    </el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-lg font-bold text-[#303133] mb-0">{{ cancanStats.exchangeCount }}</div>
                    <div class="text-xs text-[#909399]">兑换次数</div>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card class="h-22">
                <div class="flex items-center gap-2">
                  <div
                    class="w-8 h-8 rounded-lg flex items-center justify-center text-lg text-white bg-linear-to-br from-[#ffecd2] to-[#fcb69f]">
                    <el-icon>
                      <Wallet />
                    </el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-lg font-bold text-[#303133] mb-0">{{ cancanStats.exchangeCost }}</div>
                    <div class="text-xs text-[#909399]">兑换花费</div>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <el-row :gutter="15" class="mb-5">
            <el-col :span="8">
              <el-card class="h-22">
                <div class="flex items-center gap-2">
                  <div
                    class="w-8 h-8 rounded-lg flex items-center justify-center text-lg text-white bg-linear-to-br from-[#fa709a] to-[#fee140]">
                    <el-icon>
                      <Setting />
                    </el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-lg font-bold text-[#303133] mb-0">{{ cancanStats.adminCount }}</div>
                    <div class="text-xs text-[#909399]">后台操作数</div>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card class="h-22">
                <div class="flex items-center gap-2">
                  <div
                    class="w-8 h-8 rounded-lg flex items-center justify-center text-lg text-white bg-linear-to-br from-[#30cfd0] to-[#330867]">
                    <el-icon>
                      <TrendCharts />
                    </el-icon>
                  </div>
                  <div class="flex-1">
                    <div class="text-lg font-bold text-[#303133] mb-0">{{ cancanStats.adminIncome }}</div>
                    <div class="text-xs text-[#909399]">操作汇总</div>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <el-card class="mt-5">
            <template #header>
              <div class="text-base font-bold">
                <span>分类中奖统计</span>
              </div>
            </template>
            <el-table :data="cancanCategoryStats" stripe style="width: 100%" @row-click="handleCategoryClick">
              <el-table-column prop="cate_name" label="分类名称" />
              <el-table-column prop="gift_types" label="礼物种类" width="120" align="center" />
              <el-table-column prop="win_count" label="中奖次数" width="120" align="center" />
              <el-table-column prop="total_exchange_price" label="兑换总价" width="140" align="center" />
            </el-table>
          </el-card>
        </div>
      </el-col>
    </el-row>

    <!-- 礼物列表弹窗 -->
    <el-dialog v-model="giftDialogVisible" :title="`${currentCategoryName} - 礼物列表`" width="70%">
      <el-table :data="giftList" stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" align="center" />
        <el-table-column label="图片" width="100" align="center">
          <template #default="{ row }">
            <el-image
              v-if="row.image"
              :src="getPicDisplayUrl(row.image)"
              :preview-src-list="[getPicDisplayUrl(row.image)]"
              :preview-teleported="true"
              fit="cover"
              class="w-15 h-15 cursor-pointer"
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="礼物名称" />
        <el-table-column prop="cost" label="兑换价格" width="120" align="center" />
        <el-table-column label="是否可兑换" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.exchange ? 'success' : 'info'">
              {{ row.exchange ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="count" label="中奖次数" width="120" align="center" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Present, Money, CircleCheck, Coin, Setting, TrendCharts, ShoppingCart, Wallet } from "@element-plus/icons-vue";
import { getUserStats, type CategoryStat, type WonGift } from "@/api/api-stats";
import { getPicDisplayUrl } from "@/api/api-pic";
import { ElMessage } from "element-plus";
import dayjs from "dayjs";

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

// 默认日期范围：最近一个月
const endDate = dayjs().format("YYYY-MM-DD");
const startDate = dayjs().subtract(30, "day").format("YYYY-MM-DD");
const dateRange = ref<[string, string]>([startDate, endDate]);
const loading = ref(false);

// 昭昭的统计数据
const ZHAOZHAO_USER_ID = 4;
const zhaozhaoStats = ref({
  lotteryCount: 0,
  lotteryCost: 0,
  exchangeCount: 0,
  exchangeCost: 0,
  taskCount: 0,
  taskIncome: 0,
  adminCount: 0,
  adminIncome: 0,
});
const zhaozhaoCategoryStats = ref<CategoryStat[]>([]);

// 灿灿的统计数据
const CANCAN_USER_ID = 3;
const cancanStats = ref({
  lotteryCount: 0,
  lotteryCost: 0,
  exchangeCount: 0,
  exchangeCost: 0,
  taskCount: 0,
  taskIncome: 0,
  adminCount: 0,
  adminIncome: 0,
});
const cancanCategoryStats = ref<CategoryStat[]>([]);

// 弹窗相关
const giftDialogVisible = ref(false);
const currentCategoryName = ref("");
const giftList = ref<WonGift[]>([]);

// 处理日期变化
const handleDateChange = () => {
  refreshStatistics();
};

// 重置筛选条件
const resetFilters = () => {
  const endDate = dayjs().format("YYYY-MM-DD");
  const startDate = dayjs().subtract(7, "day").format("YYYY-MM-DD");
  dateRange.value = [startDate, endDate];
  refreshStatistics();
};

// 刷新统计数据
const refreshStatistics = async () => {
  loading.value = true;
  try {
    const startDate = dateRange.value?.[0];
    const endDate = dateRange.value?.[1];

    // 批量获取两个用户的数据
    const result: any = await getUserStats([ZHAOZHAO_USER_ID, CANCAN_USER_ID], startDate, endDate);

    // result 可能是 { code: 0, data: [...] } 或直接是数组
    const dataArray = Array.isArray(result) ? result : (result?.data || []);

    // 找到对应用户的数据
    const zhaozhaoData = dataArray.find((item: any) => item.user_id === ZHAOZHAO_USER_ID);
    const cancanData = dataArray.find((item: any) => item.user_id === CANCAN_USER_ID);

    if (zhaozhaoData) {
      zhaozhaoStats.value = zhaozhaoData.stats;
      zhaozhaoCategoryStats.value = zhaozhaoData.categoryStats;
    }

    if (cancanData) {
      cancanStats.value = cancanData.stats;
      cancanCategoryStats.value = cancanData.categoryStats;
    }
  } catch (error) {
    console.error("统计失败:", error);
    ElMessage.error("统计失败");
  } finally {
    loading.value = false;
  }
};

// 点击分类行，显示礼物列表
const handleCategoryClick = (row: CategoryStat) => {
  currentCategoryName.value = row.cate_name;
  giftList.value = row.won_gifts || [];
  giftDialogVisible.value = true;
};

onMounted(() => {
  refreshStatistics();
});
</script>
