<template>
  <div class="flex gap-4 h-[calc(100vh-220px)] min-w-0 overflow-hidden">
    <!-- 左侧：任务列表 -->
    <div class="w-64 shrink-0 border rounded p-3 flex flex-col">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-base font-semibold">任务列表</h3>
        <div class="flex items-center gap-1">
          <el-button
            type="info"
            v-bind="smallIconButtonProps"
            @click="loadTaskList"
            :loading="loading"
          >
            <el-icon v-if="!loading">
              <Refresh />
            </el-icon>
          </el-button>
          <el-button
            type="success"
            v-bind="smallIconButtonProps"
            @click="handleCreateTask"
            :loading="loading"
          >
            <el-icon v-if="!loading">
              <Plus />
            </el-icon>
          </el-button>
        </div>
      </div>
      <div
        v-if="taskList && taskList.length > 0"
        class="flex-1 overflow-y-auto space-y-2 pr-1 min-h-100"
      >
        <div
          v-for="task in taskList"
          :key="task.task_id"
          class="border rounded px-3 py-2 cursor-pointer hover:bg-gray-50 group min-h-15 flex flex-col justify-between"
          :class="{
            'border-blue-500 bg-blue-50':
              currentTask && task.task_id === currentTask.task_id,
          }"
          @click="handleViewTask(task.task_id)"
        >
          <!-- 第一行：名称 -->
          <div class="flex items-center justify-between gap-2">
            <div class="text-sm font-medium truncate flex-1 min-w-0" :title="task.name || task.task_id">
              {{ task.name || task.task_id }}
            </div>
          </div>
          <!-- 第二行：状态、删除按钮 -->
          <div class="flex items-center justify-between gap-2 min-h-5">
            <el-tag
              :type="getStatusTagType(task.status)"
              size="small"
              class="h-5! text-xs! w-16 text-center"
            >
              {{ getStatusText(task.status) }}
            </el-tag>
            <div class="flex items-center gap-1 shrink-0">
              <el-button
                type="danger"
                v-bind="smallTextButtonProps"
                @click.stop="handleDeleteTask(task.task_id)"
                :disabled="task.status === 'processing'"
              >
                <el-icon>
                  <Delete />
                </el-icon>
              </el-button>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="flex-1 flex items-center justify-center text-sm text-gray-400 min-h-100">
        暂无任务，请点击"新建"创建
      </div>
    </div>

    <!-- 中间：文件信息 -->
    <div class="flex-1 min-w-0 border rounded p-3 flex flex-col min-h-0" v-if="currentTask">
      <div class="flex items-center justify-between mb-3 shrink-0">
        <h3 class="text-base font-semibold">文件信息: {{ currentTask.name || currentTask.task_id }}</h3>
      </div>
      <div class="flex-1 flex flex-col gap-3 min-h-0">
        <!-- 任务信息 -->
        <div class="flex items-center gap-4 shrink-0">
          <el-tag
            :type="getStatusTagType(currentTask.status)"
            size="small"
            class="w-16 text-center shrink-0"
          >
            {{ getStatusText(currentTask.status) }}
          </el-tag>
          <el-tooltip
            v-if="currentTask.error_message"
            :content="`错误: ${currentTask.error_message}`"
            placement="top"
            class="min-w-0 max-w-md"
          >
            <span class="text-red-500 text-xs truncate block max-w-md cursor-help">
              错误: {{ currentTask.error_message }}
            </span>
          </el-tooltip>
        </div>

        <!-- 上传文件 -->
        <div class="border rounded p-3 flex flex-col gap-2 w-full min-w-0 min-h-20">
          <div class="flex items-start justify-between gap-3 min-w-0">
            <div class="flex items-center gap-2 min-w-0 flex-1 h-6">
              <h4 class="text-sm font-semibold leading-5">上传文件</h4>
            </div>
            <el-button
              type="success"
              size="small"
              plain
              class="!h-5 !text-xs !px-2 shrink-0"
              @click="handlePreview(currentTask)"
              :disabled="!currentTask.uploaded_info"
            >
              预览
            </el-button>
          </div>
          <div v-if="currentTask.uploaded_info" class="text-sm text-gray-600">
            <div class="truncate" :title="currentTask.uploaded_info.name">
              {{ currentTask.uploaded_info.name }}
            </div>
            <div class="flex items-center gap-2 text-xs text-gray-500 mt-1">
              <span>大小: {{ formatSize(currentTask.uploaded_info.size ?? 0) }}</span>
              <span>修改: {{ formatTime(currentTask.uploaded_info.modified) }}</span>
            </div>
          </div>
          <div v-else class="text-sm text-gray-400">文件信息不可用</div>
        </div>

        <!-- 输出文件 -->
        <div v-if="currentTask.output_info" class="border rounded p-3 flex flex-col gap-2 w-full min-w-0 min-h-20">
          <h4 class="text-sm font-semibold">排版结果</h4>
          <div class="text-sm text-gray-600">
            <div class="truncate" :title="currentTask.output_info.name">
              {{ currentTask.output_info.name }}
            </div>
            <div class="flex items-center gap-2 text-xs text-gray-500 mt-1">
              <span>大小: {{ formatSize(currentTask.output_info.size ?? 0) }}</span>
            </div>
          </div>
          <a
            v-if="currentTask.output_info"
            class="text-xs text-blue-600 hover:text-blue-800"
            :href="getDownloadUrl(currentTask.uploaded_info?.name || currentTask.task_id, 'output')"
            target="_blank"
            rel="noopener noreferrer"
          >
            下载排版结果
          </a>
        </div>
      </div>
    </div>

    <!-- 中间：空状态 -->
    <div class="flex-1 min-w-0 border rounded p-3 flex flex-col" v-else>
      <div class="flex items-center justify-between mb-3 shrink-0">
        <h3 class="text-base font-semibold">文件信息</h3>
      </div>
      <div class="flex-1 flex items-center justify-center text-sm text-gray-400">
        请从左侧选择一个任务查看文件信息
      </div>
    </div>

    <!-- 右侧：排版操作 -->
    <div class="w-80 shrink-0 border rounded p-3 flex flex-col" v-if="currentTask">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-base font-semibold">排版操作</h3>
      </div>
      <div class="flex-1 overflow-auto flex flex-col gap-3">
        <!-- 操作按钮 -->
        <div class="border rounded p-3 flex flex-col gap-2">
          <el-button
            type="success"
            v-bind="mediumTextButtonProps"
            @click="handleProcess"
            :disabled="isProcessDisabled"
            :loading="isTaskProcessing"
            class="w-full"
          >
            开始排版
          </el-button>
        </div>

        <!-- 排版进度 -->
        <div
          v-if="currentTask.status === 'processing'"
          class="border rounded p-3 flex flex-col gap-2"
        >
          <h4 class="text-sm font-semibold">排版进度</h4>
          <el-progress :percentage="50" indeterminate />
          <div class="text-sm text-gray-400">正在处理中，请稍候...</div>
        </div>

        <!-- 排版结果 -->
        <div
          v-if="currentTask.status === 'success'"
          class="border rounded p-3 flex flex-col gap-2"
        >
          <h4 class="text-sm font-semibold">排版结果</h4>
          <div class="text-sm text-gray-600">
            <div>排版完成！</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧：空状态 -->
    <div class="w-80 shrink-0 border rounded p-3 flex flex-col" v-else>
      <h3 class="text-base font-semibold mb-3">排版操作</h3>
      <div class="flex-1 flex items-center justify-center text-sm text-gray-400">
        请从左侧选择一个任务进行操作
      </div>
    </div>

    <!-- 上传/创建任务对话框 -->
    <el-dialog
      v-model="createDialogVisible"
      title="上传 PDF 文件"
      width="400px"
      @close="handleDialogClose"
    >
      <el-form>
        <el-form-item label="选择文件">
          <el-upload
            :auto-upload="false"
            :on-change="handleFileChange"
            :show-file-list="false"
            accept=".pdf"
          >
            <template #trigger>
              <el-button type="primary" size="small">选择文件</el-button>
            </template>
          </el-upload>
        </el-form-item>
        <div v-if="selectedFile" class="text-sm text-gray-600 mb-2">
          已选择: {{ selectedFile.name }}
        </div>
        <el-progress
          v-if="uploadProgress > 0 && uploadProgress < 100"
          :percentage="uploadProgress"
        />
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleUploadConfirm" :loading="loading" :disabled="!selectedFile">
          上传
        </el-button>
      </template>
    </el-dialog>

    <!-- PDF 预览弹窗 -->
    <el-dialog v-model="previewVisible" fullscreen :show-close="false" destroy-on-close
      class="m-0! p-0! [&_.el-dialog__header]:hidden [&_.el-dialog__body]:p-0! [&_.el-dialog__body]:h-screen [&_.el-dialog__body]:overflow-hidden">
      <div v-loading="previewLoading" element-loading-text="加载中..." class="flex h-full flex-col bg-black">
        <!-- 顶部栏 -->
        <div class="flex items-center justify-between px-4 py-2 bg-gray-900 text-white shrink-0">
          <div class="flex items-center gap-3">
            <el-button circle size="small" @click="previewVisible = false"
              class="border-none! bg-white/10! text-white! hover:bg-white/20!">
              <el-icon><Close /></el-icon>
            </el-button>
            <span class="text-sm font-medium truncate max-w-60">{{ previewFileName }}</span>
            <span class="text-xs text-gray-400">{{ previewPages.length }} 页</span>
          </div>
          <div class="flex items-center gap-2">
            <el-button size="small" :disabled="previewCurrentPage <= 1" @click="previewCurrentPage--"
              class="border-none! bg-white/10! text-white! hover:bg-white/20!">
              <el-icon><ArrowLeft /></el-icon>
            </el-button>
            <span class="text-xs">{{ previewCurrentPage }} / {{ previewPages.length }}</span>
            <el-button size="small" :disabled="previewCurrentPage >= previewPages.length"
              @click="previewCurrentPage++"
              class="border-none! bg-white/10! text-white! hover:bg-white/20!">
              <el-icon><ArrowRight /></el-icon>
            </el-button>
          </div>
        </div>
        <!-- 主体：两栏布局 -->
        <div class="flex flex-1 min-h-0 overflow-hidden">
          <!-- 左侧缩略图列表 -->
          <div class="w-44 shrink-0 bg-gray-900 overflow-y-auto p-2">
            <div v-for="(page, index) in previewPages" :key="index"
              class="flex items-center gap-2 p-2 mb-1 rounded cursor-pointer transition-colors"
              :class="previewCurrentPage === index + 1 ? 'bg-blue-600/30 ring-1 ring-blue-500' : 'hover:bg-white/10'"
              @click="previewCurrentPage = index + 1">
              <div
                class="w-5 h-5 flex items-center justify-center rounded-full text-xs font-bold shrink-0"
                :class="previewCurrentPage === index + 1 ? 'bg-blue-500 text-white' : 'bg-white/20 text-gray-300'">
                {{ index + 1 }}
              </div>
              <div class="w-16 h-12 shrink-0">
                <el-image :src="page.thumbnail" fit="cover" class="w-full h-full rounded bg-gray-800">
                  <template #error>
                    <div class="w-full h-full flex items-center justify-center bg-gray-800 text-gray-500">
                      <el-icon><Picture /></el-icon>
                    </div>
                  </template>
                </el-image>
              </div>
            </div>
            <el-empty v-if="previewPages.length === 0" :image-size="60" description="暂无页面" class="text-gray-500" />
          </div>
          <!-- 右侧大图预览 -->
          <div class="flex-1 flex items-center justify-center bg-gray-800 p-4 overflow-auto">
            <div v-if="previewCurrentPage <= previewPages.length && previewPages[previewCurrentPage - 1]"
              class="max-w-full max-h-full">
              <el-image :src="previewPages[previewCurrentPage - 1].largeImage" fit="contain"
                class="max-w-full max-h-full shadow-xl">
                <template #error>
                  <div class="w-150 h-150 flex items-center justify-center bg-gray-700 text-gray-500">
                    <el-icon :size="80"><Picture /></el-icon>
                  </div>
                </template>
              </el-image>
            </div>
            <el-empty v-else :image-size="80" description="请选择页面" class="text-gray-500" />
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { UploadFile } from "element-plus";
import { Refresh, Plus, Delete, Close, ArrowLeft, ArrowRight, Picture } from "@element-plus/icons-vue";
import { formatSize } from "@/utils/format";
import { logAndNoticeError } from "@/utils/error";
import { loadPdfDocument, renderPdfPageToDataUrl } from "@/utils/pdf-lib";
import { useControllableInterval } from "@/composables/useInterval";
import {
  getPdfLayoutList,
  uploadPdfLayout,
  processPdfLayout,
  getPdfLayoutTaskStatus,
  getPdfLayoutDownloadUrl,
  deletePdfLayout,
} from "@/api/api-pdf-layout";
import type { PdfLayoutTask } from "@/types/tools/pdf-layout";

