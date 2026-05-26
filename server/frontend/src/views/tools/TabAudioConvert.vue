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
            @click="loadConvertTaskList"
            :loading="convertLoading"
          >
            <el-icon v-if="!convertLoading">
              <Refresh />
            </el-icon>
          </el-button>
          <el-button
            type="success"
            v-bind="smallIconButtonProps"
            @click="handleConvertCreateTask"
            :loading="convertLoading"
          >
            <el-icon v-if="!convertLoading">
              <Plus />
            </el-icon>
          </el-button>
        </div>
      </div>
      <div
        v-if="convertTaskList && convertTaskList.length > 0"
        class="flex-1 overflow-y-auto space-y-2 pr-1 min-h-100"
      >
        <div
          v-for="task in convertTaskList"
          :key="task.task_id"
          class="border rounded px-3 py-2 cursor-pointer hover:bg-gray-50 group min-h-15 flex flex-col justify-between"
          :class="{
            'border-blue-500 bg-blue-50':
              convertCurrentTask && task.task_id === convertCurrentTask.task_id,
          }"
          @click="handleConvertViewTask(task.task_id)"
        >
          <!-- 第一行：名称 -->
          <div class="flex items-center justify-between gap-2">
            <div class="text-sm font-medium truncate flex-1 min-w-0" :title="task.name">
              {{ task.name }}
            </div>
          </div>
          <!-- 第二行：状态、删除按钮 -->
          <div class="flex items-center justify-between gap-2 min-h-5">
            <el-tag
              :type="getConvertStatusTagType(task.status)"
              size="small"
              class="h-5! text-xs! w-16 text-center"
            >
              {{ getConvertStatusText(task.status) }}
            </el-tag>
            <div class="flex items-center gap-1 shrink-0">
              <el-button
                type="danger"
                v-bind="smallTextButtonProps"
                @click.stop="handleConvertDeleteTask(task.task_id)"
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

    <!-- 中间：文件列表 -->
    <div class="flex-1 min-w-0 border rounded p-3 flex flex-col min-h-0" v-if="convertCurrentTask">
      <div class="flex items-center justify-between mb-3 shrink-0">
        <div class="flex items-center gap-2 flex-1">
          <h3 class="text-base font-semibold">文件列表: {{ convertCurrentTask.name }}</h3>
          <el-button
            type="default"
            size="small"
            plain
            circle
            :disabled="isDirectoryOperationDisabled"
            @click="handleConvertRenameTask"
            title="编辑名称"
          >
            <el-icon>
              <Edit />
            </el-icon>
          </el-button>
        </div>
      </div>

      <div class="flex-1 flex flex-col gap-3 min-h-0">
        <!-- 任务信息 -->
        <div class="flex items-center justify-between gap-4 shrink-0">
          <div class="flex items-center gap-4 min-w-0 flex-1">
            <el-tag
              :type="getConvertStatusTagType(convertCurrentTask.status)"
              size="small"
              class="w-16 text-center shrink-0"
            >
              {{ getConvertStatusText(convertCurrentTask.status) }}
            </el-tag>
            <el-tooltip
              v-if="convertCurrentTask.error_message"
              :content="`错误: ${convertCurrentTask.error_message}`"
              placement="top"
              class="min-w-0 max-w-md"
            >
              <span class="text-red-500 text-xs truncate block max-w-md cursor-help">
                错误: {{ convertCurrentTask.error_message }}
              </span>
            </el-tooltip>
          </div>
          <div class="flex items-center gap-2 shrink-0">
            <span class="text-sm text-gray-600">转码来源</span>
            <el-radio-group
              v-model="convertSourceType"
              size="small"
              :disabled="isDirectoryOperationDisabled"
              @change="handleConvertSourceTypeChange"
            >
              <el-radio-button label="directory">目录</el-radio-button>
              <el-radio-button label="upload">上传文件</el-radio-button>
            </el-radio-group>
          </div>
        </div>

        <!-- 目录选择 -->
        <div v-if="!isUploadSource" class="border rounded p-3 flex flex-col gap-2 w-full min-w-0 min-h-20">
          <div class="flex items-start justify-between gap-3 min-w-0">
            <div class="flex items-center gap-2 min-w-0 flex-1 h-6">
              <h4 class="text-sm font-semibold leading-5">转码目录</h4>
              <span
                v-if="
                  isSourceTypeSynced &&
                  convertCurrentTask.total_files !== null &&
                  convertCurrentTask.total_files !== undefined
                "
                class="text-xs text-gray-500"
              >
                可处理文件数: {{ convertCurrentTask.total_files }}
              </span>
            </div>
            <el-button
              type="primary"
              v-bind="smallTextButtonProps"
              :disabled="isDirectoryOperationDisabled"
              @click="handleConvertOpenDirectoryBrowser"
            >
              选择目录
            </el-button>
          </div>
          <div v-if="convertCurrentTask.directory" class="text-sm text-gray-600">
            <div class="truncate" :title="convertCurrentTask.directory">
              {{ convertCurrentTask.directory }}
            </div>
          </div>
          <div v-else class="text-sm text-gray-400">
            请选择一个目录，该目录下的所有媒体文件将被转换为 MP3 格式
          </div>
        </div>

        <!-- 上传文件 -->
        <div v-else class="border rounded p-3 flex flex-col gap-2 w-full min-w-0 min-h-20">
          <div class="flex items-start justify-between gap-3 min-w-0">
            <div class="flex items-center gap-2 min-w-0 flex-1 h-6">
              <h4 class="text-sm font-semibold leading-5">上传待转码文件</h4>
              <span
                v-if="
                  isSourceTypeSynced &&
                  convertCurrentTask.total_files !== null &&
                  convertCurrentTask.total_files !== undefined
                "
                class="text-xs text-gray-500"
              >
                已上传文件数: {{ convertCurrentTask.total_files }}
              </span>
            </div>
            <div class="flex items-center gap-2 shrink-0 self-start">
              <el-upload
                class="shrink-0 flex items-center"
                v-model:file-list="convertUploadFileList"
                :auto-upload="false"
                :show-file-list="false"
                :multiple="true"
                :disabled="isDirectoryOperationDisabled"
                :accept="CONVERT_UPLOAD_ACCEPT"
                @change="handleConvertUploadSelectionChange"
              >
                <template #trigger>
                  <el-button type="primary" v-bind="smallTextButtonProps" :disabled="isDirectoryOperationDisabled">
                    选择文件
                  </el-button>
                </template>
              </el-upload>
              <el-button
                type="success"
                v-bind="smallTextButtonProps"
                :disabled="isDirectoryOperationDisabled || convertSelectedUploadFiles.length === 0"
                :loading="convertLoading"
                @click="handleConvertUploadFiles"
              >
                上传
              </el-button>
              <el-button
                type="info"
                v-bind="smallTextButtonProps"
                :disabled="convertSelectedUploadFiles.length === 0"
                @click="handleConvertClearSelectedUploads"
              >
                清空
              </el-button>
            </div>
          </div>
          <div v-if="convertSelectedUploadFiles.length > 0" class="text-sm text-gray-600 min-w-0">
            已选择 {{ convertSelectedUploadFiles.length }} 个文件：
            <span class="text-xs text-gray-500 break-all">
              {{ convertSelectedUploadFileNames.join("、") }}
            </span>
          </div>
          <div v-else class="text-sm text-gray-400">
            请选择音频或视频文件并上传到当前任务，再开始转码
          </div>
          <el-progress
            v-if="convertUploadProgress > 0"
            :percentage="convertUploadProgress"
            :status="convertUploadProgress === 100 ? 'success' : undefined"
          />
        </div>

        <!-- 文件列表 -->
        <div class="border rounded p-3 flex flex-col gap-2 flex-1 min-h-0 overflow-hidden">
          <h4 class="text-sm font-semibold shrink-0">文件列表</h4>
          <div
            v-if="convertFileList && convertFileList.length > 0"
            class="flex-1 overflow-y-scroll scrollbar-overlay space-y-1 min-h-0"
          >
            <div
              v-for="(file, index) in convertFileList"
              :key="index"
              class="flex items-center gap-2 p-2 rounded hover:bg-gray-50 border-b border-gray-100"
            >
              <el-icon
                class="shrink-0"
                :class="{
                  'text-green-500': file.status === 'success',
                  'text-red-500': file.status === 'failed',
                  'text-yellow-500': file.status === 'processing',
                  'text-gray-400': file.status === 'pending',
                }"
              >
                <Check v-if="file.status === 'success'" />
                <Close v-else-if="file.status === 'failed'" />
                <Loading v-else-if="file.status === 'processing'" />
                <Clock v-else />
              </el-icon>
              <div class="flex-1 min-w-0 flex items-center gap-3 text-sm">
                <div class="flex-1 min-w-0 truncate" :title="file.path">
                  {{ basename(file.path) }}
                </div>
                <div class="flex items-center gap-2 text-xs text-gray-500 shrink-0">
                  <span v-if="file.size">{{ formatSize(file.size) }}</span>
                  <span v-if="file.duration">{{ formatDuration(file.duration) }}</span>
                </div>
                <div v-if="file.error" class="text-xs text-red-500 truncate max-w-xs" :title="file.error">
                  {{ file.error }}
                </div>
              </div>
              <a
                v-if="file.status === 'success' && convertCurrentTask && file.outputPath"
                class="text-xs text-blue-600 hover:text-blue-800 shrink-0 whitespace-nowrap"
                :href="getConvertFileDownloadUrl(convertCurrentTask.task_id, file.outputPath)"
                target="_blank"
                rel="noopener noreferrer"
              >
                下载
              </a>
            </div>
          </div>
          <div v-else class="flex-1 flex items-center justify-center text-sm text-gray-400 min-h-0">
            {{ isUploadSource ? "暂无文件，请先选择并上传文件" : "暂无文件，请先选择转码目录" }}
          </div>
        </div>
      </div>
    </div>

    <!-- 中间：空状态 -->
    <div class="flex-1 min-w-0 border rounded p-3 flex flex-col" v-else>
      <div class="flex items-center justify-between mb-3 shrink-0">
        <h3 class="text-base font-semibold">文件列表</h3>
      </div>
      <div class="flex-1 flex items-center justify-center text-sm text-gray-400">
        请从左侧选择一个任务查看文件列表
      </div>
    </div>

    <!-- 右侧：输出目录和转码进度 -->
    <div class="w-80 shrink-0 border rounded p-3 flex flex-col" v-if="convertCurrentTask">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-base font-semibold">输出信息</h3>
      </div>
      <div class="flex-1 overflow-auto flex flex-col gap-3">
        <!-- 操作按钮 -->
        <div class="border rounded p-3 flex flex-col gap-2">
          <div class="flex items-center gap-2">
            <span class="text-sm text-gray-600">覆盖同名文件</span>
            <el-switch
              v-model="convertOverwrite"
              :disabled="isDirectoryOperationDisabled"
              @change="handleConvertOverwriteChange"
            />
          </div>
          <el-button
            type="success"
            v-bind="mediumTextButtonProps"
            @click="handleConvertStart"
            :disabled="isStartConvertDisabled"
            :loading="isTaskProcessing"
            class="w-full"
          >
            开始转码
          </el-button>
        </div>

        <!-- 输出目录名称（仅目录转码） -->
        <div v-if="!isUploadSource" class="border rounded p-3 flex flex-col gap-2">
          <div class="flex items-center justify-between">
            <h4 class="text-sm font-semibold">输出目录名称</h4>
          </div>
          <div class="flex items-center gap-2">
            <el-input
              v-model="convertOutputDir"
              placeholder="输出目录名称"
              size="small"
              :disabled="isDirectoryOperationDisabled"
              @blur="handleConvertOutputDirChange"
            />
            <el-button
              type="primary"
              v-bind="smallTextButtonProps"
              :disabled="isDirectoryOperationDisabled || !convertOutputDirChanged"
              @click="handleConvertSaveOutputDir"
            >
              保存
            </el-button>
          </div>
          <div class="text-xs text-gray-400">文件将保存在转码目录下的此文件夹中</div>
        </div>

        <!-- 转码进度 -->
        <div
          v-if="convertCurrentTask.status === 'processing' || convertCurrentTask.progress"
          class="border rounded p-3 flex flex-col gap-2"
        >
          <h4 class="text-sm font-semibold">转码进度</h4>
          <div v-if="convertCurrentTask.progress" class="space-y-2">
            <div class="text-sm text-gray-600">
              已处理: {{ convertCurrentTask.progress.processed ?? 0 }} / {{ convertTotalFiles }}
            </div>
            <el-progress
              :percentage="convertProgressPercent"
              :status="convertCurrentTask.status === 'processing' ? undefined : 'success'"
            />
            <div
              v-if="convertCurrentTask.progress.current_file"
              class="text-xs text-gray-500 truncate"
              :title="convertCurrentTask.progress.current_file"
            >
              正在处理: {{ convertCurrentTask.progress.current_file }}
            </div>
          </div>
          <div v-else class="text-sm text-gray-400">等待开始转码...</div>
        </div>

        <!-- 转码结果 -->
        <div
          v-if="convertCurrentTask.status === 'success'"
          class="border rounded p-3 flex flex-col gap-2"
        >
          <h4 class="text-sm font-semibold">转码结果</h4>
          <div class="text-sm text-gray-600">
            <div>转码完成！所有文件已保存到输出目录</div>
            <div v-if="convertCurrentTask.progress" class="mt-2">共转换 {{ convertTotalFiles }} 个文件</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 右侧：空状态 -->
    <div class="w-80 shrink-0 border rounded p-3 flex flex-col" v-else>
      <h3 class="text-base font-semibold mb-3">输出信息</h3>
      <div class="flex-1 flex items-center justify-center text-sm text-gray-400">
        请从左侧选择一个任务查看输出信息
      </div>
    </div>

    <!-- 目录选择对话框 -->
    <FileDialog
      :visible="convertDirectoryDialogVisible"
      @update:visible="convertDirectoryDialogVisible = $event"
      title="选择转码目录"
      confirm-button-text="确定"
      mode="directory"
      :default-path="convertCurrentTask?.directory || undefined"
      :confirm-loading="convertLoading"
      @confirm="handleConvertDirectoryConfirm"
      @close="convertDirectoryDialogVisible = false"
    >
    </FileDialog>

    <!-- 创建任务对话框 -->
    <el-dialog
      v-model="convertCreateTaskDialogVisible"
      title="创建转码任务"
      width="400px"
      @close="handleConvertCreateTaskDialogClose"
    >
      <el-form>
        <el-form-item label="任务名称">
          <el-input
            v-model="convertNewTaskName"
            placeholder="请输入任务名称"
            @keyup.enter="handleConvertCreateTaskConfirm"
          />
        </el-form-item>
        <el-form-item label="转码来源">
          <el-radio-group v-model="convertNewTaskSourceType">
            <el-radio value="directory">目录</el-radio>
            <el-radio value="upload">上传文件</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="convertCreateTaskDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleConvertCreateTaskConfirm" :loading="convertLoading">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 改名对话框 -->
    <el-dialog
      v-model="convertRenameTaskDialogVisible"
      title="重命名任务"
      width="400px"
      @close="convertRenameTaskName = ''"
    >
      <el-form>
        <el-form-item label="任务名称">
          <el-input
            v-model="convertRenameTaskName"
            placeholder="请输入任务名称"
            @keyup.enter="handleConvertRenameTaskConfirm"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="convertRenameTaskDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleConvertRenameTaskConfirm" :loading="convertLoading">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import type { UploadFile, UploadFiles, UploadUserFile } from "element-plus";
