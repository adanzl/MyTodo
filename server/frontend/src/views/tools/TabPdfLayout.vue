<template>
    <div class="p-4 flex flex-col h-[calc(100vh-200px)]">
        <h2 class="text-xl font-semibold mb-4">PDF 排版工具</h2>

        <!-- 上传区域 -->
        <div class="mb-4 shrink-0 border rounded p-3 bg-gray-50">
            <div class="flex flex-col gap-3">
                <!-- 按钮和文件信息行 -->
                <div class="flex items-center gap-3">
                    <div>
                        <el-button type="success" size="small" @click="handlePdfUpload" :loading="pdfLoading"
                            :disabled="!pdfUploadFile">
                            上传
                        </el-button>
                    </div>
                    <el-upload :auto-upload="false" :on-change="handlePdfFileChange" :show-file-list="false"
                        accept=".pdf">
                        <template #trigger>
                            <el-button type="primary" size="small" class="m-0!">选择文件</el-button>
                        </template>
                    </el-upload>
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2">
                            <div class="text-sm truncate flex-1 min-w-0"
                                :class="pdfUploadFile ? 'text-gray-600' : 'text-gray-400'"
                                :title="pdfUploadFilePath || pdfUploadFile?.name">
                                {{ pdfUploadFilePath || pdfUploadFile?.name || "未选择文件" }}
                            </div>
                            <div v-if="pdfUploadElapsedTime" class="text-xs text-gray-500 shrink-0">
                                已用时间: {{ pdfUploadElapsedTime }}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- 进度条和取消按钮行 -->
                <div class="flex items-center gap-2">
                    <el-progress :percentage="pdfUploadProgress"
                        :status="pdfUploadProgress === 100 ? 'success' : undefined" class="flex-1" />
                    <el-button type="danger" size="small" plain @click="handleCancelUpload" :disabled="!pdfUploadFile">
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
                            <span v-if="row.uploaded_info" class="text-blue-600 cursor-pointer hover:underline"
                                @click="handlePdfDownload(row, 'uploaded')" :title="row.uploaded_info.name">
                                {{ row.uploaded_info.name || row.name || row.filename || row.task_id }}
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

                    <el-table-column label="排版结果" min-width="150">
                        <template #default="{ row }">
                            <div v-if="row.output_info" class="flex flex-col gap-1">
                                <span class="text-sm">{{ formatPdfFileSize(row.output_info.size) }}</span>
                                <span class="text-xs text-gray-500">{{
                                    formatPdfTime(row.output_info.modified)
                                    }}</span>
                            </div>
                            <span v-else class="text-gray-400">未处理</span>
                        </template>
                    </el-table-column>

                    <el-table-column label="状态" width="140" align="center">
                        <template #default="{ row }">
                            <div class="flex flex-col gap-1 items-center">
                                <el-tag v-if="row.status === 'success'" type="success" size="small">已处理</el-tag>
                                <el-tag v-else-if="row.status === 'processing'" type="warning" size="small">处理中</el-tag>
                                <el-tag v-else-if="row.status === 'pending'" type="info" size="small">等待中</el-tag>
                                <el-tag v-else-if="row.status === 'failed'" type="danger" size="small">失败</el-tag>
                                <el-tag v-else type="info" size="small">已上传</el-tag>
                                <span v-if="row.output_info"
                                    class="text-xs text-blue-600 cursor-pointer hover:underline"
                                    @click="handlePdfDownload(row, 'output')">
                                    下载
                                </span>
                                <span v-if="row.error_message" class="text-xs text-red-500" :title="row.error_message">
                                    错误
                                </span>
                            </div>
                        </template>
                    </el-table-column>

                    <el-table-column label="操作" width="250" fixed="right">
                        <template #default="{ row }">
                            <div class="flex items-center gap-2">
                                <!-- 预览 -->
                                <el-button v-if="row.uploaded_info" type="success" size="small" plain
                                    @click="handlePreview(row)">
                                    预览
                                </el-button>

                                <!-- 排版 -->
                                <el-button v-if="row.uploaded_info && row.status !== 'processing'" type="primary"
                                    size="small" @click="handlePdfProcess(row)" :loading="row._processing"
                                    :disabled="row._processing || row.status === 'processing'">
                                    {{ row.status === "success" ? "重新排版" : "排版" }}
                                </el-button>

                                <!-- 删除 -->
                                <el-button v-if="row.uploaded_info" type="danger" size="small" plain
                                    @click="handlePdfDelete(row)" :disabled="row.status === 'processing'">
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

        <!-- PDF 预览弹窗 -->
        <el-dialog v-model="previewVisible" fullscreen :show-close="false" destroy-on-close
            class="m-0! p-0! [&_.el-dialog__header]:hidden [&_.el-dialog__body]:p-0! [&_.el-dialog__body]:h-screen [&_.el-dialog__body]:overflow-hidden">
            <div v-loading="previewLoading" element-loading-text="加载中..."
                class="flex h-full flex-col bg-black">
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
                                <el-image :src="page.thumbnail" fit="cover"
                                    class="w-full h-full rounded bg-gray-800">
                                    <template #error>
                                        <div
                                            class="w-full h-full flex items-center justify-center bg-gray-800 text-gray-500">
                                            <el-icon><Picture /></el-icon>
                                        </div>
                                    </template>
                                </el-image>
                            </div>
                        </div>
                        <el-empty v-if="previewPages.length === 0" :image-size="60"
                            description="暂无页面" class="text-gray-500" />
                    </div>

                    <!-- 右侧大图预览 -->
                    <div class="flex-1 flex items-center justify-center bg-gray-800 p-4 overflow-auto">
                        <div v-if="previewCurrentPage <= previewPages.length && previewPages[previewCurrentPage - 1]" class="max-w-full max-h-full">
                            <el-image :src="previewPages[previewCurrentPage - 1].largeImage" fit="contain"
                                class="max-w-full max-h-full shadow-xl">
                                <template #error>
                                    <div
                                        class="w-150 h-150 flex items-center justify-center bg-gray-700 text-gray-500">
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
import { ref, onMounted, onBeforeUnmount } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { UploadFile } from "element-plus";
import { Refresh, Close, ArrowLeft, ArrowRight, Picture } from "@element-plus/icons-vue";
import { formatSize } from "@/utils/format";
import { logAndNoticeError } from "@/utils/error";
import { loadPdfDocument, renderPdfPageToDataUrl } from "@/utils/pdf-lib";
import {
    getPdfLayoutList,
    uploadPdfLayout,
    processPdfLayout,
    getPdfLayoutTaskStatus,
    getPdfLayoutDownloadUrl,
    deletePdfLayout,
} from "@/api/api-pdf-layout";

