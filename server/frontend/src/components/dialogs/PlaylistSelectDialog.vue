<template>
  <el-dialog
    v-model="internalVisible"
    title="应用到列表"
    width="900"
    :before-close="handleClose">
    <div class="flex gap-4 h-[500px]">
      <!-- 左列：播放列表选择 -->
      <div class="w-64 flex flex-col border rounded p-3">
        <div class="text-sm font-semibold mb-2">选择播放列表</div>
        <div class="flex-1 overflow-y-auto space-y-2">
          <div
            v-for="playlist in playlistCollection"
            :key="playlist.id"
            class="flex items-center justify-between px-2 py-2 rounded cursor-pointer hover:bg-gray-50 transition-colors"
            :class="{ 'bg-blue-50 border border-blue-200': playlist.id === selectedPlaylistId }"
            @click="handleSelectPlaylist(playlist.id)">
            <span class="text-sm flex-1 truncate">{{ playlist.name }}</span>
            <span class="text-xs text-gray-500 ml-2 whitespace-nowrap">
              <span
                v-if="selectedFiles && selectedFiles.length > 0"
                class="text-blue-600 font-medium">
                {{ getMatchedFileCountInPlaylist(playlist) }}/{{ getPlaylistTotalFileCount(playlist) }}
              </span>
              <span v-else> {{ getPlaylistTotalFileCount(playlist) }} </span>
            </span>
          </div>
          <div v-if="playlistCollection.length === 0" class="text-xs text-gray-400 text-center py-2">
            暂无播放列表
          </div>
        </div>
      </div>

      <!-- 右列：子列表选择（前置文件列表和正式文件列表） -->
      <div class="flex-1 flex flex-col border rounded p-3">
        <div class="text-sm font-semibold mb-3">选择目标列表（可多选）</div>
        <div v-if="selectedPlaylist" class="flex-1 overflow-y-auto">
          <!-- 前置文件列表（7天） -->
          <div class="mb-3">
            <div class="text-xs text-gray-600 mb-2 font-semibold">前置文件</div>
            <div class="space-y-1">
              <div
                v-for="(day, index) in ['周一', '周二', '周三', '周四', '周五', '周六', '周日']"
                :key="index"
                class="flex items-center gap-2 py-1">
                <el-checkbox
                  :model-value="selectedPreLists.includes(index)"
                  @change="handleTogglePreList(index)"
                  size="small">
                </el-checkbox>
                <span
                  class="text-xs flex-1 cursor-pointer hover:text-blue-500"
                  :class="{ 'text-blue-600 font-medium': selectedPreLists.includes(index) }"
                  @click="handleTogglePreList(index)">
                  {{ day }}
                </span>
                <span class="text-xs text-gray-500 whitespace-nowrap">
                  <span
                    v-if="selectedFiles && selectedFiles.length > 0"
                    class="text-blue-600 font-medium">
                    {{ getMatchedFileCountInPreList(index) }}/{{ getPreFilesCount(index) }}
                  </span>
                  <span v-else> {{ getPreFilesCount(index) }} </span>
                  <span class="text-gray-400"> 个文件</span>
                </span>
              </div>
            </div>
          </div>

          <!-- 正式文件列表 -->
          <div class="border-t pt-3">
            <div class="flex items-center gap-2 py-1">
              <el-checkbox
                :model-value="selectedFilesList"
                @change="handleToggleFilesList"
                size="small">
              </el-checkbox>
              <span
                class="text-xs font-semibold text-gray-600 cursor-pointer hover:text-blue-500 flex-1"
                :class="{ 'text-blue-600': selectedFilesList }"
                @click="handleToggleFilesList()">
                正式文件
              </span>
              <span class="text-xs text-gray-500 whitespace-nowrap">
                <span
                  v-if="selectedFiles && selectedFiles.length > 0"
                  class="text-blue-600 font-medium">
                  {{ getMatchedFileCountInFilesList() }}/{{ getFilesListCount() }}
                </span>
                <span v-else> {{ getFilesListCount() }} </span>
                <span class="text-gray-400"> 个文件</span>
              </span>
            </div>
          </div>
        </div>
        <div v-else class="flex-1 flex items-center justify-center text-sm text-gray-400">
          请先选择一个播放列表
        </div>
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-between">
        <div class="text-sm text-gray-500">
          <span v-if="selectedFiles && selectedFiles.length > 0">
            已选择 {{ selectedFiles.length }} 个文件
          </span>
        </div>
        <div class="flex gap-2">
          <el-button @click="handleClose">取消</el-button>
          <el-button
            type="primary"
            @click="handleCopy"
            :disabled="!hasSelectedLists || !selectedFiles || selectedFiles.length === 0">
            复制到列表
          </el-button>
          <el-button
            type="danger"
            @click="handleRemove"
            :disabled="!hasSelectedLists || !selectedFiles || selectedFiles.length === 0">
            从列表删除
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { logAndNoticeError } from "@/utils";

