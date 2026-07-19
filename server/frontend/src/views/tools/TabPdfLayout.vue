<template>
    <div class="flex gap-4 h-[calc(100vh-220px)] min-w-0 overflow-hidden">
        <!-- 左侧：任务列表 -->
        <div class="w-64 shrink-0 border rounded p-3 flex flex-col">
            <div class="flex items-center justify-between mb-3">
                <h3 class="text-base font-semibold">任务列表</h3>
                <div class="flex items-center gap-1">
                    <el-button type="info" v-bind="smallIconButtonProps" @click="loadTaskList" :loading="loading">
                        <el-icon v-if="!loading">
                            <Refresh />
                        </el-icon>
                    </el-button>
                    <el-button type="success" v-bind="smallIconButtonProps" @click="handleCreateTask"
                        :loading="loading">
                        <el-icon v-if="!loading">
                            <Plus />
                        </el-icon>
                    </el-button>
                </div>
            </div>
            <div v-if="taskList && taskList.length > 0" class="flex-1 overflow-y-auto space-y-2 pr-1 min-h-100">
                <div v-for="task in taskList" :key="task.task_id"
                    class="border rounded px-3 py-2 cursor-pointer hover:bg-gray-50 group min-h-15 flex flex-col justify-between"
                    :class="{
                        'border-blue-500 bg-blue-50':
                            currentTask && task.task_id === currentTask.task_id,
                    }" @click="handleViewTask(task.task_id)">
                    <!-- 第一行：名称 -->
                    <div class="flex items-center justify-between gap-2">
                        <div class="text-sm font-medium truncate flex-1 min-w-0" :title="task.name || task.task_id">
                            {{ task.name || task.task_id }}
                        </div>
                    </div>
                    <!-- 第二行：状态、删除按钮 -->
                    <div class="flex items-center justify-between gap-2 min-h-5">
                        <el-tag :type="getStatusTagType(task.status)" size="small"
                            class="h-5! text-xs! w-16 text-center">
                            {{ getStatusText(task.status) }}
                        </el-tag>
                        <div class="flex items-center gap-1 shrink-0">
                            <el-button type="danger" v-bind="smallTextButtonProps"
                                @click.stop="handleDeleteTask(task.task_id)" :disabled="task.status === 'processing'">
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

        <!-- 右侧：文件信息 + 预览 -->
        <div class="flex-1 min-w-0 border rounded p-3 flex flex-col min-h-0" v-if="currentTask">
            <!-- 上半：文件信息与操作 -->
            <div class="shrink-0 space-y-2 pr-1 overflow-auto">
                <h3 class="text-base font-semibold">文件信息: {{ currentTask.name || currentTask.task_id }}</h3>

                <!-- 任务信息 -->
                <div class="flex items-center gap-4">
                    <el-tag :type="getStatusTagType(currentTask.status)" size="small" class="w-16 text-center shrink-0">
                        {{ getStatusText(currentTask.status) }}
                    </el-tag>
                    <el-tooltip v-if="currentTask.error_message" :content="`错误: ${currentTask.error_message}`"
                        placement="top" class="min-w-0 max-w-md">
                        <span class="text-red-500 text-xs truncate block max-w-md cursor-help">
                            错误: {{ currentTask.error_message }}
                        </span>
                    </el-tooltip>
                </div>

                <!-- 上传文件 -->
                <div class="border rounded p-2 flex flex-col gap-1 w-full min-w-0">
                    <div class="flex items-start justify-between gap-2 min-w-0">
                        <div class="flex items-center gap-2 min-w-0 flex-1">
                            <h4 class="text-xs font-semibold">文件信息</h4>
                        </div>
                        <div class="flex items-center gap-1 shrink-0">
                            <el-button type="success" v-bind="mediumTextButtonProps" @click="handleProcess"
                                :disabled="isProcessDisabled" :loading="isTaskProcessing">
                                开始排版
                            </el-button>
                        </div>
                    </div>
                    <div v-if="currentTask.uploaded_info" class="text-xs text-gray-600">
                        <div class="truncate" :title="currentTask.uploaded_info.name">
                            {{ currentTask.uploaded_info.name }}
                        </div>
                        <div class="flex items-center gap-2 text-xs text-gray-500">
                            <span>大小: {{ formatSize(currentTask.uploaded_info.size ?? 0) }}</span>
                            <span>修改: {{ formatTime(currentTask.uploaded_info.modified) }}</span>
                        </div>
                    </div>
                    <div v-else class="text-sm text-gray-400">文件信息不可用</div>
                </div>

                <!-- 输出文件 -->
                <div v-if="currentTask.output_info" class="border rounded p-2 flex flex-col gap-1 w-full min-w-0">
                    <h4 class="text-xs font-semibold">排版结果</h4>
                    <div class="text-xs text-gray-600">
                        <div class="truncate" :title="currentTask.output_info.name">
                            {{ currentTask.output_info.name }}
                        </div>
                        <div class="flex items-center gap-2 text-xs text-gray-500">
                            <span>大小: {{ formatSize(currentTask.output_info.size ?? 0) }}</span>
                        </div>
                    </div>
                    <a class="text-xs text-blue-600 hover:text-blue-800"
                        :href="getDownloadUrl(currentTask.uploaded_info?.name || currentTask.task_id, 'output')"
                        target="_blank" rel="noopener noreferrer">
                        下载排版结果
                    </a>
                </div>


                <!-- 排版进度 -->
                <div v-if="currentTask.status === 'processing'" class="border rounded p-2">
                    <h4 class="text-xs font-semibold">排版进度</h4>
                    <el-progress :percentage="50" indeterminate />
                    <div class="text-xs text-gray-400">正在处理中，请稍候...</div>
                </div>
            </div>

            <!-- 下半：PDF 预览 -->
            <div class="flex-1 min-h-0 border-t pt-3 mt-3 flex flex-col">
                <div class="flex items-center justify-between shrink-0 mb-2">
                    <div class="flex items-center gap-0">
                        <span class="text-sm font-semibold mr-4">PDF 预览</span>
                        <el-button type="success" size="small" plain class="!h-5 !text-xs !px-2 shrink-0"
                            @click="handlePreview(currentTask)" :disabled="!currentTask.uploaded_info || previewLoading"
                            :class="previewMode === 'single' ? '' : '!text-gray-400 !border-gray-300'">
                            {{ previewPages.length > 0 ? "刷新" : "预览" }}
                        </el-button>
                        <el-button type="warning" size="small" plain class="!h-5 !text-xs !px-2 shrink-0"
                            @click="handleSaddleStitchPreview(currentTask)"
                            :disabled="!currentTask.uploaded_info || previewLoading"
                            :class="previewMode === 'saddle-stitch' ? '' : '!text-gray-400 !border-gray-300'">
                            骑缝排版
                        </el-button>
                        <el-button type="primary" size="small" plain class="!h-5 !text-xs !px-2 shrink-0"
                            @click="handleBoundPreview(currentTask)"
                            :disabled="!currentTask.uploaded_info || previewLoading"
                            :class="previewMode === 'bound' ? '' : '!text-gray-400 !border-gray-300'">
                            骑缝预览
                        </el-button>
                        <div v-if="previewMode === 'saddle-stitch' && fillConfigs.length > 0"
                            class="flex items-center gap-1">
                            <span class="text-xs text-gray-500 ml-1">填充:</span>
                            <el-input-number v-for="(_, i) in fillConfigs" :key="i" v-model="fillConfigs[i]"
                                size="small" class="!w-16" :min="1" :max="originalTotalPages"
                                controls-position="right" />
                            <el-button size="small" type="primary" plain class="!h-5 !text-xs !px-2"
                                @click="updateSaddleStitchPreview">
                                更新
                            </el-button>
                            <el-button type="success" size="small" plain class="!h-5 !text-xs !px-2"
                                @click="handleDownloadLayout">
                                下载
                            </el-button>
                        </div>
                    </div>
                    <!-- 单页导航 -->
                    <div v-if="previewMode === 'single' && previewPages.length > 0" class="flex items-center gap-2">
                        <el-button size="small" circle :disabled="previewCurrentPage <= 1" @click="previewCurrentPage--"
                            class="!w-6 !h-6 !p-0">
                            <el-icon>
                                <ArrowLeft />
                            </el-icon>
                        </el-button>
                        <span class="text-xs">{{ previewCurrentPage }} / {{ previewPages.length }}</span>
                        <el-button size="small" circle :disabled="previewCurrentPage >= previewPages.length"
                            @click="previewCurrentPage++" class="!w-6 !h-6 !p-0">
                            <el-icon>
                                <ArrowRight />
                            </el-icon>
                        </el-button>
                    </div>
                    <!-- 骑缝导航 -->
                    <div v-else-if="previewMode === 'saddle-stitch' && spreadPages.length > 0"
                        class="flex items-center gap-2">
                        <el-button size="small" circle :disabled="spreadCurrentPage <= 1" @click="spreadCurrentPage--"
                            class="!w-6 !h-6 !p-0">
                            <el-icon>
                                <ArrowLeft />
                            </el-icon>
                        </el-button>
                        <span class="text-xs">{{ spreadCurrentPage }} / {{ spreadPages.length }}</span>
                        <el-button size="small" circle :disabled="spreadCurrentPage >= spreadPages.length"
                            @click="spreadCurrentPage++" class="!w-6 !h-6 !p-0">
                            <el-icon>
                                <ArrowRight />
                            </el-icon>
                        </el-button>
                    </div>
                    <!-- 装订导航 -->
                    <div v-else-if="previewMode === 'bound' && boundPages.length > 0" class="flex items-center gap-2">
                        <el-button size="small" circle :disabled="spreadCurrentPage <= 1" @click="spreadCurrentPage--"
                            class="!w-6 !h-6 !p-0">
                            <el-icon>
                                <ArrowLeft />
                            </el-icon>
                        </el-button>
                        <span class="text-xs">{{ spreadCurrentPage }} / {{ boundPages.length }}</span>
                        <el-button size="small" circle :disabled="spreadCurrentPage >= boundPages.length"
                            @click="spreadCurrentPage++" class="!w-6 !h-6 !p-0">
                            <el-icon>
                                <ArrowRight />
                            </el-icon>
                        </el-button>
                    </div>
                </div>
                <div v-loading="previewLoading"
                    class="flex-1 flex items-center justify-center bg-gray-100 rounded min-h-0 overflow-hidden p-2 relative">
                    <!-- 左右翻页点击区域 -->
                    <div v-if="hasPreviewContent" class="absolute left-0 top-0 w-[20%] h-full z-10 cursor-w-resize"
                        @click="handlePrevPage"></div>
                    <div v-if="hasPreviewContent" class="absolute right-0 top-0 w-[20%] h-full z-10 cursor-e-resize"
                        @click="handleNextPage"></div>
                    <!-- 普通预览（双页）-->
                    <div v-if="previewMode === 'single' && previewPages[previewCurrentPage - 1]"
                        class="flex items-center justify-center w-full h-full gap-0">
                        <div class="h-full flex flex-col items-center justify-center shrink-0 max-w-[50%]">
                            <img :src="previewPages[previewCurrentPage - 1].leftImage"
                                class="max-w-full max-h-full object-contain" />
                            <span class="text-xs text-gray-400 mt-1">
                                第 {{ previewPages[previewCurrentPage - 1].leftPageNum || originalTotalPages }} 页
                            </span>
                        </div>
                        <div class="h-full flex flex-col items-center justify-center shrink-0 max-w-[50%] relative">
                            <img v-if="previewPages[previewCurrentPage - 1].rightPageNum === 0" :src="blankPageDataUrl"
                                class="max-w-full max-h-full object-contain rounded border-2 border-dashed border-gray-300" />
                            <img v-else :src="previewPages[previewCurrentPage - 1].rightImage"
                                class="max-w-full max-h-full object-contain" />
                            <span v-if="previewPages[previewCurrentPage - 1].rightPageNum === 0"
                                class="absolute inset-0 flex items-center justify-center text-gray-400 text-xs pointer-events-none z-10">空白</span>
                            <span class="text-xs text-gray-400 mt-1">
                                第 {{ previewPages[previewCurrentPage - 1].rightPageNum || originalTotalPages }} 页
                            </span>
                        </div>
                    </div>
                    <!-- 骑缝模式 -->
                    <div v-else-if="previewMode === 'saddle-stitch' && spreadPages[spreadCurrentPage - 1]"
                        class="flex items-center justify-center w-full h-full gap-0">
                        <div class="h-full flex flex-col items-center justify-center shrink-0 max-w-[50%] relative">
                            <img v-if="spreadPages[spreadCurrentPage - 1].leftPageNum === 0" :src="blankPageDataUrl"
                                class="max-w-full max-h-full object-contain rounded border-2 border-dashed border-gray-300" />
                            <img v-else :src="spreadPages[spreadCurrentPage - 1].leftImage"
                                class="max-w-full max-h-full object-contain" />
                            <span v-if="spreadPages[spreadCurrentPage - 1].leftPageNum === 0"
                                class="absolute inset-0 flex items-center justify-center text-gray-400 text-xs pointer-events-none z-10">空白</span>
                            <span class="text-xs text-gray-400 mt-1">
                                第 {{ spreadPages[spreadCurrentPage - 1].leftPageNum || originalTotalPages }} 页
                            </span>
                        </div>
                        <div class="h-full flex flex-col items-center justify-center shrink-0 max-w-[50%] relative">
                            <img v-if="spreadPages[spreadCurrentPage - 1].rightPageNum === 0" :src="blankPageDataUrl"
                                class="max-w-full max-h-full object-contain rounded border-2 border-dashed border-gray-300" />
                            <img v-else :src="spreadPages[spreadCurrentPage - 1].rightImage"
                                class="max-w-full max-h-full object-contain" />
                            <span v-if="spreadPages[spreadCurrentPage - 1].rightPageNum === 0"
                                class="absolute inset-0 flex items-center justify-center text-gray-400 text-xs pointer-events-none z-10">空白</span>
                            <span class="text-xs text-gray-400 mt-1">
                                第 {{ spreadPages[spreadCurrentPage - 1].rightPageNum || originalTotalPages }} 页
                            </span>
                        </div>
                    </div>
                    <!-- 装订预览 -->
                    <div v-else-if="previewMode === 'bound' && boundPages[spreadCurrentPage - 1]"
                        class="flex items-center justify-center w-full h-full"
                        style="filter: drop-shadow(0 2px 8px rgba(0,0,0,0.12))">
                        <div class="flex items-center justify-center w-full h-full gap-0">
                            <div class="h-full flex flex-col items-center justify-center shrink-0 max-w-[50%] relative">
                                <img v-if="boundPages[spreadCurrentPage - 1].leftPageNum === 0" :src="blankPageDataUrl"
                                    class="max-w-full max-h-full object-contain rounded" />
                                <img v-else :src="boundPages[spreadCurrentPage - 1].leftImage"
                                    class="max-w-full max-h-full object-contain" />
                                <span v-if="boundPages[spreadCurrentPage - 1].leftPageNum === 0"
                                    class="absolute inset-0 flex items-center justify-center text-gray-400 text-xs pointer-events-none z-10">空白</span>
                                <span class="text-xs text-gray-400 mt-1">
                                    第 {{ boundPages[spreadCurrentPage - 1].leftPageNum || originalTotalPages }} 页
                                </span>
                            </div>
                            <!-- 书脊效果 -->
                            <div
                                class="w-[3px] self-stretch bg-gradient-to-r from-transparent via-gray-400/30 to-transparent shrink-0 rounded-full">
                            </div>
                            <div class="h-full flex flex-col items-center justify-center shrink-0 max-w-[50%] relative">
                                <img v-if="boundPages[spreadCurrentPage - 1].rightPageNum === 0" :src="blankPageDataUrl"
                                    class="max-w-full max-h-full object-contain rounded" />
                                <img v-else :src="boundPages[spreadCurrentPage - 1].rightImage"
                                    class="max-w-full max-h-full object-contain" />
                                <span v-if="boundPages[spreadCurrentPage - 1].rightPageNum === 0"
                                    class="absolute inset-0 flex items-center justify-center text-gray-400 text-xs pointer-events-none z-10">空白</span>
                                <span class="text-xs text-gray-400 mt-1">
                                    第 {{ boundPages[spreadCurrentPage - 1].rightPageNum || originalTotalPages }} 页
                                </span>
                            </div>
                        </div>
                    </div>
                    <span v-else class="text-gray-400 text-sm">点击上方"预览"按钮查看 PDF 内容</span>
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

        <!-- 上传/创建任务对话框 -->
        <el-dialog v-model="createDialogVisible" title="上传 PDF 文件" width="400px" @close="handleDialogClose">
            <el-form>
                <el-form-item label="选择文件">
                    <el-upload :auto-upload="false" :on-change="handleFileChange" :show-file-list="false" accept=".pdf">
                        <template #trigger>
                            <el-button type="primary" size="small">选择文件</el-button>
                        </template>
                    </el-upload>
                </el-form-item>
                <div v-if="selectedFile" class="text-sm text-gray-600 mb-2">
                    已选择: {{ selectedFile.name }}
                </div>
                <el-progress v-if="uploadProgress > 0 && uploadProgress < 100" :percentage="uploadProgress" />
            </el-form>
            <template #footer>
                <el-button @click="createDialogVisible = false">取消</el-button>
                <el-button type="primary" @click="handleUploadConfirm" :loading="loading" :disabled="!selectedFile">
                    上传
                </el-button>
            </template>
        </el-dialog>
    </div>