import type { PdfLayoutTask } from "@/types/tools/pdf-layout";

interface PdfLayoutTaskWithUI extends PdfLayoutTask {
    _processing?: boolean;
}

// PDF 预览相关类型
interface PreviewPage {
    id: string;
    thumbnail: string;
    largeImage: string;
}

// PDF 排版相关状态
const pdfLoading = ref(false);
const pdfFileList = ref<PdfLayoutTaskWithUI[]>([]);
const pdfUploadFile = ref<File | null>(null);
const pdfUploadFilePath = ref("");
const pdfUploadProgress = ref(0);
const pdfUploadElapsedTime = ref("");
const uploadAbortController = ref<AbortController | null>(null);
const uploadStartTime = ref<number | null>(null);
let uploadTimer: ReturnType<typeof setInterval> | null = null;

// PDF 预览相关状态
const previewVisible = ref(false);
const previewLoading = ref(false);
const previewFileName = ref("");
const previewCurrentPage = ref(1);
const previewPages = ref<PreviewPage[]>([]);

// 获取 PDF 排版任务列表
const loadPdfFileList = async () => {
    try {
        pdfLoading.value = true;
        const response = await getPdfLayoutList();
        if (response.code === 0) {
            const tasks = (response.data || []) as PdfLayoutTask[];
            pdfFileList.value = tasks.map(task => ({
                ...task,
                _processing: task.status === "processing" || false,
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
        pdfUploadProgress.value = 0;
        pdfUploadElapsedTime.value = "";
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

    if (uploadAbortController.value) {
        handleCancelUpload();
    }

    try {
        pdfLoading.value = true;
        pdfUploadProgress.value = 0;
        pdfUploadElapsedTime.value = "";
        uploadStartTime.value = Date.now();

        const abortController = new AbortController();
        uploadAbortController.value = abortController;

        uploadTimer = setInterval(() => {
            updateElapsedTime();
        }, 1000);

        const response = await uploadPdfLayout(
            file,
            progress => {
                pdfUploadProgress.value = progress;
                updateElapsedTime();
            },
            abortController.signal
        );

        if (uploadTimer) {
            clearInterval(uploadTimer);
            uploadTimer = null;
        }
        uploadAbortController.value = null;

        if (response.code === 0) {
            pdfUploadProgress.value = 100;
            updateElapsedTime();
            ElMessage.success("文件上传成功");
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
        if (
            error.name === "CanceledError" ||
            error.code === "ECONNABORTED" ||
            error.message?.includes("canceled") ||
            error.message?.includes("aborted")
        ) {
            if (uploadTimer) {
                clearInterval(uploadTimer);
                uploadTimer = null;
            }
            if (!uploadAbortController.value) {
                pdfLoading.value = false;
            }
            return;
        }

        const errorMessage = error.message || "文件上传失败";
        const currentProgress = pdfUploadProgress.value;

        if (error.code === "ERR_NETWORK" || error.message?.includes("Network Error")) {
            ElMessage.error(`网络错误：上传中断。当前进度：${currentProgress}%`);
        } else if (error.response?.status === 413) {
            ElMessage.error("文件太大，超过服务器限制（最大 1000MB）");
            pdfUploadProgress.value = 0;
            pdfUploadElapsedTime.value = "";
        } else {
            ElMessage.error(`上传失败：${errorMessage}`);
        }

        if (uploadTimer) {
            clearInterval(uploadTimer);
            uploadTimer = null;
        }
        uploadAbortController.value = null;
        uploadStartTime.value = null;
        pdfLoading.value = false;
    }
};

// 预览 PDF 文件
const handlePreview = async (item: PdfLayoutTaskWithUI) => {
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

            // 生成缩略图（小尺寸）
            const thumbnail = await renderPdfPageToDataUrl(page, {
                scale: 0.3,
                mimeType: "image/jpeg",
                quality: 0.7,
            });

            // 生成大图（高分辨率）
            const largeImage = await renderPdfPageToDataUrl(page, {
                scale: 1.5,
                mimeType: "image/jpeg",
                quality: 0.9,
            });

            pages.push({
                id: String(pageNum),
                thumbnail,
                largeImage,
            });
        }

        previewPages.value = pages;
    } catch (error) {
        logAndNoticeError(error as Error, "加载 PDF 预览失败");
        previewVisible.value = false;
    } finally {
        previewLoading.value = false;
    }
};

// 执行 PDF 排版处理
const handlePdfProcess = async (item: PdfLayoutTaskWithUI) => {
    if (!item.uploaded_info) {
        ElMessage.warning("请先上传文件");
        return;
    }

    if (item._processing || item.status === "processing") {
        return;
    }

    if (item.status === "success") {
        const confirmed = await ElMessageBox.confirm("已排版的文件已存在，是否重新处理？", "提示", {
            confirmButtonText: "确定",
            cancelButtonText: "取消",
            type: "warning",
        }).catch(() => false);
        if (!confirmed) return;
    }

    try {
        item._processing = true;

        const response = await processPdfLayout(item.task_id);

        if (response.code === 0) {
            ElMessage.success(response.data?.message || "排版任务已提交，正在后台处理");
            await pollTaskStatus(item);
        } else {
            ElMessage.error(response.msg || "提交排版任务失败");
        }
    } catch (error) {
        logAndNoticeError(error as Error, "提交排版任务失败");
    } finally {
        item._processing = false;
    }
};

// 轮询任务状态
const pollTaskStatus = async (item: PdfLayoutTaskWithUI, maxAttempts = 30) => {
    let attempts = 0;
    const poll = async () => {
        if (attempts >= maxAttempts) {
            ElMessage.warning("任务处理超时，请手动刷新查看状态");
            await loadPdfFileList();
            return;
        }

        try {
            const response = await getPdfLayoutTaskStatus(item.task_id);
            if (response.code === 0) {
                const task = response.data;
                item.status = task.status;
                item.output_info = task.output_info;
                item.error_message = task.error_message;

                if (task.status === "success") {
                    ElMessage.success("文件排版成功");
                    item._processing = false;
                    await loadPdfFileList();
                } else if (task.status === "failed") {
                    ElMessage.error(task.error_message || "文件排版失败");
                    item._processing = false;
                } else if (task.status === "processing") {
                    attempts++;
                    setTimeout(poll, 1000);
                } else {
                    item._processing = false;
                }
            }
        } catch (error) {
            logAndNoticeError(error as Error, "查询任务状态失败");
            item._processing = false;
        }
    };

    poll();
};

// 下载 PDF 文件
const handlePdfDownload = async (item: PdfLayoutTaskWithUI, type: "uploaded" | "output") => {
    const fileInfo = type === "uploaded" ? item.uploaded_info : item.output_info;
    if (!fileInfo) {
        ElMessage.warning("文件不存在");
        return;
    }

    try {
        const url = getPdfLayoutDownloadUrl(fileInfo.name, type);
        window.open(url, "_blank");
    } catch (error) {
        logAndNoticeError(error as Error, "下载文件失败");
    }
};

// 删除 PDF 排版任务
const handlePdfDelete = async (item: PdfLayoutTaskWithUI) => {
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
        const response = await deletePdfLayout(item.task_id);

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

onBeforeUnmount(() => {
    if (uploadTimer) {
        clearInterval(uploadTimer);
        uploadTimer = null;
    }
    if (uploadAbortController.value) {
        uploadAbortController.value.abort();
        uploadAbortController.value = null;
    }
});
</script>
