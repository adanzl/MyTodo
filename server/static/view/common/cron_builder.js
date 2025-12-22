/**
 * Cron 表达式生成器组件
 * 可复用的 Cron 表达式可视化生成器
 */
import { generateCronExpression, calculateNextCronTimes, logAndNoticeError } from "../../js/utils.js";

const { ref, watch, nextTick } = window.Vue;
const { ElMessage } = window.ElementPlus;

async function loadTemplate() {
    const response = await fetch(`./view/common/cron_builder-template.html?t=${Date.now()}`);
    return await response.text();
}

/**
 * 解析 Cron 表达式到构建器对象
 * @param {string} cronExpr - Cron 表达式
 * @param {Object} cronBuilder - 构建器对象
 */
function parseCronExpression(cronExpr, cronBuilder) {
    try {
        if (!cronExpr || typeof cronExpr !== 'string') {
            resetCronBuilder(cronBuilder);
            return;
        }
        const parts = String(cronExpr).trim().split(/\s+/);
        let sec, min, hour, day, month, weekday;

        if (parts.length === 5) {
            const [first, second, third, fourth, fifth] = parts;
            if (first === "0" && second && second.startsWith("*/")) {
                sec = "0";
                min = second;
                hour = third || "*";
                day = fourth || "*";
                month = fifth || "*";
                weekday = "*";
            } else {
                min = first;
                hour = second;
                day = third;
                month = fourth;
                weekday = fifth;
                sec = "0";
            }
        } else if (parts.length === 6) {
            [sec, min, hour, day, month, weekday] = parts;
        } else {
            console.warn("Cron 表达式格式错误，部分数量:", parts.length);
            resetCronBuilder(cronBuilder);
            return;
        }

        if (parts.length === 5 || parts.length === 6) {
            // 解析秒
            if (sec === "*") {
                cronBuilder.second = "*";
                cronBuilder.secondCustom = "";
            } else if (sec === "0") {
                cronBuilder.second = "0";
                cronBuilder.secondCustom = "";
            } else {
                cronBuilder.second = "custom";
                cronBuilder.secondCustom = sec;
            }

            // 解析分
            if (min === "*") {
                cronBuilder.minute = "*";
                cronBuilder.minuteCustom = "";
            } else if (min === "0") {
                cronBuilder.minute = "0";
                cronBuilder.minuteCustom = "";
            } else if (min.startsWith("*/")) {
                cronBuilder.minute = "custom";
                cronBuilder.minuteCustom = min;
            } else {
                cronBuilder.minute = "custom";
                cronBuilder.minuteCustom = min;
            }

            // 解析时
            if (hour === "*") {
                cronBuilder.hour = "*";
                cronBuilder.hourCustom = "";
            } else if (hour === "0") {
                cronBuilder.hour = "0";
                cronBuilder.hourCustom = "";
            } else {
                cronBuilder.hour = "custom";
                cronBuilder.hourCustom = hour;
            }

            // 解析日
            if (day === "*") {
                cronBuilder.day = "*";
                cronBuilder.dayCustom = "";
            } else {
                cronBuilder.day = "custom";
                cronBuilder.dayCustom = day;
            }

            // 解析月
            if (month === "*") {
                cronBuilder.month = "*";
                cronBuilder.monthCustom = "";
            } else {
                cronBuilder.month = "custom";
                cronBuilder.monthCustom = month;
            }

            // 解析周
            if (weekday === "*") {
                cronBuilder.weekday = "*";
                cronBuilder.weekdayCustom = "";
            } else if (weekday === "1-5") {
                cronBuilder.weekday = "1-5";
                cronBuilder.weekdayCustom = "";
            } else if (weekday === "0,6" || weekday === "6,0") {
                cronBuilder.weekday = "0,6";
                cronBuilder.weekdayCustom = "";
            } else {
                cronBuilder.weekday = "custom";
                cronBuilder.weekdayCustom = weekday;
            }
        } else {
            console.warn("Cron 表达式格式错误，部分数量:", parts.length);
            resetCronBuilder(cronBuilder);
        }
    } catch (error) {
        console.error("解析 Cron 表达式失败:", error);
        resetCronBuilder(cronBuilder);
    }
}

