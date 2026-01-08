<template>
  <div class="p-4 flex flex-col h-[calc(100vh-250px)]">
    <h2 class="text-xl font-semibold mb-4">PDF 解密工具</h2>

    <!-- 上传区域 -->
    <div class="mb-4 flex-shrink-0 border rounded p-3 bg-gray-50">
      <div class="flex flex-col gap-3">
        <!-- 按钮和文件信息行 -->
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
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2">
              <div
                class="text-sm truncate flex-1 min-w-0"
                :class="pdfUploadFile ? 'text-gray-600' : 'text-gray-400'"
                :title="pdfUploadFilePath || pdfUploadFile?.name"
              >
                {{ pdfUploadFilePath || pdfUploadFile?.name || "未选择文件" }}
              </div>
              <div v-if="pdfUploadElapsedTime" class="text-xs text-gray-500 flex-shrink-0">
                已用时间: {{ pdfUploadElapsedTime }}
              </div>
            </div>
          </div>
        </div>

        <!-- 进度条和取消按钮行 -->
        <div class="flex items-center gap-2">
          <el-progress
            :percentage="pdfUploadProgress"
            :status="pdfUploadProgress === 100 ? 'success' : undefined"
            class="flex-1"
          />
          <el-button
            type="danger"
            size="small"
            plain
            @click="handleCancelUpload"
            :disabled="!pdfUploadFile"
          >
            取消
          </el-button>
        </div>
      </div>
    </div>

    <!-- 文件列表 -->
    <el-card class="flex-1 flex flex-col overflow-hidden" shadow="hover">
      <template #header>
        <div class="flex items-center justify-between">
          <span>文件列表</span>
          <el-button type="info" size="small" plain @click="loadPdfFileList" :loading="pdfLoading">
            <el-icon v-if="!pdfLoading">
              <Refresh />
            </el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <div class="flex-1 overflow-auto">
        <el-table :data="pdfFileList" v-loading="pdfLoading" stripe class="w-full">
          <el-table-column prop="filename" label="文件名" min-width="200">
            <template #default="{ row }">
              <span
                v-if="row.uploaded_info"
                class="text-blue-600 cursor-pointer hover:underline"
                @click="handlePdfDownload(row, 'uploaded')"
              >
                {{ row.filename }}
              </span>
              <span v-else class="text-gray-400">-</span>
            </template>
          </el-table-column>

          <el-table-column label="上传文件" min-width="150">
            <template #default="{ row }">
              <div v-if="row.uploaded_info" class="flex flex-col gap-1">
                <span class="text-sm">{{ formatPdfFileSize(row.uploaded_info.size) }}</span>
                <span class="text-xs text-gray-500">{{
                  formatPdfTime(row.uploaded_info.modified)
                }}</span>
              </div>
              <span v-else class="text-gray-400">-</span>
            </template>
          </el-table-column>

          <el-table-column label="已解密文件" min-width="150">
            <template #default="{ row }">
              <div v-if="row.unlocked_info" class="flex flex-col gap-1">
                <span class="text-sm">{{ formatPdfFileSize(row.unlocked_info.size) }}</span>
                <span class="text-xs text-gray-500">{{
                  formatPdfTime(row.unlocked_info.modified)
                }}</span>
              </div>
              <span v-else class="text-gray-400">未解密</span>
            </template>
          </el-table-column>

          <el-table-column label="状态" width="140" align="center">
            <template #default="{ row }">
              <div class="flex flex-col gap-1 items-center">
                <el-tag v-if="row.status === 'success'" type="success" size="small">已解密</el-tag>
                <el-tag v-else-if="row.status === 'processing'" type="warning" size="small"
                  >处理中</el-tag
                >
                <el-tag v-else-if="row.status === 'pending'" type="info" size="small"
                  >等待中</el-tag
                >
                <el-tag v-else-if="row.status === 'failed'" type="danger" size="small">失败</el-tag>
                <el-tag v-else type="info" size="small">已上传</el-tag>
                <span
                  v-if="row.unlocked_info"
                  class="text-xs text-blue-600 cursor-pointer hover:underline"
                  @click="handlePdfDownload(row, 'unlocked')"
                >
                  下载
                </span>
                <span
                  v-if="row.error_message"
                  class="text-xs text-red-500"
                  :title="row.error_message"
                >
                  错误
                </span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="280" fixed="right">
            <template #default="{ row }">
              <div class="flex items-center gap-2">
                <!-- 密码输入框 -->
                <el-input
                  v-if="row.uploaded_info"
                  v-model="row._password"
                  type="password"
                  size="small"
                  placeholder="密码（可选）"
                  show-password
                  clearable
                  class="w-30"
                  :disabled="row._decrypting || row.status === 'processing'"
                  @keyup.enter="handlePdfDecrypt(row)"
                >
                </el-input>

                <!-- 解密 -->
                <el-button
                  v-if="row.uploaded_info && row.status !== 'processing'"
                  type="primary"
                  size="small"
                  @click="handlePdfDecrypt(row)"
                  :loading="row._decrypting"
                  :disabled="row._decrypting || row.status === 'processing'"
                >
                  {{ row.status === "success" ? "重新解密" : "解密" }}
                </el-button>

                <!-- 删除 -->
                <el-button
                  v-if="row.uploaded_info"
                  type="danger"
                  size="small"
                  plain
                  @click="handlePdfDelete(row)"
                  :disabled="row.status === 'processing'"
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
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { UploadFile } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import { formatSize } from "@/utils/format";
import { logAndNoticeError } from "@/utils/error";
import {
  getPdfList,
  uploadPdf,
  decryptPdf,
  getTaskStatus,
  getPdfDownloadUrl,
  deletePdf,
} from "@/api/pdf";

