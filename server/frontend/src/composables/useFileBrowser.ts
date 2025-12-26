/**
 * 文件浏览器 Composable
 * 提供文件浏览和选择功能
 */
import { ref, type Ref } from "vue";
import { ElMessage } from "element-plus";
import axios from "axios";
import { getApiUrl } from "@/api/config";
import { logAndNoticeError } from "@/utils";

export interface FileBrowserOptions {
  defaultPath?: string;
  extensions?: string;
  onFilesSelected?: (filePaths: string[]) => void;
}

export interface FileBrowserItem {
  name: string;
  size?: number;
  isDirectory: boolean;
}

export interface UseFileBrowserReturn {
  fileBrowserDialogVisible: Ref<boolean>;
  fileBrowserPath: Ref<string>;
  fileBrowserList: Ref<FileBrowserItem[]>;
  fileBrowserLoading: Ref<boolean>;
  selectedFiles: Ref<string[]>;
  fileBrowserCanNavigateUp: Ref<boolean>;
  openFileBrowser: () => void;
  closeFileBrowser: () => void;
  refreshFileBrowser: () => Promise<void>;
  navigateUp: () => void;
  goToHome: () => void;
  handleRowClick: (row: FileBrowserItem) => void;
  toggleFileSelection: (row: FileBrowserItem) => void;
  isFileSelected: (row: FileBrowserItem) => boolean;
  selectAllFiles: () => void;
  deselectAllFiles: () => void;
  confirmSelection: () => void;
}

/**
 * 创建文件浏览器状态和方法
 */
export function useFileBrowser(options: FileBrowserOptions = {}): UseFileBrowserReturn {
  const { defaultPath = "/mnt/ext_base", extensions = "audio", onFilesSelected = null } = options;

  // 状态
  const fileBrowserDialogVisible = ref(false);
  const fileBrowserPath = ref(defaultPath);
  const fileBrowserList = ref<FileBrowserItem[]>([]);
  const fileBrowserLoading = ref(false);
  const selectedFiles = ref<string[]>([]);
  let lastFileBrowserPath = defaultPath;

  // 更新是否可以向上导航
  const fileBrowserCanNavigateUp = ref(false);
  const updateFileBrowserCanNavigateUp = () => {
    const path = fileBrowserPath.value;
    fileBrowserCanNavigateUp.value = !!(path && path !== "/mnt/ext_base" && path !== "/");
  };

  // 打开文件浏览器
  const openFileBrowser = () => {
    fileBrowserDialogVisible.value = true;
    fileBrowserPath.value = lastFileBrowserPath;
    selectedFiles.value = [];
    refreshFileBrowser();
  };

  // 关闭文件浏览器
  const closeFileBrowser = () => {
    fileBrowserDialogVisible.value = false;
    selectedFiles.value = [];
  };

  // 刷新文件浏览器
  const refreshFileBrowser = async () => {
    try {
      fileBrowserLoading.value = true;
      const path = fileBrowserPath.value || defaultPath;
      const rsp = await axios.get(getApiUrl() + "/listDirectory", {
        params: { path: path, extensions: extensions },
      });
      if (rsp.data.code === 0) {
        fileBrowserList.value = rsp.data.data || [];
        updateFileBrowserCanNavigateUp();
      } else {
        ElMessage.error(rsp.data.msg || "获取文件列表失败");
      }
    } catch (error) {
      logAndNoticeError(error as Error, "获取文件列表失败");
    } finally {
      fileBrowserLoading.value = false;
    }
  };

  // 向上导航
  const navigateUp = () => {
    const path = fileBrowserPath.value;
    if (path && path !== "/mnt/ext_base" && path !== "/") {
      const parts = String(path)
        .split("/")
        .filter(p => p);
      parts.pop();
      fileBrowserPath.value = parts.length > 0 ? "/" + parts.join("/") : "/mnt/ext_base";
      updateFileBrowserCanNavigateUp();
      refreshFileBrowser();
    }
  };

  // 回到首页
  const goToHome = () => {
    fileBrowserPath.value = defaultPath;
    updateFileBrowserCanNavigateUp();
    refreshFileBrowser();
  };

  // 行点击处理
  const handleRowClick = (row: FileBrowserItem) => {
    if (row.isDirectory) {
      const newPath =
        fileBrowserPath.value === "/" ? `/${row.name}` : `${fileBrowserPath.value}/${row.name}`;
      fileBrowserPath.value = newPath;
      updateFileBrowserCanNavigateUp();
      refreshFileBrowser();
    } else {
      toggleFileSelection(row);
    }
  };

  // 切换文件选择状态
  const toggleFileSelection = (row: FileBrowserItem) => {
    if (row.isDirectory) return;
    const filePath =
      fileBrowserPath.value === "/" ? `/${row.name}` : `${fileBrowserPath.value}/${row.name}`;
    const index = selectedFiles.value.indexOf(filePath);
    if (index > -1) {
      selectedFiles.value.splice(index, 1);
    } else {
      selectedFiles.value.push(filePath);
    }
  };

  // 检查文件是否被选中
  const isFileSelected = (row: FileBrowserItem): boolean => {
    if (row.isDirectory) return false;
    const filePath =
      fileBrowserPath.value === "/" ? `/${row.name}` : `${fileBrowserPath.value}/${row.name}`;
    return selectedFiles.value.includes(filePath);
  };

  // 全选当前目录下的所有文件
  const selectAllFiles = () => {
    const currentPath = fileBrowserPath.value;
    fileBrowserList.value.forEach(row => {
      if (!row.isDirectory) {
        const filePath = currentPath === "/" ? `/${row.name}` : `${currentPath}/${row.name}`;
        if (!selectedFiles.value.includes(filePath)) {
          selectedFiles.value.push(filePath);
        }
      }
    });
  };

  // 取消全选当前目录下的所有文件
  const deselectAllFiles = () => {
    const currentPath = fileBrowserPath.value;
    const currentFiles = fileBrowserList.value
      .filter(row => !row.isDirectory)
      .map(row => {
        return currentPath === "/" ? `/${row.name}` : `${currentPath}/${row.name}`;
      });

    // 只移除当前目录下的文件，保留其他目录的文件
    selectedFiles.value = selectedFiles.value.filter(filePath => {
      return !currentFiles.includes(filePath);
    });
  };

  // 确认选择文件
  const confirmSelection = () => {
    if (selectedFiles.value.length === 0) {
      ElMessage.warning("请先选择要添加的文件");
      return;
    }

    if (onFilesSelected && typeof onFilesSelected === "function") {
      onFilesSelected([...selectedFiles.value]);
    }

    lastFileBrowserPath = fileBrowserPath.value;
    closeFileBrowser();
  };

  return {
    fileBrowserDialogVisible,
    fileBrowserPath,
    fileBrowserList,
    fileBrowserLoading,
    selectedFiles,
    fileBrowserCanNavigateUp,
    openFileBrowser,
    closeFileBrowser,
    refreshFileBrowser,
    navigateUp,
    goToHome,
    handleRowClick,
    toggleFileSelection,
    isFileSelected,
    selectAllFiles,
    deselectAllFiles,
    confirmSelection,
  };
}