import { Refresh, Plus, Delete, Edit, Check, Close, Loading, Clock } from "@element-plus/icons-vue";
import FileDialog from "@/views/dialogs/FileDialog.vue";
import { logAndNoticeError } from "@/utils/error";
import { formatDuration, formatSize } from "@/utils/format";
import { useControllableInterval } from "@/composables/useInterval";
import { CONVERT_TASK_POLLING_INTERVAL } from "@/constants/media";
import type { ConvertSourceType, ConvertTask } from "@/types/tools";
import {
  getConvertTaskList,
  createConvertTask,
  getConvertTask,
  deleteConvertTask,
  updateConvertTask,
  uploadConvertFiles,
  startConvertTask,
  getConvertFileDownloadUrl,
} from "@/api/api-audio-convert";

const CONVERT_UPLOAD_ACCEPT =
  ".mp3,.wav,.flac,.aac,.m4a,.ogg,.wma,.mp4,.avi,.mkv,.mov,.wmv,.flv,.webm,.m4v,.3gp,.asf,.vob,.ts,.mts,.m2ts";
const STATUS_MAP: Record<string, { tag: string; text: string }> = {
  pending: { tag: "info", text: "等待" },
  processing: { tag: "warning", text: "处理" },
  success: { tag: "success", text: "成功" },
  failed: { tag: "danger", text: "失败" },
};
const smallIconButtonProps = { size: "small" as const, plain: true, class: "!w-8 !h-6 !p-0" };
const smallTextButtonProps = { size: "small" as const, plain: true, class: "!h-5 !text-xs !px-2" };
const mediumTextButtonProps = { size: "small" as const, plain: true, class: "!h-7 !text-xs" };

