<template>
  <div class="p-1">
    <!-- 配置区域 -->
     <el-card>
       <div class="flex flex-wrap items-end gap-2 mb-2">
         <div class="flex items-center">
           <el-text class="w-24">普通抽奖费用</el-text>
           <el-input v-model="lotterySettingData.fee" class="w-32! ml-2" type="number" />
         </div>
         <div class="flex items-center">
           <el-text class="w-28">心愿单阈值</el-text>
           <el-input v-model.number="lotterySettingData.wish_count_threshold" class="w-32! ml-2" type="number" placeholder="5" />
           <el-tooltip content="进度达到后下一抽仅从心愿单池抽取并清零" placement="top">
             <el-icon class="ml-1 cursor-help text-gray-400 hover:text-gray-600"><InfoFilled /></el-icon>
           </el-tooltip>
         </div>
         <el-button type="primary" @click="handleUpdateFee">更新配置</el-button>
       </div>
     </el-card>

    <!-- 主页签 -->
    <el-tabs
      v-model="activeMainTab"
      @tab-change="handleTabChange"
      class="flex-1 flex flex-col overflow-hidden h-[calc(100vh-220px)] mt-2"
    >
      <!-- 礼物维护页签 -->
      <el-tab-pane label="礼物维护" name="lottery">
        <TabLottery />
      </el-tab-pane>

      <!-- 奖池维护页签 -->
      <el-tab-pane label="奖池维护" name="pool">
        <TabPool />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { InfoFilled } from "@element-plus/icons-vue";
import { getLotterySetting, setLotterySetting } from "@/api/api-lottery";
import TabLottery from "./TabLottery.vue";
import TabPool from "./TabPool.vue";

// 主页签控制
const activeMainTab = ref("lottery");

// 监听页签切换
const handleTabChange = (tabName: string) => {
  // 页签切换时的处理逻辑（如果需要）
  console.log("切换到页签:", tabName);
};

// 配置数据
const lotterySettingData = ref({ fee: 10, wish_count_threshold: 5 });

// 更新配置
const handleUpdateFee = async () => {
  try {
    await setLotterySetting({
      fee: lotterySettingData.value.fee,
      wish_count_threshold: lotterySettingData.value.wish_count_threshold ?? 5,
    });
    ElMessage.success("已更新：普通抽奖费用、心愿单阈值");
  } catch (error) {
    console.error("更新配置失败:", error);
    ElMessage.error("更新配置失败");
  }
};

// 获取配置
const getLotterySettingLocal = async () => {
  try {
    const setting = await getLotterySetting();
    lotterySettingData.value = setting;
  } catch (error) {
    console.error("获取抽奖设置失败:", error);
  }
};

onMounted(async () => {
  await getLotterySettingLocal();
});
</script>
