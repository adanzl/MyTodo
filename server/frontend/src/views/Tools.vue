<template>
  <div class="p-1">
    <!-- 主页签 -->
    <el-tabs
      v-model="activeMainTab"
      @tab-change="handleTabChange"
      class="flex-1 flex flex-col overflow-hidden h-[calc(100vh-150px)]"
    >
      <!-- PDF 工具页签 -->
      <el-tab-pane label="PDF 工具" name="pdf_tool">
        <div class="p-4 flex flex-col h-full">
          <h2 class="text-xl font-semibold mb-4">PDF 解密工具</h2>

          <!-- 上传区域 -->
          <div class="mb-4 flex-shrink-0 border rounded p-3 bg-gray-50">
            <div class="flex items-center gap-3">
              <div>
                <el-button
                  type="success"
                  size="small"
                  @click="handlePdfUpload"
                  :loading="pdfLoading"
                  :disabled="!pdfUploadFile"
                >
                  上传
                </el-button>
              </div>
              <el-upload
                :auto-upload="false"
                :on-change="handlePdfFileChange"
                :show-file-list="false"
                accept=".pdf"
              >
                <template #trigger>
                  <el-button type="primary" size="small" class="!m-0">选择文件</el-button>
                </template>
              </el-upload>
              <div v-if="pdfUploadFile" class="flex-1 min-w-0">
                <div
                  class="text-sm text-gray-600 truncate"
                  :title="pdfUploadFilePath || pdfUploadFile.name"
                >
                  {{ pdfUploadFilePath || pdfUploadFile.name }}
                </div>
              </div>
            </div>
          </div>

          <!-- 文件列表 -->
          <el-card class="flex-1 flex flex-col overflow-hidden" shadow="hover">
            <template #header>
              <div class="flex items-center justify-between">
                <span>文件列表</span>
                <el-button
                  type="info"
                  size="small"
                  plain
                  @click="loadPdfFileList"
                  :loading="pdfLoading"
                >
                  <el-icon v-if="!pdfLoading"><Refresh /></el-icon>
                  刷新
                </el-button>
              </div>
            </template>

            <div class="flex-1 overflow-auto">
              <el-table :data="pdfFileList" v-loading="pdfLoading" stripe class="w-full">
                <el-table-column prop="uploaded.name" label="文件名" min-width="200">
                  <template #default="{ row }">
                    <span
                      v-if="row.uploaded"
                      class="text-blue-600 cursor-pointer hover:underline"
                      @click="handlePdfDownload(row, 'uploaded')"
                    >
                      {{ row.uploaded.name }}
                    </span>
                    <span v-else class="text-gray-400">-</span>
                  </template>
                </el-table-column>

                <el-table-column label="上传文件" min-width="150">
                  <template #default="{ row }">
                    <div v-if="row.uploaded" class="flex flex-col gap-1">
                      <span class="text-sm">{{ formatPdfFileSize(row.uploaded.size) }}</span>
                      <span class="text-xs text-gray-500">{{
                        formatPdfTime(row.uploaded.modified)
                      }}</span>
                    </div>
                    <span v-else class="text-gray-400">-</span>
                  </template>
                </el-table-column>

                <el-table-column label="已解密文件" min-width="150">
                  <template #default="{ row }">
                    <div v-if="row.unlocked" class="flex flex-col gap-1">
                      <span class="text-sm">{{ formatPdfFileSize(row.unlocked.size) }}</span>
                      <span class="text-xs text-gray-500">{{
                        formatPdfTime(row.unlocked.modified)
                      }}</span>
                    </div>
                    <span v-else class="text-gray-400">未解密</span>
                  </template>
                </el-table-column>

                <el-table-column label="状态" width="120" align="center">
                  <template #default="{ row }">
                    <div class="flex flex-col gap-1 items-center">
                      <el-tag v-if="row.has_unlocked" type="success" size="small">已解密</el-tag>
                      <el-tag v-else type="info" size="small">未解密</el-tag>
                      <span
                        v-if="row.unlocked"
                        class="text-xs text-blue-600 cursor-pointer hover:underline"
                        @click="handlePdfDownload(row, 'unlocked')"
                      >
                        下载
                      </span>
                    </div>
                  </template>
                </el-table-column>

                <el-table-column label="操作" width="280" fixed="right">
                  <template #default="{ row }">
                    <div class="flex items-center gap-2">
                      <!-- 密码输入框 -->
                      <el-input
                        v-if="row.uploaded"
                        v-model="row._password"
                        type="password"
                        size="small"
                        placeholder="密码（可选）"
                        show-password
                        clearable
                        class="w-30"
                        :disabled="row._decrypting"
                        @keyup.enter="handlePdfDecrypt(row)"
                      >
                      </el-input>

                      <!-- 解密 -->
                      <el-button
                        v-if="row.uploaded"
                        type="primary"
                        size="small"
                        @click="handlePdfDecrypt(row)"
                        :loading="row._decrypting"
                        :disabled="row._decrypting"
                      >
                        解密
                      </el-button>

                      <!-- 删除 -->
                      <el-button
                        v-if="row.uploaded"
                        type="danger"
                        size="small"
                        plain
                        @click="handlePdfDelete(row)"
                      >
                        删除
                      </el-button>
                    </div>
                  </template>
                </el-table-column>

                <template #empty>
                  <div class="text-center text-gray-400 py-8">暂无文件，请上传 PDF 文件</div>
                </template>
              </el-table>
            </div>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- 音频合成页签 -->
      <el-tab-pane label="音频合成" name="audio_merge">
        <div class="flex gap-4 h-full">
          <!-- 左侧：任务列表 -->
          <div class="w-64 border rounded p-3 flex flex-col">
            <div class="flex items-center justify-between mb-3">
              <h3 class="text-base font-semibold">任务列表</h3>
              <div class="flex items-center gap-1">
                <el-button
                  type="info"
                  size="small"
                  plain
                  @click="loadMediaTaskList"
                  :loading="mediaLoading"
                  class="!w-8 !h-6 !p-0"
                >
                  <el-icon v-if="!mediaLoading"><Refresh /></el-icon>
                </el-button>
                <el-button
                  type="success"
                  size="small"
                  @click="handleMediaCreateTask"
                  :loading="mediaLoading"
                  class="!w-8 !h-6 !p-0"
                >
                  <el-icon><Plus /></el-icon>
                </el-button>
              </div>
            </div>
            <div
              v-if="mediaTaskList && mediaTaskList.length > 0"
              class="flex-1 overflow-y-auto space-y-2 pr-1 min-h-[400px]"
            >
              <div
                v-for="task in mediaTaskList"
                :key="task.task_id"
                class="border rounded px-3 py-2 cursor-pointer hover:bg-gray-50 group min-h-[60px] flex flex-col justify-between"
                :class="{
                  'border-blue-500 bg-blue-50':
                    mediaCurrentTask && task.task_id === mediaCurrentTask.task_id,
                }"
                @click="handleMediaViewTask(task.task_id)"
              >
                <!-- 第一行：名称、文件数量 -->
                <div class="flex items-center justify-between gap-2">
                  <div class="text-sm font-medium truncate flex-1 min-w-0">{{ task.name }}</div>
                  <span
                    class="text-xs text-gray-500 whitespace-nowrap flex items-center gap-1 flex-shrink-0"
                  >
                    <el-icon><Document class="!w-3 !h-3" /></el-icon>
                    <span class="whitespace-nowrap w-5 flex items-center justify-center">{{
                      task.files ? task.files.length : 0
                    }}</span>
                  </span>
                </div>
                <!-- 第二行：状态、下载按钮、删除按钮 -->
                <div class="flex items-center justify-between gap-2 min-h-[20px]">
                  <el-tag
                    :type="getMediaStatusTagType(task.status)"
                    size="small"
                    class="!h-5 !text-xs w-16 text-center"
                  >
                    {{ getMediaStatusText(task.status) }}
                  </el-tag>
                  <div class="flex items-center gap-1 flex-shrink-0">
                    <el-button
                      v-if="task.status === 'success' && task.result_file"
                      type="primary"
                      size="small"
                      plain
                      @click.stop="handleMediaDownloadResultFromList(task)"
                      class="!h-5 !text-xs !px-2"
                    >
                      下载
                    </el-button>
                    <el-button
                      type="danger"
                      size="small"
                      plain
                      @click.stop="handleMediaDeleteTask(task.task_id)"
                      :disabled="task.status === 'processing'"
                      class="!h-5 !text-xs !px-2"
                    >
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="flex-1 flex items-center justify-center text-sm text-gray-400">
              暂无任务，请点击"新建"创建
            </div>
          </div>

          <!-- 右侧：任务详情 -->
          <div class="flex-1 border rounded p-3 flex flex-col max-w-2xl" v-if="mediaCurrentTask">
            <div class="flex items-center justify-between mb-3 flex-shrink-0">
              <h3 class="text-base font-semibold">任务详情: {{ mediaCurrentTask.name }}</h3>
              <span class="text-sm text-gray-500">
                共 {{ mediaCurrentTask.files.length }} 个文件
              </span>
            </div>

            <div class="flex-1 overflow-auto flex flex-col gap-3">
              <!-- 任务信息 -->
              <div class="flex items-center justify-between gap-4 flex-shrink-0">
                <div class="flex items-center gap-4">
                  <el-tag
                    :type="getMediaStatusTagType(mediaCurrentTask.status)"
                    size="small"
                    class="w-16 text-center"
                  >
                    {{ getMediaStatusText(mediaCurrentTask.status) }}
                  </el-tag>
                  <MediaComponent
                    v-if="mediaCurrentTask.result_file && mediaCurrentTask.status === 'success'"
                    :file="{ path: mediaCurrentTask.result_file }"
                    :is-playing="isFilePlaying({ path: mediaCurrentTask.result_file })"
                    :progress="getFilePlayProgress({ path: mediaCurrentTask.result_file })"
                    :duration="getFileDuration({ path: mediaCurrentTask.result_file })"
                    :disabled="mediaFilesDragMode"
                    @play="handleMediaTogglePlayResult"
                    @seek="
                      (_file, val) => handleSeekFile({ path: mediaCurrentTask.result_file }, val)
                    "
                  >
                  </MediaComponent>
                  <el-button
                    type="primary"
                    size="small"
                    plain
                    @click="handleMediaDownloadResult"
                    :disabled="
                      !mediaCurrentTask.result_file ||
                      mediaCurrentTask.status !== 'success' ||
                      mediaFilesDragMode
                    "
                    class="!h-7 !text-xs"
                  >
                    下载
                  </el-button>
                  <el-button
                    type="success"
                    size="small"
                    plain
                    @click="handleMediaSaveResult"
                    :disabled="
                      !mediaCurrentTask.result_file ||
                      mediaCurrentTask.status !== 'success' ||
                      mediaFilesDragMode
                    "
                    class="!h-7 !text-xs"
                  >
                    转存
                  </el-button>
                  <span v-if="mediaCurrentTask.error_message" class="text-red-500 text-xs">
                    错误: {{ mediaCurrentTask.error_message }}
                  </span>
                </div>
                <div class="flex items-center gap-2">
                  <el-button
                    type="success"
                    size="small"
                    @click="handleMediaStartMerge"
                    :disabled="
                      !mediaCurrentTask.files ||
                      mediaCurrentTask.files.length === 0 ||
                      mediaCurrentTask.status === 'processing' ||
                      mediaFilesDragMode
                    "
                    :loading="mediaCurrentTask.status === 'processing'"
                    class="!h-7 !text-xs"
                  >
                    开始合成
                  </el-button>
                </div>
              </div>

              <!-- 文件列表 -->
              <div class="border rounded p-2 flex-1 flex flex-col overflow-hidden">
                <div class="flex items-center justify-between mb-2 flex-shrink-0">
                  <h4 class="text-sm font-semibold">文件列表</h4>
                  <div class="flex items-center gap-1 pr-1">
                    <el-button
                      type="primary"
                      plain
                      size="small"
                      :disabled="mediaCurrentTask.status === 'processing' || mediaFilesDragMode"
                      @click="handleMediaOpenFileBrowser"
                      class="!h-6 !text-xs"
                    >
                      +
                    </el-button>
                    <el-button
                      :type="mediaFilesDragMode ? 'success' : 'default'"
                      size="small"
                      plain
                      class="!w-8 !h-6"
                      @click="handleMediaToggleFilesDragMode"
                      :disabled="
                        !mediaCurrentTask ||
                        !mediaCurrentTask.files ||
                        mediaCurrentTask.files.length === 0 ||
                        mediaCurrentTask.status === 'processing'
                      "
                      :title="mediaFilesDragMode ? '点击退出拖拽排序模式' : '点击进入拖拽排序模式'"
                    >
                      <el-icon v-if="mediaFilesDragMode"><Check /></el-icon>
                      <i-ion-chevron-expand-sharp
                        v-else
                        class="!w-3.5 !h-3.5"
                      ></i-ion-chevron-expand-sharp>
                    </el-button>
                  </div>
                </div>
                <div class="flex-1 overflow-auto">
                  <div v-if="mediaCurrentTask.files && mediaCurrentTask.files.length > 0">
                    <div
                      v-for="(file, index) in mediaCurrentTask.files"
                      :key="index"
                      class="flex items-center gap-2 p-1 hover:bg-gray-100 rounded"
                      :class="{
                        'cursor-move': mediaFilesDragMode,
                        'cursor-default': !mediaFilesDragMode,
                        'select-none': true,
                      }"
                      :draggable="mediaFilesDragMode"
                      @dragstart="handleMediaFileDragStart($event, Number(index))"
                      @dragend="handleMediaFileDragEnd($event)"
                      @dragover.prevent="handleMediaFileDragOver($event)"
                      @dragleave="
                        (e: any) => {
                          if (e.currentTarget) {
                            (e.currentTarget as HTMLElement).classList.remove(
                              'bg-gray-100',
                              'border-t-2',
                              'border-b-2',
                              'border-blue-500'
                            );
                          }
                        }
                      "
                      @drop.prevent="handleMediaFileDrop($event, Number(index))"
                    >
                      <span class="text-xs text-gray-500 w-8">{{ Number(index) + 1 }}</span>
                      <span class="flex-1 text-sm truncate" :title="file.path || file.name">
                        {{ file.name }}
                      </span>
                      <span
                        v-if="file.size"
                        class="text-xs text-gray-500 whitespace-nowrap w-20 text-right"
                      >
                        {{ formatMediaFileSize(file.size) }}
                      </span>
                      <div v-else class="w-20"></div>
                      <div
                        class="flex items-center gap-1 flex-shrink-0"
                        @mousedown.stop
                        @click.stop
                      >
                        <MediaComponent
                          :file="file"
                          :is-playing="isFilePlaying(file)"
                          :progress="getFilePlayProgress(file)"
                          :duration="getFileDuration(file)"
                          :disabled="mediaCurrentTask.status === 'processing' || mediaFilesDragMode"
                          @play="() => handleMediaTogglePlayFile(Number(index))"
                          @seek="(_file, val) => handleSeekFile(_file, val)"
                        >
                        </MediaComponent>
                        <el-button
                          type="info"
                          size="small"
                          plain
                          circle
                          @click.stop="handleMediaRemoveFile(Number(index))"
                          :disabled="mediaCurrentTask.status === 'processing' || mediaFilesDragMode"
                          class="!h-6 !text-xs"
                        >
                          <el-icon><Minus /></el-icon>
                        </el-button>
                      </div>
                    </div>
                  </div>
                  <div v-else class="text-sm text-gray-400 text-center py-1">文件列表为空</div>
                </div>
              </div>
            </div>
          </div>

          <!-- 右侧：空状态 -->
          <div class="flex-1 border rounded p-3 flex flex-col max-w-2xl" v-else>
            <div class="flex items-center justify-between mb-3 flex-shrink-0">
              <h3 class="text-base font-semibold">任务详情</h3>
            </div>
            <div class="flex-1 flex items-center justify-center text-sm text-gray-400">
              请从左侧选择一个任务查看详情
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 文件对话框（媒体工具使用） -->
    <FileDialog
      :visible="mediaFileBrowserDialogVisible"
      @update:visible="mediaFileBrowserDialogVisible = $event"
      title="选择文件添加到任务"
      confirm-button-text="添加"
      :confirm-loading="mediaLoading"
      @confirm="handleMediaFileBrowserConfirm"
      @close="handleMediaCloseFileBrowser"
    >
    </FileDialog>

    <!-- 转存对话框（媒体工具使用） -->
    <FileDialog
      :visible="mediaSaveResultDialogVisible"
      @update:visible="mediaSaveResultDialogVisible = $event"
      title="选择转存目录"
      confirm-button-text="转存"
      mode="directory"
      :confirm-loading="mediaLoading"
      @confirm="handleMediaSaveResultConfirm"
      @close="mediaSaveResultDialogVisible = false"
    >
    </FileDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh, Plus, Document, Delete, Check, Minus } from "@element-plus/icons-vue";