const convertLoading = ref(false);
const convertTaskList = ref<ConvertTask[]>([]);
const convertCurrentTask = ref<ConvertTask | null>(null);
const convertDirectoryDialogVisible = ref(false);
const convertOutputDir = ref("mp3");
const convertOutputDirChanged = ref(false);
const convertOverwrite = ref(true);
const convertSourceType = ref<ConvertSourceType>("directory");
const convertCreateTaskDialogVisible = ref(false);
const convertNewTaskName = ref("");
const convertNewTaskSourceType = ref<ConvertSourceType>("directory");
const convertRenameTaskDialogVisible = ref(false);
const convertRenameTaskName = ref("");
const convertUploadFileList = ref<UploadUserFile[]>([]);
const convertUploadProgress = ref(0);

const basename = (path: string) => path.split("/").pop() || path;
const getConvertStatusTagType = (status: string) => STATUS_MAP[status]?.tag ?? "info";
const getConvertStatusText = (status: string) => STATUS_MAP[status]?.text ?? "未知";
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
    convertLoading.value = true;
    await action();
  } catch (error) {
    logAndNoticeError(error as Error, errorMessage);
  } finally {
    convertLoading.value = false;
  }
};

const resetUpload = (clearFiles = false) => {
  convertUploadProgress.value = 0;
  if (clearFiles) convertUploadFileList.value = [];
};

