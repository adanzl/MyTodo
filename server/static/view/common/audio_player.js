/**
 * 音频播放器管理工具
 * 提供统一的音频播放器创建和事件管理
 */

const { ref } = window.Vue;

// 常量
const NOOP = () => { };
const INITIAL_TIME = 0;
const INITIAL_PROGRESS = 0;

/**
 * 创建音频管理器
 * @param {Object} options - 配置选项
 * @param {string} options.playingFilePath - 当前播放的文件路径标识（可选）
 * @param {number} options.playingFileIndex - 当前播放的文件索引（可选）
 * @param {Object} options.callbacks - 回调函数对象
 * @param {Function} options.callbacks.onPlay - 播放开始回调，参数: (audio)
 * @param {Function} options.callbacks.onPause - 暂停回调，参数: (audio)
 * @param {Function} options.callbacks.onTimeUpdate - 时间更新回调，参数: (currentTime, duration, progress)
 * @param {Function} options.callbacks.onDurationUpdate - 时长更新回调，参数: (duration)
 * @param {Function} options.callbacks.onError - 错误回调，参数: (error, audioUrl)
 * @param {Function} options.callbacks.onEnded - 播放结束回调，参数: (audio)
 * @returns {Object} 音频管理器对象
 */
export function createAudioPlayer(options = {}) {
    const {
        playingFilePath: initialFilePath = null,
        playingFileIndex: initialFileIndex = null,
        callbacks = {},
    } = options;

    // 回调函数，使用默认空函数
    const callbacksRef = {
        onPlay: callbacks.onPlay || NOOP,
        onPause: callbacks.onPause || NOOP,
        onTimeUpdate: callbacks.onTimeUpdate || NOOP,
        onDurationUpdate: callbacks.onDurationUpdate || NOOP,
        onError: callbacks.onError || NOOP,
        onEnded: callbacks.onEnded || NOOP,
    };

    // 创建状态
    const playingFilePath = ref(initialFilePath);
    const playProgress = ref(INITIAL_PROGRESS);
    const currentTime = ref(INITIAL_TIME);
    const duration = ref(INITIAL_TIME);
    const isPlaying = ref(false);
    const playingFileIndex = ref(initialFileIndex);

    let audio = null;
    let currentAudioUrl = null;

    /**
     * 重置播放位置到开始
     */
    const resetPlaybackPosition = () => {
        if (audio) {
            audio.currentTime = INITIAL_TIME;
        }
    };

    /**
     * 更新时长信息
     */
    const updateDuration = (newDuration) => {
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
        if (!audio) return;
        // 清空 src 并重新加载，移除所有事件监听器
        audio.src = '';
        audio.load();
        audio = null;
    };

    /**
     * 设置事件监听器
     */
    const setupEventListeners = () => {
        if (!audio) return;

        // 播放开始事件
        audio.addEventListener('play', () => {
            resetPlaybackPosition();
            isPlaying.value = true;
            callbacksRef.onPlay(audio);
        });

        // 元数据/数据加载完成（包含时长信息）
        const handleMediaLoaded = () => {
            resetPlaybackPosition();
            updateDuration(audio.duration);
        };
        audio.addEventListener('loadedmetadata', handleMediaLoaded);
        audio.addEventListener('loadeddata', handleMediaLoaded);

        // 时间更新事件
        audio.addEventListener('timeupdate', () => {
            if (audio.duration > 0 && isFinite(audio.duration)) {
                const current = audio.currentTime;
                const dur = audio.duration;
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
        audio.addEventListener('pause', () => {
            isPlaying.value = false;
            if (audio.ended) {
                callbacksRef.onEnded(audio);
            } else {
                callbacksRef.onPause(audio);
            }
        });

        // 错误事件
        audio.addEventListener('error', (e) => {
            console.error("音频播放失败:", e, "URL:", currentAudioUrl);
            isPlaying.value = false;
            callbacksRef.onError(e, currentAudioUrl);
        });

        // 播放结束事件
        audio.addEventListener('ended', () => {
            isPlaying.value = false;
            callbacksRef.onEnded(audio);
        });
    };

    /**
     * 加载/更换播放文件
     * @param {string} audioUrl - 音频文件URL
     * @param {Object} fileInfo - 文件信息（可选）
     * @param {string} fileInfo.playingFilePath - 文件路径标识
     * @param {number} fileInfo.playingFileIndex - 文件索引
     */
    const load = (audioUrl, fileInfo = {}) => {
        if (!audioUrl) {
            console.error("音频URL不能为空");
            return;
        }

        // 如果已有音频在播放，先清理
        if (audio) {
            removeEventListeners();
        }

        // 重置状态
        resetPlaybackState();

        // 创建新的 Audio 对象
        audio = new Audio(audioUrl);
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
     * @returns {Promise} 播放 Promise
     */
    const play = () => {
        if (!audio) {
            console.warn("音频未加载，无法播放");
            return Promise.reject(new Error("音频未加载"));
        }
        return audio.play().catch((error) => {
            console.error("播放失败:", error);
            throw error;
        });
    };

    /**
     * 暂停
     */
    const pause = () => {
        if (audio) {
            audio.pause();
        }
    };

    /**
     * 跳转到指定位置
     * @param {number} percentage - 进度百分比（0-100）
     */
    const seek = (percentage) => {
        if (!audio) {
            console.warn("音频未加载，无法跳转");
            return;
        }
        const { duration: audioDuration } = audio;
        if (audioDuration > 0 && isFinite(audioDuration) && isFinite(percentage)) {
            const targetTime = Math.max(0, Math.min((percentage / 100) * audioDuration, audioDuration));
            audio.currentTime = targetTime;
            // 立即更新显示，避免等待 timeupdate 事件
            currentTime.value = targetTime;
            playProgress.value = percentage;
        }
    };

    /**
     * 清理播放器状态
     */
    const clear = () => {
        if (audio) {
            // 内联 clearAudioPlayer 逻辑：先暂停并重置位置
            audio.pause();
            audio.currentTime = INITIAL_TIME;
            // 然后清理事件监听器（会清空 src 和 load）
            removeEventListeners();
        }
        currentAudioUrl = null;
        playingFilePath.value = null;
        playingFileIndex.value = null;
        resetPlaybackState();
    };

    /**
     * 更新回调函数
     * @param {Object} newCallbacks - 新的回调函数对象
     */
    const updateCallbacks = (newCallbacks) => {
        Object.assign(callbacksRef, newCallbacks);
    };

    /**
     * 检查指定文件是否正在播放
     * @param {string} filePath - 文件路径
     * @returns {boolean} 是否正在播放
     */
    const isFilePlaying = (filePath) => {
        if (!filePath) return false;
        return playingFilePath.value === filePath &&
            audio &&
            !audio.paused;
    };

    /**
     * 获取指定文件的播放进度
     * @param {string} filePath - 文件路径
     * @returns {number} 播放进度（0-100）
     */
    const getFilePlayProgress = (filePath) => {
        if (!filePath || playingFilePath.value !== filePath || !audio) {
            return INITIAL_PROGRESS;
        }
        return playProgress.value;
    };

    /**
     * 获取指定文件的当前播放时间
     * @param {string} filePath - 文件路径
     * @returns {number} 当前播放时间（秒）
     */
    const getFileCurrentTime = (filePath) => {
        if (!filePath || playingFilePath.value !== filePath) {
            return INITIAL_TIME;
        }
        return currentTime.value;
    };

    /**
     * 获取指定文件的时长
     * @param {string} filePath - 文件路径
     * @param {number} fallbackDuration - 如果文件不在播放时的回退时长（可选）
     * @returns {number} 文件时长（秒）
     */
    const getFileDuration = (filePath, fallbackDuration = INITIAL_TIME) => {
        if (!filePath) return fallbackDuration;
        if (playingFilePath.value === filePath) {
            return duration.value || fallbackDuration;
        }
        return fallbackDuration;
    };

    /**
     * 跳转指定文件的播放位置
     * @param {string} filePath - 文件路径
     * @param {number} percentage - 进度百分比（0-100）
     */
    const seekFile = (filePath, percentage) => {
        if (!audio || !filePath) return;
        if (playingFilePath.value === filePath) {
            seek(percentage);
        }
    };

    // 返回管理器对象
    return {
        // 状态（只读）
        get audio() {
            return audio;
        },
        playingFilePath,
        playProgress,
        currentTime,
        duration,
        isPlaying,
        playingFileIndex,
        // 方法
        load,
        play,
        pause,
        seek,
        clear,
        updateCallbacks,
        // 文件相关查询方法
        isFilePlaying,
        getFilePlayProgress,
        getFileCurrentTime,
        getFileDuration,
        seekFile,
    };
}