</template>

<script setup lang="ts">
import { ref, shallowRef, computed, onMounted, onBeforeUnmount } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { UploadFile } from "element-plus";
import { Refresh, Plus, Delete, ArrowLeft, ArrowRight } from "@element-plus/icons-vue";
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
    savePdfLayout,
} from "@/api/api-pdf-layout";
import type { PdfLayoutTask } from "@/types/tools/pdf-layout";

interface SpreadPage {
    id: string;
    leftImage: string;
    rightImage: string;
    leftPageNum: number;
    rightPageNum: number;
}

// 空白页占位图片（初始为空，PDF 加载后按实际页尺寸创建）
const blankPageDataUrl = ref('');

// 根据 PDF 第一页创建同等尺寸的空白 canvas
async function initBlankPageImage(pdf: any, scale = 0.5) {
    try {
        const page = await pdf.getPage(1);
        const viewport = page.getViewport({ scale });
        const canvas = document.createElement('canvas');
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        const ctx = canvas.getContext('2d');
        if (ctx) {
            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, viewport.width, viewport.height);
        }
        blankPageDataUrl.value = canvas.toDataURL('image/png');
    } catch {
        // 静默失败，空白页将降级为空字符串
    }
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
const previewMode = ref<'single' | 'saddle-stitch' | 'bound'>('single');
const previewLoading = ref(false);
const previewCurrentPage = ref(1);
const previewPages = ref<SpreadPage[]>([]);
const spreadPages = ref<SpreadPage[]>([]);
const boundPages = ref<SpreadPage[]>([]);
const spreadCurrentPage = ref(1);
const pdfDocCache = shallowRef<any>(null);
const fillConfigs = ref<number[]>([]);
const originalTotalPages = ref(0);
const spreadDataCachedTaskId = ref(''); // 标记当前骑缝数据属于哪个任务