interface PreviewPage {
  id: string;
  thumbnail: string;
  largeImage: string;
}

// 状态映射
const STATUS_MAP: Record<string, { tag: string; text: string }> = {
  uploaded: { tag: "info", text: "已上传" },
  pending: { tag: "info", text: "等待" },
  processing: { tag: "warning", text: "处理" },
  success: { tag: "success", text: "成功" },
  failed: { tag: "danger", text: "失败" },
};

// 按钮样式
const smallIconButtonProps = { size: "small" as const, plain: true, class: "!w-8 !h-6 !p-0" };
const smallTextButtonProps = { size: "small" as const, plain: true, class: "!h-5 !text-xs !px-2" };
const mediumTextButtonProps = { size: "small" as const, plain: true, class: "!h-7 !text-xs" };

// 页面状态
const loading = ref(false);
const taskList = ref<PdfLayoutTask[]>([]);
const currentTask = ref<PdfLayoutTask | null>(null);

// 上传相关
const createDialogVisible = ref(false);
const selectedFile = ref<File | null>(null);
const uploadProgress = ref(0);

// 预览相关
const previewVisible = ref(false);
const previewLoading = ref(false);
const previewFileName = ref("");
const previewCurrentPage = ref(1);
const previewPages = ref<PreviewPage[]>([]);

