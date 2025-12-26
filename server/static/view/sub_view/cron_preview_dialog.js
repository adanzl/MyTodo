/**
 * Cron 执行时间预览弹窗组件
 * 用于显示 Cron 表达式的执行时间预览
 */
const { ref, watch } = window.Vue;

async function loadTemplate() {
    const response = await fetch(`./view/sub_view/cron_preview_dialog-template.html?t=${Date.now()}`);
    return await response.text();
}

/**
 * 创建 Cron 预览弹窗组件
 * @returns {Object} Vue组件
 */
export async function createCronPreviewDialog() {
    const template = await loadTemplate();

    return {
        props: {
            visible: {
                type: Boolean,
                default: false,
            },
            times: {
                type: Array,
                default: () => [],
            },
        },
        emits: ["update:visible", "close"],
        setup(props, { emit }) {
            // 处理关闭
            const handleClose = () => {
                emit("update:visible", false);
                emit("close");
            };

            return {
                handleClose,
            };
        },
        template,
    };
}