// 辅助函数
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

// 是否有可翻页的预览内容
const hasPreviewContent = computed(() => {
    if (previewMode.value === 'single') return previewPages.value.length > 0;
    if (previewMode.value === 'saddle-stitch') return spreadPages.value.length > 0;
    if (previewMode.value === 'bound') return boundPages.value.length > 0;
    return false;
});

// 翻页操作
function handlePrevPage() {
    if (previewMode.value === 'single') {
        if (previewCurrentPage.value > 1) previewCurrentPage.value--;
    } else {
        if (spreadCurrentPage.value > 1) spreadCurrentPage.value--;
    }
}

function handleNextPage() {
    if (previewMode.value === 'single') {
        if (previewCurrentPage.value < previewPages.value.length) previewCurrentPage.value++;
    } else {
        const max = previewMode.value === 'bound' ? boundPages.value.length : spreadPages.value.length;
        if (spreadCurrentPage.value < max) spreadCurrentPage.value++;
    }
}

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

// 预览 PDF（双页预览）
const handlePreview = async (item: PdfLayoutTask) => {
    if (!item.uploaded_info) {
        ElMessage.warning("文件不存在");
        return;
    }

    previewMode.value = 'single';
    previewLoading.value = true;
    previewCurrentPage.value = 1;
    previewPages.value = [];

    try {
        const url = getPdfLayoutDownloadUrl(item.uploaded_info.name, "uploaded");
        if (!url) {
            ElMessage.error("无法获取文件地址");
            previewLoading.value = false;
            return;
        }

        console.time('loadPdf');
        const pdf = await loadPdfDocument(url);
        console.timeEnd('loadPdf');
        await initBlankPageImage(pdf, 0.5);

        const totalPages = pdf.numPages;
        console.log(`PDF 页数: ${totalPages}, 文件: ${item.uploaded_info.name}`);
        originalTotalPages.value = totalPages;

        // 并行渲染所有 spread
        console.time('renderAllPages');
        const spreadPromises: Promise<SpreadPage>[] = [];
        for (let i = 1; i <= totalPages; i += 2) {
            const pageIdx = i;
            spreadPromises.push(
                (async () => {
                    const leftImg = await renderPdfPageToDataUrl(await pdf.getPage(pageIdx), {
                        scale: 0.5,
                        mimeType: "image/jpeg",
                        quality: 0.7,
                    });

                    let rightImg = '';
                    let rightNum = 0;
                    if (pageIdx + 1 <= totalPages) {
                        rightImg = await renderPdfPageToDataUrl(await pdf.getPage(pageIdx + 1), {
                            scale: 0.5,
                            mimeType: "image/jpeg",
                            quality: 0.7,
                        });
                        rightNum = pageIdx + 1;
                    }

                    return {
                        id: `${pageIdx}-${pageIdx + 1}`,
                        leftImage: leftImg,
                        rightImage: rightImg,
                        leftPageNum: pageIdx,
                        rightPageNum: rightNum,
                    } as SpreadPage;
                })()
            );
        }

        previewPages.value = await Promise.all(spreadPromises);
        console.timeEnd('renderAllPages');
        // 加载完成后释放 PDF 文档以释放内存
        await pdf.destroy();
    } catch (error) {
        logAndNoticeError(error as Error, "加载 PDF 预览失败");
        previewPages.value = [];
    } finally {
        previewLoading.value = false;
    }
};

