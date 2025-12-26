<template>
  <el-container :loading="loading">
    <Sidebar />
    <el-container v-if="curUser.bLogin">
      <el-header class="flex justify-center items-center bg-blue-50">
        <ion-icon name="heart"></ion-icon>
        哈哈哈
        <ion-icon name="heart"></ion-icon>
      </el-header>
      <el-main>
        <router-view></router-view>
      </el-main>
    </el-container>
    <el-container v-else>
      <el-main class="bg-blue-100 !flex justify-center items-center h-screen">
        <Login @login-success="handleLoginSuccess" />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, onMounted, provide } from "vue";
import Sidebar from "@/components/layout/Sidebar.vue";
import Login from "@/components/layout/Login.vue";

const KEY_USER_ID = "user_id";
const loading = ref(false);
const curUser = ref({ bLogin: false, id: null, name: null, ico: null });

// 提供给子组件使用
provide("curUser", curUser);

const handleLoginSuccess = (userInfo) => {
  curUser.value = { ...userInfo, bLogin: true };
  window.curUser = curUser.value;
};

onMounted(async () => {
  const uId = localStorage.getItem(KEY_USER_ID);
  if (uId) {
    // 这里需要从用户列表中查找用户信息
    // 暂时先设置登录状态
    curUser.value.bLogin = true;
  }
});
</script>

<style scoped>
/* 样式将在后续迁移中完善 */
</style>
