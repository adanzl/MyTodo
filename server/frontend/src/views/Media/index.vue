<template>
  <div class="p-1">
    <!-- 3列布局：播放列表 | 文件列表 | 配置详情 -->
    <div class="flex gap-4 h-[calc(100vh-150px)]">
      <!-- 第一列：播放列表列表 -->
      <PlaylistList
        :playlist-collection="playlistCollection"
        :active-playlist-id="activePlaylistId"
        :refreshing="playlistRefreshing"
        @select="handleSelectPlaylist"
        @create="handleCreatePlaylist"
        @refresh="refreshPlaylistStatus"
        @open-device-list="handleOpenAgentListDialog"
        @menu-command="handlePlaylistMenuCommand"
      >
      </PlaylistList>

      <!-- 第二列：文件列表 -->
      <FileListPanel
        :playlist-status="playlistStatus"
        :active-playlist-id="activePlaylistId"
        :editing-playlist-id="editingPlaylistId"
        v-model:editing-playlist-name="editingPlaylistName"
        :selected-weekday-index="selectedWeekdayIndex"
        :pre-files-drag-mode="preFilesDragMode"
        :pre-files-batch-delete-mode="preFilesBatchDeleteMode"
        :selected-pre-file-indices="selectedPreFileIndices"
        :pre-files-expanded="preFilesExpanded"
        :files-drag-mode="filesDragMode"
        :files-batch-delete-mode="filesBatchDeleteMode"
        :selected-file-indices="selectedFileIndices"
        :playlist-loading="playlistLoading"
        :playing="playing"
        :stopping="stopping"
        :show-more-actions="showMoreActions"
        :is-file-playing="isFilePlaying"
        :get-file-play-progress="getFilePlayProgress"
        :get-file-duration="getFileDuration"
        @start-edit-name="handleStartEditPlaylistName"
        @save-name="handleSavePlaylistName"
        @cancel-edit-name="handleCancelEditPlaylistName"
        @open-batch-drawer="batchDrawerVisible = true"
        @play="handlePlayPlaylist"
        @play-pre="handlePlayPre"
        @play-next="handlePlayNext"
        @stop="handleStopPlaylist"
        @clear="handleClearPlaylist"
        @toggle-more-actions="showMoreActions = !showMoreActions"
        @select-weekday="handleSelectWeekday"
        @open-file-browser-for-pre-files="handleOpenFileBrowserForPreFiles"
        @toggle-pre-files-drag-mode="handleTogglePreFilesDragMode"
        @toggle-pre-files-batch-delete-mode="handleTogglePreFilesBatchDeleteMode"
        @batch-delete-pre-files="handleBatchDeletePreFiles"
        @clear-pre-files="handleClearPreFiles"
        @toggle-pre-files-expand="preFilesExpanded = !preFilesExpanded"
        @toggle-pre-file-selection="handleTogglePreFileSelection"
        @pre-file-drag-start="handlePreFileDragStart"
        @pre-file-drag-end="handlePreFileDragEnd"
        @pre-file-drag-over="handlePreFileDragOver"
        @pre-file-drop="handlePreFileDrop"
        @open-file-browser="handleOpenFileBrowser"
        @toggle-files-drag-mode="handleToggleFilesDragMode"
        @toggle-files-batch-delete-mode="handleToggleFilesBatchDeleteMode"
        @batch-delete-files="handleBatchDeleteFiles"
        @clear-files="handleClearFiles"
        @toggle-file-selection="handleToggleFileSelection"
        @file-drag-start="handleFileDragStart"
        @file-drag-end="handleFileDragEnd"
        @file-drag-over="handleFileDragOver"
        @file-drop="handleFileDrop"
        @play-file="handlePlayFileInBrowser"
        @seek-file="handleSeekFile"
        @move-pre-file-up="handleMovePreFileUp"
        @move-pre-file-down="handleMovePreFileDown"
        @replace-pre-file="handleReplacePreFile"
        @open-playlist-selector-for-pre-file="handleOpenPlaylistSelectorForPreFile"
        @delete-pre-file="handleDeletePreFile"
        @move-file-up="handleMovePlaylistItemUp"
        @move-file-down="handleMovePlaylistItemDown"
        @replace-file="handleReplacePlaylistItem"
        @open-playlist-selector-for-file="handleOpenPlaylistSelectorForFile"
        @delete-file="handleDeletePlaylistItem"
      >
      </FileListPanel>

      <!-- 第三列：配置详情（Cron + 设备） -->
      <ConfigPanel
        :playlist-status="playlistStatus"
        :connected-device-list="connectedDeviceList"
        :dlna-device-list="dlnaDeviceList"
        :mi-device-list="miDeviceList"
        :loading="loading"
        :dlna-scanning="dlnaScanning"
        :mi-scanning="miScanning"
        :on-toggle-cron-enabled="handleTogglePlaylistCronEnabled"
        :on-update-cron="handleUpdatePlaylistCron"
        :on-update-duration="handleUpdatePlaylistDuration"
        :on-update-trigger-button="handleUpdateTriggerButton"
        :on-open-cron-builder="handleOpenCronBuilder"
        :on-preview-cron="handlePreviewPlaylistCron"
        :on-update-device-type="handleUpdatePlaylistDeviceType"
        :on-update-device-address="handleUpdatePlaylistDeviceAddress"
        :on-select-bluetooth-device="handleSelectBluetoothDevice"
        :on-select-agent-device="handleSelectAgentDevice"
        :on-select-mi-device="handleSelectMiDevice"
        :on-scan-dlna-devices="scanDlnaDevices"
        :on-scan-mi-devices="scanMiDevices"
        :on-open-scan-dialog="handleOpenScanDialog"
      ></ConfigPanel>
    </div>

    <!-- 文件浏览对话框 -->
    <FileDialog
      :visible="fileBrowserDialogVisible"
      @update:visible="fileBrowserDialogVisible = $event"
      title="选择文件添加到播放列表"
      confirm-button-text="添加"
      :confirm-loading="playlistLoading"
      @confirm="handleFileBrowserConfirm"
      @close="handleCloseFileBrowser"
    >
      <template #footer-prepend>
        <el-select v-model="fileBrowserTarget" size="small" class="w-[150px]">
          <el-option label="添加到主列表" value="files"></el-option>
          <el-option label="添加到前置列表" value="pre_files"></el-option>
        </el-select>
      </template>
    </FileDialog>

    <!-- Cron 可视化生成弹窗 -->
    <CronDialog
      :visible="cronBuilderVisible"
      :initial-cron="initialCronExpr"
      @update:visible="cronBuilderVisible = $event"
      @apply="handleCronBuilderApply"
      @preview="handleCronBuilderPreview"
      @close="handleCloseCronBuilder"
    >
    </CronDialog>

    <!-- Cron 预览弹窗 -->
    <CronPreviewDialog
      :visible="cronPreviewVisible"
      :times="cronPreviewTimes"
      @update:visible="cronPreviewVisible = $event"
      @close="cronPreviewVisible = false"
    >
    </CronPreviewDialog>

    <!-- 扫描设备弹窗 -->
    <ScanDeviceDialog
      :visible="scanDialogVisible"
      :device-list="deviceList"
      :loading="loading"
      @update:visible="scanDialogVisible = $event"
      @refresh="handleUpdateDeviceList"
      @connect="handleConnectDevice"
      @close="handleCloseScanDialog"
    >
    </ScanDeviceDialog>

    <!-- Agent设备列表弹窗 -->
    <DevicesDialog
      :visible="agentListDialogVisible"
      @update:visible="agentListDialogVisible = $event"
    >
    </DevicesDialog>

    <!-- 批量操作抽屉 -->
    <BatchDrawer
      :visible="batchDrawerVisible"
      :playlist-collection="playlistCollection"
      @update:visible="batchDrawerVisible = $event"
      @refresh="refreshPlaylistStatus"
      :on-add-files="handleBatchAddFiles"
      :on-remove-files="handleBatchRemoveFiles"
    >
    </BatchDrawer>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";