// 辅助函数
const basename = (path: string) => path.split("/").pop() || path;
const getStatusTagType = (status: string) => STATUS_MAP[status]?.tag ?? "info";
const getStatusText = (status: string) => STATUS_MAP[status]?.text ?? status;

const confirmAction = (message: string, title = "提示") =>
  ElMessageBox.confirm(message, title, {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  })
    .then(() => true)
    .catch(() => false);

const withLoading = async (action: () => Promise<void>, errorMessage: string) => {
  try {
    loading.value = true;
    await action();
  } catch (error) {
    logAndNoticeError(error as Error, errorMessage);
  } finally {
    loading.value = false;
  }
};

// 计算属性
const isTaskProcessing = computed(() => currentTask.value?.status === "processing");
const isProcessDisabled = computed(() => {
  const task = currentTask.value;
  if (!task || isTaskProcessing.value) return true;
  return !task.uploaded_info || task.status === "pending";
});

// 应用任务数据到当前视图
const applyTask = (task: PdfLayoutTask) => {
  currentTask.value = task;
  const index = taskList.value.findIndex(item => item.task_id === task.task_id);
  if (index >= 0) taskList.value[index] = { ...task };
};

// 加载任务列表
const loadTaskList = () =>
  withLoading(async () => {
    const response = await getPdfLayoutList();
    if (response.code === 0) {
      const tasks = (response.data || []) as PdfLayoutTask[];
      taskList.value = tasks;
      if (!currentTask.value && taskList.value.length) {
        await syncTask(taskList.value[0].task_id);
      }
    } else {
      ElMessage.error(response.msg || "获取任务列表失败");
    }
  }, "获取任务列表失败");

