/**
 * 播放列表数据管理 Composable
 * 处理数据规范化、转换、保存等操作
 */
import { type Ref } from "vue";
import { playlistAction } from "@/api/playlist";
import { normalizeFiles } from "@/utils/file";
import { formatDateTime } from "@/utils/date";
import { logAndNoticeError } from "@/utils/error";
import { createPlaylistId } from "@/utils/playlist";
import { logger } from "@/utils/logger";
import {
  WEEKDAYS_COUNT,
  DEFAULT_PLAYLIST_NAME,
  VALID_DEVICE_TYPES,
  DEFAULT_DEVICE_TYPE,
  STORAGE_KEY_ACTIVE_PLAYLIST_ID,
} from "@/constants/playlist";
import type {
  Playlist,
  PlaylistStatus,
  PlaylistItem,
  PlaylistCollection,
  PlaylistApiData,
  PlaylistSchedule,
} from "@/types/playlist";
import type { DeviceType } from "@/constants/device";

export function usePlaylistData(
  playlistCollection: Ref<Playlist[]>,
  activePlaylistId: Ref<string>,
  playlistStatus: Ref<PlaylistStatus | null>,
  playlistRefreshing: Ref<boolean>,
  pendingDeviceType: Ref<string | null>,
  preFilesDragMode: Ref<boolean>,
  filesDragMode: Ref<boolean>,
  _getSelectedWeekdayIndex: () => number // 保留参数以保持接口兼容性，但当前未使用
) {
  // ========== 辅助函数 ==========

  /**
   * 将 NormalizedFile[] 转换为 PlaylistItem[]
   */
  const toPlaylistItems = (files: ReturnType<typeof normalizeFiles>): PlaylistItem[] => {
    return files.map(f => ({ ...f })) as PlaylistItem[];
  };

  /**
   * 从 item 中获取文件列表（支持 playlist 或 files 属性）
   */
  const getFilesFromItem = (item: Partial<PlaylistApiData> | Partial<Playlist>): PlaylistItem[] => {
    const filesData =
      ("playlist" in item && Array.isArray(item.playlist) && item.playlist) ||
      ("files" in item && Array.isArray(item.files) && item.files) ||
      [];
    return toPlaylistItems(normalizeFiles(filesData, true));
  };

  /**
   * 规范化前置文件列表
   */
  const normalizePreLists = (
    item: Partial<PlaylistApiData> | Partial<Playlist>
  ): PlaylistItem[][] => {
    // 如果已有有效的 pre_lists，直接规范化返回
    if (
      item.pre_lists &&
      Array.isArray(item.pre_lists) &&
      item.pre_lists.length === WEEKDAYS_COUNT
    ) {
      return item.pre_lists.map(pre_list =>
        toPlaylistItems(normalizeFiles(pre_list || [], true))
      ) as PlaylistItem[][];
    }

    // 否则从 pre_files 创建，复制到7天
    const preFilesData =
      ("pre_files" in item && Array.isArray(item.pre_files) && item.pre_files) || [];
    const preFiles = toPlaylistItems(normalizeFiles(preFilesData, true));
    return Array(WEEKDAYS_COUNT)
      .fill(null)
      .map(() => [...preFiles]) as PlaylistItem[][];
  };

  /**
   * 验证并规范化设备类型
   */
  const normalizeDeviceType = (type: string | undefined | null): DeviceType => {
    return (
      VALID_DEVICE_TYPES.includes(type as DeviceType) ? type : DEFAULT_DEVICE_TYPE
    ) as DeviceType;
  };

  /**
   * 规范化 Schedule
   */
  const normalizeSchedule = (schedule?: Partial<PlaylistSchedule>): PlaylistSchedule => {
    return {
      enabled: (schedule?.enabled === 1 ? 1 : 0) as 0 | 1,
      cron: schedule?.cron ? String(schedule.cron) : "",
      duration: schedule?.duration || 0,
    };
  };

  /**
   * 解析索引值（支持 number 或 string）
   */
  const parseIndex = (value: number | string | undefined | null, defaultValue: number): number => {
    if (typeof value === "number") return value;
    if (value == null) return defaultValue;
    const parsed = parseInt(String(value), 10);
    return isNaN(parsed) ? defaultValue : parsed;
  };

  /**
   * 规范化 isPlaying 值
   */
  const normalizeIsPlaying = (value: boolean | number | undefined | null): boolean => {
    return value === true || value === 1;
  };

  /**
   * 规范化 current_index，确保在有效范围内
   */
  const normalizeCurrentIndex = (
    index: number | string | undefined | null,
    playlistLength: number
  ): number => {
    if (playlistLength === 0) return 0;
    const currentIndex = parseIndex(index, 0);
    return Math.max(0, Math.min(currentIndex, playlistLength - 1));
  };

  /**
   * 创建空的 pre_lists 数组
   */
  const createEmptyPreLists = (): PlaylistItem[][] => {
    return Array(WEEKDAYS_COUNT)
      .fill(null)
      .map(() => []) as PlaylistItem[][];
  };

  /**
   * 创建新的空播放列表
   */
  const createNewPlaylist = (name: string): Playlist => {
    return normalizePlaylistItem({ name: (name || DEFAULT_PLAYLIST_NAME).trim() });
  };

  /**
   * 检查 pre_lists 是否有效
   */
  const isValidPreLists = (preLists: unknown): preLists is PlaylistItem[][] => {
    return (
      Array.isArray(preLists) &&
      preLists.length === WEEKDAYS_COUNT &&
      preLists.every(list => Array.isArray(list))
    );
  };

  // ========== 主要函数 ==========

  /**
   * 规范化播放列表项
   */
  const normalizePlaylistItem = (
    item: Partial<PlaylistApiData> | Partial<Playlist>,
    fallbackName = "播放列表"
  ): Playlist => {
    const playlist = getFilesFromItem(item);
    const pre_lists = normalizePreLists(item);
    const currentIndex = normalizeCurrentIndex(item?.current_index, playlist.length);
    const name = (item?.name && String(item.name).trim()) || fallbackName;
    const deviceType = normalizeDeviceType(item?.device?.type || item?.device_type);
    const deviceAddress = item?.device_address || item?.device?.address || null;

    return {
      id: item?.id || createPlaylistId(),
      name,
      playlist,
      pre_lists,
      total: playlist.length,
      current_index: currentIndex,
      pre_index: parseIndex(item?.pre_index, -1),
      device_address: deviceAddress,
      device_type: deviceType,
      device_volume: item?.device_volume,
      device: item?.device || {
        type: deviceType,
        address: deviceAddress,
        name: item?.device?.name || null,
      },
      schedule: normalizeSchedule(item?.schedule),
      trigger_button: item?.trigger_button || "",
      updatedAt:
        "updatedAt" in item && typeof item.updatedAt === "number" ? item.updatedAt : Date.now(),
      isPlaying: normalizeIsPlaying(item?.isPlaying),
    };
  };

  /**
   * 规范化播放列表数组
   */
  const normalizePlaylistArray = (list: PlaylistApiData[] | Playlist[]): Playlist[] => {
    if (!Array.isArray(list) || list.length === 0) {
      return [normalizePlaylistItem({ name: DEFAULT_PLAYLIST_NAME })];
    }
    return list.map((item, index) => {
      // 如果已经是 Playlist 类型，直接返回
      if ("playlist" in item && "total" in item) {
        return item as Playlist;
      }
      // 否则作为 PlaylistApiData 处理
      return normalizePlaylistItem(item as PlaylistApiData, item?.name || `播放列表${index + 1}`);
    });
  };

  /**
   * 规范化播放列表集合
   */
  const normalizePlaylistCollection = (
    raw: PlaylistCollection | PlaylistApiData | PlaylistApiData[] | null
  ): PlaylistCollection => {
    // 类型守卫：检查是否是 PlaylistCollection
    if (raw && "playlists" in raw && Array.isArray(raw.playlists)) {
      const collection = raw as PlaylistCollection;
      const playlists = normalizePlaylistArray(
        collection.playlists as PlaylistApiData[] | Playlist[]
      );
      const activeId = playlists.some(item => item.id === collection.activePlaylistId)
        ? (collection.activePlaylistId as string | null)
        : playlists[0]?.id || null;
      return { playlists, activePlaylistId: activeId };
    }

    // 类型守卫：检查是否是单个 PlaylistApiData（有 playlist 或 files 属性）
    if (raw && !Array.isArray(raw) && ("playlist" in raw || "files" in raw)) {
      const apiData = raw as PlaylistApiData;
      const playlistData =
        ("playlist" in apiData && Array.isArray(apiData.playlist) && apiData.playlist) ||
        ("files" in apiData && Array.isArray(apiData.files) && apiData.files) ||
        [];
      const migrated = normalizePlaylistItem({
        id: apiData.id || (apiData as any).playlist_id,
        name: apiData.name || DEFAULT_PLAYLIST_NAME,
        files: playlistData,
        current_index: apiData.current_index,
        device_address: apiData.device_address,
      });
      return { playlists: [migrated], activePlaylistId: migrated.id };
    }

    // 默认情况
    const defaultPlaylist = normalizePlaylistItem({ name: DEFAULT_PLAYLIST_NAME });
    return { playlists: [defaultPlaylist], activePlaylistId: defaultPlaylist.id };
  };

  /**
   * 转换 API 数据格式为播放列表集合
   */
  const transformApiDataToPlaylistFormat = (
    apiData: PlaylistApiData | PlaylistApiData[] | Record<string, PlaylistApiData> | null
  ): PlaylistCollection | null => {
    if (!apiData) return null;

    // Record<string, PlaylistApiData> 格式
    if (!Array.isArray(apiData) && Object.keys(apiData).length > 0) {
      const playlists = Object.values(apiData).map(item =>
        normalizePlaylistItem(item, item.name || DEFAULT_PLAYLIST_NAME)
      );
      return {
        playlists: playlists as Playlist[],
        activePlaylistId: playlists[0]?.id || null,
      };
    }

    // PlaylistApiData[] 格式
    if (Array.isArray(apiData)) {
      const playlists = apiData.map(item =>
        normalizePlaylistItem(item, item.name || DEFAULT_PLAYLIST_NAME)
      );
      return {
        playlists: playlists as Playlist[],
        activePlaylistId: playlists[0]?.id || null,
      };
    }

    // 单个 PlaylistApiData 格式
    if (!Array.isArray(apiData) && "id" in apiData && typeof apiData.id === "string") {
      const apiDataItem = apiData as PlaylistApiData;
      const playlist = normalizePlaylistItem(
        apiDataItem,
        apiDataItem.name || DEFAULT_PLAYLIST_NAME
      );
      return {
        playlists: [playlist],
        activePlaylistId: apiDataItem.id,
      };
    }

    return null;
  };

  /**
   * 转换前端格式为 API 格式
   */
  const transformPlaylistToApiFormat = (
    collection: Playlist[]
  ): Record<string, PlaylistApiData> => {
    const playlistDict: Record<string, PlaylistApiData> = {};

    collection.forEach(item => {
      if (!item.id) return;

      const deviceType = normalizeDeviceType(item.device?.type || item.device_type);
      const normalizedFiles = normalizeFiles(item.playlist || [], true);
      const normalizedPreLists = normalizePreLists(item);

      playlistDict[item.id] = {
        id: item.id,
        name: item.name || DEFAULT_PLAYLIST_NAME,
        files: normalizedFiles,
        pre_lists: normalizedPreLists,
        current_index: item.current_index || 0,
        device: {
          address: item.device?.address || item.device_address || "",
          type: deviceType,
          name: item.device?.name || null,
        },
        device_volume: item.device_volume,
        schedule: item.schedule || { enabled: 0, cron: "", duration: 0 },
        trigger_button: item.trigger_button || "",
        create_time: item.create_time || formatDateTime(),
        updated_time: formatDateTime(),
      } as PlaylistApiData;
    });

    return playlistDict;
  };

  /**
   * 保存播放列表
   */
  const savePlaylist = async (collectionOverride?: Playlist[]) => {
    try {
      const collection = (collectionOverride || playlistCollection.value || []).map(item => ({
        ...item,
        total: Array.isArray(item.playlist) ? item.playlist.length : 0,
        updatedAt: Date.now(),
      }));

      const playlistDict = transformPlaylistToApiFormat(collection);
      const response = await playlistAction("updateAll", "POST", playlistDict);
      if (response.code !== 0) {
        throw new Error(response.msg || "保存播放列表集合失败");
      }
    } catch (error) {
      logAndNoticeError(error as Error, "保存播放列表集合失败");
    }
  };

  /**
   * 更新单个播放列表
   */
  const updateSinglePlaylist = async (playlistData: Playlist) => {
    try {
      const playlistDict = transformPlaylistToApiFormat([playlistData]);
      const singlePlaylistData = playlistDict[playlistData.id];

      if (!singlePlaylistData) {
        throw new Error("播放列表数据格式错误");
      }

      const response = await playlistAction(
        "update",
        "POST",
        singlePlaylistData as unknown as Record<string, unknown>
      );

      if (response.code !== 0) {
        throw new Error(response.msg || "更新播放列表失败");
      }

      return true;
    } catch (error) {
      logAndNoticeError(error as Error, "更新播放列表失败");
      return false;
    }
  };

  /**
   * 同步激活的播放列表
   */
  const syncActivePlaylist = (collection: Playlist[]) => {
    const list = Array.isArray(collection) ? collection : playlistCollection.value;

    if (!list || list.length === 0) {
      playlistStatus.value = null;
      activePlaylistId.value = "";
      return;
    }

    const active = list.find(item => item.id === activePlaylistId.value) || list[0];
    activePlaylistId.value = active.id;

    const currentIndex = normalizeCurrentIndex(active.current_index, active.playlist?.length || 0);
    const pre_lists = isValidPreLists(active.pre_lists)
      ? active.pre_lists.map(list => [...(list || [])])
      : createEmptyPreLists();

    playlistStatus.value = {
      ...active,
      playlist: [...(active.playlist || [])],
      pre_lists,
      current_index: currentIndex,
      pre_index: parseIndex(active.pre_index, -1),
      in_pre_files: false, // PlaylistStatus 的 in_pre_files 是计算属性
      isPlaying: normalizeIsPlaying(active.isPlaying),
    };
  };

  /**
   * 深拷贝播放列表项（避免直接修改原对象）
   */
  const clonePlaylistItem = (item: Playlist): Playlist => {
    return {
      ...item,
      playlist: item.playlist.map(f => ({ ...f })),
      pre_lists: isValidPreLists(item.pre_lists)
        ? item.pre_lists.map(list => list.map(f => ({ ...f })))
        : createEmptyPreLists(),
    };
  };

  /**
   * 更新激活播放列表数据
   */
  const updateActivePlaylistData = async (
    mutator: (playlistInfo: Playlist) => Playlist
  ): Promise<PlaylistStatus | null> => {
    if (typeof mutator !== "function") return null;

    // 确保集合不为空
    let collection =
      playlistCollection.value.length > 0
        ? playlistCollection.value.map(clonePlaylistItem)
        : [normalizePlaylistItem({ name: DEFAULT_PLAYLIST_NAME })];

    // 确保有激活的播放列表
    let index = collection.findIndex(item => item.id === activePlaylistId.value);
    if (index === -1) {
      index = 0;
      activePlaylistId.value = collection[0].id;
    }

    const currentItem = collection[index];
    const updatedItem = mutator(clonePlaylistItem(currentItem)) || currentItem;
    const normalizedItem = normalizePlaylistItem(updatedItem, currentItem.name);

    // 保留原有的 pre_lists（如果更新后的无效）
    if (!isValidPreLists(normalizedItem.pre_lists)) {
      normalizedItem.pre_lists = isValidPreLists(currentItem.pre_lists)
        ? currentItem.pre_lists.map(list => list.map(f => ({ ...f })))
        : createEmptyPreLists();
    }

    collection[index] = normalizedItem;
    playlistCollection.value = collection;

    await updateSinglePlaylist(collection[index]);
    syncActivePlaylist(collection);
    return playlistStatus.value;
  };

  /**
   * 从 localStorage 恢复或设置激活的播放列表ID
   */
  const restoreOrSetActivePlaylistId = (playlists: Playlist[], defaultId: string | null) => {
    const savedPlaylistId = localStorage.getItem(STORAGE_KEY_ACTIVE_PLAYLIST_ID);
    if (savedPlaylistId && playlists.some(p => p.id === savedPlaylistId)) {
      activePlaylistId.value = savedPlaylistId;
    } else {
      activePlaylistId.value = defaultId || "";
    }
  };

  /**
   * 加载播放列表
   */
  const loadPlaylist = async () => {
    try {
      const response = await playlistAction("get", "GET", {});
      if (response.code !== 0) {
        throw new Error(response.msg || "获取播放列表失败");
      }

      const parsed = transformApiDataToPlaylistFormat(
        response.data as
          | PlaylistApiData
          | PlaylistApiData[]
          | Record<string, PlaylistApiData>
          | null
      );
      const normalized = parsed
        ? normalizePlaylistCollection(parsed)
        : normalizePlaylistCollection(null);

      playlistCollection.value = normalized.playlists;
      restoreOrSetActivePlaylistId(normalized.playlists, normalized.activePlaylistId);
      syncActivePlaylist(normalized.playlists);

      return normalized;
    } catch (error) {
      logger.error("从接口加载播放列表失败:", error);
      const fallback = normalizePlaylistCollection(null);

      playlistCollection.value = fallback.playlists;
      restoreOrSetActivePlaylistId(fallback.playlists, fallback.activePlaylistId);
      syncActivePlaylist(fallback.playlists);

      return fallback;
    }
  };

  /**
   * 检查是否应该跳过自动刷新
   */
  const shouldSkipAutoRefresh = (isAutoRefresh: boolean): boolean => {
    if (!isAutoRefresh) return false;
    // 正在编辑设备配置时跳过
    if (pendingDeviceType.value !== null) return true;
    // 处于拖拽排序模式时跳过
    if (preFilesDragMode.value || filesDragMode.value) return true;
    return false;
  };

  /**
   * 刷新播放列表状态
   */
  const refreshPlaylistStatus = async (onlyCurrent = false, isAutoRefresh = false) => {
    try {
      if (shouldSkipAutoRefresh(isAutoRefresh)) {
        return;
      }

      playlistRefreshing.value = true;

      if (onlyCurrent) {
        const activeId = activePlaylistId.value;
        if (!activeId) {
          return;
        }

        const response = await playlistAction("get", "GET", { id: activeId });
        if (response.code !== 0) {
          throw new Error(response.msg || "获取播放列表状态失败");
        }

        const parsed = transformApiDataToPlaylistFormat(
          response.data as
            | PlaylistApiData
            | PlaylistApiData[]
            | Record<string, PlaylistApiData>
            | null
        );

        if (!parsed?.playlists?.length) {
          return;
        }

        const updatedPlaylist = parsed.playlists[0];
        const collection = playlistCollection.value.map(item => {
          if (item.id !== activeId) return item;

          return {
            ...item,
            ...updatedPlaylist,
            playlist: updatedPlaylist.playlist || item.playlist,
            pre_lists: isValidPreLists(updatedPlaylist.pre_lists)
              ? updatedPlaylist.pre_lists.map(list => [...(list || [])])
              : item.pre_lists,
            current_index:
              updatedPlaylist.current_index !== undefined
                ? updatedPlaylist.current_index
                : item.current_index,
            isPlaying: normalizeIsPlaying(updatedPlaylist?.isPlaying),
          };
        });

        playlistCollection.value = collection;
        syncActivePlaylist(collection);
      } else {
        await loadPlaylist();
      }
    } catch (error) {
      logger.error("刷新播放列表状态失败:", error);
    } finally {
      playlistRefreshing.value = false;
    }
  };

  return {
    normalizePlaylistItem,
    normalizePlaylistCollection,
    createNewPlaylist,
    transformApiDataToPlaylistFormat,
    transformPlaylistToApiFormat,
    savePlaylist,
    updateSinglePlaylist,
    syncActivePlaylist,
    updateActivePlaylistData,
    loadPlaylist,
    refreshPlaylistStatus,
  };
}
