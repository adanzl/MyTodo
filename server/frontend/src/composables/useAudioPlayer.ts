/**
 * 音频播放器管理 Composable
 * 提供统一的音频播放器创建和事件管理
 */
import { ref, type Ref } from "vue";

// 常量
const NOOP = () => {};
const INITIAL_TIME = 0;
const INITIAL_PROGRESS = 0;

export interface AudioPlayerCallbacks {
  onPlay?: (audio: HTMLAudioElement) => void;
  onPause?: (audio: HTMLAudioElement) => void;
  onTimeUpdate?: (currentTime: number, duration: number, progress: number) => void;
  onDurationUpdate?: (duration: number) => void;
  onError?: (error: Event, audioUrl: string | null) => void;
  onEnded?: (audio: HTMLAudioElement) => void;
}

export interface AudioPlayerOptions {
  playingFilePath?: string | null;
  playingFileIndex?: number | null;
  callbacks?: AudioPlayerCallbacks;
}

export interface FileInfo {
  playingFilePath?: string | null;
  playingFileIndex?: number | null;
}

export interface UseAudioPlayerReturn {
  audio: Ref<HTMLAudioElement | null>;
  playingFilePath: Ref<string | null>;
  playProgress: Ref<number>;
  currentTime: Ref<number>;
  duration: Ref<number>;
  isPlaying: Ref<boolean>;
  playingFileIndex: Ref<number | null>;
  load: (audioUrl: string, fileInfo?: FileInfo) => void;
  play: () => Promise<void>;
  pause: () => void;
  seek: (percentage: number) => void;
  clear: () => void;
  updateCallbacks: (newCallbacks: AudioPlayerCallbacks) => void;
  isFilePlaying: (filePath: string) => boolean;
  getFilePlayProgress: (filePath: string) => number;
  getFileCurrentTime: (filePath: string) => number;
  getFileDuration: (filePath: string, fallbackDuration?: number) => number;
  seekFile: (filePath: string, percentage: number) => void;
}

/**
 * 创建音频管理器
 */
