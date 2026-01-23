<template>
  <el-card class="w-[480px]" shadow="always">
    <template #header>用户登录</template>
    <div class="flex flex-col gap-2 items-center">
      <el-select
        v-model="user.id"
        placeholder="请选择用户"
        class="!w-60"
        :loading="loading"
        loading-text="加载用户列表中..."
        :disabled="loading"
      >
        <el-option
          class="!h-13"
          v-for="item in userList"
          :key="item.id"
          :label="item.name"
          :value="item.id"
        >
          <div class="flex items-center border-b-1 border-gray-200">
            <el-avatar class="!h-10 !w-10" :src="item.icon"></el-avatar>
            <div class="pl-4 text-base text-gray-500">{{ item.name }}</div>
          </div>
        </el-option>
      </el-select>
      <el-input
        v-model="user.password"
        style="width: 240px"
        type="password"
        placeholder="Password"
        show-password
      ></el-input>
      <el-button
        type="primary"
        size="large"
        class="w-24 h-24 mt-4"
        :disabled="!user.id"
        @click="handleLogin"
      >
        Login
      </el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { ElMessage } from "element-plus";
import { useUserStore } from "@/stores/user";
import { login as apiLogin } from "@/api/auth";

const emit = defineEmits<{
  "login-success": [userInfo: { id: number; name: string; icon: string }];
}>();

// 使用 Pinia Store
const userStore = useUserStore();
const userList = computed(() => userStore.userList);
const loading = computed(() => userStore.loading);

const user = ref<{
  id: number | null;
  password: string;
}>({
  id: null,
  password: "",
});

const refreshUserList = async () => {
  // 使用 Pinia Store（会自动处理缓存）
  await userStore.refreshUserList();
  // userList 已经是 computed，会自动响应 Store 的变化
  if (userList.value.length === 0) {
    ElMessage.warning("用户列表为空，请检查数据库");
  }
};

const handleLogin = async () => {
  if (!user.value.id) return;

  const uu = userList.value.find(u => u.id === user.value.id);
  if (!uu) return;

  try {
    const resp = await apiLogin(uu.name, user.value.password);
    if (resp.code !== 0) {
      ElMessage.error(resp.msg || "用户名或密码错误");
      return;
    }

    userStore.setCurUser({
      ...uu,
      icon: resp.user.icon || uu.icon,
    });

    emit("login-success", {
      id: resp.user.id,
      name: resp.user.name,
      icon: resp.user.icon || uu.icon,
    });
  } catch (e: any) {
    ElMessage.error(e?.message || "登录失败");
  }
};

onMounted(async () => {
  await refreshUserList();
});
</script>

<style scoped>
/* 样式将在后续迁移中完善 */
</style>