// 同步任务信息
const syncTask = async (taskId?: string) => {
  const id = taskId ?? currentTask.value?.task_id;
  if (!id) return;
  try {
    const response = await getPdfLayoutTaskStatus(id);
    if (response.code === 0) {
      applyTask(response.data as PdfLayoutTask);
    }
  } catch (error) {
    logAndNoticeError(error as Error, "获取任务信息失败");
  }
};

// 查看任务
const handleViewTask = async (taskId: string) => {
  await syncTask(taskId);
};

// 创建任务（打开上传对话框）
const handleCreateTask = () => {
  selectedFile.value = null;
  uploadProgress.value = 0;
  createDialogVisible.value = true;
};

const handleDialogClose = () => {
  selectedFile.value = null;
  uploadProgress.value = 0;
};

const handleFileChange = (file: UploadFile) => {
  if (file.raw) {
    selectedFile.value = file.raw;
    uploadProgress.value = 0;
  }
};

// 上传确认
const handleUploadConfirm = async () => {
  if (!selectedFile.value) {
    ElMessage.warning("请选择文件");
    return;
  }
  await withLoading(async () => {
    uploadProgress.value = 0;
    const response = await uploadPdfLayout(selectedFile.value!, p => {
      uploadProgress.value = p;
    });
    if (response.code === 0) {
      uploadProgress.value = 100;
      ElMessage.success("文件上传成功");
      createDialogVisible.value = false;
      selectedFile.value = null;
      await loadTaskList();
      const task = response.data as PdfLayoutTask;
      if (task?.task_id) await syncTask(task.task_id);
    } else {
      ElMessage.error(response.msg || "文件上传失败");
    }
  }, "文件上传失败");
};

