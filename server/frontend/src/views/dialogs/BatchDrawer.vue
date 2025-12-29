<template>
  <el-drawer
    v-model="internalVisible"
    title="批量模式"
    :size="1200"
    direction="rtl"
    :before-close="handleClose"
  >
    <div class="flex gap-4 h-full">
      <!-- 第一列：Batch List -->
      <div class="w-64 border rounded p-3 flex flex-col">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-base font-semibold">Batch列表</h3>
          <el-button type="primary" size="small" @click="handleCreateBatch" plain>
            <el-icon><Plus /></el-icon>
          </el-button>
        </div>
        <div class="flex-1 overflow-y-auto space-y-2">
          <div
            v-for="batch in batchList"
            :key="batch.id"
            class="border rounded px-3 py-2 hover:bg-gray-50 flex items-center gap-2"
            :class="{ 'border-blue-500 bg-blue-50': batch.id === selectedBatchId }"
          >
            <div class="flex-1 cursor-pointer" @click="handleSelectBatch(batch.id)">
              <div class="text-sm font-medium truncate">{{ batch.name }}</div>
              <div class="text-xs text-gray-500 mt-1">
                {{ batch.files ? batch.files.length : 0 }} 个文件
              </div>
            </div>
            <div class="flex items-center gap-1 flex-shrink-0">
              <el-button
                type="default"
                plain
                size="small"
                circle
                @click.stop="handleDeleteBatch(batch.id)"
                title="删除"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
          <div v-if="batchList.length === 0" class="text-sm text-gray-400 text-center py-4">
            暂无Batch，点击"+"创建
          </div>
        </div>
      </div>

      <!-- 第二列：文件列表 -->
      <div class="flex-1 border rounded p-3 flex flex-col">
        <div class="mb-3 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <h3 class="text-base font-semibold">
              {{ selectedBatch ? selectedBatch.name : "请选择一个Batch" }}
            </h3>
            <el-button
              v-if="selectedBatch"
              type="default"
              plain
              size="small"
              circle
              @click="handleEditBatch(selectedBatch.id)"
              title="编辑"
            >
              <el-icon><Edit /></el-icon>
            </el-button>
          </div>
          <div v-if="selectedBatch" class="flex items-center gap-2">
            <el-button type="primary" size="small" @click="handleOpenFileBrowser" plain>
              <el-icon><Plus /></el-icon>
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="handleDeleteSelectedFiles"
              :disabled="selectedFileIndices.length === 0"
              plain
            >
              <el-icon><Delete /></el-icon>
              ({{ selectedFileIndices.length }})
            </el-button>
          </div>
        </div>
        <div class="flex-1 overflow-y-auto">
          <div
            v-if="selectedBatch && selectedBatch.files && selectedBatch.files.length > 0"
            class="space-y-1"
          >
            <div
              v-for="(file, index) in selectedBatch.files"
              :key="index"
              class="flex items-center gap-2 p-2 border border-blue-500 rounded hover:bg-gray-50 cursor-pointer"
              :class="{ 'bg-blue-50': selectedFileIndices.includes(index) }"
              @click="handleToggleFileSelection(index)"
            >
              <el-checkbox
                :model-value="selectedFileIndices.includes(index)"
                @change="handleToggleFileSelection(index)"
                class="!h-6"
                @click.stop
                size="default"
              >
              </el-checkbox>
              <span class="text-xs text-gray-500 w-8">{{ index + 1 }}</span>
              <span class="flex-1 text-sm truncate" :title="getFileUri(file)">
                {{ getFileUri(file).split("/").pop() }}
              </span>
            </div>
          </div>
          <div v-else class="text-sm text-gray-400 text-center py-8">
            {{ selectedBatch ? "该Batch暂无文件" : "请先选择一个Batch" }}
          </div>
        </div>
      </div>

      <!-- 第三列：Playlist操作 -->
      <div class="w-96 border rounded p-3 flex flex-col">
        <div class="mb-3">
          <h3 class="text-base font-semibold mb-2">Playlist操作</h3>
          <div class="flex gap-2 mb-3">
            <el-button
              type="default"
              size="small"
              @click="handleAddFilesToPlaylist"
              :disabled="
                !selectedBatch ||
                !selectedPlaylistId ||
                selectedFileIndices.length === 0 ||
                !hasSelectedLists
              "
              plain
            >
              <el-icon class="mr-1"><Plus /></el-icon>
              添加到播放列表
            </el-button>
            <el-button
              type="default"
              size="small"
              @click="handleRemoveFilesFromPlaylist"
              :disabled="
                !selectedBatch ||
                !selectedPlaylistId ||
                selectedFileIndices.length === 0 ||
                !hasSelectedLists
              "
              plain
            >
              <el-icon class="mr-1"><Delete /></el-icon>
              从播放列表删除
            </el-button>
          </div>
          <div class="mb-3">
            <div class="text-xs text-gray-500 mb-2">选择播放列表 进行批量操作</div>
            <div class="space-y-1 max-h-48 overflow-y-auto border rounded p-1">
              <div
                v-for="playlist in playlistCollection"
                :key="playlist.id"
                class="flex items-center justify-between px-2 py-1.5 rounded cursor-pointer hover:bg-gray-50 transition-colors"
                :class="{ 'bg-blue-50 border border-blue-200': playlist.id === selectedPlaylistId }"
                @click="handleSelectPlaylist(playlist.id)"
              >
                <span class="text-sm flex-1">{{ playlist.name }}</span>
                <span class="text-xs text-gray-500 ml-2 whitespace-nowrap">
                  {{ getMatchedFileCount(playlist) }} / {{ getPlaylistTotalFileCount(playlist) }}
                </span>
              </div>
              <div
                v-if="playlistCollection.length === 0"
                class="text-xs text-gray-400 text-center py-2"
              >
                暂无播放列表
              </div>
            </div>
          </div>
        </div>
        <div v-if="selectedPlaylist" class="flex-1 overflow-y-auto space-y-3">
          <!-- 前置文件列表（7个） -->
          <div class="border rounded p-2">
            <div class="text-xs font-semibold text-gray-600 mb-2">前置文件</div>
            <div class="space-y-1">
              <div
                v-for="(day, index) in ['周一', '周二', '周三', '周四', '周五', '周六', '周日']"
                :key="index"
                class="flex items-center gap-2"
              >
                <el-checkbox
                  :model-value="selectedPreLists.includes(index)"
                  @change="handleTogglePreList(index)"
                  size="small"
                >
                </el-checkbox>
                <span
                  class="text-xs flex-1 cursor-pointer hover:text-blue-500"
                  :class="{ 'text-blue-600 font-medium': selectedPreLists.includes(index) }"
                  @click="handleTogglePreList(index)"
                >
                  {{ day }}
                </span>
                <span class="text-xs text-gray-500 whitespace-nowrap">
                  {{ getPreMatchedFileCount(index) }} / {{ getPreFilesCount(index) }}
                </span>
              </div>
            </div>
          </div>
          <!-- 正式文件列表 -->
          <div class="border rounded p-2">
            <div class="flex items-center gap-2 mb-2">
              <el-checkbox
                :model-value="selectedFilesList"
                @change="handleToggleFilesList"
                size="small"
              >
              </el-checkbox>
              <span
                class="text-xs font-semibold text-gray-600 cursor-pointer hover:text-blue-500 flex-1"
                :class="{ 'text-blue-600': selectedFilesList }"
                @click="handleToggleFilesList()"
              >
                正式文件
              </span>
              <span class="text-xs text-gray-500 whitespace-nowrap">
                {{ getFilesListMatchedCount() }} / {{ getFilesListCount() }}
              </span>
            </div>
          </div>
        </div>
        <div v-else class="flex-1 flex items-center justify-center text-sm text-gray-400">
          请先选择一个播放列表
        </div>
      </div>
    </div>

    <!-- 文件浏览器对话框 -->
    <FileDialog
      :visible="fileBrowserDialogVisible"
      @update:visible="fileBrowserDialogVisible = $event"
      title="选择文件添加到Batch"
      confirm-button-text="添加"
      :confirm-loading="fileBrowserLoading"
      @confirm="handleFileBrowserConfirm"
      @close="handleCloseFileBrowser"
    >
    </FileDialog>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus, Delete, Edit } from "@element-plus/icons-vue";