// 骑缝排版算法：生成对开页序列
function generateSaddleStitchSpreads(effectiveCount: number): [number, number][] {
    const spreads: [number, number][] = [];
    for (let s = 0; s < effectiveCount / 4; s++) {
        spreads.push([effectiveCount - 2 * s, 2 * s + 1]);
        spreads.push([2 * s + 2, effectiveCount - 2 * s - 1]);
    }
    return spreads;
}

// 构建有效页面数据：0=空白页，>0=原始页码，自动补齐到4的倍数
// insertAt: 在指定页码之前插入空白页
function buildEffectivePages(totalPages: number, insertAt: number[]): number[] {
    const pages: number[] = [];
    for (let i = 1; i <= totalPages; i++) {
        const count = insertAt.filter(p => p === i).length;
        for (let b = 0; b < count; b++) pages.push(0);
        pages.push(i);
    }
    const padded = Math.ceil(pages.length / 4) * 4;
    while (pages.length < padded) pages.push(0);
    return pages;
}

// 初始化填充配置：需要几页就生成几个默认值（全部在末页后）
function initFillConfigs(totalPages: number): number[] {
    const needed = Math.ceil(totalPages / 4) * 4 - totalPages;
    return needed > 0 ? Array(needed).fill(totalPages) : [];
}

