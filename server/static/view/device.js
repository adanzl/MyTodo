import { bluetoothAction } from "../js/net_util.js";

const { ref, onMounted } = window.Vue;
const { ElMessage } = window.ElementPlus;
let component = null;
async function loadTemplate() {
  const timestamp = `?t=${Date.now()}`;
  const response = await fetch(`./view/device-template.html${timestamp}`);
  return await response.text(); // 获取模板内容
}
async function createComponent() {
  if (component) return component;
  const template = await loadTemplate();
  component = {
    setup() {
      const refData = {
        dialogForm: ref({
          visible: false,
          data: null,
          value: 0,
        }),
        scanDialogVisible: ref(false),
        directoryDialogVisible: ref(false),
        selectedPath: ref(""),
        currentPath: ref("/mnt"),
        directoryList: ref([]),
        directoryLoading: ref(false),
        loading: ref(false),
        deviceList: ref([]),
        connectedDeviceList: ref([]),
      };

      // 刷新已连接设备列表
      const refreshConnectedList = async () => {
        try {
          refData.loading.value = true;
          const rsp = await bluetoothAction("connected", "GET");
          if (rsp.code === 0) {
            refData.connectedDeviceList.value = rsp.data || [];
          } else {
            ElMessage.error(rsp.msg || "获取已连接设备失败");
          }
        } catch (error) {
          console.error("获取已连接设备失败:", error);
          ElMessage.error("获取已连接设备失败");
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

      // 断开设备
      const handleDisconnectDevice = async (device) => {
        try {
          device.disconnecting = true;
          const rsp = await bluetoothAction("disconnect", "POST", {
            address: device.address,
          });
          if (rsp.code === 0) {
            ElMessage.success(`已断开设备: ${device.name}`);
            // 刷新已连接设备列表
            await refreshConnectedList();
          } else {
            ElMessage.error(rsp.msg || "断开失败");
          }
        } catch (error) {
          console.error("断开设备失败:", error);
          ElMessage.error("断开设备失败");
        } finally {
          device.disconnecting = false;
        }
      };

      // 扫描设备
      const handleUpdateDeviceList = async () => {
        try {
          refData.loading.value = true;
          const rsp = await bluetoothAction("scan", "GET");
          if (rsp.code === 0) {
            refData.deviceList.value = (rsp.data || []).map(device => ({
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

      // 打开扫描弹窗
      const handleOpenScanDialog = () => {
        refData.scanDialogVisible.value = true;
        // 打开弹窗时自动扫描
        handleUpdateDeviceList();
      };

      // 关闭扫描弹窗
      const handleCloseScanDialog = () => {
        refData.scanDialogVisible.value = false;
      };

      // 打开目录选择弹窗
      const handleOpenDirectoryDialog = () => {
        refData.directoryDialogVisible.value = true;
        // 如果没有已选择的路径，使用默认路径 /mnt
        refData.currentPath.value = refData.selectedPath.value || "/mnt";
        handleRefreshDirectory();
      };

      // 关闭目录选择弹窗
      const handleCloseDirectoryDialog = () => {
        refData.directoryDialogVisible.value = false;
      };

      // 刷新目录列表
      const handleRefreshDirectory = async () => {
        try {
          refData.directoryLoading.value = true;
          const path = refData.currentPath.value || "/mnt";
          const rsp = await bluetoothAction("listDirectory", "GET", {
            path: path,
          });
          if (rsp.code === 0) {
            refData.directoryList.value = rsp.data || [];
            // 更新当前路径（后端可能返回实际使用的路径）
            if (rsp.currentPath) {
              refData.currentPath.value = rsp.currentPath;
            }
            updateCanNavigateUp();
          } else {
            ElMessage.error(rsp.msg || "获取目录列表失败");
            // 如果失败，尝试重置到默认路径
            if (refData.currentPath.value && refData.currentPath.value !== "/mnt") {
              refData.currentPath.value = "/mnt";
              // 不自动重试，让用户手动刷新
            }
          }
        } catch (error) {
          console.error("获取目录列表失败:", error);
          ElMessage.error("获取目录列表失败: " + (error.message || "未知错误"));
        } finally {
          refData.directoryLoading.value = false;
        }
      };

      // 导航到上一级
      const handleNavigateUp = () => {
        const path = refData.currentPath.value;
        if (path && path !== "/mnt" && path !== "/") {
          const parts = path.split("/").filter(p => p);
          parts.pop();
          refData.currentPath.value = parts.length > 0 ? "/" + parts.join("/") : "/mnt";
          updateCanNavigateUp();
          handleRefreshDirectory();
        }
      };

      // 导航到首页（默认目录）
      const handleGoToHome = () => {
        refData.currentPath.value = "/mnt";
        updateCanNavigateUp();
        handleRefreshDirectory();
      };

      // 点击目录行
      const handleDirectoryRowClick = (row) => {
        if (row.isDirectory) {
          const newPath = refData.currentPath.value === "/" 
            ? `/${row.name}` 
            : `${refData.currentPath.value}/${row.name}`;
          refData.currentPath.value = newPath;
          updateCanNavigateUp();
          handleRefreshDirectory();
        }
      };

      // 选择目录
      const handleSelectDirectory = (row) => {
        const selectedPath = refData.currentPath.value === "/" 
          ? `/${row.name}` 
          : `${refData.currentPath.value}/${row.name}`;
        refData.selectedPath.value = selectedPath;
        handleCloseDirectoryDialog();
        ElMessage.success(`已选择目录: ${selectedPath}`);
      };

      // 格式化文件大小
      const formatSize = (bytes) => {
        if (!bytes) return "0 B";
        const k = 1024;
        const sizes = ["B", "KB", "MB", "GB"];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + " " + sizes[i];
      };

      // 计算是否可以导航到上一级（使用 computed）
      const canNavigateUp = ref(false);
      const updateCanNavigateUp = () => {
        const path = refData.currentPath.value;
        canNavigateUp.value = path && path !== "/mnt" && path !== "/";
      };

      const refMethods = {
        handleUpdateDeviceList,
        handleOpenScanDialog,
        handleCloseScanDialog,
        handleOpenDirectoryDialog,
        handleCloseDirectoryDialog,
        handleRefreshDirectory,
        handleNavigateUp,
        handleGoToHome,
        handleDirectoryRowClick,
        handleSelectDirectory,
        formatSize,
        handleConnectDevice,
        handleDisconnectDevice,
        refreshConnectedList,
        handleDialogClose: () => {
          refData.dialogForm.value.visible = false;
          refData.dialogForm.value.value = 0;
        },
      };
      
      // 初始化 canNavigateUp
      updateCanNavigateUp();
      onMounted(async () => {
        await refreshConnectedList();
      });
      return {
        ...refData,
        canNavigateUp,
        ...refMethods,
      };
    },
    template,
  };
  return component;
}
export default createComponent();