import { getRdsData, setRdsData } from "@/api/rds";
import { logAndNoticeError } from "@/utils";
import FileDialog from "@/views/dialogs/FileDialog.vue";

import type { PlaylistItem } from "@/types/playlist";

interface Playlist {
  id: string;
  name: string;
  pre_lists?: PlaylistItem[][];
  playlist?: PlaylistItem[];
}

interface Batch {
  id: string;
  name: string;
  files: Array<{ uri: string } | string>;
  createTime?: string;
}

interface FileItem {
  uri?: string;
  [key: string]: unknown;
}

interface Props {
  visible?: boolean;
  playlistCollection?: Playlist[];
  onAddFiles?: (data: {
    playlistId: string;
    files: string[];
    preLists: number[];
    filesList: boolean;
  }) => Promise<void> | void;
  onRemoveFiles?: (data: {
    playlistId: string;
    files: string[];
    preLists: number[];
    filesList: boolean;
  }) => Promise<void> | void;
}

const props = withDefaults(defineProps<Props>(), {
  visible: false,
  playlistCollection: () => [],
  onAddFiles: undefined,
  onRemoveFiles: undefined,
});

const emit = defineEmits<{
  "update:visible": [value: boolean];
  refresh: [];
}>();

const RDS_TABLE = "t_batch_list";
const RDS_ID = "0";
const PRE_LISTS_COUNT = 7;

