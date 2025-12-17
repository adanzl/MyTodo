import { getApiUrl } from "../js/net_util.js";
import { formatSize, formatDuration } from "../js/utils.js";
import { createFileDialog } from "./file_dialog.js";
const axios = window.axios;

const { ref, onMounted, onUnmounted } = window.Vue;
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
      const saveResultDialogVisible = ref(false);
      
      // 文件拖拽排序模式
      const filesDragMode = ref(false);
      const filesOriginalOrder = ref(null);
      
      // 音频播放相关
      const audioPlayer = ref(null);
      const playingFileIndex = ref(null);
      const isPlaying = ref(false);
      
      // 结果文件播放相关
      const resultAudioPlayer = ref(null);
      const isPlayingResult = ref(false);
      
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
        // 如果切换任务，停止当前播放
        if (currentTask.value && currentTask.value.task_id !== taskId) {
          handleStopPlay();
        }
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
              // 如果删除的是当前选中的任务，且任务列表不为空，则选中第一个任务
              if (taskList.value && taskList.value.length > 0) {
                await handleViewTask(taskList.value[0].task_id);
              } else {
                currentTask.value = null;
              }
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
            // 如果删除的是正在播放的文件，停止播放
            if (playingFileIndex.value === fileIndex) {
              handleStopPlay();
            } else if (playingFileIndex.value !== null && playingFileIndex.value > fileIndex) {
              // 如果删除的文件在正在播放的文件之前，调整播放索引
              playingFileIndex.value = playingFileIndex.value - 1;
            }
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
            // 刷新任务列表
            await loadTaskList();
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
          // 刷新任务列表和当前任务详情
          await loadTaskList();
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

      // 获取媒体文件 URL
      const getMediaFileUrl = (filePath) => {
        if (!filePath) return '';
        // 移除路径开头的 /
        const path = filePath.startsWith('/') ? filePath.slice(1) : filePath;
        // URL 编码路径
        const encodedPath = path.split('/').map(part => encodeURIComponent(part)).join('/');
        return `${getApiUrl()}/media/files/${encodedPath}`;
      };

      // 播放/暂停文件
      const handleTogglePlayFile = (index) => {
        if (!currentTask.value || !currentTask.value.files || index < 0 || index >= currentTask.value.files.length) {
          return;
        }

        const file = currentTask.value.files[index];
        if (!file.path) {
          ElMessage.warning("文件路径不存在");
          return;
        }

        // 如果点击的是当前播放的文件，则暂停/继续
        if (playingFileIndex.value === index && audioPlayer.value) {
          if (isPlaying.value) {
            audioPlayer.value.pause();
            isPlaying.value = false;
          } else {
            audioPlayer.value.play();
            isPlaying.value = true;
          }
          return;
        }

        // 停止当前播放
        if (audioPlayer.value) {
          audioPlayer.value.pause();
          audioPlayer.value = null;
        }

        // 播放新文件
        const audioUrl = getMediaFileUrl(file.path);
        const audio = new Audio(audioUrl);
        
        audio.addEventListener('play', () => {
          isPlaying.value = true;
          playingFileIndex.value = index;
        });
        
        audio.addEventListener('pause', () => {
          isPlaying.value = false;
        });
        
        audio.addEventListener('ended', () => {
          isPlaying.value = false;
          playingFileIndex.value = null;
          audioPlayer.value = null;
        });
        
        audio.addEventListener('error', (e) => {
          console.error("音频播放失败:", e);
          ElMessage.error("音频播放失败");
          isPlaying.value = false;
          playingFileIndex.value = null;
          audioPlayer.value = null;
        });

        audioPlayer.value = audio;
        audio.play();
      };

      // 停止播放
      const handleStopPlay = () => {
        if (audioPlayer.value) {
          audioPlayer.value.pause();
          audioPlayer.value.currentTime = 0;
          audioPlayer.value = null;
        }
        isPlaying.value = false;
        playingFileIndex.value = null;
        
        // 停止结果文件播放
        if (resultAudioPlayer.value) {
          resultAudioPlayer.value.pause();
          resultAudioPlayer.value.currentTime = 0;
          resultAudioPlayer.value = null;
        }
        isPlayingResult.value = false;
      };

      // 播放/暂停结果文件
      const handleTogglePlayResult = () => {
        if (!currentTask.value || !currentTask.value.result_file) {
          ElMessage.warning("结果文件不存在");
          return;
        }

        // 如果正在播放结果文件，则暂停/继续
        if (resultAudioPlayer.value && isPlayingResult.value) {
          resultAudioPlayer.value.pause();
          isPlayingResult.value = false;
          return;
        }

        // 停止当前播放的文件列表中的文件
        if (audioPlayer.value) {
          audioPlayer.value.pause();
          audioPlayer.value.currentTime = 0;
          audioPlayer.value = null;
        }
        isPlaying.value = false;
        playingFileIndex.value = null;

        // 播放结果文件
        const audioUrl = getMediaFileUrl(currentTask.value.result_file);
        const audio = new Audio(audioUrl);
        
        audio.addEventListener('play', () => {
          isPlayingResult.value = true;
        });
        
        audio.addEventListener('pause', () => {
          isPlayingResult.value = false;
        });
        
        audio.addEventListener('ended', () => {
          isPlayingResult.value = false;
          resultAudioPlayer.value = null;
        });
        
        audio.addEventListener('error', (e) => {
          console.error("音频播放失败:", e);
          ElMessage.error("音频播放失败");
          isPlayingResult.value = false;
          resultAudioPlayer.value = null;
        });

        resultAudioPlayer.value = audio;
        audio.play();
      };

      // 转存结果文件
      const handleSaveResult = () => {
        if (!currentTask.value || !currentTask.value.result_file) {
          ElMessage.warning("结果文件不存在");
          return;
        }
        saveResultDialogVisible.value = true;
      };

      // 处理转存确认
      const handleSaveResultConfirm = async (filePaths) => {
        if (!currentTask.value || !currentTask.value.result_file) {
          return;
        }
        
        if (filePaths.length === 0) {
          ElMessage.warning("请选择转存目录");
          return;
        }
        
        // filePaths 应该是目录路径，取第一个
        const targetDir = filePaths[0];
        
        try {
          loading.value = true;
          const response = await axios.post(`${getApiUrl()}/media/task/save`, {
            task_id: currentTask.value.task_id,
            target_path: targetDir
          });
          
          if (response.data.code === 0) {
            ElMessage.success("转存成功");
            saveResultDialogVisible.value = false;
          } else {
            ElMessage.error(response.data.msg || "转存失败");
          }
        } catch (error) {
          console.error("转存失败:", error);
          ElMessage.error("转存失败: " + (error.message || "未知错误"));
        } finally {
          loading.value = false;
        }
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

      // 检查顺序是否改变
      const isOrderChanged = (original, current) => {
        if (!original || !current || original.length !== current.length) {
          return true;
        }
        for (let i = 0; i < original.length; i++) {
          const origPath = original[i]?.path || original[i]?.name;
          const currPath = current[i]?.path || current[i]?.name;
          if (origPath !== currPath) {
            return true;
          }
        }
        return false;
      };

      // 切换文件拖拽排序模式
      const handleToggleFilesDragMode = async () => {
        if (filesDragMode.value) {
          // 退出拖拽模式时，检查是否有变化
          if (currentTask.value && currentTask.value.files && currentTask.value.files.length > 0) {
            const hasChanged = isOrderChanged(filesOriginalOrder.value, currentTask.value.files);
            if (hasChanged) {
              try {
                loading.value = true;
                // 获取当前文件顺序的索引数组
                const fileIndices = currentTask.value.files.map((_, index) => index);
                const response = await axios.post(`${getApiUrl()}/media/task/reorderFiles`, {
                  task_id: currentTask.value.task_id,
                  file_indices: fileIndices
                });
                
                if (response.data.code === 0) {
                  ElMessage.success("排序已保存");
                  // 刷新任务信息
                  await handleViewTask(currentTask.value.task_id);
                } else {
                  ElMessage.error(response.data.msg || "保存排序失败");
                }
              } catch (error) {
                console.error("保存排序失败:", error);
                ElMessage.error("保存排序失败: " + (error.message || "未知错误"));
              } finally {
                loading.value = false;
              }
            }
            // 清除原始顺序
            filesOriginalOrder.value = null;
          }
        } else {
          // 启用拖拽模式时，保存原始顺序
          if (currentTask.value && currentTask.value.files && currentTask.value.files.length > 0) {
            filesOriginalOrder.value = [...(currentTask.value.files || [])];
          }
        }
        filesDragMode.value = !filesDragMode.value;
      };

      // 处理文件拖拽开始
      const handleFileDragStart = (event, index) => {
        if (!filesDragMode.value) {
          event.preventDefault();
          return false;
        }
        try {
          event.dataTransfer.effectAllowed = 'move';
          event.dataTransfer.setData('text/plain', index.toString());
        } catch (e) {
          console.error('拖拽开始失败:', e);
        }
      };

      // 处理文件拖拽结束
      const handleFileDragEnd = (event) => {
        if (event.currentTarget) {
          event.currentTarget.style.backgroundColor = '';
          event.currentTarget.style.borderTop = '';
          event.currentTarget.style.borderBottom = '';
        }
      };

      // 处理文件拖拽悬停
      const handleFileDragOver = (event) => {
        if (!filesDragMode.value) {
          return;
        }
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
        if (event.currentTarget) {
          const rect = event.currentTarget.getBoundingClientRect();
          const mouseY = event.clientY;
          const elementCenterY = rect.top + rect.height / 2;
          
          event.currentTarget.style.backgroundColor = '';
          event.currentTarget.style.borderTop = '';
          event.currentTarget.style.borderBottom = '';
          
          if (mouseY < elementCenterY) {
            event.currentTarget.style.borderTop = '2px solid #3b82f6';
          } else {
            event.currentTarget.style.borderBottom = '2px solid #3b82f6';
          }
        }
      };

      // 处理文件拖拽放置
      const handleFileDrop = (event, targetIndex) => {
        if (!filesDragMode.value) {
          return;
        }
        event.preventDefault();
        // 清除所有拖拽相关的样式
        if (event.currentTarget) {
          event.currentTarget.style.backgroundColor = '';
          event.currentTarget.style.borderTop = '';
          event.currentTarget.style.borderBottom = '';
        }
        
        // 清除所有列表项的样式
        const allItems = event.currentTarget?.parentElement?.querySelectorAll('[draggable="true"]');
        if (allItems) {
          allItems.forEach(item => {
            item.style.backgroundColor = '';
            item.style.borderTop = '';
            item.style.borderBottom = '';
          });
        }
        
        const sourceIndex = parseInt(event.dataTransfer.getData('text/plain'), 10);
        
        if (sourceIndex === targetIndex || isNaN(sourceIndex)) {
          return;
        }

        if (!currentTask.value || !currentTask.value.files || 
            sourceIndex < 0 || sourceIndex >= currentTask.value.files.length ||
            targetIndex < 0 || targetIndex >= currentTask.value.files.length) {
          return;
        }
        
        // 根据鼠标位置决定插入位置（上方或下方）
        let insertIndex = targetIndex;
        if (event.currentTarget) {
          const rect = event.currentTarget.getBoundingClientRect();
          const mouseY = event.clientY;
          const elementCenterY = rect.top + rect.height / 2;
          
          if (mouseY < elementCenterY) {
            // 插入到上方
            insertIndex = targetIndex;
          } else {
            // 插入到下方
            insertIndex = targetIndex + 1;
          }
        }
        
        // 只在内存中更新，不保存到后端
        const list = [...(currentTask.value.files || [])];
        const [removed] = list.splice(sourceIndex, 1);
        
        // 调整插入位置（如果 sourceIndex < insertIndex，插入位置需要减1）
        if (sourceIndex < insertIndex) {
          insertIndex = insertIndex - 1;
        }
        
        list.splice(insertIndex, 0, removed);
        
        // 更新文件索引
        list.forEach((file, index) => {
          file.index = index;
        });
        
        // 更新当前任务的文件列表
        currentTask.value = {
          ...currentTask.value,
          files: list
        };
      };

      onMounted(() => {
        loadTaskList();
      });

      onUnmounted(() => {
        // 组件卸载时停止播放
        handleStopPlay();
        // 停止结果文件播放
        if (resultAudioPlayer.value) {
          resultAudioPlayer.value.pause();
          resultAudioPlayer.value = null;
        }
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
        formatDuration,
        getStatusTagType,
        getStatusText,
        // 文件浏览器
        fileBrowserDialogVisible,
        handleFileBrowserConfirm,
        handleCloseFileBrowser: () => {
          fileBrowserDialogVisible.value = false;
        },
        // 文件拖拽排序
        filesDragMode,
        handleToggleFilesDragMode,
        handleFileDragStart,
        handleFileDragEnd,
        handleFileDragOver,
        handleFileDrop,
        // 音频播放
        playingFileIndex,
        isPlaying,
        handleTogglePlayFile,
        handleStopPlay,
        // 结果文件播放
        isPlayingResult,
        handleTogglePlayResult,
        // 转存
        saveResultDialogVisible,
        handleSaveResult,
        handleSaveResultConfirm,
      };
    },
    template,
  };
  return component;
}

export default createComponent();
