/**
 * 文件对话框组件
 * 可复用的文件选择对话框
 */
import { getApiUrl } from "../js/net_util.js";
import { formatSize } from "../js/utils.js";

const axios = window.axios;
const { ref, watch, computed } = window.Vue;
const { ElMessage } = window.ElementPlus;

/**
 * 创建文件浏览器状态和方法
 * @param {Object} options - 配置选项
 * @param {string} options.defaultPath - 默认路径，默认为 "/mnt/ext_base"
 * @param {string} options.extensions - 文件扩展名过滤，默认为 "audio"
 * @param {Function} options.onFilesSelected - 文件选择回调函数，接收选中的文件路径数组
 * @returns {Object} 包含状态和方法的对象
 */
function createFileBrowser(options = {}) {
  const {
    defaultPath = "/mnt/ext_base",
    extensions = "audio",
    onFilesSelected = null,
  } = options;

  // 状态
  const fileBrowserDialogVisible = ref(false);
  const fileBrowserPath = ref(defaultPath);
  const fileBrowserList = ref([]);
  const fileBrowserLoading = ref(false);
  const selectedFiles = ref([]);
  let lastFileBrowserPath = defaultPath;

  // 更新是否可以向上导航
  const fileBrowserCanNavigateUp = ref(false);
  const updateFileBrowserCanNavigateUp = () => {
    const path = fileBrowserPath.value;
    fileBrowserCanNavigateUp.value = path && path !== "/mnt/ext_base" && path !== "/";
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
      console.error("获取文件列表失败:", error);
      ElMessage.error("获取文件列表失败: " + (error.message || "未知错误"));
    } finally {
      fileBrowserLoading.value = false;
    }
  };

  // 向上导航
  const navigateUp = () => {
    const path = fileBrowserPath.value;
    if (path && path !== "/mnt/ext_base" && path !== "/") {
      const parts = String(path).split("/").filter((p) => p);
      parts.pop();
      fileBrowserPath.value =
        parts.length > 0 ? "/" + parts.join("/") : "/mnt/ext_base";
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
  const handleRowClick = (row) => {
    if (row.isDirectory) {
      const newPath =
        fileBrowserPath.value === "/"
          ? `/${row.name}`
          : `${fileBrowserPath.value}/${row.name}`;
      fileBrowserPath.value = newPath;
      updateFileBrowserCanNavigateUp();
      refreshFileBrowser();
    } else {
      toggleFileSelection(row);
    }
  };

  // 切换文件选择状态
  const toggleFileSelection = (row) => {
    if (row.isDirectory) return;
    const filePath =
      fileBrowserPath.value === "/"
        ? `/${row.name}`
        : `${fileBrowserPath.value}/${row.name}`;
    const index = selectedFiles.value.indexOf(filePath);
    if (index > -1) {
      selectedFiles.value.splice(index, 1);
    } else {
      selectedFiles.value.push(filePath);
    }
  };

  // 检查文件是否被选中
  const isFileSelected = (row) => {
    if (row.isDirectory) return false;
    const filePath =
      fileBrowserPath.value === "/"
        ? `/${row.name}`
        : `${fileBrowserPath.value}/${row.name}`;
    return selectedFiles.value.includes(filePath);
  };

  // 全选当前目录下的所有文件
  const selectAllFiles = () => {
    const currentPath = fileBrowserPath.value;
    fileBrowserList.value.forEach((row) => {
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
      .filter((row) => !row.isDirectory)
      .map((row) => {
        return currentPath === "/" ? `/${row.name}` : `${currentPath}/${row.name}`;
      });

    // 只移除当前目录下的文件，保留其他目录的文件
    selectedFiles.value = selectedFiles.value.filter((filePath) => {
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
    // 状态
    fileBrowserDialogVisible,
    fileBrowserPath,
    fileBrowserList,
    fileBrowserLoading,
    selectedFiles,
    fileBrowserCanNavigateUp,
    
    // 方法
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

// 导出 createFileBrowser 函数，以便需要时可以直接使用
export { createFileBrowser };

async function loadTemplate() {
  const response = await fetch(`./view/common/file_dialog-template.html?t=${Date.now()}`);
  return await response.text();
}

export async function createFileDialog() {
  const template = await loadTemplate();
  
  return {
    props: {
      visible: {
        type: Boolean,
        default: false,
      },
      title: {
        type: String,
        default: "选择文件",
      },
      defaultPath: {
        type: String,
        default: "/mnt/ext_base",
      },
      extensions: {
        type: String,
        default: "audio",
      },
      confirmButtonText: {
        type: String,
        default: "确定",
      },
      confirmLoading: {
        type: Boolean,
        default: false,
      },
      mode: {
        type: String,
        default: "file", // "file" 或 "directory"
      },
    },
    emits: ["update:visible", "confirm", "close"],
    setup(props, { emit }) {
      // 创建文件浏览器实例
      const fileBrowser = createFileBrowser({
        defaultPath: props.defaultPath,
        extensions: props.extensions,
        onFilesSelected: (filePaths) => {
          emit("confirm", filePaths);
        },
      });

      // 监听 visible 变化，同步到文件浏览器
      watch(
        () => props.visible,
        (newVal) => {
          if (newVal) {
            fileBrowser.openFileBrowser();
          } else {
            fileBrowser.closeFileBrowser();
          }
        }
      );

      watch(
        () => fileBrowser.fileBrowserDialogVisible.value,
        (newVal) => {
          if (newVal !== props.visible) {
            emit("update:visible", newVal);
          }
        }
      );

      // 处理确认
      const handleConfirm = () => {
        // 获取 mode 值
        const modeValue = props.mode;
        const modeStr = String(modeValue || 'file').toLowerCase().trim();
        
        if (modeStr === "directory") {
          // 目录模式：传递当前路径
          const currentPath = fileBrowser.fileBrowserPath.value || props.defaultPath || '/mnt/ext_base';
          if (!currentPath || String(currentPath).trim() === '') {
            ElMessage.warning("请先选择一个目录");
            return;
          }
          emit("confirm", [String(currentPath)]);
        } else {
          // 文件模式：传递选中的文件
          fileBrowser.confirmSelection();
        }
      };

      // 处理关闭
      const handleClose = () => {
        fileBrowser.closeFileBrowser();
        emit("close");
      };

      // 计算按钮是否禁用
      const isConfirmDisabled = computed(() => {
        const modeValue = String(props.mode || 'file').toLowerCase().trim();
        // 目录模式下，按钮始终可用
        if (modeValue === 'directory') {
          return false;
        }
        // 文件模式下，没有选中文件时禁用
        return fileBrowser.selectedFiles.value.length === 0;
      });

      return {
        fileBrowser,
        formatSize,
        handleConfirm,
        handleClose,
        // 暴露文件浏览器的状态和方法
        fileBrowserPath: fileBrowser.fileBrowserPath,
        fileBrowserList: fileBrowser.fileBrowserList,
        fileBrowserLoading: fileBrowser.fileBrowserLoading,
        selectedFiles: fileBrowser.selectedFiles,
        fileBrowserCanNavigateUp: fileBrowser.fileBrowserCanNavigateUp,
        handleRefresh: fileBrowser.refreshFileBrowser,
        handleNavigateUp: fileBrowser.navigateUp,
        handleGoToHome: fileBrowser.goToHome,
        handleSelectAll: fileBrowser.selectAllFiles,
        handleDeselectAll: fileBrowser.deselectAllFiles,
        handleRowClick: fileBrowser.handleRowClick,
        handleToggleSelection: fileBrowser.toggleFileSelection,
        isFileSelected: fileBrowser.isFileSelected,
        mode: props.mode,
        isConfirmDisabled,
      };
    },
    template,
  };
}
