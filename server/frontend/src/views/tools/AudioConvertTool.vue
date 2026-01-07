<template>
  <div class="flex gap-4 h-full">
    <!-- 左侧：任务列表 -->
    <div class="w-64 border rounded p-3 flex flex-col">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-base font-semibold">任务列表</h3>
        <div class="flex items-center gap-1">
          <el-button
            type="info"
            v-bind="smallIconButtonProps"
            @click="loadConvertTaskList"
            :loading="convertLoading"
          >
            <el-icon v-if="!convertLoading"><Refresh /></el-icon>
          </el-button>
          <el-button
            type="success"
            v-bind="smallIconButtonProps"
            @click="handleConvertCreateTask"
            :loading="convertLoading"
          >
            <el-icon><Plus /></el-icon>
          </el-button>
        </div>
      </div>
      <div
        v-if="convertTaskList && convertTaskList.length > 0"
        class="flex-1 overflow-y-auto space-y-2 pr-1 min-h-[400px]"
      >
        <div
          v-for="task in convertTaskList"
          :key="task.task_id"
          class="border rounded px-3 py-2 cursor-pointer hover:bg-gray-50 group min-h-[60px] flex flex-col justify-between"
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
          <div class="flex items-center justify-between gap-2 min-h-[20px]">
            <el-tag
              :type="getConvertStatusTagType(task.status)"
              size="small"
              class="!h-5 !text-xs w-16 text-center"
            >
              {{ getConvertStatusText(task.status) }}
            </el-tag>
            <div class="flex items-center gap-1 flex-shrink-0">
              <el-button
                type="danger"
                v-bind="smallTextButtonProps"
                @click.stop="handleConvertDeleteTask(task.task_id)"
                :disabled="task.status === 'processing'"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
        </div>
      </div>
      <div
        v-else
        class="flex-1 flex items-center justify-center text-sm text-gray-400 min-h-[400px]"
      >
        暂无任务，请点击"新建"创建
      </div>
    </div>

    <!-- 右侧：任务详情 -->
    <div class="flex-1 border rounded p-3 flex flex-col max-w-2xl" v-if="convertCurrentTask">
      <div class="flex items-center justify-between mb-3 flex-shrink-0">
        <div class="flex items-center gap-2 flex-1">
          <h3 class="text-base font-semibold">任务详情: {{ convertCurrentTask.name }}</h3>
          <el-button
            type="default"
            size="small"
            plain
            circle
            :disabled="isDirectoryOperationDisabled"
            @click="handleConvertRenameTask"
            title="编辑名称"
          >
            <el-icon><Edit /></el-icon>
          </el-button>
        </div>
      </div>

      <div class="flex-1 overflow-auto flex flex-col gap-3">
        <!-- 任务信息 -->
        <div class="flex items-center justify-between gap-4 flex-shrink-0">
          <div class="flex items-center gap-4">
            <el-tag
              :type="getConvertStatusTagType(convertCurrentTask.status)"
              size="small"
              class="w-16 text-center"
            >
              {{ getConvertStatusText(convertCurrentTask.status) }}
            </el-tag>
            <span v-if="convertCurrentTask.error_message" class="text-red-500 text-xs">
              错误: {{ convertCurrentTask.error_message }}
            </span>
          </div>
          <div class="flex items-center gap-3">
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
            >
              开始转码
            </el-button>
          </div>
        </div>

        <!-- 目录选择 -->
        <div class="border rounded p-3 flex flex-col gap-2">
          <div class="flex items-center justify-between">
            <h4 class="text-sm font-semibold">转码目录</h4>
            <el-button
              type="primary"
              v-bind="smallTextButtonProps"
              :disabled="isDirectoryOperationDisabled"
              @click="handleConvertOpenDirectoryBrowser"
            >
              选择目录
            </el-button>
          </div>
          <div
            v-if="convertCurrentTask.directory"
            class="text-sm text-gray-600 truncate"
            :title="convertCurrentTask.directory"
          >
            {{ convertCurrentTask.directory }}
          </div>
          <div v-else class="text-sm text-gray-400">
            请选择一个目录，该目录下的所有音频文件将被转换为 MP3 格式
          </div>
        </div>

        <!-- 输出目录名称 -->
        <div class="border rounded p-3 flex flex-col gap-2">
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
          <div class="text-xs text-gray-400">
            转码后的文件将保存在转码目录下的此文件夹中，默认为 "mp3"
          </div>
        </div>

        <!-- 转码进度 -->
        <div
          v-if="convertCurrentTask.status === 'processing' || convertCurrentTask.progress"
          class="border rounded p-3 flex flex-col gap-2"
        >
          <h4 class="text-sm font-semibold">转码进度</h4>
          <div v-if="convertCurrentTask.progress" class="space-y-2">
            <div class="text-sm text-gray-600">
              已处理: {{ convertCurrentTask.progress.processed ?? 0 }} /
              {{ convertCurrentTask.progress.total ?? 0 }}
            </div>
            <el-progress
              :percentage="
                (convertCurrentTask.progress.total ?? 0) > 0
                  ? Math.round(
                      ((convertCurrentTask.progress.processed ?? 0) /
                        (convertCurrentTask.progress.total ?? 1)) *
                        100
                    )
                  : 0
              "
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
            <div>转码完成！所有文件已保存到目录下的 mp3 文件夹中</div>
            <div v-if="convertCurrentTask.progress" class="mt-2">
              共转换 {{ convertCurrentTask.progress.total || 0 }} 个文件
            </div>
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
      @close="handleConvertCloseDirectoryBrowser"
    >
    </FileDialog>

    <!-- 创建任务对话框 -->
    <el-dialog
      v-model="convertCreateTaskDialogVisible"
      title="创建转码任务"
      width="400px"
      @close="convertNewTaskName = ''"
    >
      <el-form>
        <el-form-item label="任务名称">
          <el-input
            v-model="convertNewTaskName"
            placeholder="请输入任务名称"
            @keyup.enter="handleConvertCreateTaskConfirm"
          />
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
import { Refresh, Plus, Delete, Edit } from "@element-plus/icons-vue";
import FileDialog from "@/views/dialogs/FileDialog.vue";
import { logAndNoticeError } from "@/utils/error";
import { useControllableInterval } from "@/composables/useInterval";
import { CONVERT_TASK_POLLING_INTERVAL } from "@/constants/media";
import type { ConvertTask } from "@/types/tools";
import {
  getConvertTaskList,
  createConvertTask,
  getConvertTask,
  deleteConvertTask,
  updateConvertTask,
  startConvertTask,
} from "@/api/audioConvert";

