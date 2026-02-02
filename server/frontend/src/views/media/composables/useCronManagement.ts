/**
 * Cron 定时任务管理 Composable
 * 处理 Cron 表达式的设置、预览等功能
 */
import { type Ref } from "vue";
import { ElMessage } from "element-plus";
import { calculateNextCronTimes } from "@/utils/cron";
import { logAndNoticeError } from "@/utils/error";
import type { Playlist, PlaylistStatus } from "@/types/playlist";

export function useCronManagement(
  playlistStatus: Ref<PlaylistStatus | null>,
  cronBuilderVisible: Ref<boolean>,
  cronPreviewVisible: Ref<boolean>,
  cronPreviewTimes: Ref<string[]>,
  initialCronExpr: Ref<string>,
  updateActivePlaylistData: (mutator: (playlistInfo: Playlist) => Playlist) => Promise<PlaylistStatus | null>
) {
  // 打开 Cron 构建器
  const handleOpenCronBuilder = () => {
    const cronExpr = playlistStatus.value?.schedule?.cron || "";
    initialCronExpr.value = cronExpr;
    cronBuilderVisible.value = true;
  };

  // 关闭 Cron 构建器
  const handleCloseCronBuilder = () => {
    cronBuilderVisible.value = false;
  };

  // 应用 Cron 表达式
  const handleCronBuilderApply = (cronExpr: string) => {
    if (!cronExpr) return;
    if (playlistStatus.value) {
      handleUpdatePlaylistCron(cronExpr);
      ElMessage.success("Cron 表达式已应用到当前播放列表");
    } else {
      ElMessage.warning("请先选择一个播放列表");
    }
  };

  // Cron 构建器预览
  const handleCronBuilderPreview = (times: string[]) => {
    cronPreviewTimes.value = times;
    cronPreviewVisible.value = true;
  };

  // 切换 Cron 启用状态
  const handleTogglePlaylistCronEnabled = async (enabled: boolean) => {
    if (!playlistStatus.value) return;
    await updateActivePlaylistData(playlistInfo => {
      if (!playlistInfo.schedule) {
        playlistInfo.schedule = { enabled: 0, cron: "", duration: 0 };
      }
      playlistInfo.schedule.enabled = enabled ? 1 : 0;
      return playlistInfo;
    });
  };

  // 更新 Cron 表达式
  const handleUpdatePlaylistCron = async (cron: string) => {
    if (!playlistStatus.value) return;
    await updateActivePlaylistData(playlistInfo => {
      if (!playlistInfo.schedule) {
        playlistInfo.schedule = { enabled: 0, cron: "", duration: 0 };
      }
      playlistInfo.schedule.cron = cron;
      return playlistInfo;
    });
  };

  // 更新持续时间
  const handleUpdatePlaylistDuration = async (duration: number | null) => {
    if (!playlistStatus.value) return;
    await updateActivePlaylistData(playlistInfo => {
      if (!playlistInfo.schedule) {
        playlistInfo.schedule = { enabled: 0, cron: "", duration: 0 };
      }
      playlistInfo.schedule.duration = duration || 0;
      return playlistInfo;
    });
  };

  // 更新触发按钮
  const handleUpdateTriggerButton = async (triggerButton: string) => {
    if (!playlistStatus.value) return;
    await updateActivePlaylistData(playlistInfo => {
      playlistInfo.trigger_button = triggerButton || "";
      return playlistInfo;
    });
  };

  // 预览 Cron 执行时间
  const handlePreviewPlaylistCron = () => {
    if (!playlistStatus.value || !playlistStatus.value.schedule?.cron) {
      ElMessage.warning("请先设置 Cron 表达式");
      return;
    }
    try {
      const cronExpr = playlistStatus.value.schedule.cron;
      const times = calculateNextCronTimes(cronExpr, 5);
      if (times && times.length > 0) {
        cronPreviewTimes.value = times;
        cronPreviewVisible.value = true;
      } else {
        ElMessage.warning("无法解析 Cron 表达式");
      }
    } catch (error) {
      logAndNoticeError(error as Error, "预览失败");
    }
  };

  return {
    handleOpenCronBuilder,
    handleCloseCronBuilder,
    handleCronBuilderApply,
    handleCronBuilderPreview,
    handleTogglePlaylistCronEnabled,
    handleUpdatePlaylistCron,
    handleUpdatePlaylistDuration,
    handleUpdateTriggerButton,
    handlePreviewPlaylistCron,
  };
}

