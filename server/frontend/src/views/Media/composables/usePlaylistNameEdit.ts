/**
 * 播放列表名称编辑 Composable
 * 处理播放列表名称的编辑、保存、取消等操作
 */
import { type Ref } from "vue";
import { nextTick } from "vue";
import { ElMessage } from "element-plus";
import { logAndNoticeError } from "@/utils/error";

export function usePlaylistNameEdit(
  playlistCollection: Ref<any[]>,
  activePlaylistId: Ref<string>,
  editingPlaylistId: Ref<string | null>,
  editingPlaylistName: Ref<string>,
  savePlaylist: (collection: any[]) => Promise<void>,
  syncActivePlaylist: (collection: any[]) => void
) {
  // 开始编辑播放列表名称
  const handleStartEditPlaylistName = (playlistId: string) => {
    const playlist = playlistCollection.value.find(p => p.id === playlistId);
    if (playlist) {
      editingPlaylistId.value = playlistId;
      editingPlaylistName.value = playlist.name;
      nextTick(() => {
        const input = document.querySelector(
          `input[data-playlist-id="${playlistId}"]`
        ) as HTMLInputElement;
        if (input) {
          input.focus();
          input.select();
        }
      });
    }
  };

  // 保存播放列表名称
  const handleSavePlaylistName = async (playlistId: string) => {
    const newName = editingPlaylistName.value?.trim();
    if (!newName || newName.length === 0) {
      ElMessage.warning("播放列表名称不能为空");
      editingPlaylistId.value = null;
      return;
    }

    const playlist = playlistCollection.value.find(p => p.id === playlistId);
    if (!playlist || playlist.name === newName) {
      editingPlaylistId.value = null;
      return;
    }

    try {
      const collection = playlistCollection.value.map(item => {
        if (item.id === playlistId) {
          return { ...item, name: newName };
        }
        return item;
      });
      playlistCollection.value = collection;

      if (playlistId === activePlaylistId.value) {
        syncActivePlaylist(collection);
      }

      await savePlaylist(collection);

      editingPlaylistId.value = null;
      ElMessage.success("播放列表名称已更新");
    } catch (error) {
      logAndNoticeError(error as Error, "更新播放列表名称失败");
    }
  };

  // 取消编辑播放列表名称
  const handleCancelEditPlaylistName = () => {
    editingPlaylistId.value = null;
    editingPlaylistName.value = "";
  };

  return {
    handleStartEditPlaylistName,
    handleSavePlaylistName,
    handleCancelEditPlaylistName,
  };
}