const applyTask = (task: ConvertTask) => {
  convertCurrentTask.value = task;
  const index = convertTaskList.value.findIndex(item => item.task_id === task.task_id);
  if (index >= 0) convertTaskList.value[index] = { ...task };
  convertOutputDir.value = task.output_dir || "mp3";
  convertOutputDirChanged.value = false;
  convertOverwrite.value = task.overwrite !== false;
  convertSourceType.value = (task.source_type || "directory") as ConvertSourceType;
  resetUpload(true);
};

const syncTask = async (taskId?: string) => {
  const id = taskId ?? convertCurrentTask.value?.task_id;
  if (!id) return;
  applyTask((await getConvertTask(id)).data);
};

const reloadCurrentTask = (taskId?: string) =>
  withLoading(() => syncTask(taskId), "获取任务信息失败");

const patchTask = async (
  payload: Parameters<typeof updateConvertTask>[1],
  successMessage: string,
  errorMessage: string
) => {
  const task = convertCurrentTask.value;
  if (!task) return;
  await withLoading(async () => {
    await updateConvertTask(task.task_id, payload);
    ElMessage.success(successMessage);
    await syncTask();
  }, errorMessage);
};

const loadConvertTaskList = () =>
  withLoading(async () => {
    convertTaskList.value = (await getConvertTaskList()).data.tasks || [];
    if (convertTaskList.value.length && !convertCurrentTask.value) {
      await syncTask(convertTaskList.value[0].task_id);
    }
  }, "获取任务列表失败");

