<template>
  <el-container :loading="userStore.loading" class="h-screen">
    <Sidebar />
    <el-container v-if="userStore.curUser.bLogin">
      <el-header class="flex justify-center items-center bg-blue-50">
        <el-icon><StarFilled /></el-icon>
        哈哈哈
        <el-icon><StarFilled /></el-icon>
      </el-header>
      <el-main>
        <router-view></router-view>
      </el-main>
    </el-container>
    <el-container v-else>
      <el-main class="bg-blue-100 !flex justify-center items-center">
        <Login @login-success="handleLoginSuccess" />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { StarFilled } from "@element-plus/icons-vue";
import Sidebar from "@/views/Sidebar.vue";
import Login from "@/views/Login.vue";
import { useUserStore } from "@/stores/user";

// 使用 Pinia Store
const userStore = useUserStore();

const handleLoginSuccess = (userInfo: { id: number; name: string; icon: string }) => {
  // 从 Store 中获取完整的用户信息
  const fullUserInfo = userStore.getUserById(userInfo.id);
  if (fullUserInfo) {
    userStore.setCurUser(fullUserInfo);
  } else {
    // 如果 Store 中没有，创建一个临时用户对象
    // 这种情况理论上不应该发生，因为登录时用户列表应该已经加载
    console.warn("用户信息未找到，使用传入的信息");
    userStore.setCurUser({
      id: userInfo.id,
      name: userInfo.name,
      icon: userInfo.icon,
    } as any);
  }
};

onMounted(async () => {
  // 使用 store 刷新用户列表
  await userStore.refreshUserList();
  // 从 localStorage 恢复当前用户
  await userStore.restoreCurUser();
});
</script>

<style scoped>
/* 样式将在后续迁移中完善 */
</style>
