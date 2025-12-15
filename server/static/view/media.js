import { bluetoothAction, playlistAction, getApiUrl } from "../js/net_util.js";
import { createPlaylistId, formatDateTime, formatDuration, formatDurationMinutes, formatSize } from "../js/utils.js";
const axios = window.axios;

const { ref, watch, onMounted, onUnmounted, nextTick } = window.Vue;
const { ElMessage, ElMessageBox } = window.ElementPlus;
let component = null;
async function loadTemplate() {
  const response = await fetch(`./view/media-template.html?t=${Date.now()}`);
  return await response.text();
}
async function createComponent() {
  if (component) return component;
  const template = await loadTemplate();
  component = {
    setup() {
      const refData = {
        scanDialogVisible: ref(false),
        fileBrowserDialogVisible: ref(false),
        fileBrowserPath: ref("/mnt/ext_base"),
        fileBrowserList: ref([]),
        fileBrowserLoading: ref(false),
        selectedFiles: ref([]),
        fileBrowserTarget: ref("files"), // "files" 或 "pre_files"
        cronBuilder: ref({
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
        }),
        cronPreviewVisible: ref(false),
        cronPreviewTimes: ref([]),
        editingPlaylistId: ref(null),
        editingPlaylistName: ref(""),
        loading: ref(false),
        deviceList: ref([]),
        connectedDeviceList: ref([]),
        dlnaDeviceList: ref([]),
        dlnaScanning: ref(false),
        miDeviceList: ref([]),
        miScanning: ref(false),
        playing: ref(false),
        stopping: ref(false),
        playlistCollection: ref([]),
        activePlaylistId: ref(""),
        playlistStatus: ref(null),
        playlistLoading: ref(false),
        playlistRefreshing: ref(false),
        showMoreActions: ref(false),
        agentListDialogVisible: ref(false),
        agentList: ref([]),
        agentListLoading: ref(false),
      };
      const pendingDeviceType = ref(null);
      const _formatDateTime = formatDateTime;

      // 规范化文件列表格式（对象格式）
      const normalizeFiles = (files, includeDuration = true) => {
        if (!Array.isArray(files)) return [];
        return files.map((fileItem) => {
          if (!fileItem || typeof fileItem !== "object") return null;
          const normalized = {
            uri: fileItem.uri || fileItem.path || fileItem.file || "",
          };
          if (includeDuration) {
            normalized.duration = fileItem.duration || null;
          }
          return normalized;
        }).filter((item) => item !== null);
      };

      // 获取文件名
      const getFileName = (fileItem) => {
        const filePath = fileItem?.uri || fileItem?.path || '';
        return filePath ? String(filePath).split("/").pop() || filePath : '';
      };

      // 计算前置文件列表总时长（秒）
      const getPreFilesTotalDuration = () => {
        const status = refData.playlistStatus.value;
        if (!status || !status.pre_files || status.pre_files.length === 0) {
          return 0;
        }
        return status.pre_files.reduce((total, file) => {
          const duration = file?.duration;
          return total + (typeof duration === 'number' && duration > 0 ? duration : 0);
        }, 0);
      };

      // 计算正式文件列表总时长（秒）
      const getFilesTotalDuration = () => {
        const status = refData.playlistStatus.value;
        if (!status || !status.playlist || status.playlist.length === 0) {
          return 0;
        }
        return status.playlist.reduce((total, file) => {
          const duration = file?.duration;
          return total + (typeof duration === 'number' && duration > 0 ? duration : 0);
        }, 0);
      };

      // 计算播放列表总时长（秒，包括前置文件和播放列表文件）
      const getPlaylistTotalDuration = () => {
        const status = refData.playlistStatus.value;
        if (!status) return 0;
        let total = 0;
        
        // 前置文件时长
        if (status.pre_files && status.pre_files.length > 0) {
          total += status.pre_files.reduce((sum, file) => {
            const duration = file?.duration;
            return sum + (typeof duration === 'number' && duration > 0 ? duration : 0);
          }, 0);
        }
        
        // 播放列表文件时长
        const files = status.playlist || status.files || [];
        if (files.length > 0) {
          total += files.reduce((sum, file) => {
            const duration = file?.duration;
            return sum + (typeof duration === 'number' && duration > 0 ? duration : 0);
          }, 0);
        }
        
        return total;
      };

      const createDefaultPlaylist = (overrides = {}) => ({
        id: overrides.id || createPlaylistId(),
        name: overrides.name || "默认播放列表",
        playlist: overrides.playlist || [],
        pre_files: overrides.pre_files || [],
        current_index: overrides.current_index || 0,
        device_address: overrides.device_address || null,
        device_type: overrides.device_type || "dlna",
        device: overrides.device || { type: "dlna", address: null, name: null },
        schedule: overrides.schedule || { enabled: 0, cron: "", duration: 0 },
      });

      const normalizePlaylistItem = (item, fallbackName = "播放列表") => {
        const playlist = normalizeFiles(item?.playlist || item?.files || [], true);
        const pre_files = normalizeFiles(item?.pre_files || [], true);
        
        let currentIndex = typeof item?.current_index === "number" 
          ? item.current_index 
          : (item?.current_index !== undefined && item?.current_index !== null 
              ? parseInt(item.current_index, 10) || 0 
              : 0);
        if (playlist.length === 0) {
          currentIndex = 0;
        } else {
          if (currentIndex < 0) currentIndex = 0;
          if (currentIndex >= playlist.length) currentIndex = playlist.length - 1;
        }
        const name = (item?.name && String(item.name).trim()) || fallbackName;
        // 优先读取 device.type，如果没有则读取 device_type，最后默认为 "dlna"
        const deviceType = item?.device?.type || item?.device_type || "dlna";
        // 确保设备类型是有效的值：agent, dlna, bluetooth, mi
        const validDeviceType = ["agent", "dlna", "bluetooth", "mi"].includes(deviceType)
          ? deviceType
          : "dlna";
        // 规范化 schedule，确保 cron 是字符串类型
        const schedule = item?.schedule || { enabled: 0, cron: "", duration: 0 };
        const normalizedSchedule = {
          enabled: schedule.enabled || 0,
          cron: (schedule.cron !== undefined && schedule.cron !== null) ? String(schedule.cron) : "",
          duration: schedule.duration || 0,
        };
        
        return {
          id: item?.id || createPlaylistId(),
          name,
          playlist,
          pre_files,
          total: playlist.length,
          current_index: currentIndex,
          pre_index: typeof item?.pre_index === "number" 
            ? item.pre_index 
            : (item?.pre_index !== undefined && item?.pre_index !== null 
                ? parseInt(item.pre_index, 10) : -1),
          device_address: item?.device_address || item?.device?.address || null,
          device_type: validDeviceType,
          device: item?.device || { type: validDeviceType, address: item?.device_address || null, name: item?.device?.name || null },
          schedule: normalizedSchedule,
          trigger_button: item?.trigger_button || "",
          updatedAt: item?.updatedAt || Date.now(),
          isPlaying: item?.isPlaying === true || item?.isPlaying === 1 || false,
        };
      };

      const normalizePlaylistCollection = (raw) => {
        const ensureList = (list) => {
          if (!Array.isArray(list) || list.length === 0) {
            return [normalizePlaylistItem(createDefaultPlaylist())];
          }
          return list.map((item, index) =>
            normalizePlaylistItem(item, item?.name || `播放列表${index + 1}`)
          );
        };

        if (raw && Array.isArray(raw.playlists)) {
          const playlists = ensureList(raw.playlists);
          const activeId = playlists.some((item) => item.id === raw.activePlaylistId)
            ? raw.activePlaylistId
            : playlists[0].id;
          return { playlists, activePlaylistId: activeId };
        }

        if (raw && Array.isArray(raw.playlist)) {
          const migrated = normalizePlaylistItem({
            id: raw.id || raw.playlist_id,
            name: raw.name || "默认播放列表",
            playlist: raw.playlist,
            current_index: raw.current_index,
            device_address: raw.device_address,
          });
          return { playlists: [migrated], activePlaylistId: migrated.id };
        }

        const defaultPlaylist = normalizePlaylistItem(createDefaultPlaylist());
        return { playlists: [defaultPlaylist], activePlaylistId: defaultPlaylist.id };
      };

      // 保存/恢复选中的播放列表ID
      const saveActivePlaylistId = (playlistId) => {
        try {
          if (playlistId) {
            localStorage.setItem('active_playlist_id', playlistId);
          }
        } catch (error) {
          console.warn("保存选中播放列表ID失败:", error);
        }
      };

      const restoreActivePlaylistId = () => {
        try {
          return localStorage.getItem('active_playlist_id');
        } catch (error) {
          console.warn("恢复选中播放列表ID失败:", error);
        }
        return null;
      };

      // 保存最后一次添加文件时的目录路径（内存中）
      let lastFileBrowserPath = "/mnt/ext_base";

      const syncActivePlaylist = (collection) => {
        const list = Array.isArray(collection) ? collection : refData.playlistCollection.value;
        if (!list || list.length === 0) {
          refData.playlistStatus.value = null;
          refData.activePlaylistId.value = "";
          return;
        }
        let activeId = refData.activePlaylistId.value;
        const active = list.find((item) => item.id === activeId) || list[0];
        activeId = active.id;
        refData.activePlaylistId.value = activeId;
        
        // 确保 current_index 是数字类型，直接使用 API 返回的值
        let currentIndex = typeof active.current_index === "number" 
          ? active.current_index 
          : (active.current_index !== undefined && active.current_index !== null 
              ? parseInt(active.current_index, 10) || 0 
              : 0);
        
        // 确保 current_index 在有效范围内
        if (active.playlist && active.playlist.length > 0) {
          if (currentIndex < 0) currentIndex = 0;
          if (currentIndex >= active.playlist.length) currentIndex = active.playlist.length - 1;
        } else {
          currentIndex = 0;
        }
        
        refData.playlistStatus.value = {
          ...active,
          playlist: [...(active.playlist || [])],
          pre_files: [...(active.pre_files || [])],
          current_index: currentIndex,
          pre_index: typeof active.pre_index === "number" 
            ? active.pre_index 
            : (active.pre_index !== undefined && active.pre_index !== null 
                ? parseInt(active.pre_index, 10) : -1),
          in_pre_files: active?.in_pre_files === true || active?.in_pre_files === 1 || false,
          isPlaying: active?.isPlaying === true || active?.isPlaying === 1 || false,
        };
      };

      // 转换前端播放列表格式为后端 API 格式
      const transformPlaylistToApiFormat = (collection) => {
        const playlistDict = {};
        collection.forEach((item) => {
          if (item.id) {
            // 确定设备类型：优先使用 device.type，其次 device_type
            let deviceType = "dlna"; // 默认值
            if (item.device?.type && ["agent", "dlna", "bluetooth", "mi"].includes(item.device.type)) {
              deviceType = item.device.type;
            } else if (
              item.device_type &&
              ["agent", "dlna", "bluetooth", "mi"].includes(item.device_type)
            ) {
              deviceType = item.device_type;
            }

            // 确定设备地址：优先使用 device.address，其次 device_address
            const deviceAddress = item.device?.address || item.device_address || "";

            // 规范化 playlist 和 pre_files 格式：确保是新格式 {"uri": "地址"}，保留 duration
            const normalizedFiles = normalizeFiles(item.playlist || [], true);
            const normalizedPreFiles = normalizeFiles(item.pre_files || [], true);
            
            playlistDict[item.id] = {
              id: item.id,
              name: item.name || "默认播放列表",
              files: normalizedFiles,
              pre_files: normalizedPreFiles,
              current_index: item.current_index || 0,
              device: {
                address: deviceAddress,
                type: deviceType,
                name: item.device?.name || null,
              },
              schedule: item.schedule || { enabled: 0, cron: "" },
              trigger_button: item.trigger_button || "",
              create_time: item.create_time || _formatDateTime(),
              updated_time: _formatDateTime(),
            };
          }
        });
        return playlistDict;
      };

      const savePlaylist = async (collectionOverride) => {
        try {
          const collection = (collectionOverride || refData.playlistCollection.value || []).map(
            (item) => ({
              ...item,
              total: Array.isArray(item.playlist) ? item.playlist.length : 0,
              updatedAt: Date.now(),
            })
          );

          const playlistDict = transformPlaylistToApiFormat(collection);
          const response = await playlistAction("update", "POST", playlistDict);
          if (response.code !== 0) {
            throw new Error(response.msg || "保存播放列表失败");
          }
        } catch (error) {
          console.error("保存播放列表失败:", error);
        }
      };

      const transformApiDataToPlaylistFormat = (apiData) => {
        if (!apiData || typeof apiData !== "object") {
          return null;
        }

        // 如果返回的是字典格式（多个播放列表，key 是 id）
        if (!Array.isArray(apiData) && Object.keys(apiData).length > 0) {
          const playlists = Object.values(apiData).map((item) => {
            // 规范化 files 和 pre_files 格式：兼容旧格式（字符串数组）和新格式（对象数组）
            const normalizedFiles = normalizeFiles(item.files || [], true);
            const normalizedPreFiles = normalizeFiles(item.pre_files || [], true);
            
            // 规范化 schedule，确保 cron 是字符串类型
            const schedule = item.schedule || { enabled: 0, cron: "", duration: 0 };
            const normalizedSchedule = {
              enabled: schedule.enabled || 0,
              cron: (schedule.cron !== undefined && schedule.cron !== null) ? String(schedule.cron) : "",
              duration: schedule.duration || 0,
            };
            
            return {
              id: item.id,
              name: item.name || "默认播放列表",
              playlist: normalizedFiles,
              pre_files: normalizedPreFiles,
              current_index: typeof item.current_index === "number" 
                ? item.current_index 
                : (item.current_index !== undefined && item.current_index !== null 
                    ? parseInt(item.current_index, 10) || 0 
                    : 0),
              pre_index: typeof item.pre_index === "number" 
                ? item.pre_index 
                : (item.pre_index !== undefined && item.pre_index !== null 
                    ? parseInt(item.pre_index, 10) : -1),
              in_pre_files: item?.in_pre_files === true || item?.in_pre_files === 1 || false,
            device_address: item.device?.address || item.device_address || null,
            device_type: item.device?.type || item.device_type || "dlna",
            device: item.device || {
              type: item.device_type || "dlna",
              address: item.device_address || null,
            },
              schedule: normalizedSchedule,
              trigger_button: item?.trigger_button || "",
              create_time: item.create_time,
              updated_time: item.updated_time,
              updatedAt: item.updated_time ? new Date(item.updated_time).getTime() : Date.now(),
              isPlaying: item?.isPlaying === true || item?.isPlaying === 1 || false,
            };
          });

          return {
            playlists: playlists,
            activePlaylistId: playlists[0]?.id || null,
          };
        }

        // 如果返回的是数组
        if (Array.isArray(apiData)) {
          return {
            playlists: apiData.map((item) => ({
              ...item,
              playlist: normalizeFiles(item.files || item.playlist || [], false),
            })),
            activePlaylistId: apiData[0]?.id || null,
          };
        }

        // 如果返回的是单个播放列表对象
        if (apiData.id) {
          return {
            playlists: [
              {
                ...apiData,
                playlist: normalizeFiles(apiData.files || apiData.playlist || [], true),
              },
            ],
            activePlaylistId: apiData.id,
          };
        }

        return null;
      };

      const loadPlaylist = async () => {
        try {
          const response = await playlistAction("get", "GET", {});
          if (response.code !== 0) {
            throw new Error(response.msg || "获取播放列表失败");
          }

          const parsed = transformApiDataToPlaylistFormat(response.data);
          const normalized = normalizePlaylistCollection(parsed);
          refData.playlistCollection.value = normalized.playlists;
          
          // 从 localStorage 恢复选中的播放列表ID
          const savedPlaylistId = restoreActivePlaylistId();
          if (savedPlaylistId && normalized.playlists.some(p => p.id === savedPlaylistId)) {
            refData.activePlaylistId.value = savedPlaylistId;
          } else {
            refData.activePlaylistId.value = normalized.activePlaylistId;
          }
          
          syncActivePlaylist(normalized.playlists);
          return normalized;
        } catch (error) {
          console.error("从接口加载播放列表失败:", error);
          const fallback = normalizePlaylistCollection(null);
          refData.playlistCollection.value = fallback.playlists;
          
          // 从 localStorage 恢复选中的播放列表ID
          const savedPlaylistId = restoreActivePlaylistId();
          if (savedPlaylistId && fallback.playlists.some(p => p.id === savedPlaylistId)) {
            refData.activePlaylistId.value = savedPlaylistId;
          } else {
            refData.activePlaylistId.value = fallback.activePlaylistId;
          }
          
          syncActivePlaylist(fallback.playlists);
          return fallback;
        }
      };

      const updateActivePlaylistData = async (mutator) => {
        if (typeof mutator !== "function") return null;
        let collection = refData.playlistCollection.value.map((item) => ({
          ...item,
          playlist: Array.isArray(item.playlist) ? item.playlist.map(f => ({ ...f })) : [],
          pre_files: Array.isArray(item.pre_files) ? item.pre_files.map(f => ({ ...f })) : [],
        }));
        if (collection.length === 0) {
          const defaultPlaylist = normalizePlaylistItem(createDefaultPlaylist());
          collection = [defaultPlaylist];
          refData.activePlaylistId.value = defaultPlaylist.id;
        }
        let index = collection.findIndex((item) => item.id === refData.activePlaylistId.value);
        if (index === -1) {
          index = 0;
          refData.activePlaylistId.value = collection[0].id;
        }
        const currentItem = collection[index];
        const updatedItem =
          mutator({
            ...currentItem,
            playlist: currentItem.playlist.map(f => ({ ...f })),
            pre_files: (currentItem.pre_files || []).map(f => ({ ...f })),
          }) || currentItem;
        collection[index] = normalizePlaylistItem(updatedItem, currentItem.name);
        refData.playlistCollection.value = collection;
        
        await savePlaylist(collection);
        syncActivePlaylist(collection);
        return refData.playlistStatus.value;
      };

      // 刷新已配对/已连接设备列表
      const refreshConnectedList = async () => {
        const playlistStatus = refData.playlistStatus.value;
        const deviceType =
          pendingDeviceType.value ||
          playlistStatus?.device?.type ||
          playlistStatus?.device_type ||
          "dlna";
        if (!["agent", "bluetooth"].includes(deviceType)) {
          refData.connectedDeviceList.value = [];
          return;
        }

        try {
          refData.loading.value = true;
          let rspData = null;
          if (deviceType === "agent") {
            const rsp = await axios.get(getApiUrl() + "/agent/paired");
            rspData = rsp.data;
          } else {
            rspData = await bluetoothAction("paired", "GET");
          }

          if (rspData.code === 0) {
            refData.connectedDeviceList.value = rspData.data || [];
          } else {
            ElMessage.error(rspData.msg || "获取设备失败");
          }
        } catch (error) {
          console.error("获取设备失败:", error);
          ElMessage.error("获取设备失败");
        } finally {
          refData.loading.value = false;
        }
      };
      // 连接设备
      const handleConnectDevice = async (device) => {
        try {
          device.connecting = true;
          const rsp = await bluetoothAction("connect", "POST", {
            address: device.address,
          });
          if (rsp.code === 0) {
            ElMessage.success(`成功连接到设备: ${device.name}`);
            // 刷新已连接设备列表
            await refreshConnectedList();
            // 从扫描列表中移除已连接的设备
            refData.deviceList.value = refData.deviceList.value.filter(
              (d) => d.address !== device.address
            );
          } else {
            ElMessage.error(rsp.msg || "连接失败");
          }
        } catch (error) {
          console.error("连接设备失败:", error);
          ElMessage.error("连接设备失败");
        } finally {
          device.connecting = false;
        }
      };

      const scanDlnaDevices = async () => {
        try {
          refData.dlnaScanning.value = true;
          const response = await fetch(`${getApiUrl()}/dlna/scan?timeout=5`);
          const result = await response.json();
          if (result.code === 0) {
            refData.dlnaDeviceList.value = result.data || [];
            ElMessage.success(`扫描到 ${refData.dlnaDeviceList.value.length} 个 DLNA 设备`);
          } else {
            ElMessage.error(result.msg || "扫描 DLNA 设备失败");
          }
        } catch (error) {
          console.error("扫描 DLNA 设备失败:", error);
          ElMessage.error("扫描 DLNA 设备失败: " + (error.message || "未知错误"));
        } finally {
          refData.dlnaScanning.value = false;
        }
      };

      const scanMiDevices = async () => {
        try {
          refData.miScanning.value = true;
          const response = await fetch(`${getApiUrl()}/mi/scan?timeout=5`);
          const result = await response.json();
          if (result.code === 0) {
            refData.miDeviceList.value = result.data || [];
            ElMessage.success(`扫描到 ${refData.miDeviceList.value.length} 个小米设备`);
          } else {
            ElMessage.error(result.msg || "扫描小米设备失败");
          }
        } catch (error) {
          console.error("扫描小米设备失败:", error);
          ElMessage.error("扫描小米设备失败: " + (error.message || "未知错误"));
        } finally {
          refData.miScanning.value = false;
        }
      };

      const handleUpdateDeviceList = async () => {
        try {
          refData.loading.value = true;
          const rsp = await bluetoothAction("scan", "GET");
          if (rsp.code === 0) {
            refData.deviceList.value = (rsp.data || []).map((device) => ({
              ...device,
              connecting: false,
            }));
            ElMessage.success(`扫描完成，找到 ${refData.deviceList.value.length} 个设备`);
          } else {
            ElMessage.error(rsp.msg || "扫描失败");
          }
        } catch (error) {
          console.error("扫描设备失败:", error);
          ElMessage.error("扫描设备失败");
        } finally {
          refData.loading.value = false;
        }
      };

      const handleOpenScanDialog = () => {
        refData.scanDialogVisible.value = true;
      };

      const handleCloseScanDialog = () => {
        refData.scanDialogVisible.value = false;
      };

      // Agent设备列表相关方法
      const handleOpenAgentListDialog = async () => {
        refData.agentListDialogVisible.value = true;
        await handleRefreshAgentList();
      };

      const handleCloseAgentListDialog = () => {
        refData.agentListDialogVisible.value = false;
      };

      const handleRefreshAgentList = async (showLoading = true) => {
        try {
          if (showLoading) {
            refData.agentListLoading.value = true;
          }
          const response = await axios.get(getApiUrl() + "/agent/list");
          if (response.data && response.data.code === 0) {
            refData.agentList.value = response.data.data || [];
          } else {
            if (showLoading) {
              ElMessage.error(response.data?.msg || "获取设备列表失败");
            }
            refData.agentList.value = [];
          }
        } catch (error) {
          console.error("获取Agent设备列表失败:", error);
          if (showLoading) {
            ElMessage.error("获取设备列表失败: " + (error.message || "未知错误"));
          }
          refData.agentList.value = [];
        } finally {
          if (showLoading) {
            refData.agentListLoading.value = false;
          }
        }
      };

      const handleTestAgentButton = async (agentId, key) => {
        try {
          // 设置按钮loading状态
          const device = refData.agentList.value.find(d => d.agent_id === agentId);
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
          console.error(`测试按钮 ${key} 失败:`, error);
          ElMessage.error(`测试按钮 ${key} 失败: ` + (error.message || "未知错误"));
        } finally {
          // 清除loading状态
          const device = refData.agentList.value.find(d => d.agent_id === agentId);
          if (device) {
            device[`testing_${key}`] = false;
          }
        }
      };

      const cronBuilderVisible = ref(false);

      const handleOpenCronBuilder = () => {
        cronBuilderVisible.value = true;
        const cronExpr = refData.playlistStatus.value?.schedule?.cron;
        if (cronExpr) {
          parseCronExpression(cronExpr);
        } else {
          resetCronBuilder();
        }
      };

      const handleCloseCronBuilder = () => {
        cronBuilderVisible.value = false;
      };

      const resetCronBuilder = () => {
        refData.cronBuilder.value = {
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
        };
        updateCronExpression();
      };

      const parseCronExpression = (cronExpr) => {
        try {
          if (!cronExpr || typeof cronExpr !== 'string') {
            resetCronBuilder();
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
            resetCronBuilder();
            return;
          }

          if (parts.length === 5 || parts.length === 6) {
            if (sec === "*") {
              refData.cronBuilder.value.second = "*";
              refData.cronBuilder.value.secondCustom = "";
            } else if (sec === "0") {
              refData.cronBuilder.value.second = "0";
              refData.cronBuilder.value.secondCustom = "";
            } else {
              refData.cronBuilder.value.second = "custom";
              refData.cronBuilder.value.secondCustom = sec;
            }

            // 解析分
            if (min === "*") {
              refData.cronBuilder.value.minute = "*";
              refData.cronBuilder.value.minuteCustom = "";
            } else if (min === "0") {
              refData.cronBuilder.value.minute = "0";
              refData.cronBuilder.value.minuteCustom = "";
            } else if (min.startsWith("*/")) {
              // 处理步长格式：*/30, */15 等
              refData.cronBuilder.value.minute = "custom";
              refData.cronBuilder.value.minuteCustom = min;
            } else {
              refData.cronBuilder.value.minute = "custom";
              refData.cronBuilder.value.minuteCustom = min;
            }

            // 解析时
            if (hour === "*") {
              refData.cronBuilder.value.hour = "*";
              refData.cronBuilder.value.hourCustom = "";
            } else if (hour === "0") {
              refData.cronBuilder.value.hour = "0";
              refData.cronBuilder.value.hourCustom = "";
            } else {
              refData.cronBuilder.value.hour = "custom";
              refData.cronBuilder.value.hourCustom = hour;
            }

            // 解析日
            if (day === "*") {
              refData.cronBuilder.value.day = "*";
              refData.cronBuilder.value.dayCustom = "";
            } else {
              refData.cronBuilder.value.day = "custom";
              refData.cronBuilder.value.dayCustom = day;
            }

            // 解析月
            if (month === "*") {
              refData.cronBuilder.value.month = "*";
              refData.cronBuilder.value.monthCustom = "";
            } else {
              refData.cronBuilder.value.month = "custom";
              refData.cronBuilder.value.monthCustom = month;
            }

            // 解析周
            if (weekday === "*") {
              refData.cronBuilder.value.weekday = "*";
              refData.cronBuilder.value.weekdayCustom = "";
            } else if (weekday === "1-5") {
              refData.cronBuilder.value.weekday = "1-5";
              refData.cronBuilder.value.weekdayCustom = "";
            } else if (weekday === "0,6" || weekday === "6,0") {
              refData.cronBuilder.value.weekday = "0,6";
              refData.cronBuilder.value.weekdayCustom = "";
            } else {
              refData.cronBuilder.value.weekday = "custom";
              refData.cronBuilder.value.weekdayCustom = weekday;
            }

            // 立即更新生成的表达式
            updateCronExpression();
          } else {
            console.warn("Cron 表达式格式错误，部分数量:", parts.length);
            resetCronBuilder();
          }
        } catch (error) {
          console.error("解析 Cron 表达式失败:", error);
          resetCronBuilder();
        }
      };

      // 更新生成的 Cron 表达式
      const updateCronExpression = () => {
        const builder = refData.cronBuilder.value;

        const second =
          builder.second === "custom" ? builder.secondCustom || "*" : builder.second || "*";
        const minute =
          builder.minute === "custom" ? builder.minuteCustom || "*" : builder.minute || "*";
        const hour = builder.hour === "custom" ? builder.hourCustom || "*" : builder.hour || "*";
        const day = builder.day === "custom" ? builder.dayCustom || "*" : builder.day || "*";
        const month =
          builder.month === "custom" ? builder.monthCustom || "*" : builder.month || "*";
        const weekday =
          builder.weekday === "custom" ? builder.weekdayCustom || "*" : builder.weekday || "*";

        const generated = `${second} ${minute} ${hour} ${day} ${month} ${weekday}`;
        refData.cronBuilder.value.generated = generated;
      };

      const handleApplyCronExpression = () => {
        if (!refData.cronBuilder.value.generated) return;
        const cronExpr = refData.cronBuilder.value.generated;
        if (refData.playlistStatus.value) {
          handleUpdatePlaylistCron(cronExpr);
          handleCloseCronBuilder();
          ElMessage.success("Cron 表达式已应用到当前播放列表");
        } else {
          ElMessage.warning("请先选择一个播放列表");
        }
      };

      const applyExample = (example) => {
        try {
          parseCronExpression(example);
          nextTick(() => {
            if (refData.cronBuilder.value.generated && refData.playlistStatus.value) {
              handleUpdatePlaylistCron(refData.cronBuilder.value.generated);
              ElMessage.success("示例已应用到当前播放列表");
            } else if (refData.cronBuilder.value.generated) {
              ElMessage.warning("请先选择一个播放列表");
            }
          });
        } catch (error) {
          console.error("应用示例失败:", error);
          ElMessage.error("应用示例失败: " + error.message);
        }
      };

      const parseCronField = (expr, min, max) => {
        if (expr === "*") {
          return null; // null 表示匹配所有值
        }
        if (!expr || typeof expr !== 'string') {
          return null;
        }

        const values = new Set();
        const parts = String(expr).split(",");

        for (const part of parts) {
          const trimmed = part.trim();
          if (trimmed.includes("/")) {
            // 步长：*/30 或 0-59/10
            const [range, step] = trimmed.split("/");
            const stepNum = parseInt(step, 10);
            if (range === "*") {
              for (let i = min; i <= max; i += stepNum) {
                values.add(i);
              }
            } else if (range.includes("-")) {
              const [start, end] = range.split("-").map((x) => parseInt(x, 10));
              for (let i = start; i <= end; i += stepNum) {
                values.add(i);
              }
            }
          } else if (trimmed.includes("-")) {
            // 范围：1-5
            const [start, end] = trimmed.split("-").map((x) => parseInt(x, 10));
            for (let i = start; i <= end; i++) {
              values.add(i);
            }
          } else {
            // 单个值
            const val = parseInt(trimmed, 10);
            if (!isNaN(val) && val >= min && val <= max) {
              values.add(val);
            }
          }
        }

        return values.size > 0 ? Array.from(values).sort((a, b) => a - b) : null;
      };

      // 计算 Cron 表达式的下 N 次执行时间
      const calculateNextCronTimes = (cronExpr, count = 3) => {
        try {
          if (!cronExpr || typeof cronExpr !== 'string') {
            throw new Error("Cron 表达式必须是字符串类型");
          }
          const parts = String(cronExpr).trim().split(/\s+/);
          if (parts.length !== 6) {
            throw new Error("Cron 表达式必须包含6个字段：秒 分 时 日 月 周");
          }

          const [secExpr, minExpr, hourExpr, dayExpr, monthExpr, weekdayExpr] = parts;

          // 解析各个字段
          const seconds = parseCronField(secExpr, 0, 59);
          const minutes = parseCronField(minExpr, 0, 59);
          const hours = parseCronField(hourExpr, 0, 23);
          const days = parseCronField(dayExpr, 1, 31);
          const months = parseCronField(monthExpr, 1, 12);
          let weekdays = parseCronField(weekdayExpr, 0, 7);

          // 处理周字段：7 和 0 都表示周日
          if (weekdays && weekdays.includes(7)) {
            weekdays = weekdays.filter((d) => d !== 7);
            if (!weekdays.includes(0)) {
              weekdays.push(0);
            }
            weekdays.sort((a, b) => a - b);
          }

          const times = [];
          const current = new Date();
          current.setMilliseconds(0);

          // 如果当前秒不在范围内，跳到下一分钟
          if (seconds && !seconds.includes(current.getSeconds())) {
            current.setSeconds(0);
            current.setMinutes(current.getMinutes() + 1);
          }

          let iterations = 0;
          const maxIterations = 10000;

          while (times.length < count && iterations < maxIterations) {
            iterations++;

            // 检查月份
            const currentMonth = current.getMonth() + 1; // getMonth() 返回 0-11
            if (months && !months.includes(currentMonth)) {
              // 跳到下一个有效月份的第一天
              let nextMonth = null;
              for (const m of months) {
                if (m > currentMonth) {
                  nextMonth = m;
                  break;
                }
              }
              if (nextMonth === null) {
                // 跳到下一年的第一个有效月份
                nextMonth = months[0];
                current.setFullYear(current.getFullYear() + 1, nextMonth - 1, 1);
                current.setHours(0, 0, seconds ? seconds[0] : 0);
              } else {
                current.setMonth(nextMonth - 1, 1);
                current.setHours(0, 0, seconds ? seconds[0] : 0);
              }
              continue;
            }

            // 检查日期和星期
            const currentDay = current.getDate();
            const currentWeekday = current.getDay(); // 0=周日, 1=周一, ..., 6=周六

            let validDay = true;
            if (dayExpr !== "*" && weekdayExpr !== "*") {
              // 两个都指定，满足任意一个即可（OR逻辑）
              validDay =
                (days && days.includes(currentDay)) ||
                (weekdays && weekdays.includes(currentWeekday));
            } else if (dayExpr !== "*") {
              // 只检查日期
              validDay = days && days.includes(currentDay);
            } else if (weekdayExpr !== "*") {
              // 只检查星期
              validDay = weekdays && weekdays.includes(currentWeekday);
            }

            if (!validDay) {
              current.setDate(current.getDate() + 1);
              current.setHours(0, 0, seconds ? seconds[0] : 0);
              continue;
            }

            // 检查小时
            const currentHour = current.getHours();
            if (hours && !hours.includes(currentHour)) {
              // 跳到下一个有效小时
              let nextHour = null;
              for (const h of hours) {
                if (h > currentHour) {
                  nextHour = h;
                  break;
                }
              }
              if (nextHour === null) {
                // 跳到下一天的第一个有效小时
                current.setDate(current.getDate() + 1);
                current.setHours(hours[0], 0, seconds ? seconds[0] : 0);
              } else {
                current.setHours(nextHour, 0, seconds ? seconds[0] : 0);
              }
              continue;
            }

            // 检查分钟
            const currentMinute = current.getMinutes();
            if (minutes && !minutes.includes(currentMinute)) {
              // 跳到下一个有效分钟
              let nextMinute = null;
              for (const m of minutes) {
                if (m > currentMinute) {
                  nextMinute = m;
                  break;
                }
              }
              if (nextMinute === null) {
                // 跳到下一个有效小时的第一分钟
                let nextHour = null;
                for (const h of hours || [currentHour]) {
                  if (h > currentHour) {
                    nextHour = h;
                    break;
                  }
                }
                if (nextHour === null) {
                  current.setDate(current.getDate() + 1);
                  current.setHours(hours ? hours[0] : 0, minutes[0], seconds ? seconds[0] : 0);
                } else {
                  current.setHours(nextHour, minutes[0], seconds ? seconds[0] : 0);
                }
              } else {
                current.setMinutes(nextMinute, seconds ? seconds[0] : 0);
              }
              continue;
            }

            // 检查秒
            const currentSecond = current.getSeconds();
            if (seconds && !seconds.includes(currentSecond)) {
              // 跳到下一个有效秒
              let nextSecond = null;
              for (const s of seconds) {
                if (s > currentSecond) {
                  nextSecond = s;
                  break;
                }
              }
              if (nextSecond === null) {
                // 跳到下一分钟的第一个有效秒
                current.setMinutes(current.getMinutes() + 1);
                current.setSeconds(seconds[0]);
              } else {
                current.setSeconds(nextSecond);
              }
              continue;
            }

            // 检查是否在未来
            if (current > new Date()) {
              const timeStr =
                current.getFullYear() +
                "-" +
                String(current.getMonth() + 1).padStart(2, "0") +
                "-" +
                String(current.getDate()).padStart(2, "0") +
                " " +
                String(current.getHours()).padStart(2, "0") +
                ":" +
                String(current.getMinutes()).padStart(2, "0") +
                ":" +
                String(current.getSeconds()).padStart(2, "0");
              times.push(timeStr);
            }

            // 移动到下一个可能的执行时间
            if (seconds && seconds.length > 0) {
              current.setSeconds(seconds[0]);
            }
            current.setMinutes(current.getMinutes() + 1);
          }

          return times.slice(0, count);
        } catch (error) {
          console.error("计算 Cron 执行时间失败:", error);
          throw error;
        }
      };

      // 预览生成的 Cron 表达式
      const handlePreviewGeneratedCron = () => {
        const cronExpr = refData.cronBuilder.value.generated;
        if (!cronExpr) {
          ElMessage.warning("请先生成 Cron 表达式");
          return;
        }
        try {
          const times = calculateNextCronTimes(cronExpr, 5);
          refData.cronPreviewTimes.value = times;
          refData.cronPreviewVisible.value = true;
        } catch (error) {
          ElMessage.error("预览失败: " + (error.message || "无效的 Cron 表达式"));
          refData.cronPreviewTimes.value = [];
        }
      };

      // 预览 Cron 表达式
      // 切换播放列表的 Cron 启用状态
      const handleTogglePlaylistCronEnabled = async (enabled) => {
        if (!refData.playlistStatus.value) return;
        await updateActivePlaylistData((playlistInfo) => {
          if (!playlistInfo.schedule) {
            playlistInfo.schedule = { enabled: 0, cron: "", duration: 0 };
          }
          playlistInfo.schedule.enabled = enabled ? 1 : 0;
          return playlistInfo;
        });
      };

      // 更新播放列表的 Cron 表达式
      const handleUpdatePlaylistCron = async (cron) => {
        if (!refData.playlistStatus.value) return;
        await updateActivePlaylistData((playlistInfo) => {
          if (!playlistInfo.schedule) {
            playlistInfo.schedule = { enabled: 0, cron: "", duration: 0 };
          }
          playlistInfo.schedule.cron = cron;
          return playlistInfo;
        });
      };

      // 更新播放列表的持续时间
      const handleUpdatePlaylistDuration = async (duration) => {
        if (!refData.playlistStatus.value) return;
        await updateActivePlaylistData((playlistInfo) => {
          if (!playlistInfo.schedule) {
            playlistInfo.schedule = { enabled: 0, cron: "", duration: 0 };
          }
          playlistInfo.schedule.duration = duration || 0;
          return playlistInfo;
        });
      };

      // 更新播放列表的触发按钮
      const handleUpdateTriggerButton = async (triggerButton) => {
        if (!refData.playlistStatus.value) return;
        await updateActivePlaylistData((playlistInfo) => {
          playlistInfo.trigger_button = triggerButton || "";
          return playlistInfo;
        });
      };




      // 预览播放列表的 Cron 执行时间
      const handlePreviewPlaylistCron = () => {
        if (!refData.playlistStatus.value || !refData.playlistStatus.value.schedule?.cron) {
          ElMessage.warning("请先设置 Cron 表达式");
          return;
        }
        try {
          const cronExpr = refData.playlistStatus.value.schedule.cron;
          const times = calculateNextCronTimes(cronExpr, 5);
          if (times && times.length > 0) {
            refData.cronPreviewTimes.value = times;
            refData.cronPreviewVisible.value = true;
          } else {
            ElMessage.warning("无法解析 Cron 表达式");
          }
        } catch (error) {
          ElMessage.error("预览失败: " + error.message);
        }
      };

      // 更新播放列表的设备类型
      const handleUpdatePlaylistDeviceType = async (deviceType) => {
        if (!refData.playlistStatus.value) return;

        const validDeviceTypes = ["agent", "dlna", "bluetooth", "mi"];
        if (!validDeviceTypes.includes(deviceType)) {
          ElMessage.error(`无效的设备类型: ${deviceType}`);
          return;
        }

        pendingDeviceType.value = deviceType;
        const status = refData.playlistStatus.value;
        status.device_type = deviceType;
        if (!status.device) {
          status.device = { type: deviceType, address: "", name: null };
        } else {
          status.device.type = deviceType;
        }

        await refreshConnectedList();
      };

      // 更新播放列表的设备地址
      const handleUpdatePlaylistDeviceAddress = async (address, name = null) => {
        if (!refData.playlistStatus.value) return;
        await updateActivePlaylistData((playlistInfo) => {
          const finalType =
            pendingDeviceType.value ||
            playlistInfo.device?.type ||
            playlistInfo.device_type ||
            "dlna";

          if (!playlistInfo.device) {
            playlistInfo.device = { address: "", type: finalType, name: null };
          }
          playlistInfo.device.type = finalType;
          playlistInfo.device.address = address;
          if (name !== null) {
            playlistInfo.device.name = name;
          }
          playlistInfo.device_address = address;
          playlistInfo.device_type = finalType;
          return playlistInfo;
        });
        pendingDeviceType.value = null;
      };

      // 选择蓝牙设备
      const handleSelectBluetoothDevice = async (address) => {
        const device = refData.connectedDeviceList.value.find((d) => d.address === address);
        const name = device ? device.name : null;
        await handleUpdatePlaylistDeviceAddress(address, name);
      };

      // 选择设备代理设备
      const handleSelectAgentDevice = async (device) => {
        const address = typeof device === 'string' ? device : device.address;
        const name = typeof device === 'string' ? null : device.name;
        await handleUpdatePlaylistDeviceAddress(address, name);
      };

      // 选择小米设备
      const handleSelectMiDevice = async (device) => {
        const address = device.deviceID || device.address || '';
        const name = device.name || '';
        await handleUpdatePlaylistDeviceAddress(address, name);
      };




      // 刷新播放列表状态
      // @param {boolean} onlyCurrent - 如果为 true，只刷新当前激活的播放列表；如果为 false，刷新全部播放列表
      // @param {boolean} isAutoRefresh - 是否为自动刷新（定时器触发），默认为 false
      const refreshPlaylistStatus = async (onlyCurrent = false, isAutoRefresh = false) => {
        try {
          // 如果正在编辑设备配置（pendingDeviceType 不为 null），且是自动刷新，则跳过刷新，避免覆盖未保存的更改
          if (isAutoRefresh && onlyCurrent && pendingDeviceType.value !== null) {
            return;
          }
          
          refData.playlistRefreshing.value = true;
          
          if (onlyCurrent) {
            // 只刷新当前激活的播放列表状态
            const activeId = refData.activePlaylistId.value;
            if (!activeId) {
              return;
            }
            
            // 只获取当前激活的播放列表
            const response = await playlistAction("get", "GET", { id: activeId });
            if (response.code !== 0) {
              throw new Error(response.msg || "获取播放列表状态失败");
            }

            // 解析返回的数据
            const parsed = transformApiDataToPlaylistFormat(response.data);
            if (!parsed || !parsed.playlists || parsed.playlists.length === 0) {
              return;
            }

            const updatedPlaylist = parsed.playlists[0];
            
            // 更新 playlistCollection 中对应的项
            const collection = refData.playlistCollection.value.map((item) => {
              if (item.id === activeId) {
                return {
                  ...item,
                  ...updatedPlaylist,
                  // 保留原有的 playlist 和 pre_files 数组引用，只更新状态字段
                  playlist: updatedPlaylist.playlist || item.playlist,
                  pre_files: updatedPlaylist.pre_files || item.pre_files,
                  current_index: updatedPlaylist.current_index !== undefined 
                    ? updatedPlaylist.current_index 
                    : item.current_index,
                  isPlaying: updatedPlaylist?.isPlaying === true || updatedPlaylist?.isPlaying === 1 || false,
                };
              }
              return item;
            });
            
            refData.playlistCollection.value = collection;
            
            // 同步更新当前激活的播放列表状态
            syncActivePlaylist(collection);
          } else {
            // 刷新全部播放列表
            await loadPlaylist();
          }
        } catch (error) {
          console.error("刷新播放列表状态失败:", error);
        } finally {
          refData.playlistRefreshing.value = false;
        }
      };

      const handlePlayPlaylist = async () => {
        const status = refData.playlistStatus.value;
        if (!status || !status.id) {
          ElMessage.warning("播放列表不存在");
          return;
        }
        if (!status.playlist || status.playlist.length === 0) {
          ElMessage.warning("播放列表为空，请先添加文件");
          return;
        }
        try {
          refData.playing.value = true;
          await updateActivePlaylistData((playlistInfo) => {
            const list = Array.isArray(playlistInfo.playlist) ? playlistInfo.playlist : [];
            playlistInfo.current_index = Math.max(0, Math.min(playlistInfo.current_index || 0, list.length - 1));
            playlistInfo.total = list.length;
            return playlistInfo;
          });
          
          const response = await playlistAction("play", "POST", { id: status.id });
          if (response.code !== 0) {
            throw new Error(response.msg || "播放失败");
          }

          // 刷新播放列表状态以更新 isPlaying
          await refreshPlaylistStatus();

          ElMessage.success("开始播放");
        } catch (error) {
          console.error("播放失败:", error);
          ElMessage.error("播放失败: " + (error.message || "未知错误"));
        } finally {
          refData.playing.value = false;
        }
      };

      const handlePlayNext = async () => {
        const status = refData.playlistStatus.value;
        if (!status || !status.id) {
          ElMessage.warning("播放列表不存在");
          return;
        }
        if (!status.playlist || status.playlist.length === 0) {
          ElMessage.warning("播放列表为空，无法播放下一首");
          return;
        }
        try {
          refData.playing.value = true;
          const response = await playlistAction("playNext", "POST", { id: status.id });
          if (response.code !== 0) {
            throw new Error(response.msg || "播放下一首失败");
          }
          await refreshPlaylistStatus();

          ElMessage.success("已切换到下一首");
        } catch (error) {
          console.error("播放下一首失败:", error);
          ElMessage.error("播放下一首失败: " + (error.message || "未知错误"));
        } finally {
          refData.playing.value = false;
        }
      };

      const handlePlayPre = async () => {
        const status = refData.playlistStatus.value;
        if (!status || !status.id) {
          ElMessage.warning("播放列表不存在");
          return;
        }
        // 检查是否有可播放的内容（pre_files 或 playlist）
        const hasPreFiles = status.pre_files && status.pre_files.length > 0;
        const hasPlaylist = status.playlist && status.playlist.length > 0;
        if (!hasPreFiles && !hasPlaylist) {
          ElMessage.warning("播放列表为空，无法播放上一首");
          return;
        }
        try {
          refData.playing.value = true;
          const response = await playlistAction("playPre", "POST", { id: status.id });
          if (response.code !== 0) {
            throw new Error(response.msg || "播放上一首失败");
          }
          await refreshPlaylistStatus();

          ElMessage.success("已切换到上一首");
        } catch (error) {
          console.error("播放上一首失败:", error);
          ElMessage.error("播放上一首失败: " + (error.message || "未知错误"));
        } finally {
          refData.playing.value = false;
        }
      };

      const handleStopPlaylist = async () => {
        const status = refData.playlistStatus.value;
        if (!status || !status.id) {
          ElMessage.warning("播放列表不存在");
          return;
        }
        try {
          refData.stopping.value = true;
          const response = await playlistAction("stop", "POST", { id: status.id });
          if (response.code !== 0) {
            throw new Error(response.msg || "停止播放失败");
          }
          await refreshPlaylistStatus();

          ElMessage.success("已停止播放");
        } catch (error) {
          console.error("停止播放列表失败:", error);
          ElMessage.error("停止播放列表失败: " + (error.message || "未知错误"));
        } finally {
          refData.stopping.value = false;
        }
      };

      const handleMovePlaylistItemUp = async (index) => {
        const status = refData.playlistStatus.value;
        if (!status || index <= 0 || index >= status.playlist.length) return;

        try {
          refData.playlistLoading.value = true;
          await updateActivePlaylistData((playlistInfo) => {
            const list = [...playlistInfo.playlist];
            [list[index - 1], list[index]] = [list[index], list[index - 1]];
            playlistInfo.playlist = list;
            if (playlistInfo.current_index === index) {
              playlistInfo.current_index = index - 1;
            } else if (playlistInfo.current_index === index - 1) {
              playlistInfo.current_index = index;
            }
            playlistInfo.total = list.length;
            return playlistInfo;
          });
          ElMessage.success("已上移");
        } catch (error) {
          console.error("上移失败:", error);
          ElMessage.error("上移失败: " + (error.message || "未知错误"));
        } finally {
          refData.playlistLoading.value = false;
        }
      };

      const handleMovePlaylistItemDown = async (index) => {
        const status = refData.playlistStatus.value;
        if (!status || index < 0 || index >= status.playlist.length - 1) return;

        try {
          refData.playlistLoading.value = true;
          await updateActivePlaylistData((playlistInfo) => {
            const list = [...playlistInfo.playlist];
            [list[index], list[index + 1]] = [list[index + 1], list[index]];
            playlistInfo.playlist = list;
            if (playlistInfo.current_index === index) {
              playlistInfo.current_index = index + 1;
            } else if (playlistInfo.current_index === index + 1) {
              playlistInfo.current_index = index;
            }
            playlistInfo.total = list.length;
            return playlistInfo;
          });
          ElMessage.success("已下移");
        } catch (error) {
          console.error("下移失败:", error);
          ElMessage.error("下移失败: " + (error.message || "未知错误"));
        } finally {
          refData.playlistLoading.value = false;
        }
      };

      // 删除播放列表项
      const handleDeletePlaylistItem = async (index) => {
        const status = refData.playlistStatus.value;
        if (!status || index < 0 || index >= status.playlist.length) return;

        const fileItem = status.playlist[index];
        const fileName = getFileName(fileItem);

        try {
          await ElMessageBox.confirm(`确定要删除 "${fileName}" 吗？`, "确认删除", {
            confirmButtonText: "确定",
            cancelButtonText: "取消",
            type: "warning",
          });

          refData.playlistLoading.value = true;
          await updateActivePlaylistData((playlistInfo) => {
            const list = [...playlistInfo.playlist];
            list.splice(index, 1);
            playlistInfo.playlist = list;
            if (list.length === 0) {
              playlistInfo.current_index = 0;
            } else if (index < playlistInfo.current_index) {
              playlistInfo.current_index = Math.max(0, playlistInfo.current_index - 1);
            } else if (index === playlistInfo.current_index) {
              playlistInfo.current_index = Math.min(playlistInfo.current_index, list.length - 1);
            }
            playlistInfo.total = list.length;
            return playlistInfo;
          });
          ElMessage.success("已删除");
        } catch (error) {
          if (error !== "cancel") {
            console.error("删除失败:", error);
            ElMessage.error("删除失败: " + (error.message || "未知错误"));
          }
        } finally {
          refData.playlistLoading.value = false;
        }
      };

      // 复制播放列表项到末尾
      const handleCopyPlaylistItem = async (index) => {
        const status = refData.playlistStatus.value;
        if (!status || index < 0 || index >= status.playlist.length) return;

        const fileItem = status.playlist[index];
        const fileName = getFileName(fileItem);

        try {
          refData.playlistLoading.value = true;
          await updateActivePlaylistData((playlistInfo) => {
            const list = [...playlistInfo.playlist];
            // 复制文件项（深拷贝）
            const copiedItem = { ...fileItem };
            // 添加到列表末尾
            list.push(copiedItem);
            playlistInfo.playlist = list;
            playlistInfo.total = list.length;
            return playlistInfo;
          });
          ElMessage.success(`已复制 "${fileName}" 到列表末尾`);
        } catch (error) {
          console.error("复制失败:", error);
          ElMessage.error("复制失败: " + (error.message || "未知错误"));
        } finally {
          refData.playlistLoading.value = false;
        }
      };

      // 清空播放列表
      const handleClearPlaylist = async () => {
        const status = refData.playlistStatus.value;
        if (!status) return;
        
        const preFilesCount = (status.pre_files && status.pre_files.length) || 0;
        const filesCount = (status.playlist && status.playlist.length) || 0;
        const totalCount = preFilesCount + filesCount;
        
        if (totalCount === 0) return;

        try {
          const message = preFilesCount > 0 && filesCount > 0
            ? `确定要清空播放列表 "${status.name}" 吗？此操作将删除所有 ${preFilesCount} 个前置文件和 ${filesCount} 个正式文件，共 ${totalCount} 个文件。`
            : preFilesCount > 0
            ? `确定要清空播放列表 "${status.name}" 吗？此操作将删除所有 ${preFilesCount} 个前置文件。`
            : `确定要清空播放列表 "${status.name}" 吗？此操作将删除所有 ${filesCount} 个正式文件。`;
          
          await ElMessageBox.confirm(
            message,
            "确认清空",
            {
              confirmButtonText: "确定",
              cancelButtonText: "取消",
              type: "warning",
            }
          );

          refData.playlistLoading.value = true;
          await updateActivePlaylistData((playlistInfo) => {
            playlistInfo.playlist = [];
            playlistInfo.pre_files = [];
            playlistInfo.total = 0;
            playlistInfo.current_index = 0;
            return playlistInfo;
          });
          ElMessage.success("已清空播放列表（包括前置文件和正式文件）");
        } catch (error) {
          if (error !== "cancel") {
            console.error("清空失败:", error);
            ElMessage.error("清空失败: " + (error.message || "未知错误"));
          }
        } finally {
          refData.playlistLoading.value = false;
        }
      };

      // 删除 pre_files 中的文件
      const handleDeletePreFile = async (index) => {
        const status = refData.playlistStatus.value;
        if (!status || !status.pre_files || index < 0 || index >= status.pre_files.length) return;

        const fileItem = status.pre_files[index];
        const fileName = getFileName(fileItem);

        try {
          await ElMessageBox.confirm(`确定要删除 "${fileName}" 吗？`, "确认删除", {
            confirmButtonText: "确定",
            cancelButtonText: "取消",
            type: "warning",
          });

          refData.playlistLoading.value = true;
          await updateActivePlaylistData((playlistInfo) => {
            const list = [...(playlistInfo.pre_files || [])];
            list.splice(index, 1);
            playlistInfo.pre_files = list;
            return playlistInfo;
          });
          ElMessage.success("已删除");
        } catch (error) {
          if (error !== "cancel") {
            console.error("删除失败:", error);
            ElMessage.error("删除失败: " + (error.message || "未知错误"));
          }
        } finally {
          refData.playlistLoading.value = false;
        }
      };

      // 清空前置文件列表
      const handleClearPreFiles = async () => {
        const status = refData.playlistStatus.value;
        if (!status || !status.pre_files || status.pre_files.length === 0) return;

        try {
          await ElMessageBox.confirm(
            `确定要清空前置文件列表吗？此操作将删除所有 ${status.pre_files.length} 个前置文件。`,
            "确认清空",
            {
              confirmButtonText: "确定",
              cancelButtonText: "取消",
              type: "warning",
            }
          );

          refData.playlistLoading.value = true;
          await updateActivePlaylistData((playlistInfo) => {
            playlistInfo.pre_files = [];
            return playlistInfo;
          });
          ElMessage.success("已清空前置文件列表");
        } catch (error) {
          if (error !== "cancel") {
            console.error("清空失败:", error);
            ElMessage.error("清空失败: " + (error.message || "未知错误"));
          }
        } finally {
          refData.playlistLoading.value = false;
        }
      };

      // 上移 pre_files 中的文件
      const handleMovePreFileUp = async (index) => {
        const status = refData.playlistStatus.value;
        if (!status || !status.pre_files || index <= 0 || index >= status.pre_files.length) return;

        try {
          refData.playlistLoading.value = true;
          await updateActivePlaylistData((playlistInfo) => {
            const list = [...(playlistInfo.pre_files || [])];
            [list[index - 1], list[index]] = [list[index], list[index - 1]];
            playlistInfo.pre_files = list;
            return playlistInfo;
          });
        } catch (error) {
          console.error("上移失败:", error);
          ElMessage.error("上移失败: " + (error.message || "未知错误"));
        } finally {
          refData.playlistLoading.value = false;
        }
      };

      // 复制前置文件到播放列表末尾
      const handleCopyPreFile = async (index) => {
        const status = refData.playlistStatus.value;
        if (!status || !status.pre_files || index < 0 || index >= status.pre_files.length) return;

        const fileItem = status.pre_files[index];
        const fileName = getFileName(fileItem);

        try {
          refData.playlistLoading.value = true;
          await updateActivePlaylistData((playlistInfo) => {
            const list = [...(playlistInfo.playlist || [])];
            // 复制文件项（深拷贝）
            const copiedItem = { ...fileItem };
            // 添加到列表末尾
            list.push(copiedItem);
            playlistInfo.playlist = list;
            playlistInfo.total = list.length;
            return playlistInfo;
          });
          ElMessage.success(`已复制 "${fileName}" 到列表末尾`);
        } catch (error) {
          console.error("复制失败:", error);
          ElMessage.error("复制失败: " + (error.message || "未知错误"));
        } finally {
          refData.playlistLoading.value = false;
        }
      };

      // 下移 pre_files 中的文件
      const handleMovePreFileDown = async (index) => {
        const status = refData.playlistStatus.value;
        if (!status || !status.pre_files || index < 0 || index >= status.pre_files.length - 1) return;

        try {
          refData.playlistLoading.value = true;
          await updateActivePlaylistData((playlistInfo) => {
            const list = [...(playlistInfo.pre_files || [])];
            [list[index], list[index + 1]] = [list[index + 1], list[index]];
            playlistInfo.pre_files = list;
            return playlistInfo;
          });
        } catch (error) {
          console.error("下移失败:", error);
          ElMessage.error("下移失败: " + (error.message || "未知错误"));
        } finally {
          refData.playlistLoading.value = false;
        }
      };

      const handleSelectPlaylist = async (playlistId) => {
        if (!playlistId || playlistId === refData.activePlaylistId.value) return;
        const exists = refData.playlistCollection.value.find((item) => item.id === playlistId);
        if (!exists) return;
        
        refData.activePlaylistId.value = playlistId;
        saveActivePlaylistId(playlistId); // 保存选中的播放列表ID
        syncActivePlaylist(refData.playlistCollection.value);
        pendingDeviceType.value = null;
        await refreshConnectedList();
      };

      // 开始编辑播放列表名称
      const handleStartEditPlaylistName = (playlistId) => {
        const playlist = refData.playlistCollection.value.find((p) => p.id === playlistId);
        if (playlist) {
          refData.editingPlaylistId.value = playlistId;
          refData.editingPlaylistName.value = playlist.name;
          // 等待 DOM 更新后聚焦输入框
          nextTick(() => {
            const input = document.querySelector(`input[data-playlist-id="${playlistId}"]`);
            if (input) {
              input.focus();
              input.select();
            }
          });
        }
      };

      // 保存播放列表名称
      const handleSavePlaylistName = async (playlistId) => {
        const newName = refData.editingPlaylistName.value?.trim();
        if (!newName || newName.length === 0) {
          ElMessage.warning("播放列表名称不能为空");
          refData.editingPlaylistId.value = null;
          return;
        }

        const playlist = refData.playlistCollection.value.find((p) => p.id === playlistId);
        if (!playlist || playlist.name === newName) {
          refData.editingPlaylistId.value = null;
          return;
        }

        try {
          // 更新集合中对应项的名称
          const collection = refData.playlistCollection.value.map((item) => {
            if (item.id === playlistId) {
              return { ...item, name: newName };
            }
            return item;
          });
          refData.playlistCollection.value = collection;

          // 如果当前编辑的是激活的播放列表，同步更新状态
          if (playlistId === refData.activePlaylistId.value) {
            syncActivePlaylist(collection);
          }

          // 保存到后端
          await savePlaylist(collection);

          refData.editingPlaylistId.value = null;
          ElMessage.success("播放列表名称已更新");
        } catch (error) {
          console.error("更新播放列表名称失败:", error);
          ElMessage.error("更新播放列表名称失败: " + (error.message || "未知错误"));
        }
      };

      // 取消编辑播放列表名称
      const handleCancelEditPlaylistName = () => {
        refData.editingPlaylistId.value = null;
        refData.editingPlaylistName.value = "";
      };

      // 格式化日期时间，包含星期
      const formatDateTimeWithWeekday = (dateStr) => {
        if (!dateStr) return null;
        try {
          // 解析格式: "YYYY-MM-DD HH:mm:ss"
          const parts = dateStr.match(/(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})/);
          if (!parts) return dateStr;

          const year = parseInt(parts[1], 10);
          const month = parseInt(parts[2], 10) - 1; // 月份从0开始
          const day = parseInt(parts[3], 10);
          const hours = parseInt(parts[4], 10);
          const minutes = parseInt(parts[5], 10);
          const seconds = parseInt(parts[6], 10);

          const date = new Date(year, month, day, hours, minutes, seconds);
          const weekdays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
          const weekday = weekdays[date.getDay()];

          return `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(
            2,
            "0"
          )} ${weekday} ${String(hours).padStart(2, "0")}:${String(minutes).padStart(
            2,
            "0"
          )}:${String(seconds).padStart(2, "0")}`;
        } catch (error) {
          return dateStr;
        }
      };

      // 获取播放列表的下次 Cron 运行时间
      const getPlaylistNextCronTime = (playlist) => {
        if (
          !playlist ||
          !playlist.schedule ||
          playlist.schedule.enabled !== 1 ||
          !playlist.schedule.cron ||
          typeof playlist.schedule.cron !== 'string'
        ) {
          return null;
        }
        try {
          const cronExpr = String(playlist.schedule.cron).trim();
          if (!cronExpr) {
            return null;
          }
          const times = calculateNextCronTimes(cronExpr, 1);
          if (times && times.length > 0) {
            return formatDateTimeWithWeekday(times[0]);
          }
          return null;
        } catch (error) {
          return null;
        }
      };

      const handleCreatePlaylist = async () => {
        try {
          const defaultName = `播放列表${refData.playlistCollection.value.length + 1}`;
          const { value } = await ElMessageBox.prompt("请输入播放列表名称", "新建播放列表", {
            confirmButtonText: "确定",
            cancelButtonText: "取消",
            inputValue: defaultName,
            inputPlaceholder: defaultName,
            inputValidator: (val) => (!!val && val.trim().length > 0) || "名称不能为空",
          });
          const playlistName = (value || defaultName).trim();
          const newPlaylist = normalizePlaylistItem(
            {
              id: createPlaylistId(),
              name: playlistName,
              playlist: [],
              current_index: 0,
              device_address: null,
            },
            playlistName
          );
          const updated = [...refData.playlistCollection.value, newPlaylist];
          refData.playlistCollection.value = updated;
          refData.activePlaylistId.value = newPlaylist.id;
          saveActivePlaylistId(newPlaylist.id); // 保存新创建的播放列表ID
          syncActivePlaylist(updated);
          await savePlaylist(updated);
          ElMessage.success("播放列表已创建");
        } catch (error) {
          if (error === "cancel") return;
          console.error("创建播放列表失败:", error);
          ElMessage.error("创建播放列表失败: " + (error.message || "未知错误"));
        }
      };

      const handlePlaylistMenuCommand = async (command, playlistId) => {
        if (command === "delete") {
          await handleDeletePlaylistGroup(playlistId);
        } else if (command === "copy") {
          await handleCopyPlaylist(playlistId);
        }
      };

      const handleCopyPlaylist = async (playlistId) => {
        if (!playlistId) return;
        const sourcePlaylist = refData.playlistCollection.value.find((item) => item.id === playlistId);
        if (!sourcePlaylist) return;
        
        try {
          const defaultName = `${sourcePlaylist.name}_副本`;
          const { value } = await ElMessageBox.prompt("请输入播放列表名称", "复制播放列表", {
            confirmButtonText: "确定",
            cancelButtonText: "取消",
            inputValue: defaultName,
            inputPlaceholder: defaultName,
            inputValidator: (val) => (!!val && val.trim().length > 0) || "名称不能为空",
          });
          const playlistName = (value || defaultName).trim();
          
          // 复制播放列表内容（深拷贝）
          const copiedPlaylist = sourcePlaylist.playlist 
            ? sourcePlaylist.playlist.map(file => ({ ...file }))
            : [];
          const newPlaylist = normalizePlaylistItem(
            {
              id: createPlaylistId(),
              name: playlistName,
              playlist: copiedPlaylist,
              current_index: 0,
              device: sourcePlaylist.device ? { ...sourcePlaylist.device } : null,
              device_address: sourcePlaylist.device_address || null,
              device_type: sourcePlaylist.device_type || null,
              schedule: sourcePlaylist.schedule ? { ...sourcePlaylist.schedule } : { enabled: 0, cron: "", duration: 0 },
            },
            playlistName
          );
          
          const updated = [...refData.playlistCollection.value, newPlaylist];
          refData.playlistCollection.value = updated;
          refData.activePlaylistId.value = newPlaylist.id;
          saveActivePlaylistId(newPlaylist.id);
          syncActivePlaylist(updated);
          await savePlaylist(updated);
          ElMessage.success("播放列表已复制");
        } catch (error) {
          if (error === "cancel") return;
          console.error("复制播放列表失败:", error);
          ElMessage.error("复制播放列表失败: " + (error.message || "未知错误"));
        }
      };

      const handleDeletePlaylistGroup = async (playlistId) => {
        if (!playlistId) return;
        if (refData.playlistCollection.value.length <= 1) {
          ElMessage.warning("至少保留一个播放列表");
          return;
        }
        const target = refData.playlistCollection.value.find((item) => item.id === playlistId);
        if (!target) return;
        try {
          await ElMessageBox.confirm(`确认删除播放列表"${target.name}"吗？`, "删除播放列表", {
            confirmButtonText: "删除",
            cancelButtonText: "取消",
            type: "warning",
          });
          const updated = refData.playlistCollection.value.filter((item) => item.id !== playlistId);
          refData.playlistCollection.value = updated;
          
          // 如果删除的是当前选中的播放列表，切换到第一个
          if (playlistId === refData.activePlaylistId.value && updated.length > 0) {
            refData.activePlaylistId.value = updated[0].id;
            saveActivePlaylistId(updated[0].id);
          }
          
          // 清理已删除播放列表的localStorage数据
          try {
            localStorage.removeItem(`playlist_index_${playlistId}`);
          } catch (e) {
            console.warn("清理播放列表索引失败:", e);
          }
          
          syncActivePlaylist(updated);
          await savePlaylist(updated);
          ElMessage.success("播放列表已删除");
        } catch (error) {
          if (error === "cancel") return;
          console.error("删除播放列表失败:", error);
          ElMessage.error("删除播放列表失败: " + (error.message || "未知错误"));
        }
      };

      const handleOpenFileBrowser = () => {
        if (!refData.playlistStatus.value) {
          ElMessage.warning("请先选择一个播放列表");
          return;
        }
        refData.fileBrowserDialogVisible.value = true;
        refData.fileBrowserPath.value = lastFileBrowserPath;
        refData.selectedFiles.value = [];
        refData.fileBrowserTarget.value = "files"; // 默认添加到 files
        handleRefreshFileBrowser();
      };

      const handleOpenFileBrowserForPreFiles = () => {
        if (!refData.playlistStatus.value) {
          ElMessage.warning("请先选择一个播放列表");
          return;
        }
        refData.fileBrowserDialogVisible.value = true;
        refData.fileBrowserPath.value = lastFileBrowserPath;
        refData.selectedFiles.value = [];
        refData.fileBrowserTarget.value = "pre_files"; // 默认添加到 pre_files
        handleRefreshFileBrowser();
      };

      const handleCloseFileBrowser = () => {
        refData.fileBrowserDialogVisible.value = false;
        refData.selectedFiles.value = [];
      };

      const handleRefreshFileBrowser = async () => {
        try {
          refData.fileBrowserLoading.value = true;
          const path = refData.fileBrowserPath.value || "/mnt/ext_base";
          const rsp = await axios.get(getApiUrl() + "/listDirectory", {
            params: { path: path, extensions: "audio" },
          });
          if (rsp.data.code === 0) {
            refData.fileBrowserList.value = rsp.data.data || [];
            updateFileBrowserCanNavigateUp();
          } else {
            ElMessage.error(rsp.data.msg || "获取文件列表失败");
          }
        } catch (error) {
          console.error("获取文件列表失败:", error);
          ElMessage.error("获取文件列表失败: " + (error.message || "未知错误"));
        } finally {
          refData.fileBrowserLoading.value = false;
        }
      };

      const handleFileBrowserNavigateUp = () => {
        const path = refData.fileBrowserPath.value;
        if (path && path !== "/mnt/ext_base" && path !== "/") {
          const parts = String(path).split("/").filter((p) => p);
          parts.pop();
          refData.fileBrowserPath.value =
            parts.length > 0 ? "/" + parts.join("/") : "/mnt/ext_base";
          updateFileBrowserCanNavigateUp();
          handleRefreshFileBrowser();
        }
      };

      const handleFileBrowserGoToHome = () => {
        refData.fileBrowserPath.value = "/mnt/ext_base";
        updateFileBrowserCanNavigateUp();
        handleRefreshFileBrowser();
      };

      const handleFileBrowserRowClick = (row) => {
        if (row.isDirectory) {
          const newPath =
            refData.fileBrowserPath.value === "/"
              ? `/${row.name}`
              : `${refData.fileBrowserPath.value}/${row.name}`;
          refData.fileBrowserPath.value = newPath;
          updateFileBrowserCanNavigateUp();
          handleRefreshFileBrowser();
        } else {
          handleToggleFileSelection(row);
        }
      };

      const handleToggleFileSelection = (row) => {
        if (row.isDirectory) return;
        const filePath =
          refData.fileBrowserPath.value === "/"
            ? `/${row.name}`
            : `${refData.fileBrowserPath.value}/${row.name}`;
        const index = refData.selectedFiles.value.indexOf(filePath);
        if (index > -1) {
          refData.selectedFiles.value.splice(index, 1);
        } else {
          refData.selectedFiles.value.push(filePath);
        }
      };

      // 检查文件是否被选中
      const isFileSelected = (row) => {
        if (row.isDirectory) return false;
        const filePath =
          refData.fileBrowserPath.value === "/"
            ? `/${row.name}`
            : `${refData.fileBrowserPath.value}/${row.name}`;
        return refData.selectedFiles.value.includes(filePath);
      };

      // 全选当前目录下的所有文件
      const handleSelectAllFiles = () => {
        const currentPath = refData.fileBrowserPath.value;
        refData.fileBrowserList.value.forEach((row) => {
          if (!row.isDirectory) {
            const filePath = currentPath === "/" ? `/${row.name}` : `${currentPath}/${row.name}`;
            if (!refData.selectedFiles.value.includes(filePath)) {
              refData.selectedFiles.value.push(filePath);
            }
          }
        });
      };

      // 取消全选当前目录下的所有文件
      const handleDeselectAllFiles = () => {
        const currentPath = refData.fileBrowserPath.value;
        const currentFiles = refData.fileBrowserList.value
          .filter((row) => !row.isDirectory)
          .map((row) => {
            return currentPath === "/" ? `/${row.name}` : `${currentPath}/${row.name}`;
          });

        // 只移除当前目录下的文件，保留其他目录的文件
        refData.selectedFiles.value = refData.selectedFiles.value.filter((filePath) => {
          return !currentFiles.includes(filePath);
        });
      };

      const fileBrowserCanNavigateUp = ref(false);
      const updateFileBrowserCanNavigateUp = () => {
        const path = refData.fileBrowserPath.value;
        fileBrowserCanNavigateUp.value = path && path !== "/mnt/ext_base" && path !== "/";
      };

      // 添加文件到播放列表
      const handleAddFilesToPlaylist = async () => {
        if (refData.selectedFiles.value.length === 0) {
          ElMessage.warning("请先选择要添加的文件");
          return;
        }
        if (!refData.playlistStatus.value) {
          ElMessage.warning("请先创建并选择一个播放列表");
          return;
        }

        try {
          refData.playlistLoading.value = true;

          let deviceAddress = refData.playlistStatus.value.device_address;

          // 如果没有设备地址，尝试获取已连接的设备
          if (!deviceAddress && refData.connectedDeviceList.value.length > 0) {
            const connectedDevice = refData.connectedDeviceList.value.find((d) => d.connected);
            if (connectedDevice) {
              deviceAddress = connectedDevice.address;
            } else if (refData.connectedDeviceList.value.length > 0) {
              deviceAddress = refData.connectedDeviceList.value[0].address;
            }
          }

          await updateActivePlaylistData((playlistInfo) => {
            const targetList = refData.fileBrowserTarget.value === "pre_files" 
              ? (Array.isArray(playlistInfo.pre_files) ? [...playlistInfo.pre_files] : [])
              : (Array.isArray(playlistInfo.playlist) ? [...playlistInfo.playlist] : []);
            
            // 获取已存在的 URI 集合
            const existingUris = new Set();
            targetList.forEach((item) => {
              if (item?.uri) {
                existingUris.add(item.uri);
              }
            });
            
            // 添加新文件，格式化为新格式 {"uri": "地址"}
            for (const filePath of refData.selectedFiles.value) {
              if (!existingUris.has(filePath)) {
                const fileItem = {
                  uri: filePath,
                };
                targetList.push(fileItem);
                existingUris.add(filePath);
              }
            }
            
            if (refData.fileBrowserTarget.value === "pre_files") {
              playlistInfo.pre_files = targetList;
            } else {
              playlistInfo.playlist = targetList;
              playlistInfo.total = targetList.length;
              playlistInfo.device_address = deviceAddress || playlistInfo.device_address;
              if (targetList.length === 0) {
                playlistInfo.current_index = 0;
              } else if (playlistInfo.current_index >= targetList.length) {
                playlistInfo.current_index = targetList.length - 1;
              }
            }
            return playlistInfo;
          });

          const targetName = refData.fileBrowserTarget.value === "pre_files" ? "前置列表" : "播放列表";
          ElMessage.success(`成功添加 ${refData.selectedFiles.value.length} 个文件到${targetName}`);
          // 保存当前目录路径，以便下次打开时使用
          lastFileBrowserPath = refData.fileBrowserPath.value;
          handleCloseFileBrowser();
        } catch (error) {
          console.error("添加文件到播放列表失败:", error);
          ElMessage.error("添加文件到播放列表失败: " + (error.message || "未知错误"));
        } finally {
          refData.playlistLoading.value = false;
        }
      };

      const refMethods = {
        handleUpdateDeviceList,
        handleOpenScanDialog,
        handleCloseScanDialog,
        handleOpenCronBuilder,
        handleCloseCronBuilder,
        updateCronExpression,
        handleApplyCronExpression,
        applyExample,
        handlePreviewGeneratedCron,
        formatSize,
        formatDuration,
        handleConnectDevice,
        refreshConnectedList,
        refreshPlaylistStatus,
        handlePlayPlaylist,
        handlePlayPre,
        handlePlayNext,
        handleStopPlaylist,
        handleMovePlaylistItemUp,
        handleMovePlaylistItemDown,
        handleDeletePlaylistItem,
        handleCopyPlaylistItem,
        handleClearPlaylist,
        handleDeletePreFile,
        handleClearPreFiles,
        handleMovePreFileUp,
        handleMovePreFileDown,
        handleCopyPreFile,
        handleSelectPlaylist,
        handleCreatePlaylist,
        handleDeletePlaylistGroup,
        handlePlaylistMenuCommand,
        handleCopyPlaylist,
        handleStartEditPlaylistName,
        handleSavePlaylistName,
        handleCancelEditPlaylistName,
        getPlaylistNextCronTime,
        handleOpenFileBrowser,
        handleOpenFileBrowserForPreFiles,
        handleCloseFileBrowser,
        handleRefreshFileBrowser,
        handleFileBrowserNavigateUp,
        handleFileBrowserGoToHome,
        handleFileBrowserRowClick,
        handleToggleFileSelection,
        isFileSelected,
        handleSelectAllFiles,
        handleDeselectAllFiles,
        handleAddFilesToPlaylist,
        handleTogglePlaylistCronEnabled,
        handleUpdatePlaylistCron,
        handleUpdatePlaylistDuration,
        formatDurationMinutes,
        handlePreviewPlaylistCron,
        handleUpdateTriggerButton,
        handleUpdatePlaylistDeviceType,
        handleUpdatePlaylistDeviceAddress,
        handleSelectBluetoothDevice,
        handleSelectAgentDevice,
        handleSelectMiDevice,
        scanDlnaDevices,
        scanMiDevices,
        getPreFilesTotalDuration,
        getFilesTotalDuration,
        getPlaylistTotalDuration,
        handleOpenAgentListDialog,
        handleCloseAgentListDialog,
        handleRefreshAgentList,
        handleTestAgentButton,
      };

      updateFileBrowserCanNavigateUp();

      // 定时器：每5秒刷新播放列表状态
      let statusRefreshTimer = null;
      // Agent设备列表刷新定时器
      let agentListRefreshTimer = null;

      // 监听Agent设备列表弹窗状态，实现10秒定时刷新
      watch(
        () => refData.agentListDialogVisible.value,
        (isVisible) => {
          // 清除之前的定时器
          if (agentListRefreshTimer) {
            clearInterval(agentListRefreshTimer);
            agentListRefreshTimer = null;
          }
          
          // 如果弹窗显示，启动10秒定时刷新
          if (isVisible) {
            agentListRefreshTimer = setInterval(async () => {
              try {
                // 自动刷新时不显示loading图标
                await handleRefreshAgentList(false);
              } catch (error) {
                console.error("定时刷新Agent设备列表失败:", error);
              }
            }, 10000); // 10秒刷新一次
          }
        }
      );

      onMounted(async () => {
        await loadPlaylist();
        await refreshConnectedList();
        
        // 启动定时器，每5秒刷新一次当前播放列表状态
        statusRefreshTimer = setInterval(async () => {
          try {
            await refreshPlaylistStatus(true, true); // 第二个参数 true 表示是自动刷新
          } catch (error) {
            console.error("定时刷新播放列表状态失败:", error);
          }
        }, 5000);
      });

      onUnmounted(() => {
        // 清理定时器
        if (statusRefreshTimer) {
          clearInterval(statusRefreshTimer);
          statusRefreshTimer = null;
        }
        if (agentListRefreshTimer) {
          clearInterval(agentListRefreshTimer);
          agentListRefreshTimer = null;
        }
      });

      return {
        ...refData,
        cronBuilderVisible,
        fileBrowserCanNavigateUp,
        ...refMethods,
      };
    },
    template,
  };
  return component;
}
export default createComponent();