const handleConvertViewTask = (taskId: string) => reloadCurrentTask(taskId);

const handleConvertCreateTask = () => {
  convertNewTaskName.value = new Date().toISOString().slice(0, 19).replace("T", " ");
  convertCreateTaskDialogVisible.value = true;
};

const handleConvertCreateTaskDialogClose = () => {
  convertNewTaskName.value = "";
  convertNewTaskSourceType.value = "directory";
};

const handleConvertCreateTaskConfirm = async () => {
  if (!convertNewTaskName.value.trim()) return ElMessage.warning("请输入任务名称");
  await withLoading(async () => {
    const { data } = await createConvertTask({
      name: convertNewTaskName.value.trim(),
      source_type: convertNewTaskSourceType.value,
    });
    ElMessage.success("任务创建成功");
    convertCreateTaskDialogVisible.value = false;
    await loadConvertTaskList();
    if (data?.task_id) await syncTask(data.task_id);
  }, "创建任务失败");
};

const handleConvertRenameTask = () => {
  if (!convertCurrentTask.value) return;
  convertRenameTaskName.value = convertCurrentTask.value.name;
  convertRenameTaskDialogVisible.value = true;
};

const handleConvertRenameTaskConfirm = async () => {
  if (!convertRenameTaskName.value.trim()) return ElMessage.warning("请输入任务名称");
  await patchTask({ name: convertRenameTaskName.value.trim() }, "任务名称修改成功", "修改任务名称失败");
  convertRenameTaskDialogVisible.value = false;
  convertRenameTaskName.value = "";
};

