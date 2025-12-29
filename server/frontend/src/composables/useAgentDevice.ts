/**
 * AgentDevice 管理 Composable
 * 专门处理 AgentDevice 相关的逻辑，包括列表获取、刷新、测试按钮等
 */
import { ref, type Ref } from "vue";
import { ElMessage } from "element-plus";
import { api } from "@/api/config";
import { logAndNoticeError } from "@/utils/error";
import { AGENT_LIST_REFRESH_INTERVAL } from "@/constants/device";
import { useControllableInterval } from "@/composables/useInterval";
import type { AgentDevice } from "@/types/device";

export interface UseAgentDeviceOptions {
  /**
   * 是否启用自动刷新
   * @default false
   */
  autoRefresh?: boolean;
  /**
   * 自动刷新间隔（毫秒）
   * @default AGENT_LIST_REFRESH_INTERVAL
   */
  refreshInterval?: number;
}

/**
 * AgentDevice 管理 Composable
 * @param options 配置选项
 * @returns AgentDevice 管理相关的方法和状态
 */
export function useAgentDevice(options: UseAgentDeviceOptions = {}) {
  const { autoRefresh = false, refreshInterval = AGENT_LIST_REFRESH_INTERVAL } = options;

  // 设备列表
  const agentList = ref<AgentDevice[]>([]);
  // 加载状态
  const loading = ref(false);

  /**
   * 刷新 Agent 设备列表
   * @param showLoading 是否显示加载状态
   * @param showMessage 是否显示成功/失败消息
   */
  const refreshAgentList = async (showLoading = true, showMessage = false) => {
    try {
      if (showLoading) {
        loading.value = true;
      }

      const response = await api.get("/agent/list");
      const result = response.data;

      if (result && result.code === 0) {
        agentList.value = result.data || [];
        if (showMessage) {
          ElMessage.success(`已获取 ${agentList.value.length} 个 Agent 设备`);
        }
      } else {
        if (showMessage || showLoading) {
          ElMessage.error(result?.msg || "获取设备列表失败");
        }
        agentList.value = [];
      }
    } catch (error) {
      console.error("获取Agent设备列表失败:", error);
      if (showMessage || showLoading) {
        logAndNoticeError(error as Error, "获取设备列表失败");
      }
      agentList.value = [];
    } finally {
      if (showLoading) {
        loading.value = false;
      }
    }
  };

  /**
   * 测试 Agent 按钮
   * @param agentId Agent ID
   * @param key 按键代码（如 "F13", "F14" 等）
   */
  const testAgentButton = async (agentId: string, key: string) => {
    const device = agentList.value.find(d => d.agent_id === agentId);
    if (!device) {
      ElMessage.error("设备不存在");
      return;
    }

    // 设置测试状态
    const testingKey = `testing_${key}` as `testing_F${number}`;
    (device as Record<string, boolean>)[testingKey] = true;

    try {
      const response = await api.post("/agent/mock", {
        agent_id: agentId,
        action: "keyboard",
        key: key,
        value: "test",
      });

      const result = response.data;

      if (result && result.code === 0) {
        ElMessage.success(`测试按钮 ${key} 成功`);
      } else {
        ElMessage.error(result?.msg || `测试按钮 ${key} 失败`);
      }
    } catch (error) {
      logAndNoticeError(error as Error, `测试按钮 ${key} 失败`);
    } finally {
      // 清除测试状态
      (device as Record<string, boolean>)[testingKey] = false;
    }
  };

  /**
   * 根据 agent_id 获取设备
   * @param agentId Agent ID
   * @returns AgentDevice 或 undefined
   */
  const getAgentDevice = (agentId: string): AgentDevice | undefined => {
    return agentList.value.find(d => d.agent_id === agentId);
  };

  /**
   * 根据 address 获取设备
   * @param address 设备地址
   * @returns AgentDevice 或 undefined
   */
  const getAgentDeviceByAddress = (address: string): AgentDevice | undefined => {
    return agentList.value.find(d => d.address === address);
  };

  /**
   * 检查设备是否在线
   * @param agentId Agent ID
   * @returns 是否在线
   */
  const isDeviceOnline = (agentId: string): boolean => {
    const device = getAgentDevice(agentId);
    return device?.is_online ?? false;
  };

  /**
   * 获取在线设备列表
   * @returns 在线设备列表
   */
  const getOnlineDevices = (): AgentDevice[] => {
    return agentList.value.filter(device => device.is_online === true);
  };

  /**
   * 获取离线设备列表
   * @returns 离线设备列表
   */
  const getOfflineDevices = (): AgentDevice[] => {
    return agentList.value.filter(device => device.is_online !== true);
  };

  // 自动刷新逻辑
  const { start: startAutoRefresh, stop: stopAutoRefresh } = useControllableInterval(
    async () => {
      await refreshAgentList(false, false);
    },
    refreshInterval,
    { immediate: false }
  );

  /**
   * 启动自动刷新
   */
  const startRefresh = () => {
    refreshAgentList(true, false);
    startAutoRefresh();
  };

  /**
   * 停止自动刷新
   */
  const stopRefresh = () => {
    stopAutoRefresh();
  };

  // 如果启用了自动刷新，在 composable 创建时启动
  if (autoRefresh) {
    startRefresh();
  }

  return {
    // 状态
    agentList,
    loading,

    // 方法
    refreshAgentList,
    testAgentButton,
    getAgentDevice,
    getAgentDeviceByAddress,
    isDeviceOnline,
    getOnlineDevices,
    getOfflineDevices,
    startRefresh,
    stopRefresh,
  };
}