/**
 * 重置 Cron 构建器
 * @param {Object} cronBuilder - 构建器对象
 */
function resetCronBuilder(cronBuilder) {
    cronBuilder.second = "*";
    cronBuilder.secondCustom = "";
    cronBuilder.minute = "*";
    cronBuilder.minuteCustom = "";
    cronBuilder.hour = "*";
    cronBuilder.hourCustom = "";
    cronBuilder.day = "*";
    cronBuilder.dayCustom = "";
    cronBuilder.month = "*";
    cronBuilder.monthCustom = "";
    cronBuilder.weekday = "*";
    cronBuilder.weekdayCustom = "";
    cronBuilder.generated = "";
}

export async function createCronBuilder() {
    const template = await loadTemplate();

    return {
        props: {
            visible: {
                type: Boolean,
                default: false,
            },
            initialCron: {
                type: String,
                default: "",
            },
        },
        emits: ["update:visible", "apply", "preview", "close"],
        setup(props, { emit }) {
            const cronBuilder = ref({
                second: "*",
                secondCustom: "",
                minute: "*",
                minuteCustom: "",
                hour: "*",
                hourCustom: "",
                day: "*",
                dayCustom: "",
                month: "*",
                monthCustom: "",
                weekday: "*",
                weekdayCustom: "",
                generated: "",
            });

            // 更新生成的 Cron 表达式
            const updateCronExpression = () => {
                cronBuilder.value.generated = generateCronExpression(cronBuilder.value);
            };

            // 监听 visible 变化，初始化 Cron 表达式
            watch(
                () => props.visible,
                (newVal) => {
                    if (newVal) {
                        if (props.initialCron) {
                            parseCronExpression(props.initialCron, cronBuilder.value);
                        } else {
                            resetCronBuilder(cronBuilder.value);
                        }
                        updateCronExpression();
                    }
                },
                { immediate: true }
            );

            // 监听 initialCron 变化
            watch(
                () => props.initialCron,
                (newVal) => {
                    if (props.visible && newVal) {
                        parseCronExpression(newVal, cronBuilder.value);
                        updateCronExpression();
                    }
                }
            );

            // 处理关闭
            const handleClose = () => {
                emit("update:visible", false);
                emit("close");
            };

            // 处理应用
            const handleApply = () => {
                if (!cronBuilder.value.generated) {
                    ElMessage.warning("请先生成 Cron 表达式");
                    return;
                }
                emit("apply", cronBuilder.value.generated);
                handleClose();
            };

            // 处理预览
            const handlePreview = () => {
                const cronExpr = cronBuilder.value.generated;
                if (!cronExpr) {
                    ElMessage.warning("请先生成 Cron 表达式");
                    return;
                }
                try {
                    const times = calculateNextCronTimes(cronExpr, 5);
                    emit("preview", times);
                } catch (error) {
                    logAndNoticeError(error, "预览失败");
                }
            };

            // 应用示例
            const applyExample = (example) => {
                try {
                    parseCronExpression(example, cronBuilder.value);
                    updateCronExpression();
                    nextTick(() => {
                        if (cronBuilder.value.generated) {
                            emit("apply", cronBuilder.value.generated);
                            ElMessage.success("示例已应用");
                        }
                    });
                } catch (error) {
                    logAndNoticeError(error, "应用示例失败");
                }
            };

            // 内部 visible 状态，用于 v-model
            const internalVisible = ref(props.visible);
            watch(() => props.visible, (newVal) => {
                internalVisible.value = newVal;
            });
            watch(internalVisible, (newVal) => {
                if (newVal !== props.visible) {
                    emit("update:visible", newVal);
                }
            });

            return {
                visible: internalVisible,
                cronBuilder,
                updateCronExpression,
                handleClose,
                handleApply,
                handlePreview,
                applyExample,
            };
        },
        template,
    };
}