export function useAudioPlayer(options: AudioPlayerOptions = {}): UseAudioPlayerReturn {
  const {
    playingFilePath: initialFilePath = null,
    playingFileIndex: initialFileIndex = null,
    callbacks = {},
  } = options;

  // 回调函数，使用默认空函数
  const callbacksRef: Required<AudioPlayerCallbacks> = {
    onPlay: callbacks.onPlay || NOOP,
    onPause: callbacks.onPause || NOOP,
    onTimeUpdate: callbacks.onTimeUpdate || NOOP,
    onDurationUpdate: callbacks.onDurationUpdate || NOOP,
    onError: callbacks.onError || NOOP,
    onEnded: callbacks.onEnded || NOOP,
  };

  // 创建状态
  const playingFilePath = ref<string | null>(initialFilePath);
  const playProgress = ref<number>(INITIAL_PROGRESS);
  const currentTime = ref<number>(INITIAL_TIME);
  const duration = ref<number>(INITIAL_TIME);
  const isPlaying = ref<boolean>(false);
  const playingFileIndex = ref<number | null>(initialFileIndex);
  const audio = ref<HTMLAudioElement | null>(null);

  let currentAudioUrl: string | null = null;

  /**
   * 重置播放位置到开始
   */
  const resetPlaybackPosition = () => {
    if (audio.value) {
      audio.value.currentTime = INITIAL_TIME;
    }
  };

  /**
   * 更新时长信息
   */
  const updateDuration = (newDuration: number) => {
    if (newDuration > 0 && isFinite(newDuration)) {
      duration.value = newDuration;
      callbacksRef.onDurationUpdate(newDuration);
    }
  };

  /**
   * 重置播放状态
   */
  const resetPlaybackState = () => {
    playProgress.value = INITIAL_PROGRESS;
    currentTime.value = INITIAL_TIME;
    duration.value = INITIAL_TIME;
    isPlaying.value = false;
  };

  /**
   * 清理当前音频对象的事件监听器
   */
  const removeEventListeners = () => {
    if (!audio.value) return;

    // 先暂停播放并重置位置，避免在清理过程中触发加载
    try {
      if (!audio.value.paused) {
        audio.value.pause();
      }
      audio.value.currentTime = 0;
      // 停止所有网络请求
      audio.value.removeAttribute("src");
    } catch (e) {
      // 忽略错误，继续清理
    }

    // 不调用 load()，避免触发新的网络请求
    // 直接设置为 null，让浏览器自然清理
    audio.value = null;
  };

  /**
   * 设置事件监听器
   */
  const setupEventListeners = () => {
    if (!audio.value) return;

    // 播放开始事件
    audio.value.addEventListener("play", (e) => {
      const audioElement = e.target as HTMLAudioElement;
      if (!audioElement || audio.value !== audioElement) return;
      resetPlaybackPosition();
      isPlaying.value = true;
      callbacksRef.onPlay(audioElement);
    });

    // 元数据/数据加载完成（包含时长信息）
    const handleMediaLoaded = (e: Event) => {
      const audioElement = e.target as HTMLAudioElement;
      if (!audioElement || audio.value !== audioElement) return;
      resetPlaybackPosition();
      updateDuration(audioElement.duration);
    };
    audio.value.addEventListener("loadedmetadata", handleMediaLoaded);
    audio.value.addEventListener("loadeddata", handleMediaLoaded);

    // 时间更新事件
    audio.value.addEventListener("timeupdate", (e) => {
      const audioElement = e.target as HTMLAudioElement;
      if (!audioElement || audio.value !== audioElement) return;
      const dur = audioElement.duration;
      if (dur > 0 && isFinite(dur)) {
        const current = audioElement.currentTime;
        const progress = (current / dur) * 100;
        currentTime.value = current;
        playProgress.value = progress;
        // 如果时长有变化，更新时长
        if (duration.value !== dur) {
          duration.value = dur;
        }
        callbacksRef.onTimeUpdate(current, dur, progress);
      }
    });

    // 暂停事件
    audio.value.addEventListener("pause", (e) => {
      const audioElement = e.target as HTMLAudioElement;
      if (!audioElement || audio.value !== audioElement) return;
      isPlaying.value = false;
      if (audioElement.ended) {
        callbacksRef.onEnded(audioElement);
      } else {
        callbacksRef.onPause(audioElement);
      }
    });

    // 错误事件
    audio.value.addEventListener("error", (e) => {
      const audioElement = e.target as HTMLAudioElement;
      if (!audioElement || audio.value !== audioElement) return;
      console.error("音频播放失败:", e, "URL:", currentAudioUrl);
      isPlaying.value = false;
      callbacksRef.onError(e, currentAudioUrl);
    });

    // 播放结束事件
    audio.value.addEventListener("ended", (e) => {
      const audioElement = e.target as HTMLAudioElement;
      if (!audioElement || audio.value !== audioElement) return;
      isPlaying.value = false;
      callbacksRef.onEnded(audioElement);
    });
  };

  /**
   * 加载/更换播放文件
   */
  const load = (audioUrl: string, fileInfo: FileInfo = {}) => {
    if (!audioUrl || typeof audioUrl !== "string" || audioUrl.trim() === "") {
      console.error("音频URL不能为空或无效:", audioUrl);
      return;
    }

    // 验证 URL 格式
    try {
      const url = new URL(audioUrl, window.location.origin);
      if (!url.pathname || url.pathname === "/" || url.pathname.endsWith(".html")) {
        console.error("音频URL格式无效，可能是HTML页面:", audioUrl);
        return;
      }
    } catch (e) {
      // 如果 URL 解析失败，尝试相对路径验证
      if (audioUrl.includes("index.html") || audioUrl.endsWith(".html")) {
        console.error("音频URL格式无效，可能是HTML页面:", audioUrl);
        return;
      }
    }

    // 如果已有音频在播放，先清理
    if (audio.value) {
      removeEventListeners();
    }

    // 重置状态
    resetPlaybackState();

    // 创建新的 Audio 对象
    audio.value = new Audio(audioUrl);
    currentAudioUrl = audioUrl;
    resetPlaybackPosition();

    // 更新文件信息
    if (fileInfo.playingFilePath !== undefined) {
      playingFilePath.value = fileInfo.playingFilePath;
    }
    if (fileInfo.playingFileIndex !== undefined) {
      playingFileIndex.value = fileInfo.playingFileIndex;
    }

    // 设置事件监听器
    setupEventListeners();
  };

  /**
   * 播放
   */
  const play = (): Promise<void> => {
    if (!audio.value) {
      console.warn("音频未加载，无法播放");
      return Promise.reject(new Error("音频未加载"));
    }
    return audio.value.play().catch((error) => {
      console.error("播放失败:", error);
      throw error;
    });
  };

  /**
   * 暂停
   */
  const pause = () => {
    if (audio.value) {
      audio.value.pause();
    }
  };

  /**
   * 跳转到指定位置
   */
  const seek = (percentage: number) => {
    if (!audio.value) {
      console.warn("音频未加载，无法跳转");
      return;
    }
    const { duration: audioDuration } = audio.value;
    if (audioDuration > 0 && isFinite(audioDuration) && isFinite(percentage)) {
      const targetTime = Math.max(
        0,
        Math.min((percentage / 100) * audioDuration, audioDuration)
      );
      audio.value.currentTime = targetTime;
      // 立即更新显示，避免等待 timeupdate 事件
      currentTime.value = targetTime;
      playProgress.value = percentage;
    }
  };

  /**
   * 清理播放器状态
   */
  const clear = () => {
    if (audio.value) {
      // 先暂停并重置位置，停止所有播放活动
      try {
        if (!audio.value.paused) {
          audio.value.pause();
        }
        audio.value.currentTime = INITIAL_TIME;
      } catch (e) {
        // 忽略错误，继续清理
      }

      // 然后清理事件监听器（会移除 src）
      removeEventListeners();
    }
    currentAudioUrl = null;
    playingFilePath.value = null;
    playingFileIndex.value = null;
    resetPlaybackState();
  };

  /**
   * 更新回调函数
   */
  const updateCallbacks = (newCallbacks: AudioPlayerCallbacks) => {
    Object.assign(callbacksRef, newCallbacks);
  };

  /**
   * 检查指定文件是否正在播放
   */
  const isFilePlaying = (filePath: string): boolean => {
    if (!filePath) return false;
    return (
      playingFilePath.value === filePath &&
      audio.value !== null &&
      !audio.value.paused
    );
  };

  /**
   * 获取指定文件的播放进度
   */
  const getFilePlayProgress = (filePath: string): number => {
    if (!filePath || playingFilePath.value !== filePath || !audio.value) {
      return INITIAL_PROGRESS;
    }
    return playProgress.value;
  };

  /**
   * 获取指定文件的当前播放时间
   */
  const getFileCurrentTime = (filePath: string): number => {
    if (!filePath || playingFilePath.value !== filePath) {
      return INITIAL_TIME;
    }
    return currentTime.value;
  };

  /**
   * 获取指定文件的时长
   */
  const getFileDuration = (
    filePath: string,
    fallbackDuration: number = INITIAL_TIME
  ): number => {
    if (!filePath) return fallbackDuration;
    if (playingFilePath.value === filePath) {
      return duration.value || fallbackDuration;
    }
    return fallbackDuration;
  };

  /**
   * 跳转指定文件的播放位置
   */
  const seekFile = (filePath: string, percentage: number) => {
    if (!audio.value || !filePath) return;
    if (playingFilePath.value === filePath) {
      seek(percentage);
    }
  };

  // 返回管理器对象
  return {
    audio,
    playingFilePath,
    playProgress,
    currentTime,
    duration,
    isPlaying,
    playingFileIndex,
    load,
    play,
    pause,
    seek,
    clear,
    updateCallbacks,
    isFilePlaying,
    getFilePlayProgress,
    getFileCurrentTime,
    getFileDuration,
    seekFile,
  };
}

