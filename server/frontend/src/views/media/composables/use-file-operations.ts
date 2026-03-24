/**
 * 文件操作 Composable
 * 处理文件的增删改查、批量操作、文件浏览器等
 */
import { type Ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { logAndNoticeError } from "@/utils/error";
import { getWeekdayIndex } from "@/utils/date";
import { logger } from "@/utils/logger";
import type { Playlist, PlaylistStatus, PlaylistItem } from "@/types/playlist";
import type { MediaFile } from "@/types/tools";

// 文件输入类型（支持多种格式）
type FileInput = MediaFile | PlaylistItem | string;

export function useFileOperations(
  _playlistCollection: Ref<Playlist[]>,
  playlistStatus: Ref<PlaylistStatus | null>,
  playlistLoading: Ref<boolean>,
  fileBrowserDialogVisible: Ref<boolean>,
  fileBrowserTarget: Ref<"files" | "pre_files">,
  replaceFileInfo: Ref<{ type: "pre_files" | "files"; index: number } | null>,
  selectedWeekdayIndex: Ref<number | null>,
  preFilesBatchDeleteMode: Ref<boolean>,
  filesBatchDeleteMode: Ref<boolean>,
  selectedPreFileIndices: Ref<number[]>,
  selectedFileIndices: Ref<number[]>,
  updateActivePlaylistData: (updater: (playlistInfo: Playlist) => Playlist) => Promise<void>,
  getCurrentPreFiles: () => PlaylistItem[],
  playlistSelectorVisible?: Ref<boolean>,
  playlistSelectorSelectedFiles?: Ref<PlaylistItem[]>
) {
  const getSelectedWeekdayIndex = () => {
    return selectedWeekdayIndex.value !== null ? selectedWeekdayIndex.value : getWeekdayIndex();
  };

  // 确保 pre_lists 已初始化（7天的数组）
  const ensurePreListsInitialized = (playlistInfo: Playlist): PlaylistItem[][] => {
    if (
      !playlistInfo.pre_lists ||
      !Array.isArray(playlistInfo.pre_lists) ||
      playlistInfo.pre_lists.length !== 7
    ) {
      playlistInfo.pre_lists = Array(7)
        .fill(null)
        .map(() => []);
    }
    return playlistInfo.pre_lists;
  };

  // 验证播放列表状态
  const validatePlaylistStatus = (message = "请先选择一个播放列表"): boolean => {
    if (!playlistStatus.value) {
      ElMessage.warning(message);
      return false;
    }
    return true;
  };

  // 统一错误处理包装器（忽略取消操作）
  const handleOperationError = (error: unknown, errorMessage: string): void => {
    if (error !== "cancel") {
      logAndNoticeError(error as Error, errorMessage);
    }
  };

  // 执行带加载状态的异步操作
  const executeWithLoading = async (
    operation: () => Promise<void>,
    errorMessage: string
  ): Promise<void> => {
    try {
      playlistLoading.value = true;
      await operation();
    } catch (error) {
      handleOperationError(error, errorMessage);
    } finally {
      playlistLoading.value = false;
    }
  };

  // 打开文件浏览器（添加到正式文件列表）
  const handleOpenFileBrowser = () => {
    if (!validatePlaylistStatus()) return;
    fileBrowserDialogVisible.value = true;
    fileBrowserTarget.value = "files";
    replaceFileInfo.value = null;
  };

  // 打开文件浏览器（添加到前置文件列表）
  const handleOpenFileBrowserForPreFiles = () => {
    if (!validatePlaylistStatus()) return;
    fileBrowserDialogVisible.value = true;
    fileBrowserTarget.value = "pre_files";
    replaceFileInfo.value = null;
  };

  // 文件浏览器确认
  const handleFileBrowserConfirm = async (filePaths: string[]) => {
    if (filePaths.length === 0) {
      return;
    }
    if (!playlistStatus.value) {
      ElMessage.warning("请先创建并选择一个播放列表");
      return;
    }

    try {
      playlistLoading.value = true;

      await updateActivePlaylistData(playlistInfo => {
        const weekdayIndex = getSelectedWeekdayIndex();
        const targetType = fileBrowserTarget.value;
        const targetList =
          targetType === "pre_files"
            ? Array.isArray(playlistInfo.pre_lists) && playlistInfo.pre_lists.length === 7
              ? [...(playlistInfo.pre_lists[weekdayIndex] || [])]
              : []
            : Array.isArray(playlistInfo.playlist)
              ? [...playlistInfo.playlist]
              : [];

        const existingUris = new Set<string>();
        targetList.forEach((item: PlaylistItem) => {
          if (item?.uri) {
            existingUris.add(item.uri);
          }
        });

        // 如果是替换操作
        if (replaceFileInfo.value && filePaths.length > 0) {
          const replaceIndex = replaceFileInfo.value.index;
          if (replaceFileInfo.value.type === "pre_files") {
            ensurePreListsInitialized(playlistInfo);
            const list = [...(playlistInfo.pre_lists[weekdayIndex] || [])];
            if (replaceIndex >= 0 && replaceIndex < list.length) {
              list[replaceIndex] = { uri: filePaths[0] };
              playlistInfo.pre_lists[weekdayIndex] = list;
            }
          } else {
            const list = [...playlistInfo.playlist];
            if (replaceIndex >= 0 && replaceIndex < list.length) {
              list[replaceIndex] = { uri: filePaths[0] };
              playlistInfo.playlist = list;
              playlistInfo.total = list.length;
            }
          }
          replaceFileInfo.value = null;
          return playlistInfo;
        }

        // 添加文件
        for (const filePath of filePaths) {
          if (!existingUris.has(filePath)) {
            const fileItem = {
              uri: filePath,
            };
            targetList.push(fileItem);
            existingUris.add(filePath);
          }
        }

        if (targetType === "pre_files") {
          ensurePreListsInitialized(playlistInfo);
          playlistInfo.pre_lists[weekdayIndex] = targetList;
        } else {
          playlistInfo.playlist = targetList;
          playlistInfo.total = targetList.length;
          if (targetList.length === 0) {
            playlistInfo.current_index = 0;
          } else if (playlistInfo.current_index >= targetList.length) {
            playlistInfo.current_index = targetList.length - 1;
          }
        }
        return playlistInfo;
      });

      const targetName = fileBrowserTarget.value === "pre_files" ? "前置列表" : "播放列表";
      ElMessage.success(`成功添加 ${filePaths.length} 个文件到${targetName}`);
      fileBrowserDialogVisible.value = false;
    } catch (error) {
      logAndNoticeError(error as Error, "添加文件到播放列表失败");
    } finally {
      playlistLoading.value = false;
    }
  };

  // 关闭文件浏览器
  const handleCloseFileBrowser = () => {
    fileBrowserDialogVisible.value = false;
  };

  // 上移播放列表项
  const handleMovePlaylistItemUp = async (index: number) => {
    const status = playlistStatus.value;
    if (!status || index <= 0 || index >= status.playlist.length) return;

    try {
      playlistLoading.value = true;
      await updateActivePlaylistData(playlistInfo => {
        const list = [...playlistInfo.playlist];
        [list[index - 1], list[index]] = [list[index], list[index - 1]];
        playlistInfo.playlist = list;
        if (playlistInfo.current_index === index) {
          playlistInfo.current_index = index - 1;
        } else if (playlistInfo.current_index === index - 1) {
          playlistInfo.current_index = index;
        }
        playlistInfo.total = list.length;
        return playlistInfo;
      });
      ElMessage.success("已上移");
    } catch (error) {
      logAndNoticeError(error as Error, "上移失败");
    } finally {
      playlistLoading.value = false;
    }
  };

  // 下移播放列表项
  const handleMovePlaylistItemDown = async (index: number) => {
    const status = playlistStatus.value;
    if (!status || index < 0 || index >= status.playlist.length - 1) return;

    try {
      playlistLoading.value = true;
      await updateActivePlaylistData(playlistInfo => {
        const list = [...playlistInfo.playlist];
        [list[index], list[index + 1]] = [list[index + 1], list[index]];
        playlistInfo.playlist = list;
        if (playlistInfo.current_index === index) {
          playlistInfo.current_index = index + 1;
        } else if (playlistInfo.current_index === index + 1) {
          playlistInfo.current_index = index;
        }
        playlistInfo.total = list.length;
        return playlistInfo;
      });
      ElMessage.success("已下移");
    } catch (error) {
      logAndNoticeError(error as Error, "下移失败");
    } finally {
      playlistLoading.value = false;
    }
  };

  // 删除播放列表项
  const handleDeletePlaylistItem = async (index: number) => {
    const status = playlistStatus.value;
    if (!status || index < 0 || index >= status.playlist.length) return;

    const fileItem = status.playlist[index];
    const fileName = fileItem?.uri?.split("/").pop() || "文件";

    try {
      await ElMessageBox.confirm(`确定要删除 "${fileName}" 吗？`, "确认删除", {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      });

      playlistLoading.value = true;
      await updateActivePlaylistData(playlistInfo => {
        const list = [...playlistInfo.playlist];
        list.splice(index, 1);
        playlistInfo.playlist = list;
        if (list.length === 0) {
          playlistInfo.current_index = 0;
        } else if (index < playlistInfo.current_index) {
          playlistInfo.current_index = Math.max(0, playlistInfo.current_index - 1);
        } else if (index === playlistInfo.current_index) {
          playlistInfo.current_index = Math.min(playlistInfo.current_index, list.length - 1);
        }
        playlistInfo.total = list.length;
        return playlistInfo;
      });
      ElMessage.success("已删除");
    } catch (error) {
      if (error !== "cancel") {
        logAndNoticeError(error as Error, "删除失败");
      }
    } finally {
      playlistLoading.value = false;
    }
  };

  // 替换播放列表项
  const handleReplacePlaylistItem = async (index: number) => {
    const status = playlistStatus.value;
    if (!status || index < 0 || index >= status.playlist.length) return;

    replaceFileInfo.value = {
      type: "files",
      index: index,
    };
    fileBrowserTarget.value = "files";
    fileBrowserDialogVisible.value = true;
  };

  // 上移前置文件
  const handleMovePreFileUp = async (index: number) => {
    const status = playlistStatus.value;
    const preFiles = getCurrentPreFiles();
    if (!status || !preFiles || index <= 0 || index >= preFiles.length) return;

    await executeWithLoading(async () => {
      await updateActivePlaylistData(playlistInfo => {
        const weekdayIndex = getSelectedWeekdayIndex();
        ensurePreListsInitialized(playlistInfo);
        const list = [...(playlistInfo.pre_lists[weekdayIndex] || [])];
        [list[index - 1], list[index]] = [list[index], list[index - 1]];
        playlistInfo.pre_lists[weekdayIndex] = list;
        return playlistInfo;
      });
    }, "上移失败");
  };

  // 下移前置文件
  const handleMovePreFileDown = async (index: number) => {
    const status = playlistStatus.value;
    const preFiles = getCurrentPreFiles();
    if (!status || !preFiles || index < 0 || index >= preFiles.length - 1) return;

    await executeWithLoading(async () => {
      await updateActivePlaylistData(playlistInfo => {
        const weekdayIndex = getSelectedWeekdayIndex();
        ensurePreListsInitialized(playlistInfo);
        const list = [...(playlistInfo.pre_lists[weekdayIndex] || [])];
        [list[index], list[index + 1]] = [list[index + 1], list[index]];
        playlistInfo.pre_lists[weekdayIndex] = list;
        return playlistInfo;
      });
    }, "下移失败");
  };

  // 删除前置文件
  const handleDeletePreFile = async (index: number) => {
    const status = playlistStatus.value;
    const preFiles = getCurrentPreFiles();
    if (!status || !preFiles || index < 0 || index >= preFiles.length) return;

    const fileItem = preFiles[index];
    const fileName = fileItem?.uri?.split("/").pop() || "文件";

    try {
      await ElMessageBox.confirm(`确定要删除 "${fileName}" 吗？`, "确认删除", {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      });

      await executeWithLoading(async () => {
        await updateActivePlaylistData(playlistInfo => {
          const weekdayIndex = getSelectedWeekdayIndex();
          ensurePreListsInitialized(playlistInfo);
          const list = [...(playlistInfo.pre_lists[weekdayIndex] || [])];
          list.splice(index, 1);
          playlistInfo.pre_lists[weekdayIndex] = list;
          return playlistInfo;
        });
        ElMessage.success("已删除");
      }, "删除失败");
    } catch (error) {
      handleOperationError(error, "删除失败");
    }
  };

  // 替换前置文件
  const handleReplacePreFile = async (index: number) => {
    const status = playlistStatus.value;
    const preFiles = getCurrentPreFiles();
    if (!status || !preFiles || index < 0 || index >= preFiles.length) return;

    replaceFileInfo.value = {
      type: "pre_files",
      index: index,
    };
    fileBrowserTarget.value = "pre_files";
    fileBrowserDialogVisible.value = true;
  };

  // 切换前置文件批量删除模式
  const handleTogglePreFilesBatchDeleteMode = () => {
    preFilesBatchDeleteMode.value = !preFilesBatchDeleteMode.value;
    if (!preFilesBatchDeleteMode.value) {
      selectedPreFileIndices.value = [];
    }
  };

  // 切换正式文件批量删除模式
  const handleToggleFilesBatchDeleteMode = () => {
    filesBatchDeleteMode.value = !filesBatchDeleteMode.value;
    if (!filesBatchDeleteMode.value) {
      selectedFileIndices.value = [];
    }
  };

  // 切换前置文件选中状态
  const handleTogglePreFileSelection = (index: number) => {
    const indices = selectedPreFileIndices.value;
    const pos = indices.indexOf(index);
    if (pos > -1) {
      indices.splice(pos, 1);
    } else {
      indices.push(index);
    }
  };

  // 切换正式文件选中状态
  const handleToggleFileSelection = (index: number) => {
    const indices = selectedFileIndices.value;
    const pos = indices.indexOf(index);
    if (pos > -1) {
      indices.splice(pos, 1);
    } else {
      indices.push(index);
    }
  };

  // 批量删除前置文件
  const handleBatchDeletePreFiles = async () => {
    const status = playlistStatus.value;
    const preFiles = getCurrentPreFiles();
    const selectedIndices = selectedPreFileIndices.value;
    if (!status || !preFiles || selectedIndices.length === 0) return;

    const selectedCount = selectedIndices.length;
    try {
      await ElMessageBox.confirm(
        `确定要删除选中的 ${selectedCount} 个前置文件吗？`,
        "确认批量删除",
        {
          confirmButtonText: "确定",
          cancelButtonText: "取消",
          type: "warning",
        }
      );

      await executeWithLoading(async () => {
        const indicesToDelete = [...new Set(selectedIndices)].sort((a, b) => b - a);

        await updateActivePlaylistData(playlistInfo => {
          const weekdayIndex = getSelectedWeekdayIndex();
          ensurePreListsInitialized(playlistInfo);
          const list = [...(playlistInfo.pre_lists[weekdayIndex] || [])];
          indicesToDelete.forEach(index => {
            if (index >= 0 && index < list.length) {
              list.splice(index, 1);
            }
          });
          playlistInfo.pre_lists[weekdayIndex] = list;
          return playlistInfo;
        });

        selectedPreFileIndices.value = [];
        preFilesBatchDeleteMode.value = false;
        ElMessage.success(`已删除 ${selectedCount} 个前置文件`);
      }, "批量删除失败");
    } catch (error) {
      handleOperationError(error, "批量删除失败");
    }
  };

  // 批量删除正式文件
  const handleBatchDeleteFiles = async () => {
    const status = playlistStatus.value;
    const selectedIndices = selectedFileIndices.value;
    if (!status || !status.playlist || selectedIndices.length === 0) return;

    const selectedCount = selectedIndices.length;
    try {
      await ElMessageBox.confirm(
        `确定要删除选中的 ${selectedCount} 个正式文件吗？`,
        "确认批量删除",
        {
          confirmButtonText: "确定",
          cancelButtonText: "取消",
          type: "warning",
        }
      );

      await executeWithLoading(async () => {
        const indicesToDelete = [...new Set(selectedIndices)].sort((a, b) => b - a);

        await updateActivePlaylistData(playlistInfo => {
          const list = [...playlistInfo.playlist];
          indicesToDelete.forEach(index => {
            if (index >= 0 && index < list.length) {
              list.splice(index, 1);
            }
          });
          playlistInfo.playlist = list;
          if (list.length === 0) {
            playlistInfo.current_index = 0;
          } else {
            let newCurrentIndex = playlistInfo.current_index;
            indicesToDelete.forEach(index => {
              if (index < playlistInfo.current_index) {
                newCurrentIndex = Math.max(0, newCurrentIndex - 1);
              } else if (index === playlistInfo.current_index) {
                newCurrentIndex = Math.min(newCurrentIndex, list.length - 1);
              }
            });
            playlistInfo.current_index = newCurrentIndex;
          }
          playlistInfo.total = list.length;
          return playlistInfo;
        });

        selectedFileIndices.value = [];
        filesBatchDeleteMode.value = false;
        ElMessage.success(`已删除 ${selectedCount} 个正式文件`);
      }, "批量删除失败");
    } catch (error) {
      handleOperationError(error, "批量删除失败");
    }
  };

  // 清空前置文件列表
  const handleClearPreFiles = async () => {
    const status = playlistStatus.value;
    const preFiles = getCurrentPreFiles();
    if (!status || !preFiles || preFiles.length === 0) return;

    try {
      await ElMessageBox.confirm(
        `确定要清空前置文件列表吗？此操作将删除所有 ${preFiles.length} 个前置文件。`,
        "确认清空",
        {
          confirmButtonText: "确定",
          cancelButtonText: "取消",
          type: "warning",
        }
      );

      await executeWithLoading(async () => {
        await updateActivePlaylistData(playlistInfo => {
          const weekdayIndex = getSelectedWeekdayIndex();
          ensurePreListsInitialized(playlistInfo);
          playlistInfo.pre_lists[weekdayIndex] = [];
          return playlistInfo;
        });
        ElMessage.success("已清空前置文件列表");
      }, "清空失败");
    } catch (error) {
      handleOperationError(error, "清空失败");
    }
  };

  // 清空正式文件列表
  const handleClearFiles = async () => {
    const status = playlistStatus.value;
    if (!status || !status.playlist || status.playlist.length === 0) return;

    try {
      await ElMessageBox.confirm(
        `确定要清空正式文件列表吗？此操作将删除所有 ${status.playlist.length} 个正式文件。`,
        "确认清空",
        {
          confirmButtonText: "确定",
          cancelButtonText: "取消",
          type: "warning",
        }
      );

      await executeWithLoading(async () => {
        await updateActivePlaylistData(playlistInfo => {
          playlistInfo.playlist = [];
          playlistInfo.total = 0;
          playlistInfo.current_index = 0;
          return playlistInfo;
        });
        ElMessage.success("已清空正式文件列表");
      }, "清空失败");
    } catch (error) {
      handleOperationError(error, "清空失败");
    }
  };

  // 清空播放列表（包括前置文件和正式文件）
  const handleClearPlaylist = async () => {
    const status = playlistStatus.value;
    if (!status) return;

    const preFiles = getCurrentPreFiles();
    const preFilesCount = (preFiles && preFiles.length) || 0;
    const filesCount = (status.playlist && status.playlist.length) || 0;
    const totalCount = preFilesCount + filesCount;

    if (totalCount === 0) return;

    try {
      const message =
        preFilesCount > 0 && filesCount > 0
          ? `确定要清空播放列表 "${status.name}" 吗？此操作将删除所有 ${preFilesCount} 个前置文件和 ${filesCount} 个正式文件，共 ${totalCount} 个文件。`
          : preFilesCount > 0
            ? `确定要清空播放列表 "${status.name}" 吗？此操作将删除所有 ${preFilesCount} 个前置文件。`
            : `确定要清空播放列表 "${status.name}" 吗？此操作将删除所有 ${filesCount} 个正式文件。`;

      await ElMessageBox.confirm(message, "确认清空", {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      });

      await executeWithLoading(async () => {
        await updateActivePlaylistData(playlistInfo => {
          playlistInfo.playlist = [];
          ensurePreListsInitialized(playlistInfo);
          playlistInfo.pre_lists = playlistInfo.pre_lists.map(() => []);
          playlistInfo.total = 0;
          playlistInfo.current_index = 0;
          return playlistInfo;
        });
        ElMessage.success("已清空播放列表（包括前置文件和正式文件）");
      }, "清空失败");
    } catch (error) {
      handleOperationError(error, "清空失败");
    }
  };

  // 将文件输入转换为 PlaylistItem
  const convertToPlaylistItem = (file: FileInput): PlaylistItem => {
    if (typeof file === "string") {
      return { uri: file };
    }
    return { ...file, uri: file.uri || "" };
  };

  // 打开播放列表选择器（前置文件）
  const handleOpenPlaylistSelectorForPreFile = async (file: FileInput) => {
    try {
      if (!file) {
        ElMessage.warning("文件信息无效");
        return;
      }
      if (playlistSelectorSelectedFiles && playlistSelectorVisible) {
        const playlistItem = convertToPlaylistItem(file);
        playlistSelectorSelectedFiles.value = [playlistItem];
        playlistSelectorVisible.value = true;
      } else {
        ElMessage.info("请使用文件浏览器添加文件到播放列表");
      }
    } catch (error) {
      logger.error("打开播放列表选择器失败:", error);
      ElMessage.error("打开对话框失败");
    }
  };

  // 打开播放列表选择器（正式文件）
  const handleOpenPlaylistSelectorForFile = async (file: FileInput) => {
    try {
      if (!file) {
        ElMessage.warning("文件信息无效");
        return;
      }
      const playlistItem = convertToPlaylistItem(file);
      if (!playlistItem.uri) {
        ElMessage.warning("文件URI无效");
        return;
      }
      if (playlistSelectorSelectedFiles && playlistSelectorVisible) {
        playlistSelectorSelectedFiles.value = [playlistItem];
        playlistSelectorVisible.value = true;
      } else {
        ElMessage.info("请使用文件浏览器添加文件到播放列表");
      }
    } catch (error) {
      logger.error("打开播放列表选择器失败:", error);
      ElMessage.error("打开对话框失败");
    }
  };

  return {
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
  };
}