interface Playlist {
  id: string;
  name: string;
  pre_lists?: any[][];
  playlist?: any[];
}

interface FileItem {
  uri?: string;
  [key: string]: any;
}

interface Props {
  visible?: boolean;
  playlistCollection?: Playlist[];
  selectedFiles?: Array<FileItem | string>;
  onCopy?: (data: {
    playlistId: string;
    files: string[];
    preLists: number[];
    filesList: boolean;
  }) => Promise<void> | void;
  onRemove?: (data: {
    playlistId: string;
    files: string[];
    preLists: number[];
    filesList: boolean;
  }) => Promise<void> | void;
}

const props = withDefaults(defineProps<Props>(), {
  visible: false,
  playlistCollection: () => [],
  selectedFiles: () => [],
  onCopy: undefined,
  onRemove: undefined,
});

const emit = defineEmits<{
  "update:visible": [value: boolean];
}>();

const internalVisible = ref(props.visible);
const selectedPlaylistId = ref<string | null>(null);
const selectedPreLists = ref<number[]>([]);
const selectedFilesList = ref(false);

// 计算属性
const selectedPlaylist = computed(() => {
  return props.playlistCollection.find((p) => p.id === selectedPlaylistId.value) || null;
});

const hasSelectedLists = computed(() => {
  return selectedPreLists.value.length > 0 || selectedFilesList.value;
});

// 获取前置文件数量
const getPreFilesCount = (weekdayIndex: number): number => {
  const playlist = selectedPlaylist.value;
  if (
    !playlist ||
    !playlist.pre_lists ||
    !Array.isArray(playlist.pre_lists) ||
    playlist.pre_lists.length !== 7
  ) {
    return 0;
  }
  const preList = playlist.pre_lists[weekdayIndex];
  return Array.isArray(preList) ? preList.length : 0;
};

// 获取正式文件数量
const getFilesListCount = (): number => {
  const playlist = selectedPlaylist.value;
  if (!playlist || !playlist.playlist) {
    return 0;
  }
  return Array.isArray(playlist.playlist) ? playlist.playlist.length : 0;
};

// 获取播放列表总文件数
const getPlaylistTotalFileCount = (playlist: Playlist): number => {
  if (!playlist) return 0;
  const preCount =
    playlist.pre_lists &&
    Array.isArray(playlist.pre_lists) &&
    playlist.pre_lists.length === 7
      ? playlist.pre_lists.reduce(
          (sum, list) => sum + (Array.isArray(list) ? list.length : 0),
          0
        )
      : 0;
  const filesCount = Array.isArray(playlist.playlist) ? playlist.playlist.length : 0;
  return preCount + filesCount;
};

// 获取选中的文件URI集合
const getSelectedFileUris = (): Set<string> => {
  if (!props.selectedFiles || props.selectedFiles.length === 0) {
    return new Set();
  }
  return new Set(
    props.selectedFiles.map((f) => {
      if (typeof f === "string") return f;
      return f.uri || String(f);
    })
  );
};