const handleConvertDeleteTask = async (taskId: string) => {
  if (!(await confirmAction("确定要删除该任务吗？"))) return;
  await withLoading(async () => {
    await deleteConvertTask(taskId);
    ElMessage.success("任务删除成功");
    convertTaskList.value = (await getConvertTaskList()).data.tasks || [];
    if (convertCurrentTask.value?.task_id !== taskId) return;
    if (convertTaskList.value.length) await syncTask(convertTaskList.value[0].task_id);
    else {
      convertCurrentTask.value = null;
      resetUpload(true);
    }
  }, "删除任务失败");
};

const handleConvertOpenDirectoryBrowser = () => {
  if (!convertCurrentTask.value) return ElMessage.warning("请先创建或选择任务");
  convertDirectoryDialogVisible.value = true;
};

const handleConvertDirectoryConfirm = async (filePaths: string[]) => {
  if (!filePaths.length) return;
  await patchTask({ directory: filePaths[0], source_type: "directory" }, "目录设置成功", "设置目录失败");
  convertDirectoryDialogVisible.value = false;
};

const handleConvertSourceTypeChange = (value: string | number | boolean) => {
  convertSourceType.value = value as ConvertSourceType;
  if (convertSourceType.value !== "upload") resetUpload(true);
};

const handleConvertUploadSelectionChange = (_file: UploadFile, files: UploadFiles) => {
  convertUploadFileList.value = files;
  if (convertUploadProgress.value === 100) convertUploadProgress.value = 0;
};

const handleConvertClearSelectedUploads = () => resetUpload(true);

const handleConvertUploadFiles = async () => {
  const task = convertCurrentTask.value;
  const files = convertSelectedUploadFiles.value;
  if (!task || !files.length) return ElMessage.warning("请先选择待上传文件");
  await withLoading(async () => {
    convertUploadProgress.value = 0;
    await uploadConvertFiles(task.task_id, files, p => {
      convertUploadProgress.value = p;
    });
    convertUploadProgress.value = 100;
    ElMessage.success("文件上传成功");
    resetUpload(true);
    await syncTask();
    setTimeout(() => {
      if (convertUploadProgress.value === 100) convertUploadProgress.value = 0;
    }, 500);
  }, "文件上传失败");
};

const handleConvertOutputDirChange = () => {
  if (!convertCurrentTask.value) return;
  convertOutputDirChanged.value =
    convertOutputDir.value !== (convertCurrentTask.value.output_dir || "mp3");
};

const handleConvertSaveOutputDir = async () => {
  if (!convertOutputDir.value.trim()) return ElMessage.error("输出目录名称不能为空");
  await patchTask({ output_dir: convertOutputDir.value.trim() }, "输出目录名称保存成功", "保存输出目录名称失败");
};