import type { PdfTask } from "@/types/tools";

interface PdfTaskWithUI extends PdfTask {
  _decrypting?: boolean;
  _password?: string;
}

// PDF 工具相关状态
const pdfLoading = ref(false);
const pdfFileList = ref<PdfTaskWithUI[]>([]);
const pdfUploadFile = ref<File | null>(null);
const pdfUploadFilePath = ref("");
const pdfUploadProgress = ref(0);
const pdfUploadElapsedTime = ref("");
const uploadAbortController = ref<AbortController | null>(null);
const uploadStartTime = ref<number | null>(null);
let uploadTimer: ReturnType<typeof setInterval> | null = null;

// 获取 PDF 任务列表
const loadPdfFileList = async () => {
  try {
    pdfLoading.value = true;
    const response = await getPdfList();
    if (response.code === 0) {
      const tasks = (response.data || []) as PdfTask[];
      pdfFileList.value = tasks.map(task => ({
        ...task,
        _decrypting: task.status === "processing" || false,
        _password: "",
      }));
    } else {
      ElMessage.error(response.msg || "获取任务列表失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "获取任务列表失败");
  } finally {
    pdfLoading.value = false;
  }
};

// 处理 PDF 文件选择
const handlePdfFileChange = (file: UploadFile) => {
  if (file.raw) {
    pdfUploadFile.value = file.raw;
    pdfUploadFilePath.value = file.raw.name;
    pdfUploadProgress.value = 0; // 重置进度
    pdfUploadElapsedTime.value = ""; // 重置时间
    // 如果正在上传，取消上传
    if (uploadAbortController.value) {
      handleCancelUpload();
    }
  }
};

// 格式化已用时间
const formatElapsedTime = (seconds: number): string => {
  if (seconds < 60) {
    return `${seconds}秒`;
  } else if (seconds < 3600) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}分${secs}秒`;
  } else {
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours}小时${mins}分${secs}秒`;
  }
};

// 更新已用时间显示
const updateElapsedTime = () => {
  if (
    uploadStartTime.value !== null &&
    pdfUploadProgress.value > 0 &&
    pdfUploadProgress.value < 100
  ) {
    const elapsed = Math.floor((Date.now() - uploadStartTime.value) / 1000);
    pdfUploadElapsedTime.value = formatElapsedTime(elapsed);
  }
};