import FileDialog from "@/components/dialogs/FileDialog.vue";
import MediaComponent from "@/components/common/MediaComponent.vue";
import { formatSize } from "@/utils/format";
import { getMediaFileUrl } from "@/utils/file";
import { logAndNoticeError } from "@/utils/error";
import { useAudioPlayer } from "@/composables/useAudioPlayer";
import { getPdfList, uploadPdf, decryptPdf, getPdfDownloadUrl, deletePdf } from "@/api/pdf";
import {
  getMediaTaskList,
  createMediaTask,
  getMediaTask,
  deleteMediaTask,
  addFileToMediaTask,
  deleteFileFromMediaTask,
  startMediaTask,
  reorderMediaTaskFiles,
  getMediaTaskDownloadUrl,
  saveMediaTaskResult,
} from "@/api/media";

// 主页签控制
const activeMainTab = ref("pdf_tool");

// PDF 工具相关状态
const pdfLoading = ref(false);
const pdfFileList = ref<any[]>([]);
const pdfUploadFile = ref<File | null>(null);
const pdfUploadFilePath = ref("");

// 音频合成相关状态
const mediaLoading = ref(false);
const mediaTaskList = ref<any[]>([]);
const mediaCurrentTask = ref<any | null>(null);
const mediaFileBrowserDialogVisible = ref(false);
const mediaSaveResultDialogVisible = ref(false);
const mediaFilesDragMode = ref(false);
const mediaFilesOriginalOrder = ref<any[] | null>(null);