const handleConvertOverwriteChange = () => {
  const task = convertCurrentTask.value;
  if (!task) return;
  if (convertOverwrite.value !== (task.overwrite !== false)) {
    void patchTask({ overwrite: convertOverwrite.value }, "覆盖选项保存成功", "保存覆盖选项失败");
  }
};

const handleConvertStart = async () => {
  const task = convertCurrentTask.value;
  if (!task) return;
  if (isUploadSource.value && !convertFileList.value.length) return ElMessage.warning("请先上传待转码文件");
  if (!isUploadSource.value && !task.directory) return ElMessage.warning("请先选择转码目录");
  const message = isUploadSource.value
    ? `确定要开始转码吗？将转换当前任务中已上传的 ${convertFileList.value.length} 个文件。`
    : `确定要开始转码吗？将转换 "${task.name}"。`;
  if (!(await confirmAction(message, "确认转码"))) return;
  await withLoading(async () => {
    await startConvertTask(task.task_id);
    ElMessage.success("转码任务已启动");
    convertTaskList.value = (await getConvertTaskList()).data.tasks || [];
    await syncTask();
    startPolling();
  }, "启动任务失败");
};

const { start: startPolling, stop: stopPolling } = useControllableInterval(async () => {
  const task = convertCurrentTask.value;
  if (!task?.task_id) return stopPolling();
  try {
    const { data } = await getConvertTask(task.task_id);
    applyTask(data);
    if (data.status !== "processing") {
      convertTaskList.value = (await getConvertTaskList()).data.tasks || [];
      stopPolling();
    }
  } catch (error) {
    logAndNoticeError(error as Error, "刷新任务状态失败");
  }
}, CONVERT_TASK_POLLING_INTERVAL);

const isTaskProcessing = computed(() => convertCurrentTask.value?.status === "processing");
const isUploadSource = computed(() => convertSourceType.value === "upload");
const isSourceTypeSynced = computed(
  () =>
    !!convertCurrentTask.value &&
    convertSourceType.value ===
      ((convertCurrentTask.value.source_type || "directory") as ConvertSourceType)
);
const isStartConvertDisabled = computed(() => {
  const task = convertCurrentTask.value;
  if (!task || isTaskProcessing.value || !isSourceTypeSynced.value) return true;
  return isUploadSource.value ? !convertFileList.value.length : !task.directory;
});
const isDirectoryOperationDisabled = computed(() => isTaskProcessing.value);
const convertSelectedUploadFiles = computed(() => {
  const files: File[] = [];
  for (const item of convertUploadFileList.value) {
    if (item.raw) files.push(item.raw as File);
  }
  return files;
});
const convertSelectedUploadFileNames = computed(() =>
  convertSelectedUploadFiles.value.map(f => f.name)
);
const convertTotalFiles = computed(() => {
  const task = convertCurrentTask.value;
  return task?.total_files ?? task?.progress?.total ?? 0;
});
const convertProgressPercent = computed(() => {
  const task = convertCurrentTask.value;
  if (!task?.progress || !convertTotalFiles.value) return 0;
  return Math.round(((task.progress.processed ?? 0) / convertTotalFiles.value) * 100);
});

const resolveOutputPath = (task: ConvertTask, inputPath: string, stored?: string) => {
  if (stored) return stored;
  if (task.file_status?.[inputPath]?.status !== "success" || !task.resolved_output_dir) return;
  const name = basename(inputPath);
  const dot = name.lastIndexOf(".");
  return `${task.resolved_output_dir}/${dot > 0 ? name.slice(0, dot) : name}.mp3`;
};

const convertFileList = computed(() => {
  const task = convertCurrentTask.value;
  if (!task?.file_status || !isSourceTypeSynced.value) return [];
  return Object.entries(task.file_status).map(([path, file]) => ({
    path,
    outputPath: resolveOutputPath(task, path, file.output_path),
    status: file.status || "pending",
    error: file.error,
    size: file.size,
    duration: file.duration,
  }));
});

onMounted(loadConvertTaskList);
onUnmounted(() => {
  stopPolling();
  resetUpload(true);
});
</script>