import { ElMessage } from "element-plus";
import { logAndNoticeError } from "@/utils/error";
import FileDialog from "@/components/dialogs/FileDialog.vue";
import CronDialog from "@/components/dialogs/CronDialog.vue";
import CronPreviewDialog from "@/components/dialogs/CronPreviewDialog.vue";
import PlaylistList from "./PlaylistList.vue";
import FileListPanel from "./FileListPanel.vue";
import ConfigPanel from "./ConfigPanel.vue";
import ScanDeviceDialog from "./ScanDeviceDialog.vue";
import DevicesDialog from "@/components/dialogs/DevicesDialog.vue";
import BatchDrawer from "@/components/drawers/BatchDrawer.vue";
import { getWeekdayIndex } from "@/utils/date";
import { usePlaylistState } from "./composables/usePlaylistState";
import { usePlaylistData } from "./composables/usePlaylistData";
import { usePlaylistOperations } from "./composables/usePlaylistOperations";
import { useCronManagement } from "./composables/useCronManagement";
import { useDeviceManagement } from "./composables/useDeviceManagement";
import { useAudioPlayback } from "./composables/useAudioPlayback";
import { useFileOperations } from "./composables/useFileOperations";
import { useDragAndDrop } from "./composables/useDragAndDrop";
import { usePlaylistNameEdit } from "./composables/usePlaylistNameEdit";