// 统一的播放器相关状态
const mediaPlayer = useAudioPlayer({
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

// 拖拽样式类名常量
const DRAG_STYLE_CLASSES = ["bg-gray-100", "border-t-2", "border-b-2", "border-blue-500"];

// 清除拖拽样式
const clearDragStyles = (element: HTMLElement) => {
  if (element) {
    element.classList.remove(...DRAG_STYLE_CLASSES);
  }
};

// 清除所有拖拽项的样式
const clearAllDragStyles = (parentElement: HTMLElement | null) => {
  if (!parentElement) return;
  const allItems = parentElement.querySelectorAll('[draggable="true"]');
  allItems.forEach(item => clearDragStyles(item as HTMLElement));
};

// ========== PDF 工具相关方法 ==========

// 获取 PDF 文件列表
const loadPdfFileList = async () => {
  try {
    pdfLoading.value = true;
    const response = await getPdfList();
    if (response.code === 0) {
      const mapping = response.data.mapping || [];
      pdfFileList.value = mapping.map((item: any) => ({
        ...item,
        _decrypting: item._decrypting || false,
        _password: item._password !== undefined ? item._password : "",
      }));
    } else {
      ElMessage.error(response.msg || "获取文件列表失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "获取文件列表失败");
  } finally {
    pdfLoading.value = false;
  }
};

// 处理 PDF 文件选择
const handlePdfFileChange = (file: any) => {
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
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    ElMessage.error("只支持 PDF 文件");
    return;
  }

  try {
    pdfLoading.value = true;
    const response = await uploadPdf(file);

    if (response.code === 0) {
      ElMessage.success("文件上传成功");
      pdfUploadFile.value = null;
      pdfUploadFilePath.value = "";
      await loadPdfFileList();
    } else {
      ElMessage.error(response.msg || "文件上传失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "文件上传失败");
  } finally {
    pdfLoading.value = false;
  }
};

// 解密 PDF 文件
const handlePdfDecrypt = async (item: any) => {
  if (!item.uploaded) {
    ElMessage.warning("请先上传文件");
    return;
  }

  if (item._decrypting) {
    return;
  }

  if (item.has_unlocked) {
    const confirmed = await ElMessageBox.confirm("已解密的文件已存在，是否重新解密？", "提示", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    }).catch(() => false);
    if (!confirmed) return;
  }

  try {
    item._decrypting = true;

    const requestData: { filename: string; password?: string } = {
      filename: item.uploaded.name,
    };

    if (item._password !== undefined && item._password !== null) {
      requestData.password = item._password;
    }

    const response = await decryptPdf(requestData.filename, requestData.password);

    if (response.code === 0) {
      ElMessage.success("文件解密成功");
      item._password = "";
      await loadPdfFileList();
    } else {
      if (response.msg && response.msg.includes("密码")) {
        ElMessage.error(response.msg || "密码错误，请重试");
      } else {
        ElMessage.error(response.msg || "文件解密失败");
      }
    }
  } catch (error) {
    logAndNoticeError(error as Error, "文件解密失败");
  } finally {
    item._decrypting = false;
  }
};

// 下载 PDF 文件
const handlePdfDownload = async (item: any, type: "uploaded" | "unlocked") => {
  if (!item[type]) {
    ElMessage.warning("文件不存在");
    return;
  }

  try {
    const url = getPdfDownloadUrl(item[type].name, type);
    window.open(url, "_blank");
  } catch (error) {
    logAndNoticeError(error as Error, "下载文件失败");
  }
};

// 删除 PDF 文件
const handlePdfDelete = async (item: any) => {
  if (!item.uploaded) {
    ElMessage.warning("请先上传文件");
    return;
  }

  const confirmed = await ElMessageBox.confirm("确定要删除该文件吗？", "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).catch(() => false);

  if (!confirmed) return;

  try {
    pdfLoading.value = true;
    const response = await deletePdf(item.uploaded.name, "both");

    if (response.code === 0) {
      ElMessage.success("文件删除成功");
      await loadPdfFileList();
    } else {
      ElMessage.error(response.msg || "文件删除失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "删除文件失败");
  } finally {
    pdfLoading.value = false;
  }
};

// 格式化 PDF 文件大小
const formatPdfFileSize = formatSize;

// 格式化 PDF 时间
const formatPdfTime = (timestamp: number) => {
  if (!timestamp) return "-";
  return new Date(timestamp * 1000).toLocaleString();
};

// ========== 媒体工具相关方法 ==========

// 处理媒体工具文件选择确认
const handleMediaFileBrowserConfirm = async (filePaths: string[]) => {
  if (!mediaCurrentTask.value) {
    return;
  }

  if (filePaths.length === 0) {
    return;
  }

  try {
    mediaLoading.value = true;
    for (const filePath of filePaths) {
      const response = await addFileToMediaTask(mediaCurrentTask.value.task_id, filePath);

      if (response.code !== 0) {
        ElMessage.error(`添加文件失败: ${response.msg || "未知错误"}`);
        break;
      }
    }

    ElMessage.success(`成功添加 ${filePaths.length} 个文件`);
    await handleMediaViewTask(mediaCurrentTask.value.task_id);
  } catch (error) {
    logAndNoticeError(error as Error, "添加文件失败");
  } finally {
    mediaLoading.value = false;
  }
};

// 加载媒体任务列表
const loadMediaTaskList = async () => {
  try {
    mediaLoading.value = true;
    const response = await getMediaTaskList();
    if (response.code === 0) {
      mediaTaskList.value = response.data.tasks || [];
      if (mediaTaskList.value.length > 0 && !mediaCurrentTask.value) {
        await handleMediaViewTask(mediaTaskList.value[0].task_id);
      }
    } else {
      ElMessage.error(response.msg || "获取任务列表失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "获取任务列表失败");
  } finally {
    mediaLoading.value = false;
  }
};

// 创建媒体任务
const handleMediaCreateTask = async () => {
  try {
    mediaLoading.value = true;
    const response = await createMediaTask();

    if (response.code === 0) {
      ElMessage.success("任务创建成功");
      await loadMediaTaskList();
      handleMediaViewTask(response.data.task_id);
    } else {
      ElMessage.error(response.msg || "创建任务失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "创建任务失败");
  } finally {
    mediaLoading.value = false;
  }
};

// 查看媒体任务
const handleMediaViewTask = async (taskId: string) => {
  if (mediaCurrentTask.value && mediaCurrentTask.value.task_id !== taskId) {
    handleMediaStopPlay();
  }
  try {
    mediaLoading.value = true;
    const response = await getMediaTask(taskId);
    if (response.code === 0) {
      mediaCurrentTask.value = response.data;
    } else {
      ElMessage.error(response.msg || "获取任务信息失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "获取任务信息失败");
  } finally {
    mediaLoading.value = false;
  }
};

// 删除媒体任务
const handleMediaDeleteTask = async (taskId: string) => {
  const confirmed = await ElMessageBox.confirm("确定要删除该任务吗？", "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).catch(() => false);

  if (!confirmed) return;

  try {
    mediaLoading.value = true;
    const response = await deleteMediaTask(taskId);
    if (response.code === 0) {
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
      ElMessage.error(response.msg || "删除任务失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "删除任务失败");
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
const handleMediaRemoveFile = async (fileIndex: number) => {
  if (!mediaCurrentTask.value) {
    return;
  }

  const confirmed = await ElMessageBox.confirm("确定要删除该文件吗？", "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).catch(() => false);

  if (!confirmed) return;

  try {
    mediaLoading.value = true;
    const response = await deleteFileFromMediaTask(mediaCurrentTask.value.task_id, fileIndex);
    if (response.code === 0) {
      if (mediaPlayer.playingFileIndex.value === fileIndex) {
        handleMediaStopPlay();
      } else if (
        mediaPlayer.playingFileIndex.value !== null &&
        mediaPlayer.playingFileIndex.value > fileIndex
      ) {
        mediaPlayer.playingFileIndex.value = mediaPlayer.playingFileIndex.value - 1;
      }
      ElMessage.success("文件删除成功");
      await handleMediaViewTask(mediaCurrentTask.value.task_id);
    } else {
      ElMessage.error(response.msg || "删除文件失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "删除文件失败");
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
    const response = await startMediaTask(mediaCurrentTask.value.task_id);
    if (response.code === 0) {
      ElMessage.success("合成任务已启动");
      await loadMediaTaskList();
      await handleMediaViewTask(mediaCurrentTask.value.task_id);
      startMediaPollingTaskStatus();
    } else {
      ElMessage.error(response.msg || "启动任务失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "启动任务失败");
  } finally {
    mediaLoading.value = false;
  }
};

// 轮询媒体任务状态
let mediaPollingTimer: ReturnType<typeof setInterval> | null = null;
const startMediaPollingTaskStatus = () => {
  if (mediaPollingTimer) {
    clearInterval(mediaPollingTimer);
  }
  mediaPollingTimer = setInterval(async () => {
    if (!mediaCurrentTask.value || mediaCurrentTask.value.status !== "processing") {
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
const downloadMediaResult = (taskId: string) => {
  if (!taskId) return;
  const url = getMediaTaskDownloadUrl(taskId);
  window.open(url, "_blank");
};

// 下载媒体结果
const handleMediaDownloadResult = () => {
  if (!mediaCurrentTask.value?.result_file) return;
  downloadMediaResult(mediaCurrentTask.value.task_id);
};

// 从任务列表下载媒体结果
const handleMediaDownloadResultFromList = (task: any) => {
  if (!task?.result_file) return;
  downloadMediaResult(task.task_id);
};

// 清理浏览器音频播放器状态（统一清理所有播放）
const clearBrowserAudioPlayer = () => {
  mediaPlayer.clear();
};

// 检查文件是否正在播放
const isFilePlaying = (fileItem: any): boolean => {
  if (!fileItem) {
    return false;
  }
  const filePath = fileItem?.path || fileItem?.name || "";
  return mediaPlayer.isFilePlaying(filePath);
};

// 获取文件播放进度
const getFilePlayProgress = (fileItem: any): number => {
  if (!fileItem) {
    return 0;
  }
  const filePath = fileItem?.path || fileItem?.name || "";
  return mediaPlayer.getFilePlayProgress(filePath);
};

// 获取文件时长
const getFileDuration = (fileItem: any): number => {
  if (!fileItem) {
    return 0;
  }
  const filePath = fileItem?.path || fileItem?.name || "";
  // 确定回退值：优先使用文件本身的duration属性，对于结果文件则使用任务中的 result_duration
  let fallbackDuration = fileItem.duration;
  if (fallbackDuration === undefined && mediaCurrentTask.value?.result_file === filePath) {
    fallbackDuration = mediaCurrentTask.value?.result_duration;
  }
  return mediaPlayer.getFileDuration(filePath, fallbackDuration || 0);
};

// 处理文件进度条拖拽
const handleSeekFile = (fileItem: any, percentage: number) => {
  if (!fileItem) return;
  const filePath = fileItem?.path || fileItem?.name || "";
  mediaPlayer.seekFile(filePath, percentage);
};

// 播放/暂停媒体文件
const handleMediaTogglePlayFile = (index: number) => {
  if (
    !mediaCurrentTask.value ||
    !mediaCurrentTask.value.files ||
    index < 0 ||
    index >= mediaCurrentTask.value.files.length
  ) {
    return;
  }

  const file = mediaCurrentTask.value.files[index];
  const filePath = file.path || file.name || "";
  if (!filePath) {
    ElMessage.warning("文件路径不存在");
    return;
  }

  // 如果点击的是正在播放的文件，则停止播放
  if (
    mediaPlayer.playingFilePath.value === filePath &&
    mediaPlayer.audio &&
    !mediaPlayer.audio.paused
  ) {
    clearBrowserAudioPlayer();
    ElMessage.info("已停止播放");
    return;
  }

  const audioUrl = getMediaFileUrl(filePath);
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
  mediaPlayer.play().catch(error => {
    logAndNoticeError(error as Error, "播放失败");
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
  if (
    mediaPlayer.playingFilePath.value === resultFilePath &&
    mediaPlayer.audio &&
    !mediaPlayer.audio.paused
  ) {
    clearBrowserAudioPlayer();
    ElMessage.info("已停止播放");
    return;
  }

  const audioUrl = getMediaFileUrl(resultFilePath);
  if (!audioUrl) {
    ElMessage.error("无法生成媒体文件URL");
    return;
  }

  // 加载/更换播放文件
  mediaPlayer.load(audioUrl, {
    playingFilePath: resultFilePath,
  });

  // 开始播放
  mediaPlayer.play().catch(error => {
    logAndNoticeError(error as Error, "播放失败");
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
const handleMediaSaveResultConfirm = async (filePaths: string[]) => {
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
    const response = await saveMediaTaskResult(mediaCurrentTask.value.task_id, targetDir);

    if (response.code === 0) {
      ElMessage.success("转存成功");
      mediaSaveResultDialogVisible.value = false;
    } else {
      ElMessage.error(response.msg || "转存失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "转存失败");
  } finally {
    mediaLoading.value = false;
  }
};

// 格式化媒体文件大小（使用统一的 formatSize 函数）
const formatMediaFileSize = formatSize;

// 媒体状态映射
const MEDIA_STATUS_MAP: Record<string, { tag: string; text: string }> = {
  pending: { tag: "info", text: "等待中" },
  processing: { tag: "warning", text: "处理中" },
  success: { tag: "success", text: "成功" },
  failed: { tag: "danger", text: "失败" },
};

// 获取媒体状态标签类型
const getMediaStatusTagType = (status: string): string => {
  return MEDIA_STATUS_MAP[status]?.tag || "info";
};

// 获取媒体状态文本
const getMediaStatusText = (status: string): string => {
  return MEDIA_STATUS_MAP[status]?.text || "未知";
};

// 检查媒体文件顺序是否改变
const isMediaOrderChanged = (original: any[], current: any[]): boolean => {
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
    if (
      mediaCurrentTask.value &&
      mediaCurrentTask.value.files &&
      mediaCurrentTask.value.files.length > 0
    ) {
      const hasChanged = isMediaOrderChanged(
        mediaFilesOriginalOrder.value || [],
        mediaCurrentTask.value.files
      );
      if (hasChanged) {
        try {
          mediaLoading.value = true;
          const fileIndices = mediaCurrentTask.value.files.map((_: any, index: number) => index);
          const response = await reorderMediaTaskFiles(mediaCurrentTask.value.task_id, fileIndices);

          if (response.code === 0) {
            ElMessage.success("排序已保存");
            await handleMediaViewTask(mediaCurrentTask.value.task_id);
          } else {
            ElMessage.error(response.msg || "保存排序失败");
          }
        } catch (error) {
          logAndNoticeError(error as Error, "保存排序失败");
        } finally {
          mediaLoading.value = false;
        }
      }
      mediaFilesOriginalOrder.value = null;
    }
  } else {
    if (
      mediaCurrentTask.value &&
      mediaCurrentTask.value.files &&
      mediaCurrentTask.value.files.length > 0
    ) {
      mediaFilesOriginalOrder.value = [...(mediaCurrentTask.value.files || [])];
    }
  }
  mediaFilesDragMode.value = !mediaFilesDragMode.value;
};

// 处理媒体文件拖拽开始
const handleMediaFileDragStart = (event: DragEvent, index: number) => {
  if (!mediaFilesDragMode.value) {
    event.preventDefault();
    return false;
  }
  try {
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", index.toString());
    }
  } catch (e) {
    console.error("拖拽开始失败:", e);
  }
};

// 处理媒体文件拖拽结束
const handleMediaFileDragEnd = (event: DragEvent) => {
  if (event.currentTarget) {
    clearDragStyles(event.currentTarget as HTMLElement);
  }
};

// 处理媒体文件拖拽悬停
const handleMediaFileDragOver = (event: DragEvent) => {
  if (!mediaFilesDragMode.value) {
    return;
  }
  event.preventDefault();
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = "move";
  }
  if (event.currentTarget) {
    const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
    const mouseY = event.clientY;
    const elementCenterY = rect.top + rect.height / 2;

    clearDragStyles(event.currentTarget as HTMLElement);

    if (mouseY < elementCenterY) {
      (event.currentTarget as HTMLElement).classList.add("border-t-2", "border-blue-500");
    } else {
      (event.currentTarget as HTMLElement).classList.add("border-b-2", "border-blue-500");
    }
  }
};

// 处理媒体文件拖拽放置
const handleMediaFileDrop = (event: DragEvent, targetIndex: number) => {
  if (!mediaFilesDragMode.value) {
    return;
  }
  event.preventDefault();
  if (event.currentTarget) {
    clearDragStyles(event.currentTarget as HTMLElement);
    clearAllDragStyles((event.currentTarget as HTMLElement).parentElement);
  }

  if (!event.dataTransfer) return;
  const sourceIndex = parseInt(event.dataTransfer.getData("text/plain"), 10);

  if (sourceIndex === targetIndex || isNaN(sourceIndex)) {
    return;
  }

  if (
    !mediaCurrentTask.value ||
    !mediaCurrentTask.value.files ||
    sourceIndex < 0 ||
    sourceIndex >= mediaCurrentTask.value.files.length ||
    targetIndex < 0 ||
    targetIndex >= mediaCurrentTask.value.files.length
  ) {
    return;
  }

  // 计算插入位置
  const rect = (event.currentTarget as HTMLElement)?.getBoundingClientRect();
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
    files: list,
  };
};

// 关闭文件浏览器
const handleMediaCloseFileBrowser = () => {
  mediaFileBrowserDialogVisible.value = false;
};

// 监听页签切换
const handleTabChange = (tabName: string) => {
  if (tabName === "pdf_tool" && pdfFileList.value.length === 0) {
    loadPdfFileList();
  } else if (tabName === "audio_merge" && mediaTaskList.value.length === 0) {
    loadMediaTaskList();
  }
};

onMounted(() => {
  // 根据当前页签加载相应数据
  if (activeMainTab.value === "pdf_tool") {
    loadPdfFileList();
  } else if (activeMainTab.value === "audio_merge") {
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
</script>
