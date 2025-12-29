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
import { WEEKDAYS_COUNT, DEFAULT_PLAYLIST_NAME } from "@/constants/playlist";
import type { Playlist, PlaylistStatus, PlaylistItem, PlaylistCollection, PlaylistApiData } from "@/types/playlist";

export function usePlaylistData(
  playlistCollection: Ref<Playlist[]>,
  activePlaylistId: Ref<string>,
  playlistStatus: Ref<PlaylistStatus | null>,
  playlistRefreshing: Ref<boolean>,
  pendingDeviceType: Ref<string | null>,
  preFilesDragMode: Ref<boolean>,
  filesDragMode: Ref<boolean>,
  getSelectedWeekdayIndex: () => number
) {
  // 规范化播放列表项
  const normalizePlaylistItem = (
    item: Partial<PlaylistApiData> | Partial<Playlist>,
    fallbackName = "播放列表"
  ): Playlist => {
    const playlist = normalizeFiles(item?.playlist || item?.files || [], true);
    let pre_lists = item?.pre_lists;
    if (!pre_lists || !Array.isArray(pre_lists) || pre_lists.length !== WEEKDAYS_COUNT) {
      const pre_files = normalizeFiles(item?.pre_files || [], true);
      pre_lists = Array(WEEKDAYS_COUNT)
        .fill(null)
        .map(() => [...pre_files]);
    } else {
      pre_lists = pre_lists.map((pre_list: PlaylistItem[]) => normalizeFiles(pre_list || [], true));
    }

    let currentIndex =
      typeof item?.current_index === "number"
        ? item.current_index
        : item?.current_index !== undefined && item?.current_index !== null
          ? parseInt(item.current_index, 10) || 0
          : 0;
    if (playlist.length === 0) {
      currentIndex = 0;
    } else {
      if (currentIndex < 0) currentIndex = 0;
      if (currentIndex >= playlist.length) currentIndex = playlist.length - 1;
    }
    const name = (item?.name && String(item.name).trim()) || fallbackName;
    const deviceType = item?.device?.type || item?.device_type || "dlna";
    const validDeviceType = ["agent", "dlna", "bluetooth", "mi"].includes(deviceType)
      ? deviceType
      : "dlna";
    const schedule = item?.schedule || { enabled: 0, cron: "", duration: 0 };
    const normalizedSchedule = {
      enabled: schedule.enabled || 0,
      cron: schedule.cron !== undefined && schedule.cron !== null ? String(schedule.cron) : "",
      duration: schedule.duration || 0,
    };

    return {
      id: item?.id || createPlaylistId(),
      name,
      playlist,
      pre_lists,
      total: playlist.length,
      current_index: currentIndex,
      pre_index:
        typeof item?.pre_index === "number"
          ? item.pre_index
          : item?.pre_index !== undefined && item?.pre_index !== null
            ? parseInt(item.pre_index, 10)
            : -1,
      device_address: item?.device_address || item?.device?.address || null,
      device_type: validDeviceType,
      device: item?.device || {
        type: validDeviceType,
        address: item?.device_address || null,
        name: item?.device?.name || null,
      },
      schedule: normalizedSchedule,
      trigger_button: item?.trigger_button || "",
      updatedAt: item?.updatedAt || Date.now(),
      isPlaying: item?.isPlaying === true || item?.isPlaying === 1 || false,
    };
  };

  // 规范化播放列表集合
  const normalizePlaylistCollection = (
    raw: PlaylistCollection | PlaylistApiData | PlaylistApiData[] | null
  ): PlaylistCollection => {
    const ensureList = (list: PlaylistApiData[]) => {
      if (!Array.isArray(list) || list.length === 0) {
        return [normalizePlaylistItem({ name: DEFAULT_PLAYLIST_NAME })];
      }
      return list.map((item, index) =>
        normalizePlaylistItem(item, item?.name || `播放列表${index + 1}`)
      );
    };

    if (raw && Array.isArray(raw.playlists)) {
      const playlists = ensureList(raw.playlists);
      const activeId = playlists.some(item => item.id === raw.activePlaylistId)
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

    const defaultPlaylist = normalizePlaylistItem({ name: "默认播放列表" });
    return { playlists: [defaultPlaylist], activePlaylistId: defaultPlaylist.id };
  };

  // 转换 API 数据格式
  const transformApiDataToPlaylistFormat = (
    apiData: PlaylistApiData | PlaylistApiData[] | Record<string, PlaylistApiData> | null
  ): PlaylistCollection | null => {
    if (!apiData) {
      return null;
    }

    if (!Array.isArray(apiData) && Object.keys(apiData).length > 0) {
      const playlists = Object.values(apiData).map((item: PlaylistApiData) => {
        const normalizedFiles = normalizeFiles(item.files || [], true);
        let normalizedPreLists = item.pre_lists;
        if (
          !normalizedPreLists ||
          !Array.isArray(normalizedPreLists) ||
          normalizedPreLists.length !== WEEKDAYS_COUNT
        ) {
          const normalizedPreFiles = normalizeFiles(item.pre_files || [], true);
          normalizedPreLists = Array(WEEKDAYS_COUNT)
            .fill(null)
            .map(() => [...normalizedPreFiles]);
        } else {
          normalizedPreLists = normalizedPreLists.map((pre_list: PlaylistItem[]) =>
            normalizeFiles(pre_list || [], true)
          );
        }

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

    if (Array.isArray(apiData)) {
      return {
        playlists: apiData.map(item => ({
          ...item,
          playlist: normalizeFiles(item.files || item.playlist || [], false),
        })),
        activePlaylistId: apiData[0]?.id || null,
      };
    }

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

  // 转换前端格式为 API 格式
  const transformPlaylistToApiFormat = (
    collection: Playlist[]
  ): Record<string, PlaylistApiData> => {
    const playlistDict: Record<string, PlaylistApiData> = {};
    collection.forEach(item => {
      if (item.id) {
        let deviceType = "dlna";
        if (item.device?.type && ["agent", "dlna", "bluetooth", "mi"].includes(item.device.type)) {
          deviceType = item.device.type;
        } else if (
          item.device_type &&
          ["agent", "dlna", "bluetooth", "mi"].includes(item.device_type)
        ) {
          deviceType = item.device_type;
        }

        const deviceAddress = item.device?.address || item.device_address || "";
        const normalizedFiles = normalizeFiles(item.playlist || [], true);
        let normalizedPreLists = item.pre_lists;
        if (
          !normalizedPreLists ||
          !Array.isArray(normalizedPreLists) ||
          normalizedPreLists.length !== WEEKDAYS_COUNT
        ) {
          const normalizedPreFiles = normalizeFiles(item.pre_files || [], true);
          normalizedPreLists = Array(WEEKDAYS_COUNT)
            .fill(null)
            .map(() => [...normalizedPreFiles]);
        } else {
          normalizedPreLists = normalizedPreLists.map((pre_list: PlaylistItem[]) =>
            normalizeFiles(pre_list || [], true)
          );
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
          create_time: item.create_time || formatDateTime(),
          updated_time: formatDateTime(),
        };
      }
    });
    return playlistDict;
  };

  // 保存播放列表
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

  // 更新单个播放列表
  const updateSinglePlaylist = async (playlistData: Playlist) => {
    try {
      const playlistDict = transformPlaylistToApiFormat([playlistData]);
      const playlistId = playlistData.id;
      const singlePlaylistData = playlistDict[playlistId];
      if (!singlePlaylistData) {
        throw new Error("播放列表数据格式错误");
      }
      singlePlaylistData.id = playlistId;
      const response = await playlistAction("update", "POST", singlePlaylistData);
      if (response.code !== 0) {
        throw new Error(response.msg || "更新播放列表失败");
      }
      return true;
    } catch (error) {
      logAndNoticeError(error as Error, "更新播放列表失败");
      return false;
    }
  };

  // 同步激活的播放列表
  const syncActivePlaylist = (collection: Playlist[]) => {
    const list = Array.isArray(collection) ? collection : playlistCollection.value;
    if (!list || list.length === 0) {
      playlistStatus.value = null;
      activePlaylistId.value = "";
      return;
    }
    let activeId = activePlaylistId.value;
    const active = list.find(item => item.id === activeId) || list[0];
    activeId = active.id;
    activePlaylistId.value = activeId;

    let currentIndex =
      typeof active.current_index === "number"
        ? active.current_index
        : active.current_index !== undefined && active.current_index !== null
          ? parseInt(active.current_index, 10) || 0
          : 0;

    if (active.playlist && active.playlist.length > 0) {
      if (currentIndex < 0) currentIndex = 0;
      if (currentIndex >= active.playlist.length) currentIndex = active.playlist.length - 1;
    } else {
      currentIndex = 0;
    }

    const weekdayIndex = getSelectedWeekdayIndex();
    const currentPreFiles =
      active.pre_lists &&
      Array.isArray(active.pre_lists) &&
      active.pre_lists.length === WEEKDAYS_COUNT
        ? active.pre_lists[weekdayIndex] || []
        : [];
    playlistStatus.value = {
      ...active,
      playlist: [...(active.playlist || [])],
      pre_lists: active.pre_lists
        ? active.pre_lists.map((list: PlaylistItem[]) => [...(list || [])])
        : Array(WEEKDAYS_COUNT)
            .fill(null)
            .map(() => []),
      pre_files: currentPreFiles,
      current_index: currentIndex,
      pre_index:
        typeof active.pre_index === "number"
          ? active.pre_index
          : active.pre_index !== undefined && active.pre_index !== null
            ? parseInt(active.pre_index, 10)
            : -1,
      in_pre_files: active?.in_pre_files === true || active?.in_pre_files === 1 || false,
      isPlaying: active?.isPlaying === true || active?.isPlaying === 1 || false,
    };
  };

  // 更新激活播放列表数据
  const updateActivePlaylistData = async (
    mutator: (playlistInfo: Playlist) => Playlist
  ): Promise<PlaylistStatus | null> => {
    if (typeof mutator !== "function") return null;
    let collection = playlistCollection.value.map(item => ({
      ...item,
      playlist: Array.isArray(item.playlist) ? item.playlist.map((f: PlaylistItem) => ({ ...f })) : [],
      pre_lists:
        Array.isArray(item.pre_lists) && item.pre_lists.length === WEEKDAYS_COUNT
          ? item.pre_lists.map((list: PlaylistItem[]) => list.map((f: PlaylistItem) => ({ ...f })))
          : Array(WEEKDAYS_COUNT)
              .fill(null)
              .map(() => []),
    }));
    if (collection.length === 0) {
      const defaultPlaylist = normalizePlaylistItem({ name: DEFAULT_PLAYLIST_NAME });
      collection = [defaultPlaylist];
      activePlaylistId.value = defaultPlaylist.id;
    }
    let index = collection.findIndex(item => item.id === activePlaylistId.value);
    if (index === -1) {
      index = 0;
      activePlaylistId.value = collection[0].id;
    }
    const currentItem = collection[index];
    const itemToMutate = {
      ...currentItem,
      playlist: currentItem.playlist.map((f: PlaylistItem) => ({ ...f })),
      pre_lists:
        Array.isArray(currentItem.pre_lists) && currentItem.pre_lists.length === WEEKDAYS_COUNT
          ? currentItem.pre_lists.map((list: PlaylistItem[]) => [...list.map((f: PlaylistItem) => ({ ...f }))])
          : Array(WEEKDAYS_COUNT)
              .fill(null)
              .map(() => []),
    };
    const updatedItem = mutator(itemToMutate) || itemToMutate;

    const preservedPreLists =
      updatedItem.pre_lists &&
      Array.isArray(updatedItem.pre_lists) &&
      updatedItem.pre_lists.length === WEEKDAYS_COUNT
        ? updatedItem.pre_lists.map((list: PlaylistItem[]) =>
            Array.isArray(list) ? list.map((f: PlaylistItem) => ({ ...f })) : []
          )
        : Array.isArray(currentItem.pre_lists) && currentItem.pre_lists.length === WEEKDAYS_COUNT
          ? currentItem.pre_lists.map((list: PlaylistItem[]) => list.map((f: PlaylistItem) => ({ ...f })))
          : Array(WEEKDAYS_COUNT)
              .fill(null)
              .map(() => []);

    const normalizedItem = normalizePlaylistItem(updatedItem, currentItem.name);
    normalizedItem.pre_lists = preservedPreLists;
    collection[index] = normalizedItem;
    playlistCollection.value = collection;

    await updateSinglePlaylist(collection[index]);
    syncActivePlaylist(collection);
    return playlistStatus.value;
  };

  // 加载播放列表
  const loadPlaylist = async () => {
    try {
      const response = await playlistAction("get", "GET", {});
      if (response.code !== 0) {
        throw new Error(response.msg || "获取播放列表失败");
      }

      const parsed = transformApiDataToPlaylistFormat(response.data);
      const normalized = normalizePlaylistCollection(parsed);
      playlistCollection.value = normalized.playlists;

      const savedPlaylistId = localStorage.getItem("active_playlist_id");
      if (savedPlaylistId && normalized.playlists.some((p: Playlist) => p.id === savedPlaylistId)) {
        activePlaylistId.value = savedPlaylistId;
      } else {
        activePlaylistId.value = normalized.activePlaylistId;
      }

      syncActivePlaylist(normalized.playlists);
      return normalized;
    } catch (error) {
      logger.error("从接口加载播放列表失败:", error);
      const fallback = normalizePlaylistCollection(null);
      playlistCollection.value = fallback.playlists;

      const savedPlaylistId = localStorage.getItem("active_playlist_id");
      if (savedPlaylistId && fallback.playlists.some((p: Playlist) => p.id === savedPlaylistId)) {
        activePlaylistId.value = savedPlaylistId;
      } else {
        activePlaylistId.value = fallback.activePlaylistId;
      }

      syncActivePlaylist(fallback.playlists);
      return fallback;
    }
  };

  // 刷新播放列表状态
  const refreshPlaylistStatus = async (onlyCurrent = false, isAutoRefresh = false) => {
    try {
      // 如果正在编辑设备配置（pendingDeviceType 不为 null），且是自动刷新，则跳过刷新，避免覆盖未保存的更改
      if (isAutoRefresh && pendingDeviceType.value !== null) {
        return;
      }
      // 如果是自动刷新，且处于拖拽排序模式，则跳过（避免覆盖拖拽结果）
      if (isAutoRefresh && (preFilesDragMode.value || filesDragMode.value)) {
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

        const parsed = transformApiDataToPlaylistFormat(response.data);
        if (!parsed || !parsed.playlists || parsed.playlists.length === 0) {
          return;
        }

        const updatedPlaylist = parsed.playlists[0];

        const collection = playlistCollection.value.map(item => {
          if (item.id === activeId) {
            return {
              ...item,
              ...updatedPlaylist,
              playlist: updatedPlaylist.playlist || item.playlist,
              pre_lists:
                updatedPlaylist.pre_lists &&
                Array.isArray(updatedPlaylist.pre_lists) &&
                updatedPlaylist.pre_lists.length === WEEKDAYS_COUNT
                  ? updatedPlaylist.pre_lists.map((list: PlaylistItem[]) => [...(list || [])])
                  : item.pre_lists,
              current_index:
                updatedPlaylist.current_index !== undefined
                  ? updatedPlaylist.current_index
                  : item.current_index,
              isPlaying:
                updatedPlaylist?.isPlaying === true || updatedPlaylist?.isPlaying === 1 || false,
            };
          }
          return item;
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