// 骑缝排版（加载并初始化填充配置）
const handleSaddleStitchPreview = async (item: PdfLayoutTask) => {
    if (!item.uploaded_info) {
        ElMessage.warning("文件不存在");
        return;
    }

    // 如果骑缝数据已为当前任务生成过，直接切换模式不重新计算
    if (spreadPages.value.length > 0 && pdfDocCache.value && spreadDataCachedTaskId.value === item.task_id) {
        previewMode.value = 'saddle-stitch';
        spreadCurrentPage.value = 1;
        return;
    }

    previewLoading.value = true;
    previewMode.value = 'saddle-stitch';
    spreadPages.value = [];
    spreadCurrentPage.value = 1;

    try {
        const url = getPdfLayoutDownloadUrl(item.uploaded_info.name, "uploaded");
        if (!url) {
            ElMessage.error("无法获取文件地址");
            previewLoading.value = false;
            return;
        }

        const pdf = await loadPdfDocument(url);
        await initBlankPageImage(pdf, 0.5);
        const totalPages = pdf.numPages;
        originalTotalPages.value = totalPages;
        fillConfigs.value = (item.fill_configs && item.fill_configs.length > 0)
            ? [...item.fill_configs]
            : initFillConfigs(totalPages);
        pdfDocCache.value = pdf;
        spreadDataCachedTaskId.value = item.task_id;
        await renderSaddleStitchPreview();
    } catch (error) {
        logAndNoticeError(error as Error, "加载骑缝排版失败");
        spreadPages.value = [];
    } finally {
        previewLoading.value = false;
    }
};

