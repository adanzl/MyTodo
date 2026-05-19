<template>
  <div class="p-1">
    <!-- 主页签 -->
    <el-tabs v-model="activeMainTab" @tab-change="handleTabChange"
      class="flex-1 flex flex-col overflow-hidden h-[calc(100vh-120px)] mt-2">
      <!-- 素材管理页签 -->
      <el-tab-pane label="素材管理" name="material">
        <TabMaterial />
      </el-tab-pane>

      <!-- 任务管理页签 -->
      <el-tab-pane label="任务管理" name="tasks">
        <TabTasks />
      </el-tab-pane>

      <!-- 任务日历页签 -->
      <el-tab-pane label="任务日历" name="calendar">
        <TabTaskCalendar />
      </el-tab-pane>

      <!-- 任务预览页签 -->
      <el-tab-pane label="任务预览" name="preview">
        <TabTasksPreview />
      </el-tab-pane>

      <!-- 使用统计页签 -->
      <el-tab-pane label="使用统计" name="usage">
        <TabUsage />
      </el-tab-pane>

      <!-- 任务记录页签 -->
      <el-tab-pane label="任务记录" name="history">
        <TabTaskHistory />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from "vue";
import TabMaterial from "./TabMaterial.vue";
import TabTasks from "./TabTasks.vue";
import TabTaskCalendar from "./TabTaskCalendar.vue";
import TabTasksPreview from "./TabTasksPreview.vue";
import TabUsage from "./TabUsage.vue";
import TabTaskHistory from "./TabTaskHistory.vue";

// 主页签控制
const STORAGE_KEY = 'tasks-active-tab';
const activeMainTab = ref("calendar");

// 从 localStorage 加载上次选中的页签
onMounted(() => {
  const savedTab = localStorage.getItem(STORAGE_KEY);
  if (savedTab) {
    activeMainTab.value = savedTab;
  }
});

// 监听页签切换
const handleTabChange = (tabName: string) => {
  console.log("切换到页签:", tabName);
  // 保存到 localStorage
  localStorage.setItem(STORAGE_KEY, tabName);
};

// 监听页签变化，切换到对应页签时触发刷新
watch(activeMainTab, (newTab) => {
  const eventMap: Record<string, string> = {
    'material': 'refresh-material-tab',
    'tasks': 'refresh-tasks-tab',
    'calendar': 'refresh-calendar-tab',
    'preview': 'refresh-preview-tab',
    'usage': 'refresh-usage-tab',
    'history': 'refresh-history-tab'
  };

  const eventName = eventMap[newTab];
  if (eventName) {
    window.dispatchEvent(new CustomEvent(eventName));
  }
});
</script>

<style scoped>
/* 使用 Tailwind CSS，无需额外样式 */
</style>
