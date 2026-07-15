<template>
  <el-dialog v-model="dialogVisible" title="构建日志" width="90%" top="20px" @closed="stopLogAutoRefresh">
    <template #header>
      <div class="flex justify-between items-center">
        <span class="text-base font-bold">构建日志</span>
        <el-button size="small" @click="fetchLog" :loading="loadingLog">刷新</el-button>
      </div>
    </template>
    <div ref="logContainer" class="max-h-[70vh] overflow-auto" v-loading="loadingLog">
      <pre class="text-xs bg-gray-50 p-4 rounded whitespace-pre-wrap">{{ logContent || '暂无日志' }}</pre>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, watch, ref, nextTick } from "vue";
import { getBuildLog, getBuildStatus } from "@/api/api-browser";

const props = defineProps<{ modelValue: boolean }>();
const emit = defineEmits<{ (e: "update:modelValue", v: boolean): void }>();

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});

const logContent = ref("");
const loadingLog = ref(false);
const logContainer = ref<HTMLElement | null>(null);
let logRefreshTimer: ReturnType<typeof setInterval> | null = null;

const scrollToBottom = () => {
  nextTick(() => {
    if (logContainer.value) {
      logContainer.value.scrollTop = logContainer.value.scrollHeight;
    }
  });
};

const fetchLog = async () => {
  loadingLog.value = true;
  try {
    const result = await getBuildLog();
    logContent.value = result.log;
    scrollToBottom();
  } catch {
    logContent.value = "加载日志失败";
  } finally {
    loadingLog.value = false;
  }
};

const startAutoRefresh = () => {
  stopLogAutoRefresh();
  logRefreshTimer = setInterval(async () => {
    await fetchLog();
    // 构建成功后停止自动刷新
    try {
      const status = await getBuildStatus();
      if (status.status === 'success') {
        stopLogAutoRefresh();
      }
    } catch {
      // 忽略
    }
  }, 5000);
};

const stopLogAutoRefresh = () => {
  if (logRefreshTimer) {
    clearInterval(logRefreshTimer);
    logRefreshTimer = null;
  }
};

watch(dialogVisible, (v) => {
  if (v) {
    fetchLog();
    stopLogAutoRefresh();
    // 先立即检查一下状态
    getBuildStatus().then((status) => {
      if (status.status !== 'success') {
        startAutoRefresh();
      }
    }).catch(() => {
      startAutoRefresh();
    });
  } else {
    stopLogAutoRefresh();
  }
});
</script>
