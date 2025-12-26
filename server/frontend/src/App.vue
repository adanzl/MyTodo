<template>
  <el-container :loading="loading" class="h-screen">
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

<script setup>
import { ref, onMounted, provide } from "vue";
import { StarFilled } from "@element-plus/icons-vue";
import _ from "lodash-es";
import Sidebar from "@/components/layout/Sidebar.vue";
import Login from "@/components/layout/Login.vue";
import { getList } from "@/api/common";

const KEY_USER_ID = "user_id";
const loading = ref(false);
const curUser = ref({ bLogin: false, id: null, name: null, ico: null });
const userList = ref([]);

// 提供给子组件使用
provide("curUser", curUser);

const handleLoginSuccess = userInfo => {
  curUser.value = { ...userInfo, bLogin: true };
  window.curUser = curUser.value;
};

const refreshUserList = async () => {
  loading.value = true;
  try {
    const response = await getList("t_user");
    if (response && response.data) {
      // API 返回的是分页格式，用户数组在 response.data.data 中
      const users = response.data.data || response.data;
      userList.value = Array.isArray(users) ? users : [];
    } else {
      userList.value = [];
    }
  } catch (error) {
    console.error("获取用户列表失败:", error);
    userList.value = [];
  } finally {
    loading.value = false;
  }
};

onMounted(async () => {
  await refreshUserList();
  const uId = localStorage.getItem(KEY_USER_ID);
  if (uId) {
    const u = _.find(userList.value, item => item.id == uId);
    if (u) {
      curUser.value.bLogin = true;
      curUser.value.id = u.id;
      curUser.value.name = u.name;
      curUser.value.ico = u.icon;
      window.curUser = curUser.value;
    }
  }
});
</script>

<style scoped>
/* 样式将在后续迁移中完善 */
</style>
