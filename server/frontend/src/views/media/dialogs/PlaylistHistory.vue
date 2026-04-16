<template>
  <el-dialog
    v-model="visible"
    title="播放列表历史记录"
    width="90%"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <template #header>
      <div class="flex items-center">
        <span>播放列表历史记录</span>
        <el-button
          type="primary"
          size="small"
          :icon="Refresh"
          :loading="loading"
          @click="loadHistory"
          circle
          plain
          title="刷新"
          class="ml-2"
        />
      </div>
    </template>
    <div v-loading="loading" class="flex gap-4 h-[calc(100vh-300px)]">
      <!-- 第一列：时间戳列表 -->
      <div class="w-64 shrink-0 border-r pr-4 overflow-y-auto">
        <el-empty v-if="!loading && historyList.length === 0" description="暂无历史记录" />
        <div v-else class="space-y-2">
          <div
            v-for="item in historyList"
            :key="item.timestamp"
            class="p-3 rounded cursor-pointer transition-colors flex"
            :class="selectedTimestamp === item.timestamp ? 'bg-blue-50 border-blue-500 border' : 'hover:bg-gray-50 border border-transparent'"
            @click="selectHistory(item)"
          >
            <div class="flex-1">
              <div class="text-sm font-medium">{{ item.timestamp }}</div>
              <div class="text-xs text-gray-500 mt-1">
                {{ item.playlistCount }} 个列表
              </div>
            </div>
            <div class="flex items-center" >
              <el-button type="primary" size="small" @click="applyHistory(item)">应用</el-button>
            </div>
          </div>
        </div>
      </div>

      <!-- 第二列：Playlist 内容概览 -->
      <div class="w-70 shrink-0 border-r pr-4 overflow-y-auto">
        <div v-if="!selectedHistory" class="text-gray-400 text-center mt-20">
          请选择一个历史记录
        </div>
        <div v-else>
          <h3 class="text-base font-semibold mb-3">播放列表概览</h3>
          <div class="space-y-2">
            <div
              v-for="(playlist, id) in parsedPlaylists"
              :key="id"
              class="p-3 border rounded cursor-pointer transition-colors"
              :class="selectedPlaylistId === String(id) ? 'bg-blue-50 border-blue-500' : 'hover:bg-gray-50 border-transparent'"
              @click="selectPlaylist(String(id), playlist)"
            >
              <div class="text-sm font-medium truncate">{{ playlist.name || id }}</div>
              <div class="text-xs text-gray-500 mt-1">
                <span>ID: {{ id }}</span>
                <el-tag v-if="playlist.isPlaying" size="small" type="success" class="ml-2">
                  播放中
                </el-tag>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 第三列：Playlist 详情 -->
      <div class="flex-1 overflow-y-auto">
        <div v-if="!selectedPlaylistId" class="text-gray-400 text-center mt-20">
          请选择一个播放列表查看详情
        </div>
        <div v-else>
          <h3 class="text-base font-semibold mb-3">{{ selectedPlaylistName }} 详情</h3>

          <!-- 前置文件列表 -->
          <div v-if="selectedPlaylist.pre_lists && selectedPlaylist.pre_lists.length > 0" class="mb-4">
            <h4 class="text-sm font-medium mb-2">前置文件 (Pre Lists)</h4>
            <el-tabs type="border-card">
              <el-tab-pane
                v-for="(preList, dayIndex) in selectedPlaylist.pre_lists"
                :key="dayIndex"
                :label="getWeekdayName(Number(dayIndex))"
              >
                <el-table :data="preList" border stripe max-height="300">
                  <el-table-column type="index" label="#" width="60" />
                  <el-table-column prop="uri" label="路径" show-overflow-tooltip />
                  <el-table-column prop="duration" label="时长(秒)" width="80" />
                </el-table>
              </el-tab-pane>
            </el-tabs>
          </div>

          <!-- 播放列表 -->
          <div v-if="selectedPlaylist.playlist && selectedPlaylist.playlist.length > 0">
            <h4 class="text-sm font-medium mb-2">播放列表 (Playlist)</h4>
            <el-table :data="selectedPlaylist.playlist" border stripe max-height="400">
              <el-table-column type="index" label="#" width="60" />
              <el-table-column prop="uri" label="路径" show-overflow-tooltip />
              <el-table-column prop="duration" label="时长(秒)" width="80" />
            </el-table>
          </div>

          <!-- 空状态 -->
          <el-empty v-if="!selectedPlaylist.pre_lists?.length && !selectedPlaylist.playlist?.length" description="暂无文件" />
        </div>
      </div>
    </div>

  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from "vue";
