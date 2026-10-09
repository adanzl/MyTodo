<template>
  <div class="p-1">
    <!-- 主页签 -->
    <el-tabs
      v-model="activeMainTab"
      @tab-change="handleTabChange"
      class="flex-1 flex flex-col overflow-hidden h-[calc(100vh-120px)] mt-2">
      <!-- 聊天室页签 -->
      <el-tab-pane lazy label="聊天室" name="chat">
        <TabChatRoom />
      </el-tab-pane>

      <!-- AI 对话记录页签 -->
      <el-tab-pane lazy label="AI 对话记录" name="ai-history">
        <TabAiHistory />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { defineAsyncComponent, ref, watch } from "vue";

const TabChatRoom = defineAsyncComponent(() => import("./TabChatRoom.vue"));
const TabAiHistory = defineAsyncComponent(() => import("./TabAiHistory.vue"));

// 主页签控制
const STORAGE_KEY = "chat-active-tab";
const VALID_TABS = ["chat", "ai-history"];
const REFRESH_EVENTS: Record<string, string> = {
  chat: "refresh-chat-tab",
  "ai-history": "refresh-ai-history-tab",
};

const savedTab = localStorage.getItem(STORAGE_KEY);
const activeMainTab = ref(savedTab && VALID_TABS.includes(savedTab) ? savedTab : "chat");

// 监听页签切换
const handleTabChange = (tabName: string) => {
  localStorage.setItem(STORAGE_KEY, tabName);
};

// 切换到对应页签时触发刷新（聊天室页签不订阅：它靠 socket 实时推送 + 下拉刷新，
// 重复拉取会按 length 推断 startId 造成消息重复）
watch(activeMainTab, tabName => {
  const eventName = REFRESH_EVENTS[tabName];
  if (eventName) {
    window.dispatchEvent(new CustomEvent(eventName));
  }
});
</script>

<style scoped>
/* 使用 Tailwind CSS，无需额外样式 */
</style>