// 取消上传
const handleCancelUpload = () => {
  // 如果正在上传，取消上传
  if (uploadAbortController.value && pdfLoading.value) {
    uploadAbortController.value.abort();
    uploadAbortController.value = null;
    if (uploadTimer) {
      clearInterval(uploadTimer);
      uploadTimer = null;
    }
    pdfUploadProgress.value = 0;
    pdfUploadElapsedTime.value = "";
    uploadStartTime.value = null;
    pdfLoading.value = false;
    ElMessage.info("上传已取消");
  } else {
    // 如果未在上传，删除当前选中的文件
    pdfUploadFile.value = null;
    pdfUploadFilePath.value = "";
    pdfUploadProgress.value = 0;
    pdfUploadElapsedTime.value = "";
    uploadStartTime.value = null;
    ElMessage.info("已清除选中文件");
  }
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

  // 如果已有上传在进行，先取消
  if (uploadAbortController.value) {
    handleCancelUpload();
  }

  try {
    pdfLoading.value = true;
    pdfUploadProgress.value = 0;
    pdfUploadElapsedTime.value = "";
    uploadStartTime.value = Date.now();

    // 创建 AbortController 用于取消上传
    const abortController = new AbortController();
    uploadAbortController.value = abortController;

    // 启动定时器更新已用时间
    uploadTimer = setInterval(() => {
      updateElapsedTime();
    }, 1000);

    const response = await uploadPdf(
      file,
      progress => {
        pdfUploadProgress.value = progress;
        updateElapsedTime();
      },
      abortController.signal
    );

    // 清除定时器和控制器
    if (uploadTimer) {
      clearInterval(uploadTimer);
      uploadTimer = null;
    }
    uploadAbortController.value = null;

    if (response.code === 0) {
      pdfUploadProgress.value = 100;
      // 最后更新一次时间
      updateElapsedTime();
      ElMessage.success("文件上传成功");
      // 延迟一下再清空，让用户看到 100% 的进度
      setTimeout(() => {
        pdfUploadFile.value = null;
        pdfUploadFilePath.value = "";
        pdfUploadProgress.value = 0;
        pdfUploadElapsedTime.value = "";
        uploadStartTime.value = null;
      }, 500);
      await loadPdfFileList();
    } else {
      ElMessage.error(response.msg || "文件上传失败");
      pdfUploadProgress.value = 0;
      pdfUploadElapsedTime.value = "";
      uploadStartTime.value = null;
    }
  } catch (error: any) {
    // 如果是取消操作，不显示错误
    if (
      error.name === "CanceledError" ||
      error.code === "ECONNABORTED" ||
      error.message?.includes("canceled") ||
      error.message?.includes("aborted")
    ) {
      // 取消操作已在 handleCancelUpload 中处理，但需要确保清理状态
      if (uploadTimer) {
        clearInterval(uploadTimer);
        uploadTimer = null;
      }
      // 如果控制器还存在，说明是外部取消，不需要再次调用 handleCancelUpload
      if (!uploadAbortController.value) {
        // 已经被 handleCancelUpload 清理过了
        pdfLoading.value = false;
      }
      return;
    }

    // 其他错误，保持当前进度，显示错误，但不重置进度条（让用户看到失败时的进度）
    const errorMessage = error.message || "文件上传失败";
    const currentProgress = pdfUploadProgress.value; // 保存当前进度

    if (error.code === "ERR_NETWORK" || error.message?.includes("Network Error")) {
      ElMessage.error(`网络错误：上传中断。当前进度：${currentProgress}%`);
    } else if (error.response?.status === 413) {
      ElMessage.error("文件太大，超过服务器限制（最大 1000MB）");
      // 文件太大，重置进度
      pdfUploadProgress.value = 0;
      pdfUploadElapsedTime.value = "";
    } else {
      ElMessage.error(`上传失败：${errorMessage}`);
    }

    // 停止定时器，但保持进度条显示（除非是文件太大错误）
    if (uploadTimer) {
      clearInterval(uploadTimer);
      uploadTimer = null;
    }
    uploadAbortController.value = null;
    uploadStartTime.value = null;
    pdfLoading.value = false;
    // 不重置进度条和时间（文件太大错误除外），让用户看到失败时的状态
  }
};

