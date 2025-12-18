import { getApiUrl } from "../js/net_util.js";
import { formatSize, formatDuration } from "../js/utils.js";
import { createFileDialog } from "./file_dialog.js";
const axios = window.axios;

const { ref, onMounted, onUnmounted } = window.Vue;
const { ElMessage, ElMessageBox } = window.ElementPlus;
let component = null;

async function loadTemplate() {
  const response = await fetch(`./view/tools-template.html?t=${Date.now()}`);
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
      // 主页签控制
      const activeMainTab = ref('pdf_tool');
      
      // PDF 工具相关状态
      const pdfLoading = ref(false);
      const pdfFileList = ref([]);
      const pdfUploadFile = ref(null);
      const pdfUploadFilePath = ref("");

      // 音频合成相关状态
      const mediaLoading = ref(false);
      const mediaTaskList = ref([]);
      const mediaCurrentTask = ref(null);
      const mediaFileBrowserDialogVisible = ref(false);
      const mediaSaveResultDialogVisible = ref(false);
      const mediaFilesDragMode = ref(false);
      const mediaFilesOriginalOrder = ref(null);
      const mediaAudioPlayer = ref(null);
      const mediaPlayingFileIndex = ref(null);
      const mediaIsPlaying = ref(false);
      const mediaResultAudioPlayer = ref(null);
      const mediaIsPlayingResult = ref(false);

      // ========== PDF 工具相关方法 ==========
      
      // 获取 PDF 文件列表
      const loadPdfFileList = async () => {
        try {
          pdfLoading.value = true;
          const response = await axios.get(`${getApiUrl()}/pdf/list`);
          if (response.data.code === 0) {
            const mapping = response.data.data.mapping || [];
            pdfFileList.value = mapping.map(item => ({
              ...item,
              _decrypting: item._decrypting || false,
              _password: item._password !== undefined ? item._password : ""
            }));
          } else {
            ElMessage.error(response.data.msg || "获取文件列表失败");
          }
        } catch (error) {
          console.error("获取文件列表失败:", error);
          ElMessage.error("获取文件列表失败: " + (error.message || "未知错误"));
        } finally {
          pdfLoading.value = false;
        }
      };

      // 处理 PDF 文件选择
      const handlePdfFileChange = (file) => {
        pdfUploadFile.value = file.raw;
        pdfUploadFilePath.value = file.raw.name;
      };

      // 上传 PDF 文件
      const handlePdfUpload = async () => {
        if (!pdfUploadFile.value) {
          ElMessage.warning("请选择要上传的文件");
          return;
        }

        const file = pdfUploadFile.value;
        if (!file.name.toLowerCase().endsWith('.pdf')) {
          ElMessage.error("只支持 PDF 文件");
          return;
        }

        try {
          pdfLoading.value = true;
          const formData = new FormData();
          formData.append('file', file);

          const response = await axios.post(`${getApiUrl()}/pdf/upload`, formData, {
            headers: {
              'Content-Type': 'multipart/form-data',
            },
          });

          if (response.data.code === 0) {
            ElMessage.success("文件上传成功");
            pdfUploadFile.value = null;
            pdfUploadFilePath.value = "";
            await loadPdfFileList();
          } else {
            ElMessage.error(response.data.msg || "文件上传失败");
          }
        } catch (error) {
          console.error("文件上传失败:", error);
          ElMessage.error("文件上传失败: " + (error.message || "未知错误"));
        } finally {
          pdfLoading.value = false;
        }
      };

      // 解密 PDF 文件
      const handlePdfDecrypt = async (item) => {
        if (!item.uploaded) {
          ElMessage.warning("请先上传文件");
          return;
        }

        if (item._decrypting) {
          return;
        }

        if (item.has_unlocked) {
          const confirmed = await ElMessageBox.confirm(
            "已解密的文件已存在，是否重新解密？",
            "提示",
            {
              confirmButtonText: "确定",
              cancelButtonText: "取消",
              type: "warning",
            }
          ).catch(() => false);
          if (!confirmed) return;
        }

        try {
          item._decrypting = true;
          
          const requestData = {
            filename: item.uploaded.name,
          };
          
          if (item._password !== undefined && item._password !== null) {
            requestData.password = item._password;
          }

          const response = await axios.post(`${getApiUrl()}/pdf/decrypt`, requestData);

          if (response.data.code === 0) {
            ElMessage.success("文件解密成功");
            item._password = "";
            await loadPdfFileList();
          } else {
            if (response.data.msg && response.data.msg.includes("密码")) {
              ElMessage.error(response.data.msg || "密码错误，请重试");
            } else {
              ElMessage.error(response.data.msg || "文件解密失败");
            }
          }
        } catch (error) {
          console.error("文件解密失败:", error);
          ElMessage.error("文件解密失败: " + (error.message || "未知错误"));
        } finally {
          item._decrypting = false;
        }
      };

      // 下载 PDF 文件
      const handlePdfDownload = async (item, type) => {
        if (!item[type]) {
          ElMessage.warning("文件不存在");
          return;
        }

        try {
          const url = `${getApiUrl()}/pdf/download/${encodeURIComponent(item[type].name)}?type=${type}`;
          window.open(url, '_blank');
        } catch (error) {
          console.error("下载文件失败:", error);
          ElMessage.error("下载文件失败: " + (error.message || "未知错误"));
        }
      };

      // 删除 PDF 文件
      const handlePdfDelete = async (item) => {
        if (!item.uploaded) {
          ElMessage.warning("请先上传文件");
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
          pdfLoading.value = true;
          const response = await axios.post(`${getApiUrl()}/pdf/delete`, {
            filename: item.uploaded.name,
            type: 'both',
          });

          if (response.data.code === 0) {
            ElMessage.success("文件删除成功");
            await loadPdfFileList();
          } else {
            ElMessage.error(response.data.msg || "文件删除失败");
          }
        } catch (error) {
          console.error("删除文件失败:", error);
          ElMessage.error("删除文件失败: " + (error.message || "未知错误"));
        } finally {
          pdfLoading.value = false;
        }
      };

      // 格式化 PDF 文件大小
      const formatPdfFileSize = (bytes) => {
        if (!bytes) return '-';
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
      };

      // 格式化 PDF 时间
      const formatPdfTime = (timestamp) => {
        if (!timestamp) return '-';
        return new Date(timestamp * 1000).toLocaleString();
      };

      // ========== 媒体工具相关方法 ==========
      // 这里需要将 media_tool.js 中的所有方法复制过来
      // 为了简化，我会创建一个辅助函数来加载媒体工具的逻辑
      
      // 处理媒体工具文件选择确认
      const handleMediaFileBrowserConfirm = async (filePaths) => {
        if (!mediaCurrentTask.value) {
          return;
        }
        
        if (filePaths.length === 0) {
          return;
        }
        
        try {
          mediaLoading.value = true;
          for (const filePath of filePaths) {
            const response = await axios.post(`${getApiUrl()}/media/task/addFileByPath`, {
              task_id: mediaCurrentTask.value.task_id,
              file_path: filePath
            });
            
            if (response.data.code !== 0) {
              ElMessage.error(`添加文件失败: ${response.data.msg || "未知错误"}`);
              break;
            }
          }
          
          ElMessage.success(`成功添加 ${filePaths.length} 个文件`);
          await handleMediaViewTask(mediaCurrentTask.value.task_id);
        } catch (error) {
          console.error("添加文件失败:", error);
          ElMessage.error("添加文件失败: " + (error.message || "未知错误"));
        } finally {
          mediaLoading.value = false;
        }
      };

      // 加载媒体任务列表
      const loadMediaTaskList = async () => {
        try {
          mediaLoading.value = true;
          const response = await axios.get(`${getApiUrl()}/media/task/list`);
          if (response.data.code === 0) {
            mediaTaskList.value = response.data.data.tasks || [];
            if (mediaTaskList.value.length > 0 && !mediaCurrentTask.value) {
              await handleMediaViewTask(mediaTaskList.value[0].task_id);
            }
          } else {
            ElMessage.error(response.data.msg || "获取任务列表失败");
          }
        } catch (error) {
          console.error("获取任务列表失败:", error);
          ElMessage.error("获取任务列表失败: " + (error.message || "未知错误"));
        } finally {
          mediaLoading.value = false;
        }
      };

      // 创建媒体任务
      const handleMediaCreateTask = async () => {
        try {
          mediaLoading.value = true;
          const response = await axios.post(`${getApiUrl()}/media/task/create`, {});

          if (response.data.code === 0) {
            ElMessage.success("任务创建成功");
            await loadMediaTaskList();
            handleMediaViewTask(response.data.data.task_id);
          } else {
            ElMessage.error(response.data.msg || "创建任务失败");
          }
        } catch (error) {
          console.error("创建任务失败:", error);
          ElMessage.error("创建任务失败: " + (error.message || "未知错误"));
        } finally {
          mediaLoading.value = false;
        }
      };

      // 查看媒体任务
      const handleMediaViewTask = async (taskId) => {
        if (mediaCurrentTask.value && mediaCurrentTask.value.task_id !== taskId) {
          handleMediaStopPlay();
        }
        try {
          mediaLoading.value = true;
          const response = await axios.post(`${getApiUrl()}/media/task/get`, {
            task_id: taskId
          });
          if (response.data.code === 0) {
            mediaCurrentTask.value = response.data.data;
          } else {
            ElMessage.error(response.data.msg || "获取任务信息失败");
          }
        } catch (error) {
          console.error("获取任务信息失败:", error);
          ElMessage.error("获取任务信息失败: " + (error.message || "未知错误"));
        } finally {
          mediaLoading.value = false;
        }
      };

      // 删除媒体任务
      const handleMediaDeleteTask = async (taskId) => {
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
          mediaLoading.value = true;
          const response = await axios.post(`${getApiUrl()}/media/task/delete`, {
            task_id: taskId
          });
          if (response.data.code === 0) {
            ElMessage.success("任务删除成功");
            await loadMediaTaskList();
            if (mediaCurrentTask.value && mediaCurrentTask.value.task_id === taskId) {
              if (mediaTaskList.value && mediaTaskList.value.length > 0) {
                await handleMediaViewTask(mediaTaskList.value[0].task_id);
              } else {
                mediaCurrentTask.value = null;
              }
            }
          } else {
            ElMessage.error(response.data.msg || "删除任务失败");
          }
        } catch (error) {
          console.error("删除任务失败:", error);
          ElMessage.error("删除任务失败: " + (error.message || "未知错误"));
        } finally {
          mediaLoading.value = false;
        }
      };

      // 打开媒体文件浏览器
      const handleMediaOpenFileBrowser = () => {
        if (!mediaCurrentTask.value) {
          ElMessage.warning("请先创建或选择任务");
          return;
        }
        mediaFileBrowserDialogVisible.value = true;
      };

      // 移除媒体文件
      const handleMediaRemoveFile = async (fileIndex) => {
        if (!mediaCurrentTask.value) {
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
          mediaLoading.value = true;
          const response = await axios.post(
            `${getApiUrl()}/media/task/deleteFile`,
            {
              task_id: mediaCurrentTask.value.task_id,
              file_index: fileIndex
            }
          );
          if (response.data.code === 0) {
            if (mediaPlayingFileIndex.value === fileIndex) {
              handleMediaStopPlay();
            } else if (mediaPlayingFileIndex.value !== null && mediaPlayingFileIndex.value > fileIndex) {
              mediaPlayingFileIndex.value = mediaPlayingFileIndex.value - 1;
            }
            ElMessage.success("文件删除成功");
            await handleMediaViewTask(mediaCurrentTask.value.task_id);
          } else {
            ElMessage.error(response.data.msg || "删除文件失败");
          }
        } catch (error) {
          console.error("删除文件失败:", error);
          ElMessage.error("删除文件失败: " + (error.message || "未知错误"));
        } finally {
          mediaLoading.value = false;
        }
      };

      // 开始媒体合成
      const handleMediaStartMerge = async () => {
        if (!mediaCurrentTask.value) {
          return;
        }

        const confirmed = await ElMessageBox.confirm(
          `确定要开始合成吗？将合并 ${mediaCurrentTask.value.files.length} 个音频文件。`,
          "确认合成",
          {
            confirmButtonText: "确定",
            cancelButtonText: "取消",
            type: "warning",
          }
        ).catch(() => false);

        if (!confirmed) return;

        try {
          mediaLoading.value = true;
          const response = await axios.post(
            `${getApiUrl()}/media/task/start`,
            {
              task_id: mediaCurrentTask.value.task_id
            }
          );
          if (response.data.code === 0) {
            ElMessage.success("合成任务已启动");
            await loadMediaTaskList();
            await handleMediaViewTask(mediaCurrentTask.value.task_id);
            startMediaPollingTaskStatus();
          } else {
            ElMessage.error(response.data.msg || "启动任务失败");
          }
        } catch (error) {
          console.error("启动任务失败:", error);
          ElMessage.error("启动任务失败: " + (error.message || "未知错误"));
        } finally {
          mediaLoading.value = false;
        }
      };

      // 轮询媒体任务状态
      let mediaPollingTimer = null;
      const startMediaPollingTaskStatus = () => {
        if (mediaPollingTimer) {
          clearInterval(mediaPollingTimer);
        }
        mediaPollingTimer = setInterval(async () => {
          if (!mediaCurrentTask.value || mediaCurrentTask.value.status !== 'processing') {
            if (mediaPollingTimer) {
              clearInterval(mediaPollingTimer);
              mediaPollingTimer = null;
            }
            return;
          }
          await loadMediaTaskList();
          await handleMediaViewTask(mediaCurrentTask.value.task_id);
        }, 2000);
      };

      // 下载媒体结果
      const handleMediaDownloadResult = () => {
        if (!mediaCurrentTask.value || !mediaCurrentTask.value.result_file) {
          return;
        }
        const url = `${getApiUrl()}/media/task/download?task_id=${mediaCurrentTask.value.task_id}`;
        window.open(url, '_blank');
      };

      // 从任务列表下载媒体结果
      const handleMediaDownloadResultFromList = (task) => {
        if (!task || !task.result_file) {
          return;
        }
        const url = `${getApiUrl()}/media/task/download?task_id=${task.task_id}`;
        window.open(url, '_blank');
      };

      // 获取媒体文件 URL
      const getMediaFileUrl = (filePath) => {
        if (!filePath) return '';
        const path = filePath.startsWith('/') ? filePath.slice(1) : filePath;
        const encodedPath = path.split('/').map(part => encodeURIComponent(part)).join('/');
        return `${getApiUrl()}/media/files/${encodedPath}`;
      };

      // 播放/暂停媒体文件
      const handleMediaTogglePlayFile = (index) => {
        if (!mediaCurrentTask.value || !mediaCurrentTask.value.files || index < 0 || index >= mediaCurrentTask.value.files.length) {
          return;
        }

        const file = mediaCurrentTask.value.files[index];
        if (!file.path) {
          ElMessage.warning("文件路径不存在");
          return;
        }

        if (mediaPlayingFileIndex.value === index && mediaAudioPlayer.value) {
          if (mediaIsPlaying.value) {
            mediaAudioPlayer.value.pause();
            mediaIsPlaying.value = false;
          } else {
            mediaAudioPlayer.value.play();
            mediaIsPlaying.value = true;
          }
          return;
        }

        if (mediaAudioPlayer.value) {
          mediaAudioPlayer.value.pause();
          mediaAudioPlayer.value = null;
        }

        const audioUrl = getMediaFileUrl(file.path);
        const audio = new Audio(audioUrl);
        
        audio.addEventListener('play', () => {
          mediaIsPlaying.value = true;
          mediaPlayingFileIndex.value = index;
        });
        
        audio.addEventListener('pause', () => {
          mediaIsPlaying.value = false;
        });
        
        audio.addEventListener('ended', () => {
          mediaIsPlaying.value = false;
          mediaPlayingFileIndex.value = null;
          mediaAudioPlayer.value = null;
        });
        
        audio.addEventListener('error', (e) => {
          console.error("音频播放失败:", e);
          ElMessage.error("音频播放失败");
          mediaIsPlaying.value = false;
          mediaPlayingFileIndex.value = null;
          mediaAudioPlayer.value = null;
        });

        mediaAudioPlayer.value = audio;
        audio.play();
      };

      // 停止媒体播放
      const handleMediaStopPlay = () => {
        if (mediaAudioPlayer.value) {
          mediaAudioPlayer.value.pause();
          mediaAudioPlayer.value.currentTime = 0;
          mediaAudioPlayer.value = null;
        }
        mediaIsPlaying.value = false;
        mediaPlayingFileIndex.value = null;
        
        if (mediaResultAudioPlayer.value) {
          mediaResultAudioPlayer.value.pause();
          mediaResultAudioPlayer.value.currentTime = 0;
          mediaResultAudioPlayer.value = null;
        }
        mediaIsPlayingResult.value = false;
      };

      // 播放/暂停媒体结果文件
      const handleMediaTogglePlayResult = () => {
        if (!mediaCurrentTask.value || !mediaCurrentTask.value.result_file) {
          ElMessage.warning("结果文件不存在");
          return;
        }

        if (mediaResultAudioPlayer.value && mediaIsPlayingResult.value) {
          mediaResultAudioPlayer.value.pause();
          mediaIsPlayingResult.value = false;
          return;
        }

        if (mediaAudioPlayer.value) {
          mediaAudioPlayer.value.pause();
          mediaAudioPlayer.value.currentTime = 0;
          mediaAudioPlayer.value = null;
        }
        mediaIsPlaying.value = false;
        mediaPlayingFileIndex.value = null;

        const audioUrl = getMediaFileUrl(mediaCurrentTask.value.result_file);
        const audio = new Audio(audioUrl);
        
        audio.addEventListener('play', () => {
          mediaIsPlayingResult.value = true;
        });
        
        audio.addEventListener('pause', () => {
          mediaIsPlayingResult.value = false;
        });
        
        audio.addEventListener('ended', () => {
          mediaIsPlayingResult.value = false;
          mediaResultAudioPlayer.value = null;
        });
        
        audio.addEventListener('error', (e) => {
          console.error("音频播放失败:", e);
          ElMessage.error("音频播放失败");
          mediaIsPlayingResult.value = false;
          mediaResultAudioPlayer.value = null;
        });

        mediaResultAudioPlayer.value = audio;
        audio.play();
      };

      // 转存媒体结果文件
      const handleMediaSaveResult = () => {
        if (!mediaCurrentTask.value || !mediaCurrentTask.value.result_file) {
          ElMessage.warning("结果文件不存在");
          return;
        }
        mediaSaveResultDialogVisible.value = true;
      };

      // 处理媒体转存确认
      const handleMediaSaveResultConfirm = async (filePaths) => {
        if (!mediaCurrentTask.value || !mediaCurrentTask.value.result_file) {
          return;
        }
        
        if (filePaths.length === 0) {
          ElMessage.warning("请选择转存目录");
          return;
        }
        
        const targetDir = filePaths[0];
        
        try {
          mediaLoading.value = true;
          const response = await axios.post(`${getApiUrl()}/media/task/save`, {
            task_id: mediaCurrentTask.value.task_id,
            target_path: targetDir
          });
          
          if (response.data.code === 0) {
            ElMessage.success("转存成功");
            mediaSaveResultDialogVisible.value = false;
          } else {
            ElMessage.error(response.data.msg || "转存失败");
          }
        } catch (error) {
          console.error("转存失败:", error);
          ElMessage.error("转存失败: " + (error.message || "未知错误"));
        } finally {
          mediaLoading.value = false;
        }
      };

      // 格式化媒体文件大小
      const formatMediaFileSize = (bytes) => {
        if (!bytes) return '-';
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
      };

      // 获取媒体状态标签类型
      const getMediaStatusTagType = (status) => {
        const statusMap = {
          'pending': 'info',
          'processing': 'warning',
          'success': 'success',
          'failed': 'danger'
        };
        return statusMap[status] || 'info';
      };

      // 获取媒体状态文本
      const getMediaStatusText = (status) => {
        const statusMap = {
          'pending': '等待中',
          'processing': '处理中',
          'success': '成功',
          'failed': '失败'
        };
        return statusMap[status] || '未知';
      };

      // 检查媒体文件顺序是否改变
      const isMediaOrderChanged = (original, current) => {
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

      // 切换媒体文件拖拽排序模式
      const handleMediaToggleFilesDragMode = async () => {
        if (mediaFilesDragMode.value) {
          if (mediaCurrentTask.value && mediaCurrentTask.value.files && mediaCurrentTask.value.files.length > 0) {
            const hasChanged = isMediaOrderChanged(mediaFilesOriginalOrder.value, mediaCurrentTask.value.files);
            if (hasChanged) {
              try {
                mediaLoading.value = true;
                const fileIndices = mediaCurrentTask.value.files.map((_, index) => index);
                const response = await axios.post(`${getApiUrl()}/media/task/reorderFiles`, {
                  task_id: mediaCurrentTask.value.task_id,
                  file_indices: fileIndices
                });
                
                if (response.data.code === 0) {
                  ElMessage.success("排序已保存");
                  await handleMediaViewTask(mediaCurrentTask.value.task_id);
                } else {
                  ElMessage.error(response.data.msg || "保存排序失败");
                }
              } catch (error) {
                console.error("保存排序失败:", error);
                ElMessage.error("保存排序失败: " + (error.message || "未知错误"));
              } finally {
                mediaLoading.value = false;
              }
            }
            mediaFilesOriginalOrder.value = null;
          }
        } else {
          if (mediaCurrentTask.value && mediaCurrentTask.value.files && mediaCurrentTask.value.files.length > 0) {
            mediaFilesOriginalOrder.value = [...(mediaCurrentTask.value.files || [])];
          }
        }
        mediaFilesDragMode.value = !mediaFilesDragMode.value;
      };

      // 处理媒体文件拖拽开始
      const handleMediaFileDragStart = (event, index) => {
        if (!mediaFilesDragMode.value) {
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

      // 处理媒体文件拖拽结束
      const handleMediaFileDragEnd = (event) => {
        if (event.currentTarget) {
          event.currentTarget.style.backgroundColor = '';
          event.currentTarget.style.borderTop = '';
          event.currentTarget.style.borderBottom = '';
        }
      };

      // 处理媒体文件拖拽悬停
      const handleMediaFileDragOver = (event) => {
        if (!mediaFilesDragMode.value) {
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

      // 处理媒体文件拖拽放置
      const handleMediaFileDrop = (event, targetIndex) => {
        if (!mediaFilesDragMode.value) {
          return;
        }
        event.preventDefault();
        if (event.currentTarget) {
          event.currentTarget.style.backgroundColor = '';
          event.currentTarget.style.borderTop = '';
          event.currentTarget.style.borderBottom = '';
        }
        
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

        if (!mediaCurrentTask.value || !mediaCurrentTask.value.files || 
            sourceIndex < 0 || sourceIndex >= mediaCurrentTask.value.files.length ||
            targetIndex < 0 || targetIndex >= mediaCurrentTask.value.files.length) {
          return;
        }
        
        let insertIndex = targetIndex;
        if (event.currentTarget) {
          const rect = event.currentTarget.getBoundingClientRect();
          const mouseY = event.clientY;
          const elementCenterY = rect.top + rect.height / 2;
          
          if (mouseY < elementCenterY) {
            insertIndex = targetIndex;
          } else {
            insertIndex = targetIndex + 1;
          }
        }
        
        const list = [...(mediaCurrentTask.value.files || [])];
        const [removed] = list.splice(sourceIndex, 1);
        
        if (sourceIndex < insertIndex) {
          insertIndex = insertIndex - 1;
        }
        
        list.splice(insertIndex, 0, removed);
        
        list.forEach((file, index) => {
          file.index = index;
        });
        
        mediaCurrentTask.value = {
          ...mediaCurrentTask.value,
          files: list
        };
      };

      onMounted(() => {
        // 根据当前页签加载相应数据
        if (activeMainTab.value === 'pdf_tool') {
          loadPdfFileList();
        } else if (activeMainTab.value === 'audio_merge') {
          loadMediaTaskList();
        }
      });

      onUnmounted(() => {
        handleMediaStopPlay();
        if (mediaResultAudioPlayer.value) {
          mediaResultAudioPlayer.value.pause();
          mediaResultAudioPlayer.value = null;
        }
        if (mediaPollingTimer) {
          clearInterval(mediaPollingTimer);
          mediaPollingTimer = null;
        }
      });

      // 监听页签切换
      const handleTabChange = (tabName) => {
        if (tabName === 'pdf_tool' && pdfFileList.value.length === 0) {
          loadPdfFileList();
        } else if (tabName === 'audio_merge' && mediaTaskList.value.length === 0) {
          loadMediaTaskList();
        }
      };

      return {
        // 主页签
        activeMainTab,
        handleTabChange,
        
        // PDF 工具
        pdfLoading,
        pdfFileList,
        pdfUploadFile,
        pdfUploadFilePath,
        loadPdfFileList,
        handlePdfFileChange,
        handlePdfUpload,
        handlePdfDecrypt,
        handlePdfDownload,
        handlePdfDelete,
        formatPdfFileSize,
        formatPdfTime,
        
        // 音频合成
        mediaLoading,
        mediaTaskList,
        mediaCurrentTask,
        mediaFileBrowserDialogVisible,
        mediaSaveResultDialogVisible,
        mediaFilesDragMode,
        mediaFilesOriginalOrder,
        mediaPlayingFileIndex,
        mediaIsPlaying,
        mediaIsPlayingResult,
        loadMediaTaskList,
        handleMediaCreateTask,
        handleMediaViewTask,
        handleMediaDeleteTask,
        handleMediaOpenFileBrowser,
        handleMediaRemoveFile,
        handleMediaStartMerge,
        handleMediaDownloadResult,
        handleMediaDownloadResultFromList,
        formatMediaFileSize,
        formatSize,
        formatDuration,
        getMediaStatusTagType,
        getMediaStatusText,
        handleMediaFileBrowserConfirm,
        handleMediaCloseFileBrowser: () => {
          mediaFileBrowserDialogVisible.value = false;
        },
        handleMediaToggleFilesDragMode,
        handleMediaFileDragStart,
        handleMediaFileDragEnd,
        handleMediaFileDragOver,
        handleMediaFileDrop,
        handleMediaTogglePlayFile,
        handleMediaStopPlay,
        handleMediaTogglePlayResult,
        handleMediaSaveResult,
        handleMediaSaveResultConfirm,
      };
    },
    template,
  };
  return component;
}

export default createComponent();