// 音频转码相关状态
const convertLoading = ref(false);
const convertTaskList = ref<ConvertTask[]>([]);
const convertCurrentTask = ref<ConvertTask | null>(null);
const convertDirectoryDialogVisible = ref(false);
const convertOutputDir = ref("mp3");
const convertOutputDirChanged = ref(false);
const convertOverwrite = ref(true);
const convertOverwriteChanged = ref(false);
const convertCreateTaskDialogVisible = ref(false);
const convertNewTaskName = ref("");
const convertRenameTaskDialogVisible = ref(false);
const convertRenameTaskName = ref("");

// 按钮公共属性
const smallIconButtonProps = { size: "small" as const, plain: true, class: "!w-8 !h-6 !p-0" };
const smallTextButtonProps = { size: "small" as const, plain: true, class: "!h-5 !text-xs !px-2" };
const mediumTextButtonProps = { size: "small" as const, plain: true, class: "!h-7 !text-xs" };

// 加载转码任务列表
const loadConvertTaskList = async () => {
  try {
    convertLoading.value = true;
    const response = await getConvertTaskList();
    if (response.code === 0) {
      convertTaskList.value = response.data.tasks || [];
      if (convertTaskList.value.length > 0 && !convertCurrentTask.value) {
        await handleConvertViewTask(convertTaskList.value[0].task_id);
      }
    } else {
      ElMessage.error(response.msg || "获取任务列表失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "获取任务列表失败");
  } finally {
    convertLoading.value = false;
  }
};

// 打开创建任务对话框
const handleConvertCreateTask = () => {
  convertNewTaskName.value = "";
  convertCreateTaskDialogVisible.value = true;
};

// 确认创建任务
const handleConvertCreateTaskConfirm = async () => {
  if (!convertNewTaskName.value.trim()) {
    ElMessage.warning("请输入任务名称");
    return;
  }

  try {
    convertLoading.value = true;
    const response = await createConvertTask({
      name: convertNewTaskName.value.trim(),
    });

    if (response.code === 0) {
      ElMessage.success("任务创建成功");
      convertCreateTaskDialogVisible.value = false;
      convertNewTaskName.value = "";
      await loadConvertTaskList();
      handleConvertViewTask(response.data.task_id);
    } else {
      ElMessage.error(response.msg || "创建任务失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "创建任务失败");
  } finally {
    convertLoading.value = false;
  }
};

// 打开改名对话框
const handleConvertRenameTask = () => {
  if (!convertCurrentTask.value) {
    return;
  }
  convertRenameTaskName.value = convertCurrentTask.value.name;
  convertRenameTaskDialogVisible.value = true;
};

// 确认改名
const handleConvertRenameTaskConfirm = async () => {
  if (!convertCurrentTask.value) {
    return;
  }

  if (!convertRenameTaskName.value.trim()) {
    ElMessage.warning("请输入任务名称");
    return;
  }

  try {
    convertLoading.value = true;
    const response = await updateConvertTask(convertCurrentTask.value.task_id, {
      name: convertRenameTaskName.value.trim(),
    });

    if (response.code === 0) {
      ElMessage.success("任务名称修改成功");
      convertRenameTaskDialogVisible.value = false;
      convertRenameTaskName.value = "";
      await handleConvertViewTask(convertCurrentTask.value.task_id);
    } else {
      ElMessage.error(response.msg || "修改任务名称失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "修改任务名称失败");
  } finally {
    convertLoading.value = false;
  }
};

// 查看转码任务
const handleConvertViewTask = async (taskId: string) => {
  try {
    convertLoading.value = true;
    const response = await getConvertTask(taskId);
    if (response.code === 0) {
      convertCurrentTask.value = response.data;
      // 初始化输出目录名称
      convertOutputDir.value = response.data.output_dir || "mp3";
      convertOutputDirChanged.value = false;
      // 初始化覆盖选项
      convertOverwrite.value = response.data.overwrite !== false; // 默认为 true
      convertOverwriteChanged.value = false;
    } else {
      ElMessage.error(response.msg || "获取任务信息失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "获取任务信息失败");
  } finally {
    convertLoading.value = false;
  }
};

// 删除转码任务
const handleConvertDeleteTask = async (taskId: string) => {
  const confirmed = await ElMessageBox.confirm("确定要删除该任务吗？", "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).catch(() => false);

  if (!confirmed) return;

  try {
    convertLoading.value = true;
    const response = await deleteConvertTask(taskId);
    if (response.code === 0) {
      ElMessage.success("任务删除成功");
      await loadConvertTaskList();
      if (convertCurrentTask.value && convertCurrentTask.value.task_id === taskId) {
        if (convertTaskList.value && convertTaskList.value.length > 0) {
          await handleConvertViewTask(convertTaskList.value[0].task_id);
        } else {
          convertCurrentTask.value = null;
        }
      }
    } else {
      ElMessage.error(response.msg || "删除任务失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "删除任务失败");
  } finally {
    convertLoading.value = false;
  }
};

// 打开目录选择对话框
const handleConvertOpenDirectoryBrowser = () => {
  if (!convertCurrentTask.value) {
    ElMessage.warning("请先创建或选择任务");
    return;
  }
  convertDirectoryDialogVisible.value = true;
};

// 处理目录选择确认
const handleConvertDirectoryConfirm = async (filePaths: string[]) => {
  if (!convertCurrentTask.value) {
    return;
  }

  if (filePaths.length === 0) {
    return;
  }

  const directoryPath = filePaths[0];

  try {
    convertLoading.value = true;
    const response = await updateConvertTask(convertCurrentTask.value.task_id, {
      directory: directoryPath,
    });

    if (response.code === 0) {
      ElMessage.success("目录设置成功");
      await handleConvertViewTask(convertCurrentTask.value.task_id);
      convertDirectoryDialogVisible.value = false;
    } else {
      ElMessage.error(response.msg || "设置目录失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "设置目录失败");
  } finally {
    convertLoading.value = false;
  }
};

// 关闭目录选择对话框
const handleConvertCloseDirectoryBrowser = () => {
  convertDirectoryDialogVisible.value = false;
};

// 输出目录名称变化处理
const handleConvertOutputDirChange = () => {
  if (!convertCurrentTask.value) {
    return;
  }
  const currentValue = convertCurrentTask.value.output_dir || "mp3";
  convertOutputDirChanged.value = convertOutputDir.value !== currentValue;
};

// 保存输出目录名称
const handleConvertSaveOutputDir = async () => {
  if (!convertCurrentTask.value) {
    return;
  }

  if (!convertOutputDir.value.trim()) {
    ElMessage.error("输出目录名称不能为空");
    return;
  }

  try {
    convertLoading.value = true;
    const response = await updateConvertTask(convertCurrentTask.value.task_id, {
      output_dir: convertOutputDir.value.trim(),
    });

    if (response.code === 0) {
      ElMessage.success("输出目录名称保存成功");
      await handleConvertViewTask(convertCurrentTask.value.task_id);
    } else {
      ElMessage.error(response.msg || "保存输出目录名称失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "保存输出目录名称失败");
  } finally {
    convertLoading.value = false;
  }
};

// 覆盖选项变化处理
const handleConvertOverwriteChange = () => {
  if (!convertCurrentTask.value) {
    return;
  }
  const currentValue = convertCurrentTask.value.overwrite !== false; // 默认为 true
  convertOverwriteChanged.value = convertOverwrite.value !== currentValue;

  // 如果改变了，自动保存
  if (convertOverwriteChanged.value) {
    handleConvertSaveOverwrite();
  }
};

// 保存覆盖选项
const handleConvertSaveOverwrite = async () => {
  if (!convertCurrentTask.value) {
    return;
  }

  try {
    convertLoading.value = true;
    const response = await updateConvertTask(convertCurrentTask.value.task_id, {
      overwrite: convertOverwrite.value,
    });

    if (response.code === 0) {
      ElMessage.success("覆盖选项保存成功");
      await handleConvertViewTask(convertCurrentTask.value.task_id);
    } else {
      ElMessage.error(response.msg || "保存覆盖选项失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "保存覆盖选项失败");
  } finally {
    convertLoading.value = false;
  }
};

// 开始转码
const handleConvertStart = async () => {
  if (!convertCurrentTask.value) {
    return;
  }

  if (!convertCurrentTask.value.directory) {
    ElMessage.warning("请先选择转码目录");
    return;
  }

  const confirmed = await ElMessageBox.confirm(
    `确定要开始转码吗？将转换目录 "${convertCurrentTask.value.directory}" 下的所有音频文件为 MP3 格式。`,
    "确认转码",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    }
  ).catch(() => false);

  if (!confirmed) return;

  try {
    convertLoading.value = true;
    const response = await startConvertTask(convertCurrentTask.value.task_id);
    if (response.code === 0) {
      ElMessage.success("转码任务已启动");
      await loadConvertTaskList();
      await handleConvertViewTask(convertCurrentTask.value.task_id);
      startConvertPollingTaskStatus();
    } else {
      ElMessage.error(response.msg || "启动任务失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "启动任务失败");
  } finally {
    convertLoading.value = false;
  }
};

// 轮询转码任务状态
const { start: startConvertPolling, stop: stopConvertPolling } = useControllableInterval(
  async () => {
    if (!convertCurrentTask.value || convertCurrentTask.value.status !== "processing") {
      stopConvertPolling();
      return;
    }
    await loadConvertTaskList();
    await handleConvertViewTask(convertCurrentTask.value.task_id);
  },
  CONVERT_TASK_POLLING_INTERVAL,
  { immediate: false }
);

const startConvertPollingTaskStatus = () => {
  startConvertPolling();
};

// 转码状态映射
const CONVERT_STATUS_MAP: Record<string, { tag: string; text: string }> = {
  pending: { tag: "info", text: "等待中" },
  processing: { tag: "warning", text: "处理中" },
  success: { tag: "success", text: "成功" },
  failed: { tag: "danger", text: "失败" },
};

// 获取转码状态标签类型
const getConvertStatusTagType = (status: string): string => {
  return CONVERT_STATUS_MAP[status]?.tag || "info";
};

// 获取转码状态文本
const getConvertStatusText = (status: string): string => {
  return CONVERT_STATUS_MAP[status]?.text || "未知";
};

// 计算属性
const isTaskProcessing = computed(() => convertCurrentTask.value?.status === "processing");
const isStartConvertDisabled = computed(
  () => !convertCurrentTask.value?.directory || isTaskProcessing.value
);
const isDirectoryOperationDisabled = computed(() => isTaskProcessing.value);

onMounted(() => {
  loadConvertTaskList();
});

onUnmounted(() => {
  stopConvertPolling();
});
</script>
