/**
 * 设备列表弹窗组件
 * 显示Agent设备和小米设备列表
 */
import { getApiUrl } from "../../js/net_util.js";
import { logAndNoticeError } from "../../js/utils.js";

const axios = window.axios;
const { ref, watch, onUnmounted, onMounted } = window.Vue;
const { ElMessage } = window.ElementPlus;

async function loadTemplate() {
    const response = await fetch(`./view/sub_view/devices_dialog-template.html?t=${Date.now()}`);
    return await response.text();
}

/**
 * 创建设备列表弹窗组件
 * @returns {Object} Vue组件
 */
export async function createDevicesDialog() {
    const template = await loadTemplate();

    return {
        props: {
            visible: {
                type: Boolean,
                default: false,
            },
        },
        emits: ['update:visible'],
        setup(props, { emit }) {
            const agentList = ref([]);
            const agentListLoading = ref(false);
            const miDeviceList = ref([]);
            const miScanning = ref(false);
            let agentListRefreshTimer = null;

            // 辅助函数
            const getMiDeviceId = (device) => device.deviceID || device.address;
            const clampVolume = (volume) => Math.max(0, Math.min(100, volume));

            // 刷新Agent设备列表
            const handleRefreshAgentList = async (showLoading = true) => {
                try {
                    if (showLoading) {
                        agentListLoading.value = true;
                    }
                    const response = await axios.get(getApiUrl() + "/agent/list");
                    if (response.data && response.data.code === 0) {
                        agentList.value = response.data.data || [];
                    } else {
                        if (showLoading) {
                            ElMessage.error(response.data?.msg || "获取设备列表失败");
                        }
                        agentList.value = [];
                    }
                } catch (error) {
                    console.error("获取Agent设备列表失败:", error);
                    if (showLoading) {
                        logAndNoticeError(error, "获取设备列表失败");
                    }
                    agentList.value = [];
                } finally {
                    if (showLoading) {
                        agentListLoading.value = false;
                    }
                }
            };

            // 测试Agent按钮
            const handleTestAgentButton = async (agentId, key) => {
                try {
                    // 设置按钮loading状态
                    const device = agentList.value.find(d => d.agent_id === agentId);
                    if (device) {
                        device[`testing_${key}`] = true;
                    }

                    const response = await axios.post(getApiUrl() + "/agent/mock", {
                        agent_id: agentId,
                        action: "keyboard",
                        key: key,
                        value: "test"
                    });

                    if (response.data && response.data.code === 0) {
                        ElMessage.success(`测试按钮 ${key} 成功`);
                    } else {
                        ElMessage.error(response.data?.msg || `测试按钮 ${key} 失败`);
                    }
                } catch (error) {
                    logAndNoticeError(error, `测试按钮 ${key} 失败`);
                } finally {
                    // 清除loading状态
                    const device = agentList.value.find(d => d.agent_id === agentId);
                    if (device) {
                        device[`testing_${key}`] = false;
                    }
                }
            };

            // 扫描小米设备
            const scanMiDevices = async () => {
                try {
                    miScanning.value = true;
                    const response = await fetch(`${getApiUrl()}/mi/scan?timeout=5`);
                    const result = await response.json();

                    if (result.code === 0) {
                        const devices = (result.data || []).map(device => ({
                            ...device,
                            volume: undefined,
                            _volumeChanging: false,
                            _volumeRefreshing: false
                        }));
                        miDeviceList.value = devices;

                        // 并行获取所有设备的音量（使用响应式数组确保 Vue 能检测到变化）
                        await Promise.allSettled(miDeviceList.value.map(device => getMiDeviceVolume(device)));

                        ElMessage.success(`扫描到 ${devices.length} 个小米设备`);
                    } else {
                        ElMessage.error(result.msg || "扫描小米设备失败");
                    }
                } catch (error) {
                    logAndNoticeError(error, "扫描小米设备失败");
                } finally {
                    miScanning.value = false;
                }
            };

            // 获取小米设备音量
            const getMiDeviceVolume = async (device) => {
                const deviceId = getMiDeviceId(device);
                if (!deviceId) return;

                // 在响应式数组中找到对应的设备对象
                const deviceList = miDeviceList.value;
                const targetDevice = deviceList.find(d => getMiDeviceId(d) === deviceId);
                if (!targetDevice) return;

                // 设置刷新状态
                targetDevice._volumeRefreshing = true;

                try {
                    const response = await fetch(`${getApiUrl()}/mi/volume?device_id=${encodeURIComponent(deviceId)}`);
                    const result = await response.json();

                    if (result.code === 0) {
                        // 直接更新响应式数组中的设备对象
                        targetDevice.volume = result.data?.volume ?? result.data ?? undefined;
                    } else {
                        ElMessage.error(result.msg || `获取设备 ${targetDevice.name || deviceId} 音量失败`);
                    }
                } catch (error) {
                    logAndNoticeError(error, `获取设备 ${targetDevice.name || deviceId} 音量失败`);
                } finally {
                    targetDevice._volumeRefreshing = false;
                }
            };

            // 设置小米设备音量
            const setMiDeviceVolume = async (device, volume) => {
                const deviceId = getMiDeviceId(device);
                if (!deviceId) {
                    ElMessage.error("设备ID无效");
                    return;
                }

                const clampedVolume = clampVolume(volume);
                device._volumeChanging = true;

                try {
                    const response = await fetch(`${getApiUrl()}/mi/volume`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            device_id: deviceId,
                            volume: clampedVolume
                        })
                    });

                    const result = await response.json();

                    if (result.code === 0) {
                        device.volume = clampedVolume;
                        ElMessage.success('音量设置成功');
                    } else {
                        ElMessage.error(result.msg || "设置音量失败");
                    }
                } catch (error) {
                    logAndNoticeError(error, "设置小米设备音量失败");
                } finally {
                    device._volumeChanging = false;
                }
            };

            // 停止小米设备播放
            const handleStopMiDevice = async (device) => {
                const deviceId = getMiDeviceId(device);
                if (!deviceId) {
                    ElMessage.warning("设备ID无效");
                    return;
                }

                try {
                    device._stopping = true;
                    const response = await axios.post(`${getApiUrl()}/mi/stop`, {
                        device_id: deviceId
                    });

                    if (response.data.code === 0) {
                        ElMessage.success("停止播放成功");
                    } else {
                        ElMessage.error(response.data.msg || "停止播放失败");
                    }
                } catch (error) {
                    logAndNoticeError(error, "停止小米设备播放失败");
                } finally {
                    device._stopping = false;
                }
            };

            // 关闭对话框
            const handleClose = () => {
                emit('update:visible', false);
            };

            // 启动自动刷新的函数
            const startAutoRefresh = () => {
                // 清除之前的定时器
                if (agentListRefreshTimer) {
                    clearInterval(agentListRefreshTimer);
                    agentListRefreshTimer = null;
                }

                // 立即刷新一次（显示loading）
                handleRefreshAgentList(true);
                // 启动10秒定时刷新（不显示loading）
                agentListRefreshTimer = setInterval(async () => {
                    try {
                        // 自动刷新时不显示loading图标
                        await handleRefreshAgentList(false);
                    } catch (error) {
                        console.error("定时刷新Agent设备列表失败:", error);
                    }
                }, 10000);
            };

            // 停止自动刷新的函数
            const stopAutoRefresh = () => {
                if (agentListRefreshTimer) {
                    clearInterval(agentListRefreshTimer);
                    agentListRefreshTimer = null;
                }
            };

            // 监听对话框显示状态，实现10秒定时刷新
            watch(
                () => props.visible,
                (isVisible) => {
                    if (isVisible) {
                        startAutoRefresh();
                    } else {
                        stopAutoRefresh();
                    }
                },
                { immediate: true } // 立即执行，确保初始化时如果 visible 为 true 也能触发
            );

            // 组件挂载时，如果弹窗已经显示，启动自动刷新
            onMounted(() => {
                if (props.visible) {
                    startAutoRefresh();
                }
            });

            // 组件卸载时清理定时器
            onUnmounted(() => {
                if (agentListRefreshTimer) {
                    clearInterval(agentListRefreshTimer);
                    agentListRefreshTimer = null;
                }
            });

            return {
                agentList,
                agentListLoading,
                miDeviceList,
                miScanning,
                handleRefreshAgentList,
                handleTestAgentButton,
                scanMiDevices,
                getMiDeviceVolume,
                setMiDeviceVolume,
                handleStopMiDevice,
                handleClose,
            };
        },
        template,
    };
}

