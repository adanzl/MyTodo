<template>
  <el-container :loading="userStore.loading" class="h-screen">
    <Sidebar />
    <el-container v-if="curUser.bLogin">
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
import { ref, onMounted, provide, computed } from "vue";
import { StarFilled } from "@element-plus/icons-vue";
import Sidebar from "@/components/layout/Sidebar.vue";
import Login from "@/components/layout/Login.vue";
import { useUserStore, type UserWithExtras } from "@/stores/user";

interface CurUser {
  bLogin: boolean;
  id: number | null;
  name: string | null;
  ico: string | null;
}

interface WindowWithCurUser extends Window {
  curUser?: UserWithExtras;
}

const KEY_USER_ID = "user_id";
const curUser = ref<CurUser>({ bLogin: false, id: null, name: null, ico: null });

// 使用 Pinia Store
const userStore = useUserStore();

// 提供给子组件使用（保持向后兼容）
provide("curUser", curUser);
provide(
  "userList",
  computed(() => userStore.userList)
);

const handleLoginSuccess = (userInfo: { id: number; name: string; icon: string }) => {
  // 从 Store 中获取完整的用户信息
  const fullUserInfo = userStore.getUserById(userInfo.id);
  if (fullUserInfo) {
    curUser.value = {
      bLogin: true,
      id: fullUserInfo.id,
      name: fullUserInfo.name,
      ico: fullUserInfo.icon,
    };
    (window as WindowWithCurUser).curUser = fullUserInfo;
  } else {
    // 如果 Store 中没有，使用传入的信息
  curUser.value = {
    bLogin: true,
    id: userInfo.id,
    name: userInfo.name,
    ico: userInfo.icon,
  };
  }
};

onMounted(async () => {
  // 使用 store 刷新用户列表
  await userStore.refreshUserList();
  const uId = localStorage.getItem(KEY_USER_ID);
  if (uId) {
    const u = userStore.getUserById(uId);
    if (u) {
      curUser.value.bLogin = true;
      curUser.value.id = u.id;
      curUser.value.name = u.name;
      curUser.value.ico = u.icon;
      (window as WindowWithCurUser).curUser = u;
    }
  }
});
</script>

<style scoped>
/* 样式将在后续迁移中完善 */
</style>
