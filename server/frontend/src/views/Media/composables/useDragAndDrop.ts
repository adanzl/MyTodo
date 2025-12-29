/**
 * 拖拽操作 Composable
 * 处理文件的拖拽排序功能
 */
import { type Ref } from "vue";
import { ElMessage } from "element-plus";
import { logAndNoticeError } from "@/utils/error";
import { getWeekdayIndex } from "@/utils/date";
import type { Playlist, PlaylistStatus, PlaylistItem } from "@/types/playlist";

export function useDragAndDrop(
  playlistCollection: Ref<Playlist[]>,
  playlistStatus: Ref<PlaylistStatus | null>,
  playlistLoading: Ref<boolean>,
  preFilesDragMode: Ref<boolean>,
  filesDragMode: Ref<boolean>,
  preFilesSortOrder: Ref<string | null>,
  filesSortOrder: Ref<string | null>,
  preFilesOriginalOrder: Ref<PlaylistItem[] | null>,
  filesOriginalOrder: Ref<PlaylistItem[] | null>,
  selectedWeekdayIndex: Ref<number | null>,
  updateActivePlaylistData: (updater: (playlistInfo: Playlist) => Playlist) => Promise<void>,
  syncActivePlaylist: (collection: Playlist[]) => void,
  getCurrentPreFiles: () => PlaylistItem[]
) {
  const getSelectedWeekdayIndex = () => {
    return selectedWeekdayIndex.value !== null ? selectedWeekdayIndex.value : getWeekdayIndex();
  };

  // 检查两个数组的顺序是否相同
  const isOrderChanged = (original: PlaylistItem[], current: PlaylistItem[]) => {
    if (!original || !current || original.length !== current.length) {
      return true;
    }
    for (let i = 0; i < original.length; i++) {
      const origUri = original[i]?.uri || original[i];
      const currUri = current[i]?.uri || current[i];
      if (origUri !== currUri) {
        return true;
      }
    }
    return false;
  };

  // 切换前置文件拖拽排序模式
  const handleTogglePreFilesDragMode = async () => {
    if (preFilesDragMode.value) {
      // 退出拖拽模式时，检查是否有变化
      const status = playlistStatus.value;
      const preFiles = getCurrentPreFiles();
      if (status && preFiles && preFiles.length > 0) {
        const hasChanged = isOrderChanged(preFilesOriginalOrder.value || [], preFiles);
        if (hasChanged) {
          try {
            playlistLoading.value = true;
            await updateActivePlaylistData(playlistInfo => {
              const weekdayIndex = getSelectedWeekdayIndex();
              if (
                !playlistInfo.pre_lists ||
                !Array.isArray(playlistInfo.pre_lists) ||
                playlistInfo.pre_lists.length !== 7
              ) {
                playlistInfo.pre_lists = Array(7)
                  .fill(null)
                  .map(() => []);
              }
              playlistInfo.pre_lists[weekdayIndex] = [...preFiles];
              playlistInfo.pre_index = status.pre_index;
              return playlistInfo;
            });
            ElMessage.success("排序已保存");
          } catch (error) {
            logAndNoticeError(error as Error, "保存排序失败");
          } finally {
            playlistLoading.value = false;
          }
        }
        // 清除原始顺序
        preFilesOriginalOrder.value = null;
      }
    } else {
      // 启用拖拽模式时，保存原始顺序并取消自动排序
      const status = playlistStatus.value;
      const preFiles = getCurrentPreFiles();
      if (status && preFiles && preFiles.length > 0) {
        preFilesOriginalOrder.value = [...preFiles];
      }
      preFilesSortOrder.value = null;
    }
    preFilesDragMode.value = !preFilesDragMode.value;
  };

  // 切换正式文件拖拽排序模式
  const handleToggleFilesDragMode = async () => {
    if (filesDragMode.value) {
      // 退出拖拽模式时，检查是否有变化
      const status = playlistStatus.value;
      if (status && status.playlist && status.playlist.length > 0) {
        const hasChanged = isOrderChanged(filesOriginalOrder.value || [], status.playlist);
        if (hasChanged) {
          try {
            playlistLoading.value = true;
            await updateActivePlaylistData(playlistInfo => {
              playlistInfo.playlist = [...(status.playlist || [])];
              playlistInfo.current_index = status.current_index;
              playlistInfo.total = status.playlist.length;
              return playlistInfo;
            });
            ElMessage.success("排序已保存");
          } catch (error) {
            logAndNoticeError(error as Error, "保存排序失败");
          } finally {
            playlistLoading.value = false;
          }
        }
        // 清除原始顺序
        filesOriginalOrder.value = null;
      }
    } else {
      // 启用拖拽模式时，保存原始顺序并取消自动排序
      const status = playlistStatus.value;
      if (status && status.playlist && status.playlist.length > 0) {
        filesOriginalOrder.value = [...(status.playlist || [])];
      }
      filesSortOrder.value = null;
    }
    filesDragMode.value = !filesDragMode.value;
  };

  // 处理前置文件拖拽开始
  const handlePreFileDragStart = (event: DragEvent, index: number) => {
    if (!preFilesDragMode.value) {
      event.preventDefault();
      return;
    }
    try {
      event.dataTransfer!.effectAllowed = "move";
      event.dataTransfer!.setData("text/plain", index.toString());
    } catch (e) {
      console.error("拖拽开始失败:", e);
    }
  };

  // 处理前置文件拖拽结束
  const handlePreFileDragEnd = (event: DragEvent) => {
    const target = event.currentTarget as HTMLElement;
    if (target) {
      target.classList.remove("bg-gray-100", "border-t-2", "border-b-2", "border-blue-500");
    }
  };

  // 处理前置文件拖拽悬停
  const handlePreFileDragOver = (event: DragEvent) => {
    if (!preFilesDragMode.value) {
      return;
    }
    event.preventDefault();
    event.dataTransfer!.dropEffect = "move";
    const target = event.currentTarget as HTMLElement;
    if (target) {
      const rect = target.getBoundingClientRect();
      const mouseY = event.clientY;
      const elementCenterY = rect.top + rect.height / 2;

      target.classList.remove("bg-gray-100", "border-t-2", "border-b-2", "border-blue-500");

      if (mouseY < elementCenterY) {
        target.classList.add("border-t-2", "border-blue-500");
      } else {
        target.classList.add("border-b-2", "border-blue-500");
      }
    }
  };

  // 处理前置文件拖拽放置
  const handlePreFileDrop = (event: DragEvent, targetIndex: number) => {
    if (!preFilesDragMode.value) {
      return;
    }
    event.preventDefault();
    const target = event.currentTarget as HTMLElement;
    if (target) {
      target.classList.remove("bg-gray-100", "border-t-2", "border-b-2", "border-blue-500");
    }

    const sourceIndex = parseInt(event.dataTransfer!.getData("text/plain"), 10);

    if (sourceIndex === targetIndex || isNaN(sourceIndex)) {
      return;
    }

    const status = playlistStatus.value;
    const preFiles = getCurrentPreFiles();
    if (
      !status ||
      !preFiles ||
      sourceIndex < 0 ||
      sourceIndex >= preFiles.length ||
      targetIndex < 0 ||
      targetIndex >= preFiles.length
    ) {
      return;
    }

    // 只在内存中更新，不保存到后端（退出拖拽模式时再保存）
    const weekdayIndex = getSelectedWeekdayIndex();
    const list = [...preFiles];
    const [removed] = list.splice(sourceIndex, 1);
    list.splice(targetIndex, 0, removed);

    // 计算新的 pre_index
    let newPreIndex = status.pre_index;
    if (status.pre_index !== undefined && status.pre_index !== null && status.pre_index >= 0) {
      if (status.pre_index === sourceIndex) {
        newPreIndex = targetIndex;
      } else if (sourceIndex < status.pre_index && targetIndex >= status.pre_index) {
        newPreIndex = status.pre_index - 1;
      } else if (sourceIndex > status.pre_index && targetIndex <= status.pre_index) {
        newPreIndex = status.pre_index + 1;
      }
    }

    // 更新 playlistCollection 中对应的项
    const collection = playlistCollection.value.map(item => {
      if (item.id === status.id) {
        if (!item.pre_lists || !Array.isArray(item.pre_lists) || item.pre_lists.length !== 7) {
          item.pre_lists = Array(7)
            .fill(null)
            .map(() => []);
        }
        return {
          ...item,
          pre_lists: item.pre_lists.map((oldList: PlaylistItem[], idx: number) =>
            idx === weekdayIndex ? list : oldList
          ),
          pre_index: newPreIndex,
        };
      }
      return item;
    });
    playlistCollection.value = collection;

    // 同步更新到状态中
    syncActivePlaylist(collection);
  };

  // 处理正式文件拖拽开始
  const handleFileDragStart = (event: DragEvent, index: number) => {
    if (!filesDragMode.value) {
      event.preventDefault();
      return;
    }
    try {
      event.dataTransfer!.effectAllowed = "move";
      event.dataTransfer!.setData("text/plain", index.toString());
    } catch (e) {
      console.error("拖拽开始失败:", e);
    }
  };

  // 处理正式文件拖拽结束
  const handleFileDragEnd = (event: DragEvent) => {
    const target = event.currentTarget as HTMLElement;
    if (target) {
      target.classList.remove("bg-gray-100", "border-t-2", "border-b-2", "border-blue-500");
    }
  };

  // 处理正式文件拖拽悬停
  const handleFileDragOver = (event: DragEvent) => {
    if (!filesDragMode.value) {
      return;
    }
    event.preventDefault();
    event.dataTransfer!.dropEffect = "move";
    const target = event.currentTarget as HTMLElement;
    if (target) {
      const rect = target.getBoundingClientRect();
      const mouseY = event.clientY;
      const elementCenterY = rect.top + rect.height / 2;

      target.classList.remove("bg-gray-100", "border-t-2", "border-b-2", "border-blue-500");

      if (mouseY < elementCenterY) {
        target.classList.add("border-t-2", "border-blue-500");
      } else {
        target.classList.add("border-b-2", "border-blue-500");
      }
    }
  };

  // 处理正式文件拖拽放置
  const handleFileDrop = (event: DragEvent, targetIndex: number) => {
    if (!filesDragMode.value) {
      return;
    }
    event.preventDefault();
    const target = event.currentTarget as HTMLElement;
    if (target) {
      target.classList.remove("bg-gray-100", "border-t-2", "border-b-2", "border-blue-500");
    }

    const sourceIndex = parseInt(event.dataTransfer!.getData("text/plain"), 10);

    if (sourceIndex === targetIndex || isNaN(sourceIndex)) {
      return;
    }

    const status = playlistStatus.value;
    if (
      !status ||
      !status.playlist ||
      sourceIndex < 0 ||
      sourceIndex >= status.playlist.length ||
      targetIndex < 0 ||
      targetIndex >= status.playlist.length
    ) {
      return;
    }

    // 只在内存中更新，不保存到后端（退出拖拽模式时再保存）
    const list = [...(status.playlist || [])];
    const [removed] = list.splice(sourceIndex, 1);
    list.splice(targetIndex, 0, removed);

    // 计算新的 current_index
    let newCurrentIndex = status.current_index;
    if (
      status.current_index !== undefined &&
      status.current_index !== null &&
      status.current_index >= 0
    ) {
      if (status.current_index === sourceIndex) {
        newCurrentIndex = targetIndex;
      } else if (sourceIndex < status.current_index && targetIndex >= status.current_index) {
        newCurrentIndex = status.current_index - 1;
      } else if (sourceIndex > status.current_index && targetIndex <= status.current_index) {
        newCurrentIndex = status.current_index + 1;
      }
    }

    // 更新 playlistCollection 中对应的项
    const collection = playlistCollection.value.map(item => {
      if (item.id === status.id) {
        return {
          ...item,
          playlist: list,
          current_index: newCurrentIndex,
          total: list.length,
        };
      }
      return item;
    });
    playlistCollection.value = collection;

    // 同步更新到状态中
    syncActivePlaylist(collection);
  };

  return {
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
  };
}
