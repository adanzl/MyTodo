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

<script setup>
import { ref, onMounted, inject } from "vue";
import { ElMessage } from "element-plus";
import CryptoJS from "crypto-js";
import _ from "lodash-es";
import { getList } from "@/api/common";

const emit = defineEmits(["login-success"]);

const userList = ref([]);
const loading = ref(false);
const user = ref({
  id: null,
  password: "",
});

const refreshUserList = async () => {
  loading.value = true;
  try {
    const response = await getList("t_user");
    if (response && response.data) {
      // API 返回的是分页格式，用户数组在 response.data.data 中
      const users = response.data.data || response.data;
      userList.value = Array.isArray(users) ? users : [];
      if (userList.value.length === 0) {
        ElMessage.warning("用户列表为空，请检查数据库");
      }
    } else {
      userList.value = [];
      ElMessage.error("获取用户列表失败：数据格式错误");
    }
  } catch (error) {
    userList.value = [];
    const errorMsg = error?.response?.data?.msg || error?.message || String(error);
    ElMessage.error(`获取用户列表失败: ${errorMsg}`);
  } finally {
    loading.value = false;
  }
};

const handleLogin = async () => {
  if (!user.value.id) return;

  const uu = _.find(userList.value, { id: user.value.id });
  if (uu && (uu.pwd === null || uu.pwd === CryptoJS.MD5(user.value.password).toString())) {
    const userInfo = {
      bLogin: true,
      id: uu.id,
      name: uu.name,
      ico: uu.icon,
    };
    localStorage.setItem("user_id", uu.id);
    emit("login-success", userInfo);
  } else {
    ElMessage.error("用户名或密码错误");
  }
};

onMounted(async () => {
  await refreshUserList();
});
</script>

<style scoped>
/* 样式将在后续迁移中完善 */
</style>
