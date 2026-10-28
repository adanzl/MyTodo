<template>
  <el-aside
    :width="isCollapse ? '64px' : '200px'"
    class="flex flex-col overflow-hidden border-r border-(--el-border-color) transition-all duration-300 [&_.el-menu]:border-r-0"
  >
    <el-scrollbar class="min-h-0 flex-1">
      <el-menu
        :default-active="pendingRoute?.path ?? route.path"
        :collapse="isCollapse"
        unique-opened
        router
      >
        <el-menu-item index="#">
          <el-avatar :src="userStore.curUser.ico" :size="isCollapse ? 20 : 40"></el-avatar>
          <template #title>
            <el-button v-if="userStore.curUser.bLogin" size="small" class="ml-10" @click="handleLogout">
              注销
            </el-button>
          </template>
        </el-menu-item>
        <el-menu-item index="/home">
          <el-icon><HomeFilled /></el-icon>
          <template #title>Home</template>
        </el-menu-item>
        <el-menu-item index="/lottery">
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
        <el-menu-item index="/tasks">
          <el-icon><List /></el-icon>
          <template #title>阅读打卡</template>
        </el-menu-item>
        <el-menu-item index="/browser">
          <el-icon><Monitor /></el-icon>
          <template #title>浏览器</template>
        </el-menu-item>
      </el-menu>
    </el-scrollbar>
    <div
      class="flex h-20 shrink-0 pb-4"
      :class="
        isCollapse
          ? 'flex-col items-center justify-end gap-2 px-0.5'
          : 'items-end justify-center gap-3 px-2'
      "
    >
      <el-switch
        v-model="isDark"
        class="h-5! [--el-switch-border-color:var(--el-border-color)]! [--el-switch-off-color:var(--el-fill-color)]! [--el-switch-on-color:var(--el-fill-color)]! [&_.el-switch__action]:size-3.5! [&.is-checked_.el-switch__action]:left-[calc(100%-15px)]!"
        aria-label="切换暗色主题"
      >
        <template #active-action>
          <el-icon class="size-full! rounded-full bg-[#141414] text-[#cfd3dc]! [--color:#cfd3dc]!">
            <svg viewBox="0 0 24 24">
              <path
                d="M11.01 3.05C6.51 3.54 3 7.36 3 12a9 9 0 0 0 9 9c4.63 0 8.45-3.5 8.95-8c.09-.79-.78-1.42-1.54-.95A5.403 5.403 0 0 1 11.1 7.5c0-1.06.31-2.06.84-2.89c.45-.67-.04-1.63-.93-1.56z"
                fill="currentColor"
              />
            </svg>
          </el-icon>
        </template>
        <template #inactive-action>
          <el-icon class="size-full! text-[#606266]! [--color:#606266]!">
            <svg viewBox="0 0 24 24">
              <path
                d="M6.05 4.14l-.39-.39a.993.993 0 0 0-1.4 0l-.01.01a.984.984 0 0 0 0 1.4l.39.39c.39.39 1.01.39 1.4 0l.01-.01a.984.984 0 0 0 0-1.4zM3.01 10.5H1.99c-.55 0-.99.44-.99.99v.01c0 .55.44.99.99.99H3c.56.01 1-.43 1-.98v-.01c0-.56-.44-1-.99-1zm9-9.95H12c-.56 0-1 .44-1 .99v.96c0 .55.44.99.99.99H12c.56.01 1-.43 1-.98v-.97c0-.55-.44-.99-.99-.99zm7.74 3.21c-.39-.39-1.02-.39-1.41-.01l-.39.39a.984.984 0 0 0 0 1.4l.01.01c.39.39 1.02.39 1.4 0l.39-.39a.984.984 0 0 0 0-1.4zm-1.81 15.1l.39.39a.996.996 0 1 0 1.41-1.41l-.39-.39a.993.993 0 0 0-1.4 0c-.4.4-.4 1.02-.01 1.41zM20 11.49v.01c0 .55.44.99.99.99H22c.55 0 .99-.44.99-.99v-.01c0-.55-.44-.99-.99-.99h-1.01c-.55 0-.99.44-.99.99zM12 5.5c-3.31 0-6 2.69-6 6s2.69 6 6 6s6-2.69 6-6s-2.69-6-6-6zm-.01 16.95H12c.55 0 .99-.44.99-.99v-.96c0-.55-.44-.99-.99-.99h-.01c-.55 0-.99.44-.99.99v.96c0 .55.44.99.99.99zm-7.74-3.21c.39.39 1.02.39 1.41 0l.39-.39a.993.993 0 0 0 0-1.4l-.01-.01a.996.996 0 0 0-1.41 0l-.39.39c-.38.4-.38 1.02.01 1.41z"
                fill="currentColor"
              />
            </svg>
          </el-icon>
        </template>
      </el-switch>
      <el-tooltip :content="isCollapse ? '展开菜单' : '折叠菜单'" placement="right">
        <button
          type="button"
          class="inline-flex h-5 w-10 cursor-pointer items-center justify-center rounded-full border border-(--el-border-color) bg-(--el-fill-color) p-0 text-xs leading-none text-(--el-text-color-secondary) transition-colors duration-200 hover:border-(--el-color-primary) hover:text-(--el-color-primary)"
          :aria-label="isCollapse ? '展开菜单' : '折叠菜单'"
          @click="toggleCollapse"
        >
          <el-icon>
            <Expand v-if="isCollapse" />
            <Fold v-else />
          </el-icon>
        </button>
      </el-tooltip>
    </div>
  </el-aside>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { pendingRoute } from "@/router";
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
import { useAppStore } from "@/stores/app";

const emit = defineEmits<{
  collapseChange: [collapsed: boolean];
}>();

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();
const appStore = useAppStore();
const isCollapse = ref(false);

/** 开关状态直接读写主题：关=亮色，开=暗色 */
const isDark = computed({
  get: () => appStore.isDark,
  set: (value: string | number | boolean) => appStore.setTheme(value ? "dark" : "light"),
});

const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value;
  emit("collapseChange", isCollapse.value);
};

const handleLogout = () => {
  userStore.clearCurUser();
  router.push("/");
};
</script>