const batchList = ref<Batch[]>([]);
const selectedBatchId = ref<string | null>(null);
const selectedPlaylistId = ref<string | null>(null);
const selectedPreLists = ref<number[]>([]);
const selectedFilesList = ref(false);
const selectedFileIndices = ref<number[]>([]);
const fileBrowserDialogVisible = ref(false);
const fileBrowserLoading = ref(false);
const loading = ref(false);
const internalVisible = ref(props.visible);

// 计算属性
const selectedBatch = computed(() => {
  return batchList.value.find(b => b.id === selectedBatchId.value) || null;
});

const selectedPlaylist = computed(() => {
  return props.playlistCollection.find(p => p.id === selectedPlaylistId.value) || null;
});

const hasSelectedLists = computed(() => {
  return selectedPreLists.value.length > 0 || selectedFilesList.value;
});

// 辅助函数
const getFileUri = (file: FileItem | string): string => {
  if (typeof file === "string") return file;
  return file?.uri || String(file);
};

const getSelectedFiles = (): Array<FileItem | string> => {
  if (!selectedBatch.value?.files) return [];
  return selectedFileIndices.value
    .map(index => selectedBatch.value!.files[index])
    .filter(f => f !== null);
};

const getSelectedFileUris = (): Set<string> => {
  return new Set(getSelectedFiles().map(getFileUri));
};

const isValidPreLists = (playlist: Playlist | null): boolean => {
  return !!(
    playlist?.pre_lists &&
    Array.isArray(playlist.pre_lists) &&
    playlist.pre_lists.length === PRE_LISTS_COUNT
  );
};

const isValidFilesList = (playlist: Playlist | null): boolean => {
  return !!(playlist?.playlist && Array.isArray(playlist.playlist));
};

const countMatchedFiles = (fileList: PlaylistItem[], uriSet: Set<string>): number => {
  if (!Array.isArray(fileList)) return 0;
  let count = 0;
  fileList.forEach(file => {
    if (uriSet.has(getFileUri(file))) {
      count++;
    }
  });
  return count;
};

const getPreFilesCount = (weekdayIndex: number): number => {
  const playlist = selectedPlaylist.value;
  if (!isValidPreLists(playlist)) return 0;
  const preList = playlist!.pre_lists![weekdayIndex];
  return Array.isArray(preList) ? preList.length : 0;
};

