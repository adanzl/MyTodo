/**
 * 播放列表状态管理 Composable
 * 管理所有播放列表相关的状态变量
 */
import { ref } from "vue";

export function usePlaylistState() {
  const refData = {
    // 播放列表数据
    playlistCollection: ref<any[]>([]),
    activePlaylistId: ref<string>(""),
    playlistStatus: ref<any>(null),
    playlistLoading: ref(false),
    playlistRefreshing: ref(false),

    // 播放控制
    playing: ref(false),
    stopping: ref(false),
    showMoreActions: ref(false),

    // 编辑相关
    editingPlaylistId: ref<string | null>(null),
    editingPlaylistName: ref(""),

    // 文件浏览器
    fileBrowserDialogVisible: ref(false),
    fileBrowserTarget: ref<"files" | "pre_files">("files"),
    replaceFileInfo: ref<{ type: "pre_files" | "files"; index: number } | null>(null),

    // 星期选择
    selectedWeekdayIndex: ref<number | null>(null),

    // 拖拽模式
    preFilesDragMode: ref(false),
    filesDragMode: ref(false),

    // 批量删除模式
    preFilesBatchDeleteMode: ref(false),
    filesBatchDeleteMode: ref(false),
    selectedPreFileIndices: ref<number[]>([]),
    selectedFileIndices: ref<number[]>([]),

    // 前置文件展开/折叠
    preFilesExpanded: ref(false),

    // 播放列表选择器
    playlistSelectorVisible: ref(false),
    playlistSelectorSelectedFiles: ref<any[]>([]),

    // 批量抽屉
    batchDrawerVisible: ref(false),

    // Cron 相关
    cronBuilderVisible: ref(false),
    cronPreviewVisible: ref(false),
    cronPreviewTimes: ref<string[]>([]),
    initialCronExpr: ref(""),

    // 设备相关
    agentListDialogVisible: ref(false),
    scanDialogVisible: ref(false),
    loading: ref(false),
    deviceList: ref<any[]>([]),
    connectedDeviceList: ref<any[]>([]),
    dlnaDeviceList: ref<any[]>([]),
    dlnaScanning: ref(false),
    miDeviceList: ref<any[]>([]),
    miScanning: ref(false),
    pendingDeviceType: ref<string | null>(null),

    // 排序相关
    preFilesSortOrder: ref<string | null>(null),
    filesSortOrder: ref<string | null>(null),
    preFilesOriginalOrder: ref<any[] | null>(null),
    filesOriginalOrder: ref<any[] | null>(null),
  };

  return {
    ...refData,
  };
}
