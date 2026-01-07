<template>
  <div class="p-1">
    <!-- 主页签 -->
    <el-tabs
      v-model="activeMainTab"
      @tab-change="handleTabChange"
      class="flex-1 flex flex-col overflow-hidden h-[calc(100vh-150px)]"
    >
      <!-- PDF 工具页签 -->
      <el-tab-pane label="PDF 工具" name="pdf_tool">
        <PdfTool />
      </el-tab-pane>

      <!-- 音频合成页签 -->
      <el-tab-pane label="音频合成" name="audio_merge">
        <MediaTool />
      </el-tab-pane>

      <!-- 音频转码页签 -->
      <el-tab-pane label="音频转码" name="audio_convert">
        <AudioConvertTool />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import PdfTool from "./PdfTool.vue";
import MediaTool from "./MediaTool.vue";
import AudioConvertTool from "./AudioConvertTool.vue";

// 主页签控制
const activeMainTab = ref("pdf_tool");

// 监听页签切换
const handleTabChange = (tabName: string) => {
  // 页签切换时的处理逻辑（如果需要）
  console.log("切换到页签:", tabName);
};
</script>