// 解密 PDF 文件
const handlePdfDecrypt = async (item: PdfTaskWithUI) => {
  if (!item.uploaded_info) {
    ElMessage.warning("请先上传文件");
    return;
  }

  if (item._decrypting || item.status === "processing") {
    return;
  }

  if (item.status === "success") {
    const confirmed = await ElMessageBox.confirm("已解密的文件已存在，是否重新解密？", "提示", {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    }).catch(() => false);
    if (!confirmed) return;
  }

  try {
    item._decrypting = true;

    const password = item._password?.trim() || undefined;
    const response = await decryptPdf(item.task_id, password);

    if (response.code === 0) {
      ElMessage.success(response.data?.message || "解密任务已提交，正在后台处理");
      item._password = "";
      // 轮询任务状态
      await pollTaskStatus(item);
    } else {
      ElMessage.error(response.msg || "提交解密任务失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "提交解密任务失败");
  } finally {
    item._decrypting = false;
  }
};

// 轮询任务状态
const pollTaskStatus = async (item: PdfTaskWithUI, maxAttempts = 30) => {
  let attempts = 0;
  const poll = async () => {
    if (attempts >= maxAttempts) {
      ElMessage.warning("任务处理超时，请手动刷新查看状态");
      await loadPdfFileList();
      return;
    }

    try {
      const response = await getTaskStatus(item.task_id);
      if (response.code === 0) {
        const task = response.data;
        item.status = task.status;
        item.unlocked_info = task.unlocked_info;
        item.error_message = task.error_message;

        if (task.status === "success") {
          ElMessage.success("文件解密成功");
          item._decrypting = false;
          await loadPdfFileList();
        } else if (task.status === "failed") {
          ElMessage.error(task.error_message || "文件解密失败");
          item._decrypting = false;
        } else if (task.status === "processing") {
          attempts++;
          setTimeout(poll, 1000); // 1秒后再次查询
        } else {
          item._decrypting = false;
        }
      }
    } catch (error) {
      logAndNoticeError(error as Error, "查询任务状态失败");
      item._decrypting = false;
    }
  };

  poll();
};

// 下载 PDF 文件
const handlePdfDownload = async (item: PdfTaskWithUI, type: "uploaded" | "unlocked") => {
  const fileInfo = type === "uploaded" ? item.uploaded_info : item.unlocked_info;
  if (!fileInfo) {
    ElMessage.warning("文件不存在");
    return;
  }

  try {
    const url = getPdfDownloadUrl(fileInfo.name, type);
    window.open(url, "_blank");
  } catch (error) {
    logAndNoticeError(error as Error, "下载文件失败");
  }
};

// 删除 PDF 文件
const handlePdfDelete = async (item: PdfTaskWithUI) => {
  if (!item.uploaded_info) {
    ElMessage.warning("请先上传文件");
    return;
  }

  if (item.status === "processing") {
    ElMessage.warning("任务正在处理中，无法删除");
    return;
  }

  const confirmed = await ElMessageBox.confirm("确定要删除该任务吗？", "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).catch(() => false);

  if (!confirmed) return;

  try {
    pdfLoading.value = true;
    const response = await deletePdf(item.task_id);

    if (response.code === 0) {
      ElMessage.success(response.data?.message || "任务删除成功");
      await loadPdfFileList();
    } else {
      ElMessage.error(response.msg || "任务删除失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "删除任务失败");
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

onMounted(() => {
  loadPdfFileList();
});

// 组件卸载时清理定时器
onBeforeUnmount(() => {
  if (uploadTimer) {
    clearInterval(uploadTimer);
    uploadTimer = null;
  }
  // 如果正在上传，取消上传
  if (uploadAbortController.value) {
    uploadAbortController.value.abort();
    uploadAbortController.value = null;
  }
});
</script>
