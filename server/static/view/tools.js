import { getApiUrl } from "../js/net_util.js";
import { formatSize, formatDuration, getMediaFileUrl, logAndNoticeError } from "../js/utils.js";
import { createFileDialog } from "./common/file_dialog.js";
import { createMediaPlayerComponent } from "./common/media_player.js";
import { createAudioPlayer } from "./common/audio_player.js";
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
  // 加载媒体播放器组件
  const MediaPlayer = await createMediaPlayerComponent();

  component = {
    components: {
      FileDialog,
      MediaPlayer,
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
      // 统一的播放器相关状态（用于文件列表和结果文件）
      const mediaPlayer = createAudioPlayer({
        callbacks: {
          onPlay: () => {
            ElMessage.success("开始播放");
          },
          onError: () => {
            logAndNoticeError(new Error("音频播放失败"), "播放失败");
            clearBrowserAudioPlayer();
          },
          onEnded: () => {
            clearBrowserAudioPlayer();
          },
        },
      });

      // ========== 工具函数 ==========

      // 拖拽样式类名常量
      const DRAG_STYLE_CLASSES = ['bg-gray-100', 'border-t-2', 'border-b-2', 'border-blue-500'];

      // 清除拖拽样式
      const clearDragStyles = (element) => {
        if (element) {
          element.classList.remove(...DRAG_STYLE_CLASSES);
        }
      };

      // 清除所有拖拽项的样式
      const clearAllDragStyles = (parentElement) => {
        if (!parentElement) return;
        const allItems = parentElement.querySelectorAll('[draggable="true"]');
        allItems.forEach(item => clearDragStyles(item));
      };


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
          logAndNoticeError(error, "获取文件列表失败");
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
          logAndNoticeError(error, "文件上传失败");
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
          logAndNoticeError(error, "文件解密失败");
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
          logAndNoticeError(error, "下载文件失败");
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
          logAndNoticeError(error, "删除文件失败");
        } finally {
          pdfLoading.value = false;
        }
      };

      // 格式化 PDF 文件大小（使用统一的 formatSize 函数）
      const formatPdfFileSize = formatSize;

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
          logAndNoticeError(error, "添加文件失败");
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
          logAndNoticeError(error, "获取任务列表失败");
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
          logAndNoticeError(error, "创建任务失败");
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
          logAndNoticeError(error, "获取任务信息失败");
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
          logAndNoticeError(error, "删除任务失败");
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
            if (mediaPlayer.playingFileIndex.value === fileIndex) {
              handleMediaStopPlay();
            } else if (mediaPlayer.playingFileIndex.value !== null && mediaPlayer.playingFileIndex.value > fileIndex) {
              mediaPlayer.playingFileIndex.value = mediaPlayer.playingFileIndex.value - 1;
            }
            ElMessage.success("文件删除成功");
            await handleMediaViewTask(mediaCurrentTask.value.task_id);
          } else {
            ElMessage.error(response.data.msg || "删除文件失败");
          }
        } catch (error) {
          logAndNoticeError(error, "删除文件失败");
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
          logAndNoticeError(error, "启动任务失败");
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

      // 下载媒体结果（通用函数）
      const downloadMediaResult = (taskId) => {
        if (!taskId) return;
        const url = `${getApiUrl()}/media/task/download?task_id=${taskId}`;
        window.open(url, '_blank');
      };

      // 下载媒体结果
      const handleMediaDownloadResult = () => {
        if (!mediaCurrentTask.value?.result_file) return;
        downloadMediaResult(mediaCurrentTask.value.task_id);
      };

      // 从任务列表下载媒体结果
      const handleMediaDownloadResultFromList = (task) => {
        if (!task?.result_file) return;
        downloadMediaResult(task.task_id);
      };

      // 清理浏览器音频播放器状态（统一清理所有播放）
      const clearBrowserAudioPlayer = () => {
        mediaPlayer.clear();
      };

      // 检查文件是否正在播放
      const isFilePlaying = (fileItem) => {
        if (!fileItem) {
          return false;
        }
        const filePath = fileItem?.path || fileItem?.name || '';
        return mediaPlayer.isFilePlaying(filePath);
      };

      // 获取文件播放进度
      const getFilePlayProgress = (fileItem) => {
        if (!fileItem) {
          return 0;
        }
        const filePath = fileItem?.path || fileItem?.name || '';
        return mediaPlayer.getFilePlayProgress(filePath);
      };

      // 获取文件时长
      const getFileDuration = (fileItem) => {
        if (!fileItem) {
          return 0;
        }
        const filePath = fileItem?.path || fileItem?.name || '';
        // 确定回退值：优先使用文件本身的duration属性，对于结果文件则使用任务中的 result_duration
        let fallbackDuration = fileItem.duration;
        if (fallbackDuration === undefined && mediaCurrentTask.value?.result_file === filePath) {
          fallbackDuration = mediaCurrentTask.value?.result_duration;
        }
        return mediaPlayer.getFileDuration(filePath, fallbackDuration || 0);
      };

      // 处理文件进度条拖拽
      const handleSeekFile = (fileItem, percentage) => {
        if (!fileItem) return;
        const filePath = fileItem?.path || fileItem?.name || '';
        mediaPlayer.seekFile(filePath, percentage);
      };

      // 播放/暂停媒体文件
      const handleMediaTogglePlayFile = (index) => {
        if (!mediaCurrentTask.value || !mediaCurrentTask.value.files || index < 0 || index >= mediaCurrentTask.value.files.length) {
          return;
        }

        const file = mediaCurrentTask.value.files[index];
        const filePath = file.path || file.name || '';
        if (!filePath) {
          ElMessage.warning("文件路径不存在");
          return;
        }

        // 如果点击的是正在播放的文件，则停止播放
        if (mediaPlayer.playingFilePath.value === filePath && mediaPlayer.audio && !mediaPlayer.audio.paused) {
          clearBrowserAudioPlayer();
          ElMessage.info("已停止播放");
          return;
        }

        const audioUrl = getMediaFileUrl(filePath, getApiUrl);
        if (!audioUrl) {
          ElMessage.error("无法生成媒体文件URL");
          return;
        }

        // 加载/更换播放文件
        mediaPlayer.load(audioUrl, {
          playingFilePath: filePath,
          playingFileIndex: index,
        });

        // 开始播放
        mediaPlayer.play().catch((error) => {
          logAndNoticeError(error, "播放失败");
          clearBrowserAudioPlayer();
        });
      };

      // 停止媒体播放（统一清理所有播放）
      const handleMediaStopPlay = () => {
        clearBrowserAudioPlayer();
      };

      // 播放/暂停媒体结果文件（使用统一的播放器）
      const handleMediaTogglePlayResult = () => {
        if (!mediaCurrentTask.value || !mediaCurrentTask.value.result_file) {
          ElMessage.warning("结果文件不存在");
          return;
        }

        const resultFilePath = mediaCurrentTask.value.result_file;

        // 如果点击的是正在播放的结果文件，则停止播放
        if (mediaPlayer.playingFilePath.value === resultFilePath && mediaPlayer.audio && !mediaPlayer.audio.paused) {
          clearBrowserAudioPlayer();
          ElMessage.info("已停止播放");
          return;
        }

        const audioUrl = getMediaFileUrl(resultFilePath, getApiUrl);
        if (!audioUrl) {
          ElMessage.error("无法生成媒体文件URL");
          return;
        }

        // 加载/更换播放文件
        mediaPlayer.load(audioUrl, {
          playingFilePath: resultFilePath,
        });

        // 开始播放
        mediaPlayer.play().catch((error) => {
          logAndNoticeError(error, "播放失败");
          clearBrowserAudioPlayer();
        });
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
          logAndNoticeError(error, "转存失败");
        } finally {
          mediaLoading.value = false;
        }
      };

      // 格式化媒体文件大小（使用统一的 formatSize 函数）
      const formatMediaFileSize = formatSize;

      // 媒体状态映射
      const MEDIA_STATUS_MAP = {
        'pending': { tag: 'info', text: '等待中' },
        'processing': { tag: 'warning', text: '处理中' },
        'success': { tag: 'success', text: '成功' },
        'failed': { tag: 'danger', text: '失败' }
      };

      // 获取媒体状态标签类型
      const getMediaStatusTagType = (status) => {
        return MEDIA_STATUS_MAP[status]?.tag || 'info';
      };

      // 获取媒体状态文本
      const getMediaStatusText = (status) => {
        return MEDIA_STATUS_MAP[status]?.text || '未知';
      };

      // 检查媒体文件顺序是否改变
      const isMediaOrderChanged = (original, current) => {
        if (!original || !current || original.length !== current.length) {
          return true;
        }
        return original.some((item, i) => {
          const origPath = item?.path || item?.name;
          const currPath = current[i]?.path || current[i]?.name;
          return origPath !== currPath;
        });
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
                logAndNoticeError(error, "保存排序失败");
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
        clearDragStyles(event.currentTarget);
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

          clearDragStyles(event.currentTarget);

          if (mouseY < elementCenterY) {
            event.currentTarget.classList.add('border-t-2', 'border-blue-500');
          } else {
            event.currentTarget.classList.add('border-b-2', 'border-blue-500');
          }
        }
      };

      // 处理媒体文件拖拽放置
      const handleMediaFileDrop = (event, targetIndex) => {
        if (!mediaFilesDragMode.value) {
          return;
        }
        event.preventDefault();
        clearDragStyles(event.currentTarget);
        clearAllDragStyles(event.currentTarget?.parentElement);

        const sourceIndex = parseInt(event.dataTransfer.getData('text/plain'), 10);

        if (sourceIndex === targetIndex || isNaN(sourceIndex)) {
          return;
        }

        if (!mediaCurrentTask.value || !mediaCurrentTask.value.files ||
          sourceIndex < 0 || sourceIndex >= mediaCurrentTask.value.files.length ||
          targetIndex < 0 || targetIndex >= mediaCurrentTask.value.files.length) {
          return;
        }

        // 计算插入位置
        const rect = event.currentTarget?.getBoundingClientRect();
        const mouseY = event.clientY;
        const elementCenterY = rect ? rect.top + rect.height / 2 : 0;
        const insertIndex = mouseY < elementCenterY ? targetIndex : targetIndex + 1;

        // 重新排序文件列表
        const list = [...(mediaCurrentTask.value.files || [])];
        const [removed] = list.splice(sourceIndex, 1);
        const adjustedIndex = sourceIndex < insertIndex ? insertIndex - 1 : insertIndex;
        list.splice(adjustedIndex, 0, removed);

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
        isFilePlaying,
        getFilePlayProgress,
        getFileDuration,
        handleSeekFile,
      };
    },
    template,
  };
  return component;
}

export default createComponent();
