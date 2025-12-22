import { bluetoothAction, getApiUrl, playlistAction } from "../js/net_util.js";
import {
  calculateFilesTotalDuration,
  calculateNextCronTimes,
  createPlaylistId,
  formatDateTime,
  formatDateTimeWithWeekday,
  formatDuration,
  formatDurationMinutes,
  formatSize,
  getFileName,
  getMediaFileUrl,
  getWeekdayIndex,
  normalizeFiles
} from "../js/utils.js";
import { createCronBuilder } from "./common/cron_builder.js";
import { createFileDialog } from "./common/file_dialog.js";
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

  // 加载文件对话框组件
  const FileDialog = await createFileDialog();
  // 加载 Cron 生成器组件
  const CronBuilder = await createCronBuilder();

  component = {
    components: {
      FileDialog,
      CronBuilder,
    },
    setup() {
      const refData = {
        scanDialogVisible: ref(false),
        fileBrowserDialogVisible: ref(false),
        fileBrowserTarget: ref("files"), // "files" 或 "pre_files"
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
        activeDeviceTab: ref('agent'),
        preFilesSortOrder: ref(null), // null, 'name-asc', 'name-desc', 'duration-asc', 'duration-desc'
        filesSortOrder: ref(null), // null, 'name-asc', 'name-desc', 'duration-asc', 'duration-desc'
        preFilesDragMode: ref(false), // 前置文件拖拽排序模式
        filesDragMode: ref(false), // 正式文件拖拽排序模式
        preFilesOriginalOrder: ref(null), // 进入拖拽模式时的原始顺序
        filesOriginalOrder: ref(null), // 进入拖拽模式时的原始顺序
        selectedWeekdayIndex: ref(null), // 选中的星期索引（0=周一，6=周日），null表示使用今天
        replaceFileInfo: ref(null), // 替换文件信息 {type: 'pre_files' | 'files', index: number}，null表示添加模式
        browserAudioPlayer: ref(null), // 浏览器音频播放器实例
        browserPlayingFilePath: ref(null), // 当前正在播放的文件路径
        preFilesExpanded: ref(false), // 前置文件列表是否展开
      };
      const pendingDeviceType = ref(null);
      const _formatDateTime = formatDateTime;

      // 获取当前星期对应的索引（0=周一，6=周日）

      // 获取当前选中的星期索引（如果未选择则使用今天）
      const getSelectedWeekdayIndex = () => {
        return refData.selectedWeekdayIndex.value !== null
          ? refData.selectedWeekdayIndex.value
          : getWeekdayIndex();
      };

      // 获取当前显示的前置文件列表
      const getCurrentPreFiles = () => {
        const status = refData.playlistStatus.value;
        if (!status || !status.pre_lists) return [];
        const weekdayIndex = getSelectedWeekdayIndex();
        if (!Array.isArray(status.pre_lists) || status.pre_lists.length !== 7) return [];
        return status.pre_lists[weekdayIndex] || [];
      };

      // 获取指定星期的前置文件数量
      const getPreFilesCountForWeekday = (weekdayIndex) => {
        const status = refData.playlistStatus.value;
        if (!status || !status.pre_lists) return 0;
        if (!Array.isArray(status.pre_lists) || status.pre_lists.length !== 7) return 0;
        const preList = status.pre_lists[weekdayIndex];
        return Array.isArray(preList) ? preList.length : 0;
      };

      // 在浏览器中播放文件
      const handlePlayFileInBrowser = (fileItem) => {
        const filePath = fileItem?.uri || fileItem?.path || '';
        if (!filePath) {
          ElMessage.warning("文件路径无效");
          return;
        }

        // 如果点击的是正在播放的文件，则停止播放
        if (refData.browserPlayingFilePath.value === filePath &&
          refData.browserAudioPlayer.value &&
          !refData.browserAudioPlayer.value.paused) {
          refData.browserAudioPlayer.value.pause();
          refData.browserAudioPlayer.value = null;
          refData.browserPlayingFilePath.value = null;
          ElMessage.info("已停止播放");
          return;
        }

        // 如果已有播放器正在播放，先停止
        if (refData.browserAudioPlayer.value) {
          refData.browserAudioPlayer.value.pause();
          refData.browserAudioPlayer.value = null;
        }

        const mediaUrl = getMediaFileUrl(filePath);
        const audio = new Audio(mediaUrl);

        audio.addEventListener('play', () => {
          refData.browserPlayingFilePath.value = filePath;
          ElMessage.success("开始播放");
        });

        audio.addEventListener('pause', () => {
          // 只有在非用户主动暂停时才清除状态（比如播放结束）
          if (audio.ended) {
            refData.browserPlayingFilePath.value = null;
          }
        });

        audio.addEventListener('error', (e) => {
          console.error("音频播放失败:", e);
          ElMessage.error("音频播放失败");
          refData.browserAudioPlayer.value = null;
          refData.browserPlayingFilePath.value = null;
        });

        audio.addEventListener('ended', () => {
          refData.browserAudioPlayer.value = null;
          refData.browserPlayingFilePath.value = null;
        });

        refData.browserAudioPlayer.value = audio;
        audio.play().catch((error) => {
          console.error("播放失败:", error);
          ElMessage.error("播放失败: " + (error.message || "未知错误"));
          refData.browserAudioPlayer.value = null;
          refData.browserPlayingFilePath.value = null;
        });
      };

      // 检查文件是否正在播放
      const isFilePlaying = (fileItem) => {
        const filePath = fileItem?.uri || fileItem?.path || '';
        return refData.browserPlayingFilePath.value === filePath &&
          refData.browserAudioPlayer.value &&
          !refData.browserAudioPlayer.value.paused;
      };

      // 切换前置文件列表展开/折叠
      const handleTogglePreFilesExpand = () => {
        refData.preFilesExpanded.value = !refData.preFilesExpanded.value;
      };

      // 计算前置文件列表总时长（秒）
      const getPreFilesTotalDuration = () => {
        const preFiles = getCurrentPreFiles();
        return calculateFilesTotalDuration(preFiles);
      };

      // 计算正式文件列表总时长（秒）
      const getFilesTotalDuration = () => {
        const status = refData.playlistStatus.value;
        if (!status || !status.playlist || status.playlist.length === 0) {
          return 0;
        }
        return calculateFilesTotalDuration(status.playlist);
      };

      // 计算播放列表总时长（秒，包括前置文件和播放列表文件）
      const getPlaylistTotalDuration = () => {
        const status = refData.playlistStatus.value;
        if (!status) return 0;

        // 前置文件时长
        const preFiles = getCurrentPreFiles();
        const preFilesDuration = calculateFilesTotalDuration(preFiles);

        // 播放列表文件时长
        const files = status.playlist || status.files || [];
        const filesDuration = calculateFilesTotalDuration(files);

        return preFilesDuration + filesDuration;
      };

      const createDefaultPlaylist = (overrides = {}) => ({
        id: overrides.id || createPlaylistId(),
        name: overrides.name || "默认播放列表",
        playlist: overrides.playlist || [],
        pre_lists: overrides.pre_lists || (overrides.pre_files ? [Array(7).fill(null).map(() => [...(overrides.pre_files || [])])] : Array(7).fill(null).map(() => [])),
        current_index: overrides.current_index || 0,
        device_address: overrides.device_address || null,
        device_type: overrides.device_type || "dlna",
        device: overrides.device || { type: "dlna", address: null, name: null },
        schedule: overrides.schedule || { enabled: 0, cron: "", duration: 0 },
      });

      const normalizePlaylistItem = (item, fallbackName = "播放列表") => {
        const playlist = normalizeFiles(item?.playlist || item?.files || [], true);
        // 处理 pre_lists：如果存在则使用，否则从 pre_files 迁移
        let pre_lists = item?.pre_lists;
        if (!pre_lists || !Array.isArray(pre_lists) || pre_lists.length !== 7) {
          const pre_files = normalizeFiles(item?.pre_files || [], true);
          pre_lists = Array(7).fill(null).map(() => [...pre_files]); // 深拷贝到7个列表
        } else {
          // 规范化每个列表
          pre_lists = pre_lists.map(pre_list => normalizeFiles(pre_list || [], true));
        }

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
          pre_lists,
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

      // 处理文件选择确认
      const handleFileBrowserConfirm = async (filePaths) => {
        if (filePaths.length === 0) {
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

          // 检查是否是替换模式
          const isReplaceMode = refData.replaceFileInfo.value !== null;
          const replaceInfo = refData.replaceFileInfo.value;

          await updateActivePlaylistData((playlistInfo) => {
            const weekdayIndex = getSelectedWeekdayIndex();
            // 如果是替换模式，使用 replaceInfo 中的类型；否则使用 fileBrowserTarget
            const targetType = isReplaceMode && replaceInfo ? replaceInfo.type : refData.fileBrowserTarget.value;
            const targetList = targetType === "pre_files"
              ? (Array.isArray(playlistInfo.pre_lists) && playlistInfo.pre_lists.length === 7
                ? [...(playlistInfo.pre_lists[weekdayIndex] || [])]
                : [])
              : (Array.isArray(playlistInfo.playlist) ? [...playlistInfo.playlist] : []);

            if (isReplaceMode && replaceInfo) {
              // 替换模式：删除当前文件，在相同位置插入新文件
              const replaceIndex = replaceInfo.index;
              if (replaceIndex >= 0 && replaceIndex < targetList.length) {
                // 删除旧文件
                targetList.splice(replaceIndex, 1);
                // 在相同位置插入新文件（只取第一个文件）
                const newFileItem = {
                  uri: filePaths[0],
                };
                targetList.splice(replaceIndex, 0, newFileItem);
              }
            } else {
              // 添加模式：获取已存在的 URI 集合
              const existingUris = new Set();
              targetList.forEach((item) => {
                if (item?.uri) {
                  existingUris.add(item.uri);
                }
              });

              // 添加新文件，格式化为新格式 {"uri": "地址"}
              for (const filePath of filePaths) {
                if (!existingUris.has(filePath)) {
                  const fileItem = {
                    uri: filePath,
                  };
                  targetList.push(fileItem);
                  existingUris.add(filePath);
                }
              }
            }

            if (targetType === "pre_files") {
              // 确保 pre_lists 存在且格式正确
              if (!playlistInfo.pre_lists || !Array.isArray(playlistInfo.pre_lists) || playlistInfo.pre_lists.length !== 7) {
                playlistInfo.pre_lists = Array(7).fill(null).map(() => []);
              }
              playlistInfo.pre_lists[weekdayIndex] = targetList;
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

          const targetName = (isReplaceMode && replaceInfo && replaceInfo.type === "pre_files") || (!isReplaceMode && refData.fileBrowserTarget.value === "pre_files")
            ? "前置列表"
            : "播放列表";
          if (isReplaceMode) {
            ElMessage.success(`成功替换${targetName}中的文件`);
          } else {
            ElMessage.success(`成功添加 ${filePaths.length} 个文件到${targetName}`);
          }
          refData.fileBrowserDialogVisible.value = false;
          refData.replaceFileInfo.value = null; // 清除替换信息
        } catch (error) {
          console.error("添加文件到播放列表失败:", error);
          ElMessage.error("添加文件到播放列表失败: " + (error.message || "未知错误"));
          refData.replaceFileInfo.value = null; // 清除替换信息
        } finally {
          refData.playlistLoading.value = false;
        }
      };

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

        // 获取当前显示的前置文件列表（从 active 对象中获取，而不是从 playlistStatus）
        const weekdayIndex = getSelectedWeekdayIndex();
        const currentPreFiles = (active.pre_lists && Array.isArray(active.pre_lists) && active.pre_lists.length === 7)
          ? (active.pre_lists[weekdayIndex] || [])
          : [];
        refData.playlistStatus.value = {
          ...active,
          playlist: [...(active.playlist || [])],
          pre_lists: active.pre_lists ? active.pre_lists.map(list => [...(list || [])]) : Array(7).fill(null).map(() => []),
          pre_files: currentPreFiles, // 为了兼容，保留 pre_files 字段，但使用当前选中的日期列表
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

            // 规范化 playlist 和 pre_lists 格式：确保是新格式 {"uri": "地址"}，保留 duration
            const normalizedFiles = normalizeFiles(item.playlist || [], true);
            // 处理 pre_lists
            let normalizedPreLists = item.pre_lists;
            if (!normalizedPreLists || !Array.isArray(normalizedPreLists) || normalizedPreLists.length !== 7) {
              // 如果没有 pre_lists，从 pre_files 迁移（兼容旧格式）
              const normalizedPreFiles = normalizeFiles(item.pre_files || [], true);
              normalizedPreLists = Array(7).fill(null).map(() => [...normalizedPreFiles]);
            } else {
              normalizedPreLists = normalizedPreLists.map(pre_list => normalizeFiles(pre_list || [], true));
            }

            playlistDict[item.id] = {
              id: item.id,
              name: item.name || "默认播放列表",
              files: normalizedFiles,
              pre_lists: normalizedPreLists,
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
          const response = await playlistAction("updateAll", "POST", playlistDict);
          if (response.code !== 0) {
            throw new Error(response.msg || "保存播放列表集合失败");
          }
        } catch (error) {
          console.error("保存播放列表集合失败:", error);
          ElMessage.error("保存播放列表集合失败: " + (error.message || "未知错误"));
        }
      };

      const transformApiDataToPlaylistFormat = (apiData) => {
        if (!apiData) {
          return null;
        }

        // 如果返回的是字典格式（多个播放列表，key 是 id）
        if (!Array.isArray(apiData) && Object.keys(apiData).length > 0) {
          const playlists = Object.values(apiData).map((item) => {
            // 规范化 files 和 pre_lists 格式：兼容旧格式（字符串数组）和新格式（对象数组）
            const normalizedFiles = normalizeFiles(item.files || [], true);
            // 处理 pre_lists
            let normalizedPreLists = item.pre_lists;
            if (!normalizedPreLists || !Array.isArray(normalizedPreLists) || normalizedPreLists.length !== 7) {
              // 如果没有 pre_lists，从 pre_files 迁移（兼容旧格式）
              const normalizedPreFiles = normalizeFiles(item.pre_files || [], true);
              normalizedPreLists = Array(7).fill(null).map(() => [...normalizedPreFiles]);
            } else {
              normalizedPreLists = normalizedPreLists.map(pre_list => normalizeFiles(pre_list || [], true));
            }

            // 规范化 schedule
            const schedule = item.schedule || { enabled: 0, cron: "", duration: 0 };
            const normalizedSchedule = {
              enabled: schedule.enabled || 0,
              cron: schedule.cron || "",
              duration: schedule.duration || 0,
            };

            return {
              id: item.id,
              name: item.name || "默认播放列表",
              playlist: normalizedFiles,
              pre_lists: normalizedPreLists,
              current_index: item.current_index || 0,
              pre_index: item.pre_index ?? -1,
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

      // 更新单个播放列表
      const updateSinglePlaylist = async (playlistData) => {
        try {
          const playlistDict = transformPlaylistToApiFormat([playlistData]);
          const playlistId = playlistData.id;
          const singlePlaylistData = playlistDict[playlistId];
          if (!singlePlaylistData) {
            throw new Error("播放列表数据格式错误");
          }
          // 确保包含 id 字段
          singlePlaylistData.id = playlistId;
          const response = await playlistAction("update", "POST", singlePlaylistData);
          if (response.code !== 0) {
            throw new Error(response.msg || "更新播放列表失败");
          }
          return true;
        } catch (error) {
          console.error("更新播放列表失败:", error);
          ElMessage.error("更新播放列表失败: " + (error.message || "未知错误"));
          return false;
        }
      };

      const updateActivePlaylistData = async (mutator) => {
        if (typeof mutator !== "function") return null;
        let collection = refData.playlistCollection.value.map((item) => ({
          ...item,
          playlist: Array.isArray(item.playlist) ? item.playlist.map(f => ({ ...f })) : [],
          pre_lists: Array.isArray(item.pre_lists) && item.pre_lists.length === 7
            ? item.pre_lists.map(list => list.map(f => ({ ...f })))
            : Array(7).fill(null).map(() => []),
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
        // 创建深拷贝，确保 mutator 修改的是新对象
        const itemToMutate = {
          ...currentItem,
          playlist: currentItem.playlist.map(f => ({ ...f })),
          pre_lists: Array.isArray(currentItem.pre_lists) && currentItem.pre_lists.length === 7
            ? currentItem.pre_lists.map(list => [...list.map(f => ({ ...f }))])
            : Array(7).fill(null).map(() => []),
        };
        const updatedItem = mutator(itemToMutate) || itemToMutate;

        // 确保 pre_lists 被正确保留（不经过 normalizePlaylistItem 的重新规范化，因为它可能会丢失数据）
        const preservedPreLists = updatedItem.pre_lists && Array.isArray(updatedItem.pre_lists) && updatedItem.pre_lists.length === 7
          ? updatedItem.pre_lists.map(list => Array.isArray(list) ? list.map(f => ({ ...f })) : [])
          : (Array.isArray(currentItem.pre_lists) && currentItem.pre_lists.length === 7
            ? currentItem.pre_lists.map(list => list.map(f => ({ ...f })))
            : Array(7).fill(null).map(() => []));

        const normalizedItem = normalizePlaylistItem(updatedItem, currentItem.name);
        // 保留 mutator 修改后的 pre_lists
        normalizedItem.pre_lists = preservedPreLists;
        collection[index] = normalizedItem;
        refData.playlistCollection.value = collection;

        // 调用单个播放列表更新接口
        await updateSinglePlaylist(collection[index]);
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

      // 工具函数：获取设备ID
      const getMiDeviceId = (device) => device.deviceID || device.address;

      // 工具函数：音量范围限制
      const clampVolume = (volume) => Math.max(0, Math.min(100, volume));

      // 扫描小米设备
      const scanMiDevices = async () => {
        try {
          refData.miScanning.value = true;
          const response = await fetch(`${getApiUrl()}/mi/scan?timeout=5`);
          const result = await response.json();

          if (result.code === 0) {
            const devices = (result.data || []).map(device => ({
              ...device,
              volume: undefined,
              _volumeChanging: false,
              _volumeRefreshing: false
            }));
            refData.miDeviceList.value = devices;

            // 并行获取所有设备的音量（使用响应式数组确保 Vue 能检测到变化）
            await Promise.allSettled(refData.miDeviceList.value.map(device => getMiDeviceVolume(device)));

            ElMessage.success(`扫描到 ${devices.length} 个小米设备`);
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

      // 获取小米设备音量
      const getMiDeviceVolume = async (device) => {
        const deviceId = getMiDeviceId(device);
        if (!deviceId) return;

        // 在响应式数组中找到对应的设备对象
        const deviceList = refData.miDeviceList.value;
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
          console.error(`获取设备 ${deviceId} 音量失败:`, error);
          ElMessage.error(`获取设备 ${targetDevice.name || deviceId} 音量失败: ${error.message || "未知错误"}`);
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
          console.error("设置小米设备音量失败:", error);
          ElMessage.error("设置音量失败: " + (error.message || "未知错误"));
        } finally {
          device._volumeChanging = false;
        }
      };

      // 处理小米设备音量变化
      const handleMiDeviceVolumeChange = async (device, delta) => {
        const currentVolume = device.volume ?? 0;
        const newVolume = clampVolume(currentVolume + delta);
        await setMiDeviceVolume(device, newVolume);
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
          console.error("停止小米设备播放失败:", error);
          ElMessage.error("停止播放失败: " + (error.message || "未知错误"));
        } finally {
          device._stopping = false;
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
      const initialCronExpr = ref("");

      const handleOpenCronBuilder = () => {
        const cronExpr = refData.playlistStatus.value?.schedule?.cron || "";
        initialCronExpr.value = cronExpr;
        cronBuilderVisible.value = true;
      };

      const handleCloseCronBuilder = () => {
        cronBuilderVisible.value = false;
      };

      const handleCronBuilderApply = (cronExpr) => {
        if (!cronExpr) return;
        if (refData.playlistStatus.value) {
          handleUpdatePlaylistCron(cronExpr);
          ElMessage.success("Cron 表达式已应用到当前播放列表");
        } else {
          ElMessage.warning("请先选择一个播放列表");
        }
      };

      const handleCronBuilderPreview = (times) => {
        refData.cronPreviewTimes.value = times;
        refData.cronPreviewVisible.value = true;
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
          // 如果是自动刷新，且处于拖拽排序模式，则跳过（避免覆盖拖拽结果）
          if (isAutoRefresh && (refData.preFilesDragMode.value || refData.filesDragMode.value)) {
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
                  // 保留原有的 playlist 和 pre_lists 数组引用，只更新状态字段
                  playlist: updatedPlaylist.playlist || item.playlist,
                  pre_lists: (updatedPlaylist.pre_lists && Array.isArray(updatedPlaylist.pre_lists) && updatedPlaylist.pre_lists.length === 7)
                    ? updatedPlaylist.pre_lists.map(list => [...(list || [])])
                    : item.pre_lists,
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

      // 替换播放列表项
      const handleReplacePlaylistItem = async (index) => {
        const status = refData.playlistStatus.value;
        if (!status || index < 0 || index >= status.playlist.length) return;

        // 设置替换模式
        refData.replaceFileInfo.value = {
          type: 'files',
          index: index
        };
        refData.fileBrowserTarget.value = "files";
        refData.fileBrowserDialogVisible.value = true;
      };

      // 清空播放列表
      const handleClearPlaylist = async () => {
        const status = refData.playlistStatus.value;
        if (!status) return;

        const preFiles = getCurrentPreFiles();
        const preFilesCount = (preFiles && preFiles.length) || 0;
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
            // 清空所有7天的前置文件列表
            if (!playlistInfo.pre_lists || !Array.isArray(playlistInfo.pre_lists) || playlistInfo.pre_lists.length !== 7) {
              playlistInfo.pre_lists = Array(7).fill(null).map(() => []);
            } else {
              playlistInfo.pre_lists = playlistInfo.pre_lists.map(() => []);
            }
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
        const preFiles = getCurrentPreFiles();
        if (!status || !preFiles || index < 0 || index >= preFiles.length) return;

        const fileItem = preFiles[index];
        const fileName = getFileName(fileItem);

        try {
          await ElMessageBox.confirm(`确定要删除 "${fileName}" 吗？`, "确认删除", {
            confirmButtonText: "确定",
            cancelButtonText: "取消",
            type: "warning",
          });

          refData.playlistLoading.value = true;
          await updateActivePlaylistData((playlistInfo) => {
            const weekdayIndex = getSelectedWeekdayIndex();
            // 确保 pre_lists 存在且格式正确
            if (!playlistInfo.pre_lists || !Array.isArray(playlistInfo.pre_lists) || playlistInfo.pre_lists.length !== 7) {
              playlistInfo.pre_lists = Array(7).fill(null).map(() => []);
            }
            const list = [...(playlistInfo.pre_lists[weekdayIndex] || [])];
            list.splice(index, 1);
            playlistInfo.pre_lists[weekdayIndex] = list;
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
        const preFiles = getCurrentPreFiles();
        if (!status || !preFiles || preFiles.length === 0) return;

        try {
          await ElMessageBox.confirm(
            `确定要清空前置文件列表吗？此操作将删除所有 ${preFiles.length} 个前置文件。`,
            "确认清空",
            {
              confirmButtonText: "确定",
              cancelButtonText: "取消",
              type: "warning",
            }
          );

          refData.playlistLoading.value = true;
          await updateActivePlaylistData((playlistInfo) => {
            const weekdayIndex = getSelectedWeekdayIndex();
            // 确保 pre_lists 存在且格式正确
            if (!playlistInfo.pre_lists || !Array.isArray(playlistInfo.pre_lists) || playlistInfo.pre_lists.length !== 7) {
              playlistInfo.pre_lists = Array(7).fill(null).map(() => []);
            }
            playlistInfo.pre_lists[weekdayIndex] = [];
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

      // 清空正式文件列表（只清空 files，不清空前置文件）
      const handleClearFiles = async () => {
        const status = refData.playlistStatus.value;
        if (!status || !status.playlist || status.playlist.length === 0) return;

        try {
          await ElMessageBox.confirm(
            `确定要清空正式文件列表吗？此操作将删除所有 ${status.playlist.length} 个正式文件。`,
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
            playlistInfo.total = 0;
            playlistInfo.current_index = 0;
            return playlistInfo;
          });
          ElMessage.success("已清空正式文件列表");
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
        const preFiles = getCurrentPreFiles();
        if (!status || !preFiles || index <= 0 || index >= preFiles.length) return;

        try {
          refData.playlistLoading.value = true;
          await updateActivePlaylistData((playlistInfo) => {
            const weekdayIndex = getSelectedWeekdayIndex();
            // 确保 pre_lists 存在且格式正确
            if (!playlistInfo.pre_lists || !Array.isArray(playlistInfo.pre_lists) || playlistInfo.pre_lists.length !== 7) {
              playlistInfo.pre_lists = Array(7).fill(null).map(() => []);
            }
            const list = [...(playlistInfo.pre_lists[weekdayIndex] || [])];
            [list[index - 1], list[index]] = [list[index], list[index - 1]];
            playlistInfo.pre_lists[weekdayIndex] = list;
            return playlistInfo;
          });
        } catch (error) {
          console.error("上移失败:", error);
          ElMessage.error("上移失败: " + (error.message || "未知错误"));
        } finally {
          refData.playlistLoading.value = false;
        }
      };

      // 替换前置文件
      const handleReplacePreFile = async (index) => {
        const status = refData.playlistStatus.value;
        const preFiles = getCurrentPreFiles();
        if (!status || !preFiles || index < 0 || index >= preFiles.length) return;

        // 设置替换模式
        refData.replaceFileInfo.value = {
          type: 'pre_files',
          index: index
        };
        refData.fileBrowserTarget.value = "pre_files";
        refData.fileBrowserDialogVisible.value = true;
      };

      // 下移 pre_files 中的文件
      const handleMovePreFileDown = async (index) => {
        const status = refData.playlistStatus.value;
        const preFiles = getCurrentPreFiles();
        if (!status || !preFiles || index < 0 || index >= preFiles.length - 1) return;

        try {
          refData.playlistLoading.value = true;
          await updateActivePlaylistData((playlistInfo) => {
            const weekdayIndex = getSelectedWeekdayIndex();
            // 确保 pre_lists 存在且格式正确
            if (!playlistInfo.pre_lists || !Array.isArray(playlistInfo.pre_lists) || playlistInfo.pre_lists.length !== 7) {
              playlistInfo.pre_lists = Array(7).fill(null).map(() => []);
            }
            const list = [...(playlistInfo.pre_lists[weekdayIndex] || [])];
            [list[index], list[index + 1]] = [list[index + 1], list[index]];
            playlistInfo.pre_lists[weekdayIndex] = list;
            return playlistInfo;
          });
        } catch (error) {
          console.error("下移失败:", error);
          ElMessage.error("下移失败: " + (error.message || "未知错误"));
        } finally {
          refData.playlistLoading.value = false;
        }
      };

      // 排序前置文件列表
      const handleSortPreFiles = async (sortType) => {
        const status = refData.playlistStatus.value;
        const preFiles = getCurrentPreFiles();
        if (!status || !preFiles || preFiles.length === 0) return;

        try {
          refData.playlistLoading.value = true;

          // 切换排序顺序
          const currentOrder = refData.preFilesSortOrder.value;
          let newOrder = null;
          if (currentOrder === `${sortType}-asc`) {
            newOrder = `${sortType}-desc`;
          } else if (currentOrder === `${sortType}-desc`) {
            newOrder = null; // 取消排序
          } else {
            newOrder = `${sortType}-asc`;
          }
          refData.preFilesSortOrder.value = newOrder;

          await updateActivePlaylistData((playlistInfo) => {
            const weekdayIndex = getSelectedWeekdayIndex();
            // 确保 pre_lists 存在且格式正确
            if (!playlistInfo.pre_lists || !Array.isArray(playlistInfo.pre_lists) || playlistInfo.pre_lists.length !== 7) {
              playlistInfo.pre_lists = Array(7).fill(null).map(() => []);
            }
            const list = [...(playlistInfo.pre_lists[weekdayIndex] || [])];
            const oldPreIndex = playlistInfo.pre_index;

            if (newOrder) {
              const [sortField, sortDir] = newOrder.split('-');
              list.sort((a, b) => {
                let aVal, bVal;
                if (sortField === 'name') {
                  aVal = getFileName(a).toLowerCase();
                  bVal = getFileName(b).toLowerCase();
                } else if (sortField === 'duration') {
                  aVal = a.duration || 0;
                  bVal = b.duration || 0;
                } else {
                  return 0;
                }

                if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
                if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
                return 0;
              });

              // 更新 pre_index
              if (oldPreIndex !== undefined && oldPreIndex !== null && oldPreIndex >= 0) {
                const oldFile = preFiles[oldPreIndex];
                const newIndex = list.findIndex(f => f.uri === oldFile.uri);
                playlistInfo.pre_index = newIndex >= 0 ? newIndex : -1;
              }
            } else {
              // 取消排序，恢复原始顺序（这里无法完全恢复，保持当前顺序）
              // 如果需要完全恢复，需要保存原始顺序
            }

            playlistInfo.pre_lists[weekdayIndex] = list;
            return playlistInfo;
          });

          if (newOrder) {
            ElMessage.success(`已按${sortType === 'name' ? '文件名' : '时长'}${newOrder.includes('asc') ? '升序' : '降序'}排序`);
          } else {
            ElMessage.success("已取消排序");
          }
        } catch (error) {
          console.error("排序失败:", error);
          ElMessage.error("排序失败: " + (error.message || "未知错误"));
        } finally {
          refData.playlistLoading.value = false;
        }
      };

      // 排序正式文件列表
      const handleSortFiles = async (sortType) => {
        const status = refData.playlistStatus.value;
        if (!status || !status.playlist || status.playlist.length === 0) return;

        try {
          refData.playlistLoading.value = true;

          // 切换排序顺序
          const currentOrder = refData.filesSortOrder.value;
          let newOrder = null;
          if (currentOrder === `${sortType}-asc`) {
            newOrder = `${sortType}-desc`;
          } else if (currentOrder === `${sortType}-desc`) {
            newOrder = null; // 取消排序
          } else {
            newOrder = `${sortType}-asc`;
          }
          refData.filesSortOrder.value = newOrder;

          await updateActivePlaylistData((playlistInfo) => {
            const list = [...(playlistInfo.playlist || [])];
            const oldCurrentIndex = playlistInfo.current_index;

            if (newOrder) {
              const [sortField, sortDir] = newOrder.split('-');
              list.sort((a, b) => {
                let aVal, bVal;
                if (sortField === 'name') {
                  aVal = getFileName(a).toLowerCase();
                  bVal = getFileName(b).toLowerCase();
                } else if (sortField === 'duration') {
                  aVal = a.duration || 0;
                  bVal = b.duration || 0;
                } else {
                  return 0;
                }

                if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
                if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
                return 0;
              });

              // 更新 current_index
              if (oldCurrentIndex !== undefined && oldCurrentIndex !== null && oldCurrentIndex >= 0) {
                const oldFile = playlistInfo.playlist[oldCurrentIndex];
                const newIndex = list.findIndex(f => f.uri === oldFile.uri);
                playlistInfo.current_index = newIndex >= 0 ? newIndex : 0;
              }
            }

            playlistInfo.playlist = list;
            playlistInfo.total = list.length;
            return playlistInfo;
          });

          if (newOrder) {
            ElMessage.success(`已按${sortType === 'name' ? '文件名' : '时长'}${newOrder.includes('asc') ? '升序' : '降序'}排序`);
          } else {
            ElMessage.success("已取消排序");
          }
        } catch (error) {
          console.error("排序失败:", error);
          ElMessage.error("排序失败: " + (error.message || "未知错误"));
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
        // 重置排序状态
        refData.preFilesSortOrder.value = null;
        refData.filesSortOrder.value = null;
        refData.preFilesDragMode.value = false;
        refData.filesDragMode.value = false;
        refData.preFilesOriginalOrder.value = null;
        refData.filesOriginalOrder.value = null;
        await refreshConnectedList();
      };

      // 检查两个数组的顺序是否相同
      const isOrderChanged = (original, current) => {
        if (!original || !current || original.length !== current.length) {
          return true;
        }
        for (let i = 0; i < original.length; i++) {
          const origUri = original[i]?.uri || original[i];
          const currUri = current[i]?.uri || current[i];
          if (origUri !== currUri) {
            return true;
          }
        }
        return false;
      };

      // 切换前置文件拖拽排序模式
      const handleTogglePreFilesDragMode = async () => {
        if (refData.preFilesDragMode.value) {
          // 退出拖拽模式时，检查是否有变化
          const status = refData.playlistStatus.value;
          const preFiles = getCurrentPreFiles();
          if (status && preFiles && preFiles.length > 0) {
            const hasChanged = isOrderChanged(refData.preFilesOriginalOrder.value, preFiles);
            if (hasChanged) {
              try {
                refData.playlistLoading.value = true;
                await updateActivePlaylistData((playlistInfo) => {
                  const weekdayIndex = getSelectedWeekdayIndex();
                  // 确保 pre_lists 存在且格式正确
                  if (!playlistInfo.pre_lists || !Array.isArray(playlistInfo.pre_lists) || playlistInfo.pre_lists.length !== 7) {
                    playlistInfo.pre_lists = Array(7).fill(null).map(() => []);
                  }
                  // 使用当前内存中的顺序
                  playlistInfo.pre_lists[weekdayIndex] = [...preFiles];
                  playlistInfo.pre_index = status.pre_index;
                  return playlistInfo;
                });
                ElMessage.success("排序已保存");
              } catch (error) {
                console.error("保存排序失败:", error);
                ElMessage.error("保存排序失败: " + (error.message || "未知错误"));
              } finally {
                refData.playlistLoading.value = false;
              }
            }
            // 清除原始顺序
            refData.preFilesOriginalOrder.value = null;
          }
        } else {
          // 启用拖拽模式时，保存原始顺序并取消自动排序
          const status = refData.playlistStatus.value;
          const preFiles = getCurrentPreFiles();
          if (status && preFiles && preFiles.length > 0) {
            refData.preFilesOriginalOrder.value = [...preFiles];
          }
          refData.preFilesSortOrder.value = null;
        }
        refData.preFilesDragMode.value = !refData.preFilesDragMode.value;
      };

      // 切换正式文件拖拽排序模式
      const handleToggleFilesDragMode = async () => {
        if (refData.filesDragMode.value) {
          // 退出拖拽模式时，检查是否有变化
          const status = refData.playlistStatus.value;
          if (status && status.playlist && status.playlist.length > 0) {
            const hasChanged = isOrderChanged(refData.filesOriginalOrder.value, status.playlist);
            if (hasChanged) {
              try {
                refData.playlistLoading.value = true;
                await updateActivePlaylistData((playlistInfo) => {
                  // 使用当前内存中的顺序
                  playlistInfo.playlist = [...(status.playlist || [])];
                  playlistInfo.current_index = status.current_index;
                  playlistInfo.total = status.playlist.length;
                  return playlistInfo;
                });
                ElMessage.success("排序已保存");
              } catch (error) {
                console.error("保存排序失败:", error);
                ElMessage.error("保存排序失败: " + (error.message || "未知错误"));
              } finally {
                refData.playlistLoading.value = false;
              }
            }
            // 清除原始顺序
            refData.filesOriginalOrder.value = null;
          }
        } else {
          // 启用拖拽模式时，保存原始顺序并取消自动排序
          const status = refData.playlistStatus.value;
          if (status && status.playlist && status.playlist.length > 0) {
            refData.filesOriginalOrder.value = [...(status.playlist || [])];
          }
          refData.filesSortOrder.value = null;
        }
        refData.filesDragMode.value = !refData.filesDragMode.value;
      };

      // 处理前置文件拖拽开始
      const handlePreFileDragStart = (event, index) => {
        if (!refData.preFilesDragMode.value) {
          event.preventDefault();
          return false;
        }
        try {
          event.dataTransfer.effectAllowed = 'move';
          event.dataTransfer.setData('text/plain', index.toString());
          // 不改变样式，保持和非拖拽时一致
        } catch (e) {
          console.error('拖拽开始失败:', e);
        }
      };

      // 处理前置文件拖拽结束
      const handlePreFileDragEnd = (event) => {
        if (event.currentTarget) {
          // 清除所有拖拽相关的样式
          event.currentTarget.style.backgroundColor = '';
          event.currentTarget.style.borderTop = '';
          event.currentTarget.style.borderBottom = '';
        }
      };

      // 处理前置文件拖拽悬停
      const handlePreFileDragOver = (event) => {
        if (!refData.preFilesDragMode.value) {
          return;
        }
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
        // 使用和 hover 一致的样式（hover:bg-gray-100）
        if (event.currentTarget) {
          const rect = event.currentTarget.getBoundingClientRect();
          const mouseY = event.clientY;
          const elementCenterY = rect.top + rect.height / 2;

          // 清除之前的样式
          event.currentTarget.style.backgroundColor = '';
          event.currentTarget.style.borderTop = '';
          event.currentTarget.style.borderBottom = '';

          // 根据鼠标位置决定插入位置（上方或下方）
          if (mouseY < elementCenterY) {
            // 插入到上方
            event.currentTarget.style.borderTop = '2px solid #3b82f6';
          } else {
            // 插入到下方
            event.currentTarget.style.borderBottom = '2px solid #3b82f6';
          }
        }
      };

      // 处理前置文件拖拽放置
      const handlePreFileDrop = (event, targetIndex) => {
        if (!refData.preFilesDragMode.value) {
          return;
        }
        event.preventDefault();
        // 清除所有拖拽相关的样式
        if (event.currentTarget) {
          event.currentTarget.style.backgroundColor = '';
          event.currentTarget.style.borderTop = '';
          event.currentTarget.style.borderBottom = '';
        }

        const sourceIndex = parseInt(event.dataTransfer.getData('text/plain'), 10);

        if (sourceIndex === targetIndex || isNaN(sourceIndex)) {
          return;
        }

        const status = refData.playlistStatus.value;
        const preFiles = getCurrentPreFiles();
        if (!status || !preFiles || sourceIndex < 0 || sourceIndex >= preFiles.length ||
          targetIndex < 0 || targetIndex >= preFiles.length) {
          return;
        }
        // 只在内存中更新，不保存到后端
        const weekdayIndex = getSelectedWeekdayIndex();
        const list = [...preFiles];
        const [removed] = list.splice(sourceIndex, 1);
        list.splice(targetIndex, 0, removed);

        // 计算新的 pre_index
        let newPreIndex = status.pre_index;
        if (status.pre_index !== undefined && status.pre_index !== null && status.pre_index >= 0) {
          if (status.pre_index === sourceIndex) {
            newPreIndex = targetIndex;
          } else if (sourceIndex < status.pre_index && targetIndex >= status.pre_index) {
            newPreIndex = status.pre_index - 1;
          } else if (sourceIndex > status.pre_index && targetIndex <= status.pre_index) {
            newPreIndex = status.pre_index + 1;
          }
        }

        // 更新 playlistCollection 中对应的项
        const collection = refData.playlistCollection.value.map(item => {
          if (item.id === status.id) {
            // 确保 pre_lists 存在且格式正确
            if (!item.pre_lists || !Array.isArray(item.pre_lists) || item.pre_lists.length !== 7) {
              item.pre_lists = Array(7).fill(null).map(() => []);
            }
            return {
              ...item,
              pre_lists: item.pre_lists.map((oldList, idx) => idx === weekdayIndex ? list : oldList),
              pre_index: newPreIndex
            };
          }
          return item;
        });
        refData.playlistCollection.value = collection;

        // 同步更新到状态中
        syncActivePlaylist(collection);
      };

      // 切换星期按钮
      const handleSelectWeekday = (weekdayIndex) => {
        refData.selectedWeekdayIndex.value = weekdayIndex;
        // 重新同步当前播放列表状态，以更新显示的 pre_files
        syncActivePlaylist(refData.playlistCollection.value);
      };

      // 处理正式文件拖拽开始
      const handleFileDragStart = (event, index) => {
        if (!refData.filesDragMode.value) {
          event.preventDefault();
          return false;
        }
        try {
          event.dataTransfer.effectAllowed = 'move';
          event.dataTransfer.setData('text/plain', index.toString());
          // 不改变样式，保持和非拖拽时一致
        } catch (e) {
          console.error('拖拽开始失败:', e);
        }
      };

      // 处理正式文件拖拽结束
      const handleFileDragEnd = (event) => {
        if (event.currentTarget) {
          // 清除所有拖拽相关的样式
          event.currentTarget.style.backgroundColor = '';
          event.currentTarget.style.borderTop = '';
          event.currentTarget.style.borderBottom = '';
        }
      };

      // 处理正式文件拖拽悬停
      const handleFileDragOver = (event) => {
        if (!refData.filesDragMode.value) {
          return;
        }
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
        // 使用和 hover 一致的样式（hover:bg-gray-100）
        if (event.currentTarget) {
          const rect = event.currentTarget.getBoundingClientRect();
          const mouseY = event.clientY;
          const elementCenterY = rect.top + rect.height / 2;

          // 清除之前的样式
          event.currentTarget.style.backgroundColor = '';
          event.currentTarget.style.borderTop = '';
          event.currentTarget.style.borderBottom = '';

          // 根据鼠标位置决定插入位置（上方或下方）
          if (mouseY < elementCenterY) {
            // 插入到上方
            event.currentTarget.style.borderTop = '2px solid #3b82f6';
          } else {
            // 插入到下方
            event.currentTarget.style.borderBottom = '2px solid #3b82f6';
          }
        }
      };

      // 处理正式文件拖拽放置
      const handleFileDrop = (event, targetIndex) => {
        if (!refData.filesDragMode.value) {
          return;
        }
        event.preventDefault();
        // 清除所有拖拽相关的样式
        if (event.currentTarget) {
          event.currentTarget.style.backgroundColor = '';
          event.currentTarget.style.borderTop = '';
          event.currentTarget.style.borderBottom = '';
        }

        const sourceIndex = parseInt(event.dataTransfer.getData('text/plain'), 10);

        if (sourceIndex === targetIndex || isNaN(sourceIndex)) {
          return;
        }

        const status = refData.playlistStatus.value;
        if (!status || !status.playlist || sourceIndex < 0 || sourceIndex >= status.playlist.length ||
          targetIndex < 0 || targetIndex >= status.playlist.length) {
          return;
        }
        // 只在内存中更新，不保存到后端
        const list = [...(status.playlist || [])];
        const [removed] = list.splice(sourceIndex, 1);
        list.splice(targetIndex, 0, removed);

        // 计算新的 current_index
        let newCurrentIndex = status.current_index;
        if (status.current_index !== undefined && status.current_index !== null && status.current_index >= 0) {
          if (status.current_index === sourceIndex) {
            newCurrentIndex = targetIndex;
          } else if (sourceIndex < status.current_index && targetIndex >= status.current_index) {
            newCurrentIndex = status.current_index - 1;
          } else if (sourceIndex > status.current_index && targetIndex <= status.current_index) {
            newCurrentIndex = status.current_index + 1;
          }
        }

        // 更新 playlistCollection 中对应的项
        const collection = refData.playlistCollection.value.map(item => {
          if (item.id === status.id) {
            return {
              ...item,
              playlist: list,
              current_index: newCurrentIndex,
              total: list.length
            };
          }
          return item;
        });
        refData.playlistCollection.value = collection;

        // 同步更新到状态中
        syncActivePlaylist(collection);
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
        refData.fileBrowserTarget.value = "files"; // 默认添加到 files
      };

      const handleOpenFileBrowserForPreFiles = () => {
        if (!refData.playlistStatus.value) {
          ElMessage.warning("请先选择一个播放列表");
          return;
        }
        refData.fileBrowserDialogVisible.value = true;
        refData.fileBrowserTarget.value = "pre_files"; // 默认添加到 pre_files
      };

      const handleCloseFileBrowser = () => {
        refData.fileBrowserDialogVisible.value = false;
        refData.replaceFileInfo.value = null; // 清除替换信息
      };

      const refMethods = {
        handleUpdateDeviceList,
        handleOpenScanDialog,
        handleCloseScanDialog,
        handleOpenCronBuilder,
        handleCloseCronBuilder,
        handleCronBuilderApply,
        handleCronBuilderPreview,
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
        handleReplacePlaylistItem,
        handleClearPlaylist,
        handleDeletePreFile,
        handleClearPreFiles,
        handleClearFiles,
        handleMovePreFileUp,
        handleMovePreFileDown,
        handleReplacePreFile,
        handleSortPreFiles,
        handleSortFiles,
        handleTogglePreFilesDragMode,
        handleToggleFilesDragMode,
        handlePreFileDragStart,
        handlePreFileDragEnd,
        handlePreFileDragOver,
        handlePreFileDrop,
        handleFileDragStart,
        handleFileDragEnd,
        handleFileDragOver,
        handleFileDrop,
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
        handleFileBrowserConfirm,
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
        handleMiDeviceVolumeChange,
        getMiDeviceVolume,
        setMiDeviceVolume,
        handleStopMiDevice,
        getPreFilesTotalDuration,
        getFilesTotalDuration,
        getPlaylistTotalDuration,
        handleOpenAgentListDialog,
        handleCloseAgentListDialog,
        handleRefreshAgentList,
        handleTestAgentButton,
        getCurrentPreFiles,
        getSelectedWeekdayIndex,
        getWeekdayIndex,
        handleSelectWeekday,
        getPreFilesCountForWeekday,
        handlePlayFileInBrowser,
        isFilePlaying,
        handleTogglePreFilesExpand,
      };


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
        initialCronExpr,
        ...refMethods,
      };
    },
    template,
  };
  return component;
}
export default createComponent();
