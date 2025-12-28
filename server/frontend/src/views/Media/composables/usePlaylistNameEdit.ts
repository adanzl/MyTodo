/**
 * 播放列表名称编辑 Composable
 * 处理播放列表名称的编辑、保存、取消等操作
 */
import { type Ref, ref } from "vue";
import { ElMessage } from "element-plus";
import { logAndNoticeError } from "@/utils/error";

export function usePlaylistNameEdit(
  playlistCollection: Ref<any[]>,
  activePlaylistId: Ref<string>,
  _editingPlaylistId: Ref<string | null>,
  _editingPlaylistName: Ref<string>,
  savePlaylist: (collection: any[]) => Promise<void>,
  syncActivePlaylist: (collection: any[]) => void
) {
  // 对话框显示状态
  const editNameDialogVisible = ref(false);
  const editNameDialogPlaylistId = ref<string | null>(null);
  const editNameDialogName = ref("");

  // 开始编辑播放列表名称（打开对话框）
  const handleStartEditPlaylistName = (playlistId: string) => {
    const playlist = playlistCollection.value.find(p => p.id === playlistId);
    if (playlist) {
      editNameDialogPlaylistId.value = playlistId;
      editNameDialogName.value = playlist.name;
      editNameDialogVisible.value = true;
    }
  };

  // 保存播放列表名称（从对话框）
  const handleSavePlaylistName = async () => {
    if (!editNameDialogPlaylistId.value) return;

    const newName = editNameDialogName.value?.trim();
    if (!newName || newName.length === 0) {
      ElMessage.warning("播放列表名称不能为空");
      return;
    }

    const playlistId = editNameDialogPlaylistId.value;
    const playlist = playlistCollection.value.find(p => p.id === playlistId);
    if (!playlist || playlist.name === newName) {
      editNameDialogVisible.value = false;
      editNameDialogPlaylistId.value = null;
      editNameDialogName.value = "";
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

      editNameDialogVisible.value = false;
      editNameDialogPlaylistId.value = null;
      editNameDialogName.value = "";
      ElMessage.success("播放列表名称已更新");
    } catch (error) {
      logAndNoticeError(error as Error, "更新播放列表名称失败");
    }
  };

  // 取消编辑播放列表名称（关闭对话框）
  const handleCancelEditPlaylistName = () => {
    editNameDialogVisible.value = false;
    editNameDialogPlaylistId.value = null;
    editNameDialogName.value = "";
  };

  return {
    editNameDialogVisible,
    editNameDialogName,
    handleStartEditPlaylistName,
    handleSavePlaylistName,
    handleCancelEditPlaylistName,
  };
}
