<template>
  <div class="p-1">
    <el-tabs
      v-model="activeMainTab"
      @tab-change="handleTabChange"
      class="flex-1 flex flex-col overflow-hidden h-[calc(100vh-120px)] mt-2"
    >
      <el-tab-pane label="日程管理" name="manage">
        <TabScheduleManage />
      </el-tab-pane>

      <el-tab-pane label="日历视图" name="calendar">
        <TabScheduleCalendar />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import TabScheduleManage from "./TabScheduleManage.vue";
import TabScheduleCalendar from "./TabScheduleCalendar.vue";

const STORAGE_KEY = "schedule-active-tab";
const VALID_TABS = ["manage", "calendar"] as const;
const activeMainTab = ref("manage");

const handleTabChange = (tabName: string) => {
  localStorage.setItem(STORAGE_KEY, tabName);

  const eventMap: Record<string, string> = {
    manage: "refresh-schedule-manage-tab",
    calendar: "refresh-schedule-calendar-tab",
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