import { getPlaylistHistory, updateAllPlaylists } from "@/api/api-playlist";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";

interface HistoryItem {
  timestamp: string;
  data: string;
  playlistCount: number;
  playingCount: number;
}

const WEEKDAY_NAMES = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

const visible = defineModel<boolean>("visible", { required: true });
const loading = ref(false);
const historyList = ref<HistoryItem[]>([]);
const selectedTimestamp = ref<string | null>(null);
const selectedPlaylistId = ref<string | null>(null);

// 解析当前选中的历史数据
const parsedPlaylists = computed(() => {
  if (!selectedHistory.value) return {};
  try {
    return JSON.parse(selectedHistory.value.data);
  } catch (e) {
    console.error("解析历史数据失败:", e);
    return {};
  }
});

// 当前选中的播放列表对象
const selectedPlaylist = computed(() => {
  if (!selectedPlaylistId.value || !parsedPlaylists.value[selectedPlaylistId.value]) {
    return null;
  }
  return parsedPlaylists.value[selectedPlaylistId.value];
});

const selectedPlaylistName = computed(() => {
  if (!selectedPlaylist.value) return '';
  return selectedPlaylist.value.name || selectedPlaylistId.value || '';
});

const selectedHistory = computed(() => {
  if (!selectedTimestamp.value) return null;
  return historyList.value.find(h => h.timestamp === selectedTimestamp.value) || null;
});

// 获取星期名称
const getWeekdayName = (index: number) => {
  return WEEKDAY_NAMES[index] || `第${index + 1}天`;
};

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

    // 默认选中第一个（最新的）
    if (historyList.value.length > 0) {
      selectHistory(historyList.value[0]);
    }
  } catch (error) {
    console.error("加载历史记录失败:", error);
    ElMessage.error("加载历史记录失败");
  } finally {
    loading.value = false;
  }
};

// 选择历史记录
const selectHistory = (item: HistoryItem) => {
  selectedTimestamp.value = item.timestamp;

  // 默认选中第一个播放列表
  try {
    const playlists = JSON.parse(item.data);
    const firstId = Object.keys(playlists)[0];
    if (firstId) {
      selectedPlaylistId.value = firstId;
    } else {
      selectedPlaylistId.value = null;
    }
  } catch (e) {
    selectedPlaylistId.value = null;
  }
};

const applyHistory = async (item: HistoryItem) => {
  try {
    await ElMessageBox.confirm(
      `确定要应用 ${item.timestamp} 的历史记录吗？这将覆盖当前所有播放列表配置。`,
      '确认应用',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );

    const playlists = JSON.parse(item.data);
    const response = await updateAllPlaylists(playlists);

    if (response.code === 0) {
      ElMessage.success('应用成功');
      handleClose();
    } else {
      ElMessage.error(response.msg || '应用失败');
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('应用历史记录失败:', error);
      ElMessage.error('应用失败');
    }
  }
};

// 选择播放列表
const selectPlaylist = (id: string, _playlist: any) => {
  selectedPlaylistId.value = id;
};

// 监听弹窗显示状态
watch(visible, (newVal) => {
  if (newVal) {
    loadHistory();
  } else {
    historyList.value = [];
    selectedTimestamp.value = null;
    selectedPlaylistId.value = null;
  }
});

// 关闭时清空数据
const handleClose = () => {
  visible.value = false;
  historyList.value = [];
  selectedTimestamp.value = null;
  selectedPlaylistId.value = null;
};
</script>

<style scoped>
:deep(.el-timeline-item__timestamp) {
  font-size: 12px;
  color: #606266;
}
</style>
