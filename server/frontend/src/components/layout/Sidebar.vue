<template>
  <el-aside width="200px" class="w-48">
    <el-scrollbar>
      <div class="flex justify-between items-center p-5">
        <el-avatar :src="userStore.curUser.ico"></el-avatar>
        <el-button v-if="userStore.curUser.bLogin" @click="handleLogout" size="small">
          注销
        </el-button>
      </div>
      <el-menu :default-active="route.path" :collapse="isCollapse" unique-opened router>
        <el-menu-item index="/home" @click="handleMenuSelect">
          <el-icon><HomeFilled /></el-icon>
          <template #title>Home</template>
        </el-menu-item>
        <el-sub-menu index="mytodo">
          <template #title>
            <el-icon><Promotion /></el-icon>
            <span>MyTodo</span>
          </template>
          <el-menu-item index="/lottery" @click="handleMenuSelect">
            <el-icon><Present /></el-icon>
            <template #title>抽奖设置</template>
          </el-menu-item>
          <el-menu-item index="/chat">
            <el-icon><Menu /></el-icon>
            <template #title>Chat</template>
          </el-menu-item>
          <el-menu-item index="/info">
            <el-icon><Document /></el-icon>
            <template #title>Info</template>
          </el-menu-item>
          <el-menu-item index="/score">
            <el-icon><Star /></el-icon>
            <template #title>Score</template>
          </el-menu-item>
        </el-sub-menu>
        <el-menu-item index="/timetable">
          <el-icon><Calendar /></el-icon>
          <template #title>课程表</template>
        </el-menu-item>
        <el-menu-item index="/media">
          <el-icon><Platform /></el-icon>
          <template #title>媒体</template>
        </el-menu-item>
        <el-menu-item index="/tools">
          <el-icon><Setting /></el-icon>
          <template #title>工具</template>
        </el-menu-item>
      </el-menu>
    </el-scrollbar>
  </el-aside>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter, useRoute } from "vue-router";
import {
  HomeFilled,
  Promotion,
  Present,
  Menu,
  Document,
  Star,
  Calendar,
  Platform,
  Setting,
} from "@element-plus/icons-vue";
import { useUserStore } from "@/stores/user";

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();
const isCollapse = ref(false);

const handleMenuSelect = () => {
  // 菜单选择处理
};

const handleLogout = () => {
  userStore.clearCurUser();
  router.push("/");
};
</script>

<style scoped>
/* 样式将在后续迁移中完善 */
</style>
