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
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import TabMaterial from "./TabMaterial.vue";
import TabTasks from "./TabTasks.vue";
import TabTaskCalendar from "./TabTaskCalendar.vue";
import TabTasksPreview from "./TabTasksPreview.vue";
import TabUsage from "./TabUsage.vue";

// 主页签控制
const activeMainTab = ref("calendar");

// 监听页签切换
const handleTabChange = (tabName: string) => {
  console.log("切换到页签:", tabName);
};

// 监听页签变化，切换到预览页签时触发刷新
watch(activeMainTab, (newTab) => {
  if (newTab === 'preview') {
    // 通过事件总线或 provide/inject 通知子组件刷新
    window.dispatchEvent(new CustomEvent('refresh-preview-tab'));
  }
});
</script>

<style scoped>
/* 使用 Tailwind CSS，无需额外样式 */
</style>