const getPreMatchedFileCount = (weekdayIndex: number): number => {
  if (!selectedBatch.value || !selectedPlaylist.value) return 0;
  const uriSet = getSelectedFileUris();
  if (uriSet.size === 0) return 0;
  const playlist = selectedPlaylist.value;
  if (!isValidPreLists(playlist)) return 0;
  const preList = playlist!.pre_lists![weekdayIndex];
  return countMatchedFiles(preList, uriSet);
};

const getFilesListCount = (): number => {
  const playlist = selectedPlaylist.value;
  if (!isValidFilesList(playlist)) return 0;
  return playlist!.playlist!.length;
};

const getFilesListMatchedCount = (): number => {
  if (!selectedBatch.value || !selectedPlaylist.value) return 0;
  const uriSet = getSelectedFileUris();
  if (uriSet.size === 0) return 0;
  const playlist = selectedPlaylist.value;
  if (!isValidFilesList(playlist)) return 0;
  return countMatchedFiles(playlist!.playlist!, uriSet);
};

const getPlaylistTotalFileCount = (playlist: Playlist): number => {
  if (!playlist) return 0;
  let count = 0;
  if (isValidPreLists(playlist)) {
    playlist.pre_lists!.forEach(preList => {
      if (Array.isArray(preList)) {
        count += preList.length;
      }
    });
  }
  if (isValidFilesList(playlist)) {
    count += playlist.playlist!.length;
  }
  return count;
};

const getMatchedFileCount = (playlist: Playlist): number => {
  if (!selectedBatch.value || !playlist) return 0;
  const uriSet = getSelectedFileUris();
  if (uriSet.size === 0) return 0;
  let matchedCount = 0;
  if (isValidPreLists(playlist)) {
    playlist.pre_lists!.forEach(preList => {
      matchedCount += countMatchedFiles(preList, uriSet);
    });
  }
  if (isValidFilesList(playlist)) {
    matchedCount += countMatchedFiles(playlist.playlist!, uriSet);
  }
  return matchedCount;
};

const loadBatchList = async () => {
  try {
    loading.value = true;
    const data = await getRdsData(RDS_TABLE, RDS_ID);

    let parsedList: Batch[] = [];

    if (data !== null && data !== undefined) {
      if (typeof data === "string" && data.trim() !== "") {
        try {
          const parsed = JSON.parse(data);
          parsedList = Array.isArray(parsed) ? parsed : [];
        } catch (e) {
          parsedList = [];
        }
      } else if (Array.isArray(data)) {
        parsedList = data;
      }
    }

    batchList.value = parsedList;
    selectFirstBatchAndFiles();
  } catch (error) {
    batchList.value = [];
    logAndNoticeError(error as Error, "加载Batch列表失败");
  } finally {
    loading.value = false;
  }
};

const saveBatchList = async () => {
  try {
    const dataToSave = JSON.stringify(batchList.value);
    await setRdsData(RDS_TABLE, RDS_ID, dataToSave);
  } catch (error) {
    logAndNoticeError(error as Error, "保存Batch列表失败");
    throw error;
  }
};

const selectFirstBatchAndFiles = () => {
  if (batchList.value.length === 0 || selectedBatchId.value) return;
  const firstBatch = batchList.value[0];
  selectedBatchId.value = firstBatch.id;
  if (firstBatch?.files?.length > 0) {
    selectedFileIndices.value = firstBatch.files.map((_, index) => index);
  }
};

const toggleArrayItem = <T,>(array: T[], item: T) => {
  const index = array.indexOf(item);
  if (index > -1) {
    array.splice(index, 1);
  } else {
    array.push(item);
  }
};

