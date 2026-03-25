/**
 * 播放列表操作 Composable
 * 处理播放列表的 CRUD 操作和播放控制
 */
import { type Ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { playlistAction } from "@/api/playlist";
import { logAndNoticeError } from "@/utils/error";
import { logger } from "@/utils/logger";
import { STORAGE_KEY_ACTIVE_PLAYLIST_ID } from "@/constants/playlist";
import type { Playlist, PlaylistStatus, PlaylistItem } from "@/types/playlist";

export function usePlaylistOperations(
  playlistCollection: Ref<Playlist[]>,
  activePlaylistId: Ref<string>,
  playlistStatus: Ref<PlaylistStatus | null>,
  playing: Ref<boolean>,
  stopping: Ref<boolean>,
  syncActivePlaylist: (collection: Playlist[]) => void,
  updateActivePlaylistData: (
    mutator: (playlistInfo: Playlist) => Playlist
  ) => Promise<PlaylistStatus | null>,
  refreshPlaylistStatus: (onlyCurrent?: boolean, isAutoRefresh?: boolean) => Promise<void>,
  getCurrentPreFiles: () => PlaylistItem[]
) {
  // 加载播放列表
  const loadPlaylist = async () => {
    try {
      const response = await playlistAction("get", "GET", {});
      if (response.code !== 0) {
        throw new Error(response.msg || "获取播放列表失败");
      }
      return response.data;
    } catch (error) {
      logger.error("从接口加载播放列表失败:", error);
      throw error;
    }
  };

  // 选择播放列表
  const handleSelectPlaylist = async (playlistId: string) => {
    if (!playlistId || playlistId === activePlaylistId.value) return;
    const exists = playlistCollection.value.find(item => item.id === playlistId);
    if (!exists) return;

    activePlaylistId.value = playlistId;
    localStorage.setItem(STORAGE_KEY_ACTIVE_PLAYLIST_ID, playlistId);
    syncActivePlaylist(playlistCollection.value);
  };

  // 创建播放列表
  const handleCreatePlaylist = async () => {
    try {
      const defaultName = `播放列表${playlistCollection.value.length + 1}`;
      const { value } = await ElMessageBox.prompt("请输入播放列表名称", "新建播放列表", {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        inputValue: defaultName,
        inputPlaceholder: defaultName,
        inputValidator: val => (!!val && val.trim().length > 0) || "名称不能为空",
      });
      const playlistName = (value || defaultName).trim();
      return { name: playlistName };
    } catch (error) {
      if (error !== "cancel") {
        throw error;
      }
      return null;
    }
  };

  // 复制播放列表
  const handleCopyPlaylist = async (playlistId: string) => {
    if (!playlistId) return null;
    const sourcePlaylist = playlistCollection.value.find(item => item.id === playlistId);
    if (!sourcePlaylist) return null;

    try {
      const defaultName = `${sourcePlaylist.name}_副本`;
      const { value } = await ElMessageBox.prompt("请输入播放列表名称", "复制播放列表", {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        inputValue: defaultName,
        inputPlaceholder: defaultName,
        inputValidator: val => (!!val && val.trim().length > 0) || "名称不能为空",
      });
      const playlistName = (value || defaultName).trim();
      return { sourcePlaylist, name: playlistName };
    } catch (error) {
      if (error !== "cancel") {
        throw error;
      }
      return null;
    }
  };

  // 删除播放列表
  const handleDeletePlaylistGroup = async (playlistId: string) => {
    if (!playlistId) return false;
    if (playlistCollection.value.length <= 1) {
      ElMessage.warning("至少保留一个播放列表");
      return false;
    }
    const target = playlistCollection.value.find(item => item.id === playlistId);
    if (!target) return false;
    try {
      await ElMessageBox.confirm(`确认删除播放列表"${target.name}"吗？`, "删除播放列表", {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
      });
      return true;
    } catch (error) {
      if (error !== "cancel") {
        throw error;
      }
      return false;
    }
  };

  // 播放播放列表
  const handlePlayPlaylist = async () => {
    const status = playlistStatus.value;
    if (!status || !status.id) {
      ElMessage.warning("播放列表不存在");
      return;
    }
    if (!status.playlist || status.playlist.length === 0) {
      ElMessage.warning("播放列表为空，请先添加文件");
      return;
    }
    try {
      playing.value = true;
      await updateActivePlaylistData(playlistInfo => {
        const list = Array.isArray(playlistInfo.playlist) ? playlistInfo.playlist : [];
        playlistInfo.current_index = Math.max(
          0,
          Math.min(playlistInfo.current_index || 0, list.length - 1)
        );
        playlistInfo.total = list.length;
        return playlistInfo;
      });

      const response = await playlistAction("play", "POST", { id: status.id });
      if (response.code !== 0) {
        throw new Error(response.msg || "播放失败");
      }

      await refreshPlaylistStatus(true);
      ElMessage.success("开始播放");
    } catch (error) {
      logAndNoticeError(error as Error, "播放失败");
    } finally {
      playing.value = false;
    }
  };

  // 播放下一首
  const handlePlayNext = async () => {
    const status = playlistStatus.value;
    if (!status || !status.id) {
      ElMessage.warning("播放列表不存在");
      return;
    }
    if (!status.playlist || status.playlist.length === 0) {
      ElMessage.warning("播放列表为空，无法播放下一首");
      return;
    }
    try {
      playing.value = true;
      const response = await playlistAction("playNext", "POST", { id: status.id });
      if (response.code !== 0) {
        throw new Error(response.msg || "播放下一首失败");
      }
      await refreshPlaylistStatus(true);
      ElMessage.success("已切换到下一首");
    } catch (error) {
      logAndNoticeError(error as Error, "播放下一首失败");
    } finally {
      playing.value = false;
    }
  };

  // 播放上一首
  const handlePlayPre = async () => {
    const status = playlistStatus.value;
    if (!status || !status.id) {
      ElMessage.warning("播放列表不存在");
      return;
    }
    const hasPreFiles = getCurrentPreFiles().length > 0;
    const hasPlaylist = status.playlist && status.playlist.length > 0;
    if (!hasPreFiles && !hasPlaylist) {
      ElMessage.warning("播放列表为空，无法播放上一首");
      return;
    }
    try {
      playing.value = true;
      const response = await playlistAction("playPre", "POST", { id: status.id });
      if (response.code !== 0) {
        throw new Error(response.msg || "播放上一首失败");
      }
      await refreshPlaylistStatus(true);
      ElMessage.success("已切换到上一首");
    } catch (error) {
      logAndNoticeError(error as Error, "播放上一首失败");
    } finally {
      playing.value = false;
    }
  };

  // 停止播放
  const handleStopPlaylist = async () => {
    const status = playlistStatus.value;
    if (!status || !status.id) {
      ElMessage.warning("播放列表不存在");
      return;
    }
    try {
      stopping.value = true;
      const response = await playlistAction("stop", "POST", { id: status.id });
      if (response.code !== 0) {
        throw new Error(response.msg || "停止播放失败");
      }
      await refreshPlaylistStatus(true);
      ElMessage.success("已停止播放");
    } catch (error) {
      logAndNoticeError(error as Error, "停止播放列表失败");
    } finally {
      stopping.value = false;
    }
  };

  return {
    loadPlaylist,
    handleSelectPlaylist,
    handleCreatePlaylist,
    handleCopyPlaylist,
    handleDeletePlaylistGroup,
    handlePlayPlaylist,
    handlePlayNext,
    handlePlayPre,
    handleStopPlaylist,
  };
}
