<template>
  <el-container class="h-screen">
    <Sidebar @collapse-change="handleCollapseChange" />
    <el-container v-if="userStore.curUser.bLogin">
      <el-header class="flex justify-between items-center bg-blue-50 px-6">
        <div class="flex items-center gap-2">
          <el-icon>
            <StarFilled />
          </el-icon>
          麟曦之家
          <el-icon>
            <StarFilled />
          </el-icon>
        </div>
        <div class="flex items-center gap-2 text-sm">
          <span class="text-gray-500">服务器:</span>
          <el-tag :type="serverStatusType" size="small">
            {{ serverStatusText }}
          </el-tag>
        </div>
      </el-header>
      <el-main >
        <router-view></router-view>
      </el-main>
    </el-container>
    <el-container v-else>
      <el-main
        class="bg-blue-100 flex! justify-center items-center"
        v-loading="userStore.loading"
        element-loading-text="正在加载..."
      >
        <Login @login-success="handleLoginSuccess" />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { StarFilled } from "@element-plus/icons-vue";
import Sidebar from "@/views/Sidebar.vue";
import Login from "@/views/PageLogin.vue";
import { useUserStore } from "@/stores/user";
import {
  getCurrentLocalPort,
  LOCAL_IP,
  startServerMonitor,
  stopServerMonitor,
  subscribeServerStatus,
} from "@/api/config";

// 使用 Pinia Store
const userStore = useUserStore();

// 侧边栏折叠状态
const isSidebarCollapsed = ref(false);

const handleCollapseChange = (collapsed: boolean) => {
  isSidebarCollapsed.value = collapsed;
};

// 服务器状态
const localIpStatus = ref<boolean | null>(null);
let unsubscribeServerStatus: (() => void) | null = null;

// 服务器状态显示
const serverStatusText = computed(() => {
  if (localIpStatus.value === true) {
    return `本地 (${LOCAL_IP}:${getCurrentLocalPort()})`;
  } else if (localIpStatus.value === false) {
    return "远程";
  } else {
    return "检测中...";
  }
});

const serverStatusType = computed(() => {
  if (localIpStatus.value === true) {
    return "success";
  } else if (localIpStatus.value === false) {
    return "warning";
  } else {
    return "info";
  }
});

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

  unsubscribeServerStatus = subscribeServerStatus((isUsingLocalServer, changed) => {
    const previousStatus = localIpStatus.value;
    localIpStatus.value = isUsingLocalServer;

    if (!changed || previousStatus === null) {
      return;
    }

    if (isUsingLocalServer) {
      console.log(`[Server Switch] ✅ 切换到本地服务器: ${LOCAL_IP}:${getCurrentLocalPort()}`);
      return;
    }

    console.log("[Server Switch] 🔄 切换到远程服务器");
  });

  await startServerMonitor();
});

// 组件卸载时清除定时器
onBeforeUnmount(() => {
  unsubscribeServerStatus?.();
  unsubscribeServerStatus = null;
  stopServerMonitor();
});
</script>

<style scoped>
/* 样式将在后续迁移中完善 */
</style>
