<template>
  <div class="p-1">
    <!-- 主页签 -->
    <el-tabs v-model="activeMainTab" @tab-change="handleTabChange"
      class="flex-1 flex flex-col overflow-hidden h-[calc(100vh-150px)]">
      <!-- TTS 页签 -->
      <el-tab-pane lazy label="TTS" name="tts_tool">
        <TTS />
      </el-tab-pane>
      <!-- PDF 工具页签 -->
      <el-tab-pane lazy label="PDF解密" name="pdf_encrypt">
        <PdfEncrypt />
      </el-tab-pane>

      <!-- 音频合成页签 -->
      <el-tab-pane lazy label="音频合成" name="audio_merge">
        <AudioMerge />
      </el-tab-pane>

      <!-- 音频转码页签 -->
      <el-tab-pane lazy label="音频转码" name="audio_convert">
        <AudioConvert />
      </el-tab-pane>

      <!-- PDF 排版页签 -->
      <el-tab-pane lazy label="PDF排版" name="pdf_layout">
        <PdfLayout />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { defineAsyncComponent, ref } from "vue";
const PdfEncrypt = defineAsyncComponent(() => import("./TabPdfEncrypt.vue"));
const AudioMerge = defineAsyncComponent(() => import("./TabAudioMerge.vue"));
const AudioConvert = defineAsyncComponent(() => import("./TabAudioConvert.vue"));
const TTS = defineAsyncComponent(() => import("./TabTts.vue"));
const PdfLayout = defineAsyncComponent(() => import("./TabPdfLayout.vue"));

// 主页签控制
const STORAGE_KEY = "tools-active-tab";
const VALID_TABS = ["tts_tool", "pdf_encrypt", "audio_merge", "audio_convert", "pdf_layout"] as const;
const savedTab = localStorage.getItem(STORAGE_KEY);
const activeMainTab = ref(
  savedTab && VALID_TABS.includes(savedTab as (typeof VALID_TABS)[number]) ? savedTab : "tts_tool",
);

// 监听页签切换
const handleTabChange = (tabName: string) => {
  localStorage.setItem(STORAGE_KEY, tabName);
};
</script>
