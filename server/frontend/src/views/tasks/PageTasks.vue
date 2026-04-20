<template>
  <div class="p-1">
    <!-- 主页签 -->
    <el-tabs
      v-model="activeMainTab"
      @tab-change="handleTabChange"
      class="flex-1 flex flex-col overflow-hidden h-[calc(100vh-120px)] mt-2"
    >
      <!-- 素材管理页签 -->
      <el-tab-pane label="素材管理" name="material">
        <TabMaterial />
      </el-tab-pane>

      <!-- 任务管理页签 -->
      <el-tab-pane label="任务管理" name="category">
        <TabCategory />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import TabMaterial from "./TabMaterial.vue";
import TabCategory from "./TabCategory.vue";

// 主页签控制
const activeMainTab = ref("material");

// 监听页签切换
const handleTabChange = (tabName: string) => {
  console.log("切换到页签:", tabName);
};
</script>

<style scoped>
/* 使用 Tailwind CSS，无需额外样式 */
</style>
