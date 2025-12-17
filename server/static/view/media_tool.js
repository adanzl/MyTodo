import { getApiUrl } from "../js/net_util.js";
import { formatSize } from "../js/utils.js";
import { createFileDialog } from "./file_dialog.js";
const axios = window.axios;

const { ref, onMounted } = window.Vue;
const { ElMessage, ElMessageBox } = window.ElementPlus;
let component = null;

async function loadTemplate() {
  const response = await fetch(`./view/media_tool-template.html?t=${Date.now()}`);
  return await response.text();
}

async function createComponent() {
  if (component) return component;
  const template = await loadTemplate();
  
  // 加载文件对话框组件
  const FileDialog = await createFileDialog();
  
  component = {
    components: {
      FileDialog,
    },
    setup() {
      const loading = ref(false);
      const activeTab = ref('audio_merge');
      const taskList = ref([]);
      const currentTask = ref(null);
      
      // 文件浏览器对话框可见性
      const fileBrowserDialogVisible = ref(false);
      
      // 处理文件选择确认
      const handleFileBrowserConfirm = async (filePaths) => {
        if (!currentTask.value) {
          return;
        }
        
        if (filePaths.length === 0) {
          return;
        }
        
        try {
          loading.value = true;
          // 批量添加文件
          for (const filePath of filePaths) {
            const response = await axios.post(`${getApiUrl()}/media/task/addFileByPath`, {
              task_id: currentTask.value.task_id,
              file_path: filePath
            });
            
            if (response.data.code !== 0) {
              ElMessage.error(`添加文件失败: ${response.data.msg || "未知错误"}`);
              break;
            }
          }
          
          ElMessage.success(`成功添加 ${filePaths.length} 个文件`);
          // 刷新任务信息
          await handleViewTask(currentTask.value.task_id);
        } catch (error) {
          console.error("添加文件失败:", error);
          ElMessage.error("添加文件失败: " + (error.message || "未知错误"));
        } finally {
          loading.value = false;
        }
      };

      // 加载任务列表
      const loadTaskList = async () => {
        try {
          loading.value = true;
          const response = await axios.get(`${getApiUrl()}/media/task/list`);
          if (response.data.code === 0) {
            taskList.value = response.data.data.tasks || [];
            // 如果有任务列表且当前没有选中任务，默认选择第一个任务
            if (taskList.value.length > 0 && !currentTask.value) {
              await handleViewTask(taskList.value[0].task_id);
            }
          } else {
            ElMessage.error(response.data.msg || "获取任务列表失败");
          }
        } catch (error) {
          console.error("获取任务列表失败:", error);
          ElMessage.error("获取任务列表失败: " + (error.message || "未知错误"));
        } finally {
          loading.value = false;
        }
      };

      // 创建任务
      const handleCreateTask = async () => {
        try {
          loading.value = true;
          const response = await axios.post(`${getApiUrl()}/media/task/create`, {});

          if (response.data.code === 0) {
            ElMessage.success("任务创建成功");
            await loadTaskList();
            // 打开任务详情
            handleViewTask(response.data.data.task_id);
          } else {
            ElMessage.error(response.data.msg || "创建任务失败");
          }
        } catch (error) {
          console.error("创建任务失败:", error);
          ElMessage.error("创建任务失败: " + (error.message || "未知错误"));
        } finally {
          loading.value = false;
        }
      };

      // 查看任务
      const handleViewTask = async (taskId) => {
        try {
          loading.value = true;
          const response = await axios.post(`${getApiUrl()}/media/task/get`, {
            task_id: taskId
          });
          if (response.data.code === 0) {
            currentTask.value = response.data.data;
          } else {
            ElMessage.error(response.data.msg || "获取任务信息失败");
          }
        } catch (error) {
          console.error("获取任务信息失败:", error);
          ElMessage.error("获取任务信息失败: " + (error.message || "未知错误"));
        } finally {
          loading.value = false;
        }
      };

      // 删除任务
      const handleDeleteTask = async (taskId) => {
        const confirmed = await ElMessageBox.confirm(
          "确定要删除该任务吗？",
          "提示",
          {
            confirmButtonText: "确定",
            cancelButtonText: "取消",
            type: "warning",
          }
        ).catch(() => false);

        if (!confirmed) return;

        try {
          loading.value = true;
          const response = await axios.post(`${getApiUrl()}/media/task/delete`, {
            task_id: taskId
          });
          if (response.data.code === 0) {
            ElMessage.success("任务删除成功");
            await loadTaskList();
            if (currentTask.value && currentTask.value.task_id === taskId) {
              currentTask.value = null;
            }
          } else {
            ElMessage.error(response.data.msg || "删除任务失败");
          }
        } catch (error) {
          console.error("删除任务失败:", error);
          ElMessage.error("删除任务失败: " + (error.message || "未知错误"));
        } finally {
          loading.value = false;
        }
      };

      // 打开文件浏览器
      const handleOpenFileBrowser = () => {
        if (!currentTask.value) {
          ElMessage.warning("请先创建或选择任务");
          return;
        }
        fileBrowserDialogVisible.value = true;
      };

      // 移除文件
      const handleRemoveFile = async (fileIndex) => {
        if (!currentTask.value) {
          return;
        }

        const confirmed = await ElMessageBox.confirm(
          "确定要删除该文件吗？",
          "提示",
          {
            confirmButtonText: "确定",
            cancelButtonText: "取消",
            type: "warning",
          }
        ).catch(() => false);

        if (!confirmed) return;

        try {
          loading.value = true;
          const response = await axios.post(
            `${getApiUrl()}/media/task/deleteFile`,
            {
              task_id: currentTask.value.task_id,
              file_index: fileIndex
            }
          );
          if (response.data.code === 0) {
            ElMessage.success("文件删除成功");
            // 刷新任务信息
            await handleViewTask(currentTask.value.task_id);
          } else {
            ElMessage.error(response.data.msg || "删除文件失败");
          }
        } catch (error) {
          console.error("删除文件失败:", error);
          ElMessage.error("删除文件失败: " + (error.message || "未知错误"));
        } finally {
          loading.value = false;
        }
      };

      // 开始合成
      const handleStartMerge = async () => {
        if (!currentTask.value) {
          return;
        }

        const confirmed = await ElMessageBox.confirm(
          `确定要开始合成吗？将合并 ${currentTask.value.files.length} 个音频文件。`,
          "确认合成",
          {
            confirmButtonText: "确定",
            cancelButtonText: "取消",
            type: "warning",
          }
        ).catch(() => false);

        if (!confirmed) return;

        try {
          loading.value = true;
          const response = await axios.post(
            `${getApiUrl()}/media/task/start`,
            {
              task_id: currentTask.value.task_id
            }
          );
          if (response.data.code === 0) {
            ElMessage.success("合成任务已启动");
            // 刷新任务信息
            await handleViewTask(currentTask.value.task_id);
            // 开始轮询任务状态
            startPollingTaskStatus();
          } else {
            ElMessage.error(response.data.msg || "启动任务失败");
          }
        } catch (error) {
          console.error("启动任务失败:", error);
          ElMessage.error("启动任务失败: " + (error.message || "未知错误"));
        } finally {
          loading.value = false;
        }
      };

      // 轮询任务状态
      let pollingTimer = null;
      const startPollingTaskStatus = () => {
        if (pollingTimer) {
          clearInterval(pollingTimer);
        }
        pollingTimer = setInterval(async () => {
          if (!currentTask.value || currentTask.value.status !== 'processing') {
            if (pollingTimer) {
              clearInterval(pollingTimer);
              pollingTimer = null;
            }
            return;
          }
          await handleViewTask(currentTask.value.task_id);
        }, 2000); // 每2秒轮询一次
      };

      // 下载结果
      const handleDownloadResult = () => {
        if (!currentTask.value || !currentTask.value.result_file) {
          return;
        }
        const url = `${getApiUrl()}/media/task/download?task_id=${currentTask.value.task_id}`;
        window.open(url, '_blank');
      };

      // 从任务列表下载结果
      const handleDownloadResultFromList = (task) => {
        if (!task || !task.result_file) {
          return;
        }
        const url = `${getApiUrl()}/media/task/download?task_id=${task.task_id}`;
        window.open(url, '_blank');
      };

      // 格式化文件大小
      const formatFileSize = (bytes) => {
        if (!bytes) return '-';
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
      };

      // 获取状态标签类型
      const getStatusTagType = (status) => {
        const statusMap = {
          'pending': 'info',
          'processing': 'warning',
          'success': 'success',
          'failed': 'danger'
        };
        return statusMap[status] || 'info';
      };

      // 获取状态文本
      const getStatusText = (status) => {
        const statusMap = {
          'pending': '等待中',
          'processing': '处理中',
          'success': '成功',
          'failed': '失败'
        };
        return statusMap[status] || '未知';
      };

      onMounted(() => {
        loadTaskList();
      });

      return {
        loading,
        activeTab,
        taskList,
        currentTask,
        loadTaskList,
        handleCreateTask,
        handleViewTask,
        handleDeleteTask,
        handleOpenFileBrowser,
        handleRemoveFile,
        handleStartMerge,
        handleDownloadResult,
        handleDownloadResultFromList,
        formatFileSize,
        formatSize,
        getStatusTagType,
        getStatusText,
        // 文件浏览器
        fileBrowserDialogVisible,
        handleFileBrowserConfirm,
        handleCloseFileBrowser: () => {
          fileBrowserDialogVisible.value = false;
        },
      };
    },
    template,
  };
  return component;
}

export default createComponent();