// 状态管理 - 使用 composable
const {
  playlistCollection,
  activePlaylistId,
  playlistStatus,
  playlistLoading,
  playlistRefreshing,
  playing,
  stopping,
  showMoreActions,
  editingPlaylistId,
  editingPlaylistName,
  fileBrowserDialogVisible,
  fileBrowserTarget,
  replaceFileInfo,
  selectedWeekdayIndex,
  preFilesDragMode,
  filesDragMode,
  preFilesBatchDeleteMode,
  filesBatchDeleteMode,
  selectedPreFileIndices,
  selectedFileIndices,
  preFilesExpanded,
  playlistSelectorVisible,
  playlistSelectorSelectedFiles,
  batchDrawerVisible,
  cronBuilderVisible,
  cronPreviewVisible,
  cronPreviewTimes,
  initialCronExpr,
  agentListDialogVisible,
  scanDialogVisible,
  loading,
  deviceList,
  connectedDeviceList,
  dlnaDeviceList,
  dlnaScanning,
  miDeviceList,
  miScanning,
  pendingDeviceType,
  preFilesSortOrder,
  filesSortOrder,
  preFilesOriginalOrder,
  filesOriginalOrder,
} = usePlaylistState();

// 音频播放 - 使用 composable
const {
  handlePlayFileInBrowser,
  isFilePlaying,
  getFilePlayProgress,
  getFileDuration,
  handleSeekFile,
} = useAudioPlayback();

// 工具函数
const getSelectedWeekdayIndex = () => {
  return selectedWeekdayIndex.value !== null ? selectedWeekdayIndex.value : getWeekdayIndex();
};

const getCurrentPreFiles = () => {
  const status = playlistStatus.value;
  if (!status || !status.pre_lists) return [];
  const weekdayIndex = getSelectedWeekdayIndex();
  if (!Array.isArray(status.pre_lists) || status.pre_lists.length !== 7) return [];
  return status.pre_lists[weekdayIndex] || [];
};

// 数据管理 - 使用 composable（需要先定义，因为其他 composables 依赖它）
const {
  savePlaylist,
  syncActivePlaylist,
  updateActivePlaylistData,
  loadPlaylist,
  refreshPlaylistStatus,
} = usePlaylistData(
  playlistCollection,
  activePlaylistId,
  playlistStatus,
  playlistRefreshing,
  pendingDeviceType,
  preFilesDragMode,
  filesDragMode,
  getSelectedWeekdayIndex
);

// 文件操作 - 使用 composable
const {
  handleOpenFileBrowser,
  handleOpenFileBrowserForPreFiles,
  handleFileBrowserConfirm,
  handleCloseFileBrowser,
  handleMovePlaylistItemUp,
  handleMovePlaylistItemDown,
  handleDeletePlaylistItem,
  handleReplacePlaylistItem,
  handleMovePreFileUp,
  handleMovePreFileDown,
  handleDeletePreFile,
  handleReplacePreFile,
  handleTogglePreFilesBatchDeleteMode,
  handleToggleFilesBatchDeleteMode,
  handleTogglePreFileSelection,
  handleToggleFileSelection,
  handleBatchDeletePreFiles,
  handleBatchDeleteFiles,
  handleClearPreFiles,
  handleClearFiles,
  handleClearPlaylist,
  handleOpenPlaylistSelectorForPreFile,
  handleOpenPlaylistSelectorForFile,
} = useFileOperations(
  playlistCollection,
  playlistStatus,
  playlistLoading,
  fileBrowserDialogVisible,
  fileBrowserTarget,
  replaceFileInfo,
  selectedWeekdayIndex,
  preFilesBatchDeleteMode,
  filesBatchDeleteMode,
  selectedPreFileIndices,
  selectedFileIndices,
  updateActivePlaylistData,
  getCurrentPreFiles,
  playlistSelectorVisible,
  playlistSelectorSelectedFiles
);

// 拖拽操作 - 使用 composable
const {
  handleTogglePreFilesDragMode,
  handleToggleFilesDragMode,
  handlePreFileDragStart,
  handlePreFileDragEnd,
  handlePreFileDragOver,
  handlePreFileDrop,
  handleFileDragStart,
  handleFileDragEnd,
  handleFileDragOver,
  handleFileDrop,
} = useDragAndDrop(
  playlistCollection,
  playlistStatus,
  playlistLoading,
  preFilesDragMode,
  filesDragMode,
  preFilesSortOrder,
  filesSortOrder,
  preFilesOriginalOrder,
  filesOriginalOrder,
  selectedWeekdayIndex,
  updateActivePlaylistData,
  syncActivePlaylist,
  getCurrentPreFiles
);