const handleCreateBatch = async () => {
  try {
    const { value } = await ElMessageBox.prompt("请输入Batch名称", "创建Batch", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      inputPlaceholder: "Batch名称",
      inputValidator: val => (!!val && val.trim().length > 0) || "名称不能为空",
    });
    const name = value.trim();
    const newBatch: Batch = {
      id: Date.now().toString(),
      name,
      files: [],
      createTime: new Date().toISOString(),
    };
    batchList.value.push(newBatch);
    await saveBatchList();
    ElMessage.success("Batch创建成功");
    selectedBatchId.value = newBatch.id;
  } catch (error) {
    if (error !== "cancel") {
      logAndNoticeError(error as Error, "创建Batch失败");
    }
  }
};

const handleEditBatch = async (batchId: string) => {
  const batch = batchList.value.find(b => b.id === batchId);
  if (!batch) return;
  try {
    const { value } = await ElMessageBox.prompt("请输入Batch名称", "编辑Batch", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      inputValue: batch.name,
      inputPlaceholder: "Batch名称",
      inputValidator: val => (!!val && val.trim().length > 0) || "名称不能为空",
    });
    batch.name = value.trim();
    await saveBatchList();
    ElMessage.success("Batch名称已更新");
  } catch (error) {
    if (error !== "cancel") {
      logAndNoticeError(error as Error, "编辑Batch失败");
    }
  }
};

const handleDeleteBatch = async (batchId: string) => {
  const batch = batchList.value.find(b => b.id === batchId);
  if (!batch) return;
  try {
    await ElMessageBox.confirm(`确定要删除Batch "${batch.name}" 吗？`, "确认删除", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    });
    const index = batchList.value.findIndex(b => b.id === batchId);
    if (index > -1) {
      batchList.value.splice(index, 1);
      await saveBatchList();
      if (selectedBatchId.value === batchId) {
        selectedBatchId.value = null;
      }
      ElMessage.success("Batch已删除");
    }
  } catch (error) {
    if (error !== "cancel") {
      logAndNoticeError(error as Error, "删除Batch失败");
    }
  }
};

const handleSelectBatch = (batchId: string) => {
  selectedBatchId.value = batchId;
  const batch = batchList.value.find(b => b.id === batchId);
  if (batch && batch.files && batch.files.length > 0) {
    selectedFileIndices.value = batch.files.map((_, index) => index);
  } else {
    selectedFileIndices.value = [];
  }
};

const handleToggleFileSelection = (index: number) => {
  toggleArrayItem(selectedFileIndices.value, index);
};

const handleDeleteSelectedFiles = async () => {
  if (!selectedBatch.value || selectedFileIndices.value.length === 0) {
    return;
  }
  try {
    const selectedCount = selectedFileIndices.value.length;
    await ElMessageBox.confirm(`确定要删除选中的 ${selectedCount} 个文件吗？`, "确认删除", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    });
    const indicesToDelete = [...new Set(selectedFileIndices.value)].sort((a, b) => b - a);
    indicesToDelete.forEach(index => {
      if (index >= 0 && index < selectedBatch.value!.files.length) {
        selectedBatch.value!.files.splice(index, 1);
      }
    });
    if (selectedBatch.value.files.length > 0) {
      selectedFileIndices.value = selectedBatch.value.files.map((_, index) => index);
    } else {
      selectedFileIndices.value = [];
    }
    await saveBatchList();
    ElMessage.success(`已删除 ${selectedCount} 个文件`);
  } catch (error) {
    if (error !== "cancel") {
      logAndNoticeError(error as Error, "删除失败");
    }
  }
};

const handleOpenFileBrowser = () => {
  if (!selectedBatch.value) {
    ElMessage.warning("请先选择一个Batch");
    return;
  }
  fileBrowserDialogVisible.value = true;
};

const handleFileBrowserConfirm = async (filePaths: string[]) => {
  if (!selectedBatch.value || filePaths.length === 0) return;
  try {
    fileBrowserLoading.value = true;
    const batch = selectedBatch.value;
    const existingUris = new Set(batch.files.map(getFileUri));

    const newFiles = filePaths
      .filter(filePath => !existingUris.has(filePath))
      .map(filePath => ({ uri: filePath }));

    batch.files.push(...newFiles);

    await saveBatchList();
    if (batch.files.length > 0) {
      selectedFileIndices.value = batch.files.map((_, index) => index);
    }
    ElMessage.success(`成功添加 ${newFiles.length} 个文件`);
    fileBrowserDialogVisible.value = false;
  } catch (error) {
    logAndNoticeError(error as Error, "添加文件失败");
  } finally {
    fileBrowserLoading.value = false;
  }
};