// 渲染骑缝预览（使用当前 fillConfigs）
const renderSaddleStitchPreview = async () => {
    const pdf = pdfDocCache.value;
    if (!pdf) return;

    previewLoading.value = true;
    spreadPages.value = [];
    spreadCurrentPage.value = 1;

    try {
        const effectiveData = buildEffectivePages(originalTotalPages.value, fillConfigs.value);
        const spreads = generateSaddleStitchSpreads(effectiveData.length);

        // 并行渲染所有对开页
        const spreadPromises: Promise<SpreadPage>[] = spreads.map(async ([leftIdx, rightIdx]) => {
            const leftPageNum = effectiveData[leftIdx - 1];
            const rightPageNum = effectiveData[rightIdx - 1];

            let leftImg = '';
            if (leftPageNum > 0) {
                leftImg = await renderPdfPageToDataUrl(await pdf.getPage(leftPageNum), {
                    scale: 0.5, mimeType: "image/jpeg", quality: 0.8,
                });
            }

            let rightImg = '';
            if (rightPageNum > 0) {
                rightImg = await renderPdfPageToDataUrl(await pdf.getPage(rightPageNum), {
                    scale: 0.5, mimeType: "image/jpeg", quality: 0.8,
                });
            }

            return {
                id: `${leftIdx}-${rightIdx}`,
                leftImage: leftImg,
                rightImage: rightImg,
                leftPageNum,
                rightPageNum,
            } as SpreadPage;
        });

        spreadPages.value = await Promise.all(spreadPromises);
    } catch (error) {
        logAndNoticeError(error as Error, "渲染骑缝预览失败");
        spreadPages.value = [];
    } finally {
        previewLoading.value = false;
    }
};