// 播放列表名称编辑 - 使用 composable
const { handleStartEditPlaylistName, handleSavePlaylistName, handleCancelEditPlaylistName } =
  usePlaylistNameEdit(
    playlistCollection,
    activePlaylistId,
    editingPlaylistId,
    editingPlaylistName,
    savePlaylist,
    syncActivePlaylist
  );

// Cron 管理 - 使用 composable
const {
  handleOpenCronBuilder,
  handleCloseCronBuilder,
  handleCronBuilderApply,
  handleCronBuilderPreview,
  handleTogglePlaylistCronEnabled,
  handleUpdatePlaylistCron,
  handleUpdatePlaylistDuration,
  handleUpdateTriggerButton,
  handlePreviewPlaylistCron,
} = useCronManagement(
  playlistStatus,
  cronBuilderVisible,
  cronPreviewVisible,
  cronPreviewTimes,
  initialCronExpr,
  updateActivePlaylistData
);

// 设备管理 - 使用 composable
const {
  refreshConnectedList,
  handleConnectDevice,
  scanDlnaDevices,
  scanMiDevices,
  handleUpdateDeviceList,
  handleOpenScanDialog,
  handleCloseScanDialog,
  handleUpdatePlaylistDeviceType,
  handleUpdatePlaylistDeviceAddress,
  handleSelectBluetoothDevice,
  handleSelectAgentDevice,
  handleSelectMiDevice,
  handleOpenAgentListDialog: handleOpenAgentListDialogDevice,
} = useDeviceManagement(
  playlistStatus,
  pendingDeviceType,
  connectedDeviceList,
  dlnaDeviceList,
  miDeviceList,
  deviceList,
  loading,
  dlnaScanning,
  miScanning,
  scanDialogVisible,
  agentListDialogVisible,
  updateActivePlaylistData
);

// 播放列表操作 - 使用 composable
const {
  handleSelectPlaylist: handleSelectPlaylistBase,
  handleCreatePlaylist,
  handleCopyPlaylist,
  handleDeletePlaylistGroup,
  handlePlayPlaylist,
  handlePlayNext,
  handlePlayPre,
  handleStopPlaylist,
} = usePlaylistOperations(
  playlistCollection,
  activePlaylistId,
  playlistStatus,
  playing,
  stopping,
  syncActivePlaylist,
  updateActivePlaylistData,
  refreshPlaylistStatus,
  getCurrentPreFiles
);

// 选择播放列表（扩展功能）
const handleSelectPlaylist = async (playlistId: string) => {
  await handleSelectPlaylistBase(playlistId);
  pendingDeviceType.value = null;
  // 重置排序状态
  preFilesSortOrder.value = null;
  filesSortOrder.value = null;
  preFilesDragMode.value = false;
  filesDragMode.value = false;
  preFilesOriginalOrder.value = null;
  filesOriginalOrder.value = null;
  // 重置批量删除状态
  preFilesBatchDeleteMode.value = false;
  filesBatchDeleteMode.value = false;
  selectedPreFileIndices.value = [];
  selectedFileIndices.value = [];
  await refreshConnectedList();
};

// 播放列表菜单命令
const handlePlaylistMenuCommand = async (command: string, playlistId: string) => {
  if (command === "delete") {
    await handleDeletePlaylistGroup(playlistId);
  } else if (command === "copy") {
    await handleCopyPlaylist(playlistId);
  }
};

