<template>
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
          <el-button type="info" size="small" plain @click="loadPdfFileList" :loading="pdfLoading">
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
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { UploadFile } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";
import { formatSize } from "@/utils/format";
import { logAndNoticeError } from "@/utils/error";
import { getPdfList, uploadPdf, decryptPdf, getPdfDownloadUrl, deletePdf } from "@/api/pdf";

interface PdfFileInfo {
  name: string;
  size?: number;
  modified?: string;
}

interface PdfFileWithDetails {
  id: number;
  name: string;
  path: string;
  uploaded?: PdfFileInfo;
  unlocked?: PdfFileInfo;
  has_unlocked?: boolean;
  _decrypting?: boolean;
  _password?: string;
  [key: string]: unknown;
}

// PDF 工具相关状态
const pdfLoading = ref(false);
const pdfFileList = ref<PdfFileWithDetails[]>([]);
const pdfUploadFile = ref<File | null>(null);
const pdfUploadFilePath = ref("");

// 获取 PDF 文件列表
const loadPdfFileList = async () => {
  try {
    pdfLoading.value = true;
    const response = await getPdfList();
    if (response.code === 0) {
      const files = (response.data.files || []) as unknown as PdfFileWithDetails[];
      pdfFileList.value = files.map((item: PdfFileWithDetails) => ({
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
const handlePdfFileChange = (file: UploadFile) => {
  if (file.raw) {
    pdfUploadFile.value = file.raw;
    pdfUploadFilePath.value = file.raw.name;
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
const handlePdfDecrypt = async (item: PdfFileWithDetails) => {
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
const handlePdfDownload = async (item: PdfFileWithDetails, type: "uploaded" | "unlocked") => {
  const file = item[type];
  if (!file) {
    ElMessage.warning("文件不存在");
    return;
  }

  try {
    const url = getPdfDownloadUrl(file.name, type);
    window.open(url, "_blank");
  } catch (error) {
    logAndNoticeError(error as Error, "下载文件失败");
  }
};

// 删除 PDF 文件
const handlePdfDelete = async (item: PdfFileWithDetails) => {
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

onMounted(() => {
  loadPdfFileList();
});
</script>
