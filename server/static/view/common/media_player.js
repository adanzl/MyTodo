/**
 * 媒体播放器组件
 * 可复用的音频播放器控件（播放按钮 + 进度条 + 时长）
 */
import { formatDuration } from "../../js/utils.js";

const { computed } = window.Vue;

async function loadTemplate() {
    const response = await fetch(`./view/common/media_player-template.html?t=${Date.now()}`);
    return await response.text();
}

/**
 * 创建媒体播放器组件
 * @returns {Promise<Object>} Vue 组件对象
 */
export async function createMediaPlayerComponent() {
    const template = await loadTemplate();

    return {
        name: "MediaPlayer",
        props: {
            // 文件项对象
            file: {
                type: Object,
                required: true,
            },
            // 是否正在播放
            isPlaying: {
                type: Boolean,
                default: false,
            },
            // 播放进度（0-100）
            progress: {
                type: Number,
                default: 0,
            },
            // 文件时长（秒）
            duration: {
                type: Number,
                default: 0,
            },
            // 是否禁用
            disabled: {
                type: Boolean,
                default: false,
            },
            // 自定义宽度类
            widthClass: {
                type: String,
                default: "w-32",
            },
        },
        emits: ["play", "seek"],
        setup(props, { emit }) {
            // 格式化时长显示
            const formattedDuration = computed(() => {
                return formatDuration(props.duration);
            });

            // 处理播放按钮点击
            const handlePlayClick = () => {
                if (!props.disabled) {
                    emit("play", props.file);
                }
            };

            // 处理进度条变化
            const handleSeek = (value) => {
                if (!props.disabled && props.isPlaying) {
                    emit("seek", props.file, value);
                }
            };

            return {
                formattedDuration,
                handlePlayClick,
                handleSeek,
            };
        },
        template,
    };
}

