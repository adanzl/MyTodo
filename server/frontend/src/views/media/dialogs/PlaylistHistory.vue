<template>
  <el-dialog
    v-model="visible"
    title="播放列表历史记录"
    width="800px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <div v-loading="loading" class="max-h-150 overflow-y-auto">
      <el-empty v-if="!loading && historyList.length === 0" description="暂无历史记录" />

      <el-timeline v-else class="mt-4">
        <el-timeline-item
          v-for="(item, index) in historyList"
          :key="item.timestamp"
          :timestamp="item.timestamp"
          placement="top"
          :color="index === 0 ? '#409eff' : '#909399'"
        >
          <el-card class="hover:shadow-md transition-shadow cursor-pointer" @click="handleViewDetail(item)">
            <template #header>
              <div class="flex items-center justify-between">
                <span class="text-sm font-medium">
                  {{ item.timestamp }}
                </span>
                <el-tag size="small" :type="index === 0 ? 'primary' : 'info'">
                  {{ index === 0 ? '最新' : `历史 ${index + 1}` }}
                </el-tag>
              </div>
            </template>

            <div class="text-xs text-gray-600 space-y-1">
              <div>播放列表数量: {{ item.playlistCount }}</div>
              <div v-if="item.playingCount > 0" class="text-green-600">
                正在播放: {{ item.playingCount }} 个
              </div>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </div>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
    </template>
  </el-dialog>

  <!-- 详情弹窗 -->
  <el-dialog
    v-model="detailVisible"
    title="历史记录详情"
    width="90%"
    :close-on-click-modal="false"
    append-to-body
  >
    <div v-if="selectedHistory" class="max-h-150 overflow-y-auto">
      <pre class="bg-gray-50 p-4 rounded text-xs overflow-x-auto">{{ selectedHistory.data }}</pre>
    </div>

    <template #footer>
      <el-button @click="detailVisible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { getPlaylistHistory } from "@/api/api-playlist";
import { ElMessage } from "element-plus";

interface HistoryItem {
  timestamp: string;
  data: string;
  playlistCount: number;
  playingCount: number;
}

const visible = defineModel<boolean>("visible", { required: true });
const loading = ref(false);
const historyList = ref<HistoryItem[]>([]);
const detailVisible = ref(false);
const selectedHistory = ref<HistoryItem | null>(null);

// 加载历史记录
const loadHistory = async () => {
  if (!visible.value) return;

  loading.value = true;
  try {
    const response = await getPlaylistHistory(10);
    if (response.code !== 0) {
      throw new Error(response.msg || "获取历史记录失败");
    }

    // 转换数据格式
    const historyData = response.data as Record<string, string>;
    historyList.value = Object.entries(historyData).map(([timestamp, data]) => {
      let playlistCount = 0;
      let playingCount = 0;

      try {
        const playlists = JSON.parse(data);
        playlistCount = Object.keys(playlists).length;
        playingCount = Object.values(playlists).filter((p: any) => p.isPlaying).length;
      } catch (e) {
        console.error("解析历史数据失败:", e);
      }

      return {
        timestamp,
        data,
        playlistCount,
        playingCount,
      };
    });
  } catch (error) {
    console.error("加载历史记录失败:", error);
    ElMessage.error("加载历史记录失败");
  } finally {
    loading.value = false;
  }
};

// 查看详情
const handleViewDetail = (item: HistoryItem) => {
  selectedHistory.value = item;
  detailVisible.value = true;
};

// 监听弹窗显示状态
watch(visible, (newVal) => {
  if (newVal) {
    loadHistory();
  } else {
    historyList.value = [];
    selectedHistory.value = null;
  }
});

// 关闭时清空数据
const handleClose = () => {
  visible.value = false;
  historyList.value = [];
  selectedHistory.value = null;
};
</script>

<style scoped>
:deep(.el-timeline-item__timestamp) {
  font-size: 12px;
  color: #606266;
}
</style>