// 生成阅读顺序对开页（底-1, 2-3, 4-5...）
function generateBoundSpreads(effectiveData: number[]): [number, number][] {
    const spreads: [number, number][] = [];
    const n = effectiveData.length;
    if (n === 0) return spreads;

    // 找到最后一个非空白页（最后一页原始内容）
    let lastContentIdx = n - 1;
    while (lastContentIdx >= 0 && effectiveData[lastContentIdx] === 0) {
        lastContentIdx--;
    }
    if (lastContentIdx < 0) return spreads;

    // 第一个对开：[末页, 第1页]
    spreads.push([effectiveData[lastContentIdx], effectiveData[0]]);

    // 中间页：顺序配对（2-3, 4-5...）
    for (let i = 1; i < lastContentIdx; i += 2) {
        spreads.push([effectiveData[i], effectiveData[i + 1]]);
    }

    // 末尾填充页（空白页）
    for (let i = lastContentIdx + 1; i < n; i += 2) {
        if (i + 1 < n) {
            spreads.push([effectiveData[i], effectiveData[i + 1]]);
        }
    }

    return spreads;
}

// 渲染装订预览（从骑缝排版数据提取，按阅读顺序重排）
const renderBoundPreview = async () => {
    const pdf = pdfDocCache.value;
    if (!pdf) return;

    previewLoading.value = true;
    boundPages.value = [];
    spreadCurrentPage.value = 1;

    try {
        // 从已渲染的 spreadPages 建立页码→图片映射
        const pageImageMap = new Map<number, string>();
        for (const sp of spreadPages.value) {
            if (sp.leftPageNum > 0) pageImageMap.set(sp.leftPageNum, sp.leftImage);
            if (sp.rightPageNum > 0) pageImageMap.set(sp.rightPageNum, sp.rightImage);
        }

        const effectiveData = buildEffectivePages(originalTotalPages.value, fillConfigs.value);
        const boundSpreads = generateBoundSpreads(effectiveData);

        for (const [leftNum, rightNum] of boundSpreads) {
            boundPages.value.push({
                id: `${leftNum}-${rightNum}`,
                leftImage: pageImageMap.get(leftNum) || '',
                rightImage: pageImageMap.get(rightNum) || '',
                leftPageNum: leftNum,
                rightPageNum: rightNum,
            });
        }
    } catch (error) {
        logAndNoticeError(error as Error, "渲染装订预览失败");
        boundPages.value = [];
    } finally {
        previewLoading.value = false;
    }
};