// 获取播放列表中符合条件的文件数
const getMatchedFileCountInPlaylist = (playlist: Playlist): number => {
  if (!playlist || !props.selectedFiles || props.selectedFiles.length === 0) {
    return 0;
  }
  const selectedFileUris = getSelectedFileUris();
  let matchedCount = 0;

  if (
    playlist.pre_lists &&
    Array.isArray(playlist.pre_lists) &&
    playlist.pre_lists.length === 7
  ) {
    playlist.pre_lists.forEach((preList) => {
      if (Array.isArray(preList)) {
        preList.forEach((file) => {
          const fileUri = file.uri || String(file);
          if (selectedFileUris.has(fileUri)) {
            matchedCount++;
          }
        });
      }
    });
  }

  if (Array.isArray(playlist.playlist)) {
    playlist.playlist.forEach((file) => {
      const fileUri = file.uri || String(file);
      if (selectedFileUris.has(fileUri)) {
        matchedCount++;
      }
    });
  }

  return matchedCount;
};

// 获取前置文件列表中符合条件的文件数
const getMatchedFileCountInPreList = (weekdayIndex: number): number => {
  const playlist = selectedPlaylist.value;
  if (!playlist || !props.selectedFiles || props.selectedFiles.length === 0) {
    return 0;
  }
  if (!playlist.pre_lists || !Array.isArray(playlist.pre_lists) || playlist.pre_lists.length !== 7) {
    return 0;
  }
  const preList = playlist.pre_lists[weekdayIndex];
  if (!Array.isArray(preList)) {
    return 0;
  }
  const selectedFileUris = getSelectedFileUris();
  let matchedCount = 0;
  preList.forEach((file) => {
    const fileUri = file.uri || String(file);
    if (selectedFileUris.has(fileUri)) {
      matchedCount++;
    }
  });
  return matchedCount;
};

// 获取正式文件列表中符合条件的文件数
const getMatchedFileCountInFilesList = (): number => {
  const playlist = selectedPlaylist.value;
  if (!playlist || !props.selectedFiles || props.selectedFiles.length === 0) {
    return 0;
  }
  if (!Array.isArray(playlist.playlist)) {
    return 0;
  }
  const selectedFileUris = getSelectedFileUris();
  let matchedCount = 0;
  playlist.playlist.forEach((file) => {
    const fileUri = file.uri || String(file);
    if (selectedFileUris.has(fileUri)) {
      matchedCount++;
    }
  });
  return matchedCount;
};

// 选择播放列表
const handleSelectPlaylist = (playlistId: string) => {
  selectedPlaylistId.value = playlistId;
  selectedPreLists.value = [];
  selectedFilesList.value = false;
};

// 切换前置文件列表选择
const handleTogglePreList = (index: number) => {
  const pos = selectedPreLists.value.indexOf(index);
  if (pos > -1) {
    selectedPreLists.value.splice(pos, 1);
  } else {
    selectedPreLists.value.push(index);
  }
};

// 切换正式文件列表选择
const handleToggleFilesList = () => {
  selectedFilesList.value = !selectedFilesList.value;
};

