<template>
  <el-card class="w-[480px]" shadow="always">
    <template #header>用户登录</template>
    <div class="flex flex-col gap-2 items-center">
      <el-select v-model="user.id" placeholder="Select" class="!w-60">
        <el-option
          class="!h-13"
          v-for="item in userList"
          :key="item.id"
          :label="item.name"
          :value="item.id">
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
        show-password></el-input>
      <el-button
        type="primary"
        size="large"
        class="w-24 h-24 mt-4"
        :disabled="!user.id"
        @click="handleLogin">
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
const user = ref({
  id: null,
  password: "",
});

const refreshUserList = async () => {
  try {
    const data = await getList("t_user");
    Object.assign(userList.value, data.data);
  } catch (error) {
    console.error("获取用户列表失败:", error);
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