// 装订预览（复用骑缝排版数据，按阅读顺序展示）
const handleBoundPreview = async (item: PdfLayoutTask) => {
    if (!item.uploaded_info) {
        ElMessage.warning("文件不存在");
        return;
    }
    if (!pdfDocCache.value) {
        await handleSaddleStitchPreview(item);
    }
    previewMode.value = 'bound';
    spreadCurrentPage.value = 1;
    await renderBoundPreview();
};

// 按当前填充配置重新渲染骑缝预览
const updateSaddleStitchPreview = async () => {
    await renderSaddleStitchPreview();
};

// 生成并下载骑缝排版 PDF
const handleDownloadLayout = async () => {
    const task = currentTask.value;
    if (!task) return;
    if (previewLoading.value) {
        ElMessage.warning("正在渲染中，请稍候");
        return;
    }

    previewLoading.value = true;
    try {
        const response = await savePdfLayout(task.task_id, fillConfigs.value);
        if (response.code !== 0 || !response.data) {
            ElMessage.error(response.msg || "生成骑缝 PDF 失败");
            return;
        }

        const result = response.data;
        const filename = result.output_info?.name || result.task_id;
        if (filename) {
            const url = getPdfLayoutDownloadUrl(filename, 'output');
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            ElMessage.success("骑缝排版 PDF 已生成并开始下载");
        }
    } catch (error) {
        logAndNoticeError(error as Error, "保存骑缝排版 PDF 失败");
    } finally {
        previewLoading.value = false;
    }
};

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
