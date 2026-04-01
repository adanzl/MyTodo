<template>
  <div class="">
    <!-- 增加刷新数据按钮 -->
    <div class="mb-4">
      <el-button @click="refreshUserList" type="primary" :loading="loading">
        <el-icon><Refresh /></el-icon>
        刷新数据
      </el-button>
    </div>
    <el-table :data="userList" stripe class="w-full" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column label="Icon" width="100">
        <template #default="scope">
          <el-avatar :src="scope.row.icon" />
        </template>
      </el-table-column>
      <el-table-column prop="name" label="Name" width="100" />
      <el-table-column prop="admin" label="Admin" width="100" class="items-center text-center" />
      <el-table-column label="WProgress" width="120" class="items-center text-center">
        <template #default="{ row }">
          <div class="flex justify-end px-2">
            <span class="text-[10px] text-gray-600">{{ row.wish_progress }} / {{ wishCountThreshold }}</span>
          </div>
          <el-progress
            :text-inside="true"
            :stroke-width="16"
            :percentage="calculateProgress(row.wish_progress)"
          />
        </template>
      </el-table-column>
      <el-table-column
        prop="wish_list"
        label="WList"
        width="150"
        class="items-center text-center"
        show-overflow-tooltip
      >
      </el-table-column>
      <el-table-column prop="score" label="Score" width="100">
        <template #default="{ row }">
          <el-input v-model="row.score" size="small" />
        </template>
      </el-table-column>
      <el-table-column label="Operations">
        <template #default="{ row }">
          <el-button class="w-16" @click="handleUpdateUser(row)" type="primary"> Update </el-button>
          <el-button class="w-16" @click="onAddScoreBtnClick(row)"> Score </el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-dialog
      v-model="dialogForm.visible"
      title="Change Score"
      width="600"
      :before-close="handleDialogClose"
    >
      <span>输入的积分会作用在当前积分上，输入负数则会减少积分</span>
      <div v-if="dialogForm.data">
        {{ dialogForm.data.name }} 当前积分: {{ dialogForm.data.score }}
      </div>
      <div class="flex mt-4">
        <el-input v-model="dialogForm.value" style="width: 240px" placeholder="Please input" />

        <el-button @click="handleAddScore()" class="ml-2 w-16" type="primary"> Submit </el-button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { ElMessage } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import { setUserInfo, addScore } from "@/api/user";
import { getLotterySetting } from "@/api/api-lottery";
import { useUserStore, type UserWithExtras } from "@/stores/user";

// 使用 Pinia Store
const userStore = useUserStore();

// 从 store 获取用户列表（响应式）
const userList = computed(() => userStore.userList);
const loading = computed(() => userStore.loading);

// 心愿单阈值配置
const wishCountThreshold = ref<number>(5); // 默认值

// 计算进度百分比
const calculateProgress = (wishProgress?: number): number => {
  if (!wishProgress || wishProgress < 0) return 0;
  const percentage = Math.floor((wishProgress / wishCountThreshold.value) * 100);
  return Math.min(percentage, 100); // 最大不超过 100%
};

// 获取抽奖配置
const getLotterySettingLocal = async () => {
  try {
    const setting = await getLotterySetting();
    wishCountThreshold.value = setting.wish_count_threshold;
  } catch (error) {
    console.error("获取抽奖设置失败:", error);
  }
};

const dialogForm = ref<{
  visible: boolean;
  data: UserWithExtras | null;
  value: number;
}>({
  visible: false,
  data: null,
  value: 0,
});

const refreshUserList = async () => {
  // 使用 store 刷新用户列表（会自动处理缓存）
  await userStore.refreshUserList();
};

const handleUpdateUser = async (item: UserWithExtras) => {
  try {
    const data = {
      id: item.id,
      score: item.score,
    };
    await setUserInfo(data.id, data.score);
    console.log("update user", data);
    await refreshUserList();
  } catch (error) {
    console.error("更新用户失败:", error);
    ElMessage.error("更新用户失败");
  }
};

const onAddScoreBtnClick = (item: UserWithExtras) => {
  dialogForm.value.visible = true;
  dialogForm.value.data = item;
};

const handleAddScore = async () => {
  if (!dialogForm.value.data) {
    ElMessage.warning("请选择用户");
    return;
  }
  try {
    await addScore(dialogForm.value.data.id, "pcAdmin", dialogForm.value.value, "管理后台变更");
    await refreshUserList();
    dialogForm.value.visible = false;
    dialogForm.value.value = 0;
  } catch (error) {
    console.error("添加积分失败:", error);
    ElMessage.error("添加积分失败");
  }
};

const handleDialogClose = () => {
  dialogForm.value.visible = false;
  dialogForm.value.value = 0;
};

onMounted(async () => {
  // 先获取配置数据
  await getLotterySettingLocal();
  // 如果 Store 已经有数据且数据新鲜，就不需要重复请求
  // Store 的 refreshUserList 会自动处理缓存
  await refreshUserList();
});
</script>

<style scoped></style>
