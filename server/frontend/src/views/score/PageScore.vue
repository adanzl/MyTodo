<template>
  <div class="p-1">
    <el-tabs
      v-model="activeMainTab"
      @tab-change="handleTabChange"
      class="flex-1 flex flex-col overflow-hidden h-[calc(100vh-120px)] mt-2"
    >
      <el-tab-pane label="星星" name="star">
        <TabScoreStar />
      </el-tab-pane>

      <el-tab-pane label="金币" name="coin">
        <TabScoreCoin />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import TabScoreStar from "./TabScoreStar.vue";
import TabScoreCoin from "./TabScoreCoin.vue";

const STORAGE_KEY = "score-active-tab";
const VALID_TABS = ["star", "coin"] as const;
const activeMainTab = ref("star");

const handleTabChange = (tabName: string) => {
  localStorage.setItem(STORAGE_KEY, tabName);

  const eventMap: Record<string, string> = {
    star: "refresh-score-star-tab",
    coin: "refresh-score-coin-tab",
  };

  const eventName = eventMap[tabName];
  if (eventName) {
    window.dispatchEvent(new CustomEvent(eventName));
  }
};

onMounted(() => {
  const savedTab = localStorage.getItem(STORAGE_KEY);
  if (savedTab && VALID_TABS.includes(savedTab as (typeof VALID_TABS)[number])) {
    activeMainTab.value = savedTab;
  }
});
</script>
