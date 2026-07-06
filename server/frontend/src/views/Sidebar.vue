<template>
  <el-aside :width="isCollapse ? '64px' : '200px'" class="transition-all duration-300">
    <el-scrollbar>
      <el-menu :default-active="route.path" :collapse="isCollapse" unique-opened router>
        <el-menu-item index="#">
          <el-avatar :src="userStore.curUser.ico" :size="isCollapse ? 20 : 40"></el-avatar>
          <template #title >
            <el-button v-if="userStore.curUser.bLogin" @click="handleLogout" size="small" class="ml-10">
              注销
            </el-button>
          </template>
        </el-menu-item>
        <el-menu-item index="/home" @click="handleMenuSelect">
          <el-icon><HomeFilled /></el-icon>
          <template #title>Home</template>
        </el-menu-item>
        <el-menu-item index="/lottery" @click="handleMenuSelect">
          <el-icon><Present /></el-icon>
          <template #title>抽奖</template>
        </el-menu-item>
        <el-menu-item index="/chat">
          <el-icon><ChatRound /></el-icon>
          <template #title>Chat</template>
        </el-menu-item>
        <el-menu-item index="/schedule">
          <el-icon><Timer /></el-icon>
          <template #title>日程</template>
        </el-menu-item>
        <el-menu-item index="/score">
          <el-icon><Star /></el-icon>
          <template #title>Score</template>
        </el-menu-item>
        <el-menu-item index="/statistics">
          <el-icon><PieChart /></el-icon>
          <template #title>统计</template>
        </el-menu-item>
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
        <el-menu-item index="/tasks" @click="handleMenuSelect">
          <el-icon><List /></el-icon>
          <template #title>阅读打卡</template>
        </el-menu-item>
        <el-menu-item index="/browser">
          <el-icon><Monitor /></el-icon>
          <template #title>浏览器</template>
        </el-menu-item>
        <el-menu-item index="#" @click="toggleCollapse">
          <el-icon><Expand v-if="isCollapse" /><Fold v-else /></el-icon>
          <template #title>折叠</template>
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
  ChatRound,
  Present,
  Star,
  Calendar,
  Platform,
  Setting,
  PieChart,
  List,
  Timer,
  Monitor,
  Expand,
  Fold,
} from "@element-plus/icons-vue";
import { useUserStore } from "@/stores/user";

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();
const isCollapse = ref(false);

const emit = defineEmits(['collapse-change']);

const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value;
  emit('collapse-change', isCollapse.value);
};

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