// 复制文件到列表
const handleCopy = async () => {
  if (
    !selectedPlaylist.value ||
    !props.selectedFiles ||
    props.selectedFiles.length === 0 ||
    !hasSelectedLists.value
  ) {
    ElMessage.warning("请选择播放列表和目标列表，并至少选中一个文件");
    return;
  }

  try {
    const fileUris = props.selectedFiles.map((f) => {
      if (typeof f === "string") return f;
      return f.uri || String(f);
    });

    const preListsCount = selectedPreLists.value.length;
    const filesListSelected = selectedFilesList.value;
    let targetDesc = "";
    if (preListsCount > 0 && filesListSelected) {
      targetDesc = `${preListsCount}个前置文件列表和正式文件列表`;
    } else if (preListsCount > 0) {
      const dayNames = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
      const selectedDays = selectedPreLists.value.map((i) => dayNames[i]).join("、");
      targetDesc = `前置文件列表（${selectedDays}）`;
    } else if (filesListSelected) {
      targetDesc = "正式文件列表";
    }

    await ElMessageBox.confirm(
      `确定要将选中的 ${fileUris.length} 个文件复制到播放列表"${selectedPlaylist.value.name}"的${targetDesc}吗？`,
      "确认复制",
      {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      }
    );

    if (props.onCopy) {
      await props.onCopy({
        playlistId: selectedPlaylistId.value!,
        files: fileUris,
        preLists: selectedPreLists.value,
        filesList: selectedFilesList.value,
      });
      ElMessage.success("文件已复制到播放列表");
      handleClose();
    }
  } catch (error) {
    if (error !== "cancel") {
      logAndNoticeError(error as Error, "复制文件失败");
    }
  }
};

// 从列表删除文件
const handleRemove = async () => {
  if (
    !selectedPlaylist.value ||
    !props.selectedFiles ||
    props.selectedFiles.length === 0 ||
    !hasSelectedLists.value
  ) {
    ElMessage.warning("请选择播放列表和目标列表，并至少选中一个文件");
    return;
  }

  try {
    const fileUris = props.selectedFiles.map((f) => {
      if (typeof f === "string") return f;
      return f.uri || String(f);
    });

    const preListsCount = selectedPreLists.value.length;
    const filesListSelected = selectedFilesList.value;
    let targetDesc = "";
    if (preListsCount > 0 && filesListSelected) {
      targetDesc = `${preListsCount}个前置文件列表和正式文件列表`;
    } else if (preListsCount > 0) {
      const dayNames = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
      const selectedDays = selectedPreLists.value.map((i) => dayNames[i]).join("、");
      targetDesc = `前置文件列表（${selectedDays}）`;
    } else if (filesListSelected) {
      targetDesc = "正式文件列表";
    }

    await ElMessageBox.confirm(
      `确定要从播放列表"${selectedPlaylist.value.name}"的${targetDesc}中删除选中的 ${fileUris.length} 个文件吗？`,
      "确认删除",
      {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      }
    );

    if (props.onRemove) {
      await props.onRemove({
        playlistId: selectedPlaylistId.value!,
        files: fileUris,
        preLists: selectedPreLists.value,
        filesList: selectedFilesList.value,
      });
      ElMessage.success("文件已从播放列表删除");
      handleClose();
    }
  } catch (error) {
    if (error !== "cancel") {
      logAndNoticeError(error as Error, "删除文件失败");
    }
  }
};

// 关闭对话框
const handleClose = () => {
  internalVisible.value = false;
  selectedPlaylistId.value = null;
  selectedPreLists.value = [];
  selectedFilesList.value = false;
};

// 自动选择第一个播放列表
const autoSelectFirstPlaylist = () => {
  if (
    props.playlistCollection &&
    props.playlistCollection.length > 0 &&
    !selectedPlaylistId.value
  ) {
    selectedPlaylistId.value = props.playlistCollection[0].id;
  }
};

watch(
  () => props.playlistCollection,
  (newCollection) => {
    if (newCollection && newCollection.length > 0 && !selectedPlaylistId.value) {
      selectedPlaylistId.value = newCollection[0].id;
    }
  },
  { immediate: true }
);

watch(
  () => props.visible,
  (isVisible) => {
    internalVisible.value = isVisible;
    if (isVisible) {
      autoSelectFirstPlaylist();
    }
  }
);

watch(internalVisible, (newVal) => {
  if (newVal !== props.visible) {
    emit("update:visible", newVal);
  }
});

onMounted(() => {
  autoSelectFirstPlaylist();
});
</script>

