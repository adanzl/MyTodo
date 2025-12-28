/**
 * 音频播放 Composable
 * 处理浏览器内音频播放相关功能
 */
import { ElMessage } from "element-plus";
import { useAudioPlayer } from "@/composables/useAudioPlayer";
import { getMediaFileUrl } from "@/utils/file";
import { logAndNoticeError } from "@/utils/error";

export function useAudioPlayback() {
  // 音频播放器
  const audioPlayer = useAudioPlayer({
    callbacks: {
      onPlay: () => {
        ElMessage.success("开始播放");
      },
      onError: () => {
        logAndNoticeError(new Error("音频播放失败"), "播放失败");
        clearBrowserAudioPlayer();
      },
      onEnded: () => {
        clearBrowserAudioPlayer();
      },
    },
  });

  // 清理浏览器音频播放器状态
  const clearBrowserAudioPlayer = () => {
    audioPlayer.clear();
  };

  // 在浏览器中播放文件
  const handlePlayFileInBrowser = (fileItem: any) => {
    const filePath = fileItem?.uri || fileItem?.path || "";
    if (!filePath || typeof filePath !== "string" || filePath.trim() === "") {
      ElMessage.warning("文件路径无效");
      return;
    }

    // 如果点击的是正在播放的文件，则停止播放
    if (
      audioPlayer.playingFilePath.value === filePath &&
      audioPlayer.audio &&
      !audioPlayer.audio.paused
    ) {
      clearBrowserAudioPlayer();
      ElMessage.info("已停止播放");
      return;
    }

    const mediaUrl = getMediaFileUrl(filePath);
    if (!mediaUrl || typeof mediaUrl !== "string" || mediaUrl.trim() === "") {
      ElMessage.error("无法生成媒体文件URL");
      return;
    }

    // 验证生成的 URL 是否有效
    if (mediaUrl.includes("index.html") || mediaUrl.endsWith(".html")) {
      ElMessage.error("生成的媒体URL无效，可能是HTML页面");
      return;
    }

    // 加载/更换播放文件
    audioPlayer.load(mediaUrl, {
      playingFilePath: filePath,
    });

    // 开始播放
    audioPlayer.play().catch(error => {
      logAndNoticeError(error as Error, "播放失败");
      clearBrowserAudioPlayer();
    });
  };

  // 检查文件是否正在播放
  const isFilePlaying = (fileItem: any) => {
    const filePath = fileItem?.uri || fileItem?.path || "";
    return audioPlayer.isFilePlaying(filePath);
  };

  // 获取文件播放进度
  const getFilePlayProgress = (fileItem: any) => {
    const filePath = fileItem?.uri || fileItem?.path || "";
    return audioPlayer.getFilePlayProgress(filePath);
  };

  // 获取文件时长
  const getFileDuration = (fileItem: any) => {
    const filePath = fileItem?.uri || fileItem?.path || "";
    const fallbackDuration = fileItem?.duration || 0;
    return audioPlayer.getFileDuration(filePath, fallbackDuration);
  };

  // 处理进度条拖拽
  const handleSeekFile = (fileItem: any, percentage: number) => {
    const filePath = fileItem?.uri || fileItem?.path || "";
    audioPlayer.seekFile(filePath, percentage);
  };

  return {
    audioPlayer,
    clearBrowserAudioPlayer,
    handlePlayFileInBrowser,
    isFilePlaying,
    getFilePlayProgress,
    getFileDuration,
    handleSeekFile,
  };
}
