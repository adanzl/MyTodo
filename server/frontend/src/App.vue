<template>
  <el-container :loading="userStore.loading" class="h-screen">
    <Sidebar />
    <el-container v-if="userStore.curUser.bLogin">
      <el-header class="flex justify-between items-center bg-blue-50 px-6">
        <div class="flex items-center gap-2">
          <el-icon>
            <StarFilled />
          </el-icon>
          哈哈哈
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
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { StarFilled } from "@element-plus/icons-vue";
import Sidebar from "@/views/Sidebar.vue";
import Login from "@/views/Login.vue";
import { useUserStore } from "@/stores/user";
import {
  isLocalIpAvailable,
  checkLocalIpAvailable,
  switchToLocal,
  switchToRemote,
  LOCAL_IP,
  LOCAL_PORT,
} from "@/api/config";

// 使用 Pinia Store
const userStore = useUserStore();

// 服务器状态
const localIpStatus = ref<boolean | null>(null);

// 检测并切换服务器
const checkAndSwitchServer = async () => {
  const isAvailable = await checkLocalIpAvailable();

  // 获取当前状态
  const currentStatus = isLocalIpAvailable();

  if (isAvailable && currentStatus !== true) {
    // 本地可用且当前不是本地，尝试切换到本地
    switchToLocal();
    // 重新获取状态（switchToLocal 可能因为协议问题没有切换）
    const newStatus = isLocalIpAvailable();
    localIpStatus.value = newStatus;

    if (newStatus === true) {
      console.log(`[Server Switch] ✅ 切换到本地服务器: ${LOCAL_IP}:${LOCAL_PORT}`);
    } else {
      // 未能切换（可能是协议不匹配）
      console.log(`[Server Switch] ⚠️ 检测到本地服务器可用，但因协议不匹配无法切换`);
    }
  } else if (!isAvailable && currentStatus !== false) {
    // 本地不可用且当前不是远程，切换到远程
    switchToRemote();
    localIpStatus.value = false;
    console.log("[Server Switch] 🔄 切换到远程服务器");
  } else {
    // 状态未变化，只更新显示
    localIpStatus.value = currentStatus;
  }
};

// 服务器状态显示
const serverStatusText = computed(() => {
  if (localIpStatus.value === true) {
    return `本地 (${LOCAL_IP}:${LOCAL_PORT})`;
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

let serverCheckInterval: ReturnType<typeof setInterval> | null = null;

onMounted(async () => {
  // 使用 store 刷新用户列表
  await userStore.refreshUserList();
  // 从 localStorage 恢复当前用户
  await userStore.restoreCurUser();

  // 立即执行一次检测
  await checkAndSwitchServer();

  // 创建定时任务，每 5 秒检测一次
  serverCheckInterval = setInterval(async () => {
    await checkAndSwitchServer();
  }, 5000);

  console.log("[Server Monitor] 服务器监控已启动，每 5 秒检测一次");
});

// 组件卸载时清除定时器
onBeforeUnmount(() => {
  if (serverCheckInterval) {
    clearInterval(serverCheckInterval);
    console.log("[Server Monitor] 服务器监控已停止");
  }
});
</script>

<style scoped>
/* 样式将在后续迁移中完善 */
</style>