// 删除任务
const handleDeleteTask = async (taskId: string) => {
  if (!(await confirmAction("确定要删除该任务吗？"))) return;
  await withLoading(async () => {
    const response = await deletePdfLayout(taskId);
    if (response.code === 0) {
      ElMessage.success("任务删除成功");
      taskList.value = (await getPdfLayoutList()).data as PdfLayoutTask[] || [];
      if (currentTask.value?.task_id !== taskId) return;
      if (taskList.value.length) await syncTask(taskList.value[0].task_id);
      else currentTask.value = null;
    } else {
      ElMessage.error(response.msg || "删除任务失败");
    }
  }, "删除任务失败");
};

// 开始排版
const handleProcess = async () => {
  const task = currentTask.value;
  if (!task) return;
  if (!task.uploaded_info) return ElMessage.warning("没有可处理的文件");
  if (!(await confirmAction(`确定要排版 "${task.name || task.task_id}" 吗?`, "确认排版"))) return;

  await withLoading(async () => {
    const response = await processPdfLayout(task!.task_id);
    if (response.code === 0) {
      ElMessage.success("排版任务已启动");
      taskList.value = (await getPdfLayoutList()).data as PdfLayoutTask[] || [];
      await syncTask();
      startPolling();
    } else {
      ElMessage.error(response.msg || "启动排版失败");
    }
  }, "启动排版失败");
};

// 轮询
const { start: startPolling, stop: stopPolling } = useControllableInterval(async () => {
  const task = currentTask.value;
  if (!task?.task_id) return stopPolling();
  try {
    const response = await getPdfLayoutTaskStatus(task.task_id);
    if (response.code === 0) {
      applyTask(response.data as PdfLayoutTask);
      if (response.data.status !== "processing") {
        taskList.value = (await getPdfLayoutList()).data as PdfLayoutTask[] || [];
        stopPolling();
      }
    }
  } catch (error) {
    logAndNoticeError(error as Error, "刷新任务状态失败");
  }
}, 1000);

// 下载 URL
const getDownloadUrl = (filename: string, type: "uploaded" | "output") => {
  return getPdfLayoutDownloadUrl(filename, type);
};

// 预览 PDF
const handlePreview = async (item: PdfLayoutTask) => {
  if (!item.uploaded_info) {
    ElMessage.warning("文件不存在");
    return;
  }

  previewLoading.value = true;
  previewVisible.value = true;
  previewFileName.value = item.uploaded_info.name;
  previewCurrentPage.value = 1;
  previewPages.value = [];

  try {
    const url = getPdfLayoutDownloadUrl(item.uploaded_info.name, "uploaded");
    if (!url) {
      ElMessage.error("无法获取文件地址");
      previewLoading.value = false;
      return;
    }

    const pdf = await loadPdfDocument(url);
    const pages: PreviewPage[] = [];

    for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
      const page = await pdf.getPage(pageNum);
      const thumbnail = await renderPdfPageToDataUrl(page, {
        scale: 0.3,
        mimeType: "image/jpeg",
        quality: 0.7,
      });
      const largeImage = await renderPdfPageToDataUrl(page, {
        scale: 1.5,
        mimeType: "image/jpeg",
        quality: 0.9,
      });
      pages.push({ id: String(pageNum), thumbnail, largeImage });
    }

    previewPages.value = pages;
  } catch (error) {
    logAndNoticeError(error as Error, "加载 PDF 预览失败");
    previewVisible.value = false;
  } finally {
    previewLoading.value = false;
  }
};

// 格式化时间
const formatTime = (timestamp?: number) => {
  if (!timestamp) return "-";
  return new Date(timestamp * 1000).toLocaleString();
};

// 生命周期
onMounted(loadTaskList);
onBeforeUnmount(() => {
  stopPolling();
});
</script>