// 批量添加文件到播放列表
const handleBatchAddFiles = async (data: {
  playlistId: string;
  files: string[];
  preLists: number[];
  filesList: boolean;
}) => {
  try {
    playlistLoading.value = true;
    const playlist = playlistCollection.value.find(p => p.id === data.playlistId);
    if (!playlist) {
      ElMessage.warning("播放列表不存在");
      return;
    }

    await updateActivePlaylistData(playlistInfo => {
      if (playlistInfo.id !== data.playlistId) {
        return playlistInfo;
      }

      // 添加文件到前置列表
      if (data.preLists.length > 0) {
        if (
          !playlistInfo.pre_lists ||
          !Array.isArray(playlistInfo.pre_lists) ||
          playlistInfo.pre_lists.length !== 7
        ) {
          playlistInfo.pre_lists = Array(7)
            .fill(null)
            .map(() => []);
        }
        data.preLists.forEach(weekdayIndex => {
          if (weekdayIndex >= 0 && weekdayIndex < 7) {
            const existingUris = new Set(
              (playlistInfo.pre_lists[weekdayIndex] || []).map((item: any) => item?.uri || item)
            );
            data.files.forEach(fileUri => {
              if (!existingUris.has(fileUri)) {
                if (!playlistInfo.pre_lists[weekdayIndex]) {
                  playlistInfo.pre_lists[weekdayIndex] = [];
                }
                playlistInfo.pre_lists[weekdayIndex].push({ uri: fileUri });
              }
            });
          }
        });
      }

      // 添加文件到正式列表
      if (data.filesList) {
        if (!Array.isArray(playlistInfo.playlist)) {
          playlistInfo.playlist = [];
        }
        const existingUris = new Set(playlistInfo.playlist.map((item: any) => item?.uri || item));
        data.files.forEach(fileUri => {
          if (!existingUris.has(fileUri)) {
            playlistInfo.playlist.push({ uri: fileUri });
          }
        });
        playlistInfo.total = playlistInfo.playlist.length;
      }

      return playlistInfo;
    });

    // 同步到 collection
    syncActivePlaylist(playlistCollection.value);
    await savePlaylist(playlistCollection.value);
  } catch (error) {
    logAndNoticeError(error as Error, "批量添加文件失败");
  } finally {
    playlistLoading.value = false;
  }
};

// 批量从播放列表删除文件
const handleBatchRemoveFiles = async (data: {
  playlistId: string;
  files: string[];
  preLists: number[];
  filesList: boolean;
}) => {
  try {
    playlistLoading.value = true;
    const playlist = playlistCollection.value.find(p => p.id === data.playlistId);
    if (!playlist) {
      ElMessage.warning("播放列表不存在");
      return;
    }

    const fileUriSet = new Set(data.files);

    await updateActivePlaylistData(playlistInfo => {
      if (playlistInfo.id !== data.playlistId) {
        return playlistInfo;
      }

      // 从前置列表删除文件
      if (data.preLists.length > 0) {
        if (
          playlistInfo.pre_lists &&
          Array.isArray(playlistInfo.pre_lists) &&
          playlistInfo.pre_lists.length === 7
        ) {
          data.preLists.forEach(weekdayIndex => {
            if (weekdayIndex >= 0 && weekdayIndex < 7 && playlistInfo.pre_lists[weekdayIndex]) {
              playlistInfo.pre_lists[weekdayIndex] = playlistInfo.pre_lists[weekdayIndex].filter(
                (item: any) => !fileUriSet.has(item?.uri || item)
              );
            }
          });
        }
      }

      // 从正式列表删除文件
      if (data.filesList && Array.isArray(playlistInfo.playlist)) {
        playlistInfo.playlist = playlistInfo.playlist.filter(
          (item: any) => !fileUriSet.has(item?.uri || item)
        );
        playlistInfo.total = playlistInfo.playlist.length;
        if (playlistInfo.playlist.length === 0) {
          playlistInfo.current_index = 0;
        } else if (playlistInfo.current_index >= playlistInfo.playlist.length) {
          playlistInfo.current_index = playlistInfo.playlist.length - 1;
        }
      }

      return playlistInfo;
    });

    // 同步到 collection
    syncActivePlaylist(playlistCollection.value);
    await savePlaylist(playlistCollection.value);
  } catch (error) {
    logAndNoticeError(error as Error, "批量删除文件失败");
  } finally {
    playlistLoading.value = false;
  }
};

// 打开设备列表对话框（扩展功能）
const handleOpenAgentListDialog = async () => {
  await handleOpenAgentListDialogDevice();
};

// 切换星期按钮
const handleSelectWeekday = (weekdayIndex: number) => {
  selectedWeekdayIndex.value = weekdayIndex;
  // 重新同步当前播放列表状态，以更新显示的 pre_files
  syncActivePlaylist(playlistCollection.value);
};

// 定时器
let statusRefreshTimer: any = null;

// 初始化
onMounted(async () => {
  await loadPlaylist();

  await refreshConnectedList();

  // 启动定时器，每5秒刷新一次当前播放列表状态
  statusRefreshTimer = setInterval(async () => {
    try {
      await refreshPlaylistStatus(true, true);
    } catch (error) {
      console.error("定时刷新播放列表状态失败:", error);
    }
  }, 5000);
});

onUnmounted(() => {
  if (statusRefreshTimer) {
    clearInterval(statusRefreshTimer);
    statusRefreshTimer = null;
  }
});
</script>