const handleCloseFileBrowser = () => {
  fileBrowserDialogVisible.value = false;
};

const handleSelectPlaylist = (playlistId: string) => {
  selectedPlaylistId.value = selectedPlaylistId.value === playlistId ? null : playlistId;
  selectedPreLists.value = [];
  selectedFilesList.value = false;
};

const handleTogglePreList = (weekdayIndex: number) => {
  toggleArrayItem(selectedPreLists.value, weekdayIndex);
};

const handleToggleFilesList = (checked?: boolean) => {
  selectedFilesList.value = checked !== undefined ? checked : !selectedFilesList.value;
};

const validateOperation = (): boolean => {
  if (
    !selectedBatch.value ||
    !selectedPlaylistId.value ||
    selectedFileIndices.value.length === 0 ||
    !hasSelectedLists.value
  ) {
    ElMessage.warning("请选择Batch、播放列表和目标列表，并至少选中一个文件");
    return false;
  }
  return true;
};

const handleAddFilesToPlaylist = async () => {
  if (!validateOperation()) return;

  try {
    const fileUris = getSelectedFiles().map(getFileUri);

    await ElMessageBox.confirm(
      `确定要将选中的 ${fileUris.length} 个文件添加到选中的列表吗？`,
      "确认添加",
      {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      }
    );

    if (props.onAddFiles) {
      await props.onAddFiles({
        playlistId: selectedPlaylistId.value!,
        files: fileUris,
        preLists: selectedPreLists.value,
        filesList: selectedFilesList.value,
      });
      ElMessage.success("文件已添加到播放列表");
    }
  } catch (error) {
    if (error !== "cancel") {
      logAndNoticeError(error as Error, "添加文件失败");
    }
  }
};

const handleRemoveFilesFromPlaylist = async () => {
  if (!validateOperation()) return;

  try {
    const fileUris = getSelectedFiles().map(getFileUri);

    await ElMessageBox.confirm(
      `确定要从选中的列表中删除选中的 ${fileUris.length} 个文件吗？`,
      "确认删除",
      {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      }
    );

    if (props.onRemoveFiles) {
      await props.onRemoveFiles({
        playlistId: selectedPlaylistId.value!,
        files: fileUris,
        preLists: selectedPreLists.value,
        filesList: selectedFilesList.value,
      });
      ElMessage.success("文件已从播放列表删除");
    }
  } catch (error) {
    if (error !== "cancel") {
      logAndNoticeError(error as Error, "删除文件失败");
    }
  }
};

const handleClose = () => {
  internalVisible.value = false;
};

const resetSelection = () => {
  selectedPreLists.value = [];
  selectedFilesList.value = false;
  selectedFileIndices.value = [];
};

const clearAllSelection = () => {
  selectedBatchId.value = null;
  selectedPlaylistId.value = null;
  resetSelection();
};

const initPlaylistSelection = () => {
  if (props.playlistCollection?.length > 0) {
    selectedPlaylistId.value = props.playlistCollection[0].id;
  } else {
    selectedPlaylistId.value = null;
  }
};

watch(
  () => props.playlistCollection,
  newCollection => {
    if (newCollection?.length > 0 && !selectedPlaylistId.value) {
      selectedPlaylistId.value = newCollection[0].id;
    }
  },
  { immediate: true }
);

watch(
  () => props.visible,
  newVal => {
    internalVisible.value = newVal;
    if (newVal) {
      resetSelection();
      initPlaylistSelection();
      loadBatchList();
    } else {
      clearAllSelection();
    }
  },
  { immediate: true }
);

watch(internalVisible, newVal => {
  if (newVal !== props.visible) {
    emit("update:visible", newVal);
  }
});

onMounted(() => {
  loadBatchList();
});
</script>

