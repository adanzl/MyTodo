import { getApiUrl } from "../js/net_util.js";
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
  
  component = {
    setup() {
      const loading = ref(false);
      const activeTab = ref('audio_merge');
      const taskList = ref([]);
      const taskDialogVisible = ref(false);
      const currentTask = ref(null);
      const uploadFile = ref(null);

      // 加载任务列表
      const loadTaskList = async () => {
        try {
          loading.value = true;
          const response = await axios.get(`${getApiUrl()}/media/task/list`);
          if (response.data.code === 0) {
            taskList.value = response.data.data.tasks || [];
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
          const { value } = await ElMessageBox.prompt(
            "请输入任务名称",
            "新建任务",
            {
              confirmButtonText: "确定",
              cancelButtonText: "取消",
              inputPlaceholder: "任务名称",
            }
          ).catch(() => {
            return { value: null };
          });

          if (!value || !value.trim()) {
            return;
          }

          loading.value = true;
          const response = await axios.post(`${getApiUrl()}/media/task/create`, {
            name: value.trim()
          });

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
            taskDialogVisible.value = true;
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
              taskDialogVisible.value = false;
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

      // 处理文件选择
      const handleFileChange = async (file) => {
        if (!currentTask.value) {
          ElMessage.warning("请先创建或选择任务");
          return;
        }

        uploadFile.value = file.raw;
        await handleUploadFile();
      };

      // 上传文件
      const handleUploadFile = async () => {
        if (!uploadFile.value || !currentTask.value) {
          return;
        }

        const file = uploadFile.value;
        const allowedExtensions = ['.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg', '.wma'];
        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (!allowedExtensions.includes(ext)) {
          ElMessage.error(`不支持的文件类型，支持的格式: ${allowedExtensions.join(', ')}`);
          uploadFile.value = null;
          return;
        }

        try {
          loading.value = true;
          const formData = new FormData();
          formData.append('file', file);
          formData.append('task_id', currentTask.value.task_id);

          const response = await axios.post(
            `${getApiUrl()}/media/task/upload`,
            formData,
            {
              headers: {
                'Content-Type': 'multipart/form-data',
              },
            }
          );

          if (response.data.code === 0) {
            ElMessage.success("文件上传成功");
            uploadFile.value = null;
            // 刷新任务信息
            await handleViewTask(currentTask.value.task_id);
          } else {
            ElMessage.error(response.data.msg || "文件上传失败");
          }
        } catch (error) {
          console.error("文件上传失败:", error);
          ElMessage.error("文件上传失败: " + (error.message || "未知错误"));
        } finally {
          loading.value = false;
        }
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
        taskDialogVisible,
        currentTask,
        uploadFile,
        loadTaskList,
        handleCreateTask,
        handleViewTask,
        handleDeleteTask,
        handleFileChange,
        handleUploadFile,
        handleRemoveFile,
        handleStartMerge,
        handleDownloadResult,
        formatFileSize,
        getStatusTagType,
        getStatusText,
      };
    },
    template,
  };
  return component;
}

export default createComponent();
