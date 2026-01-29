<template>
  <div class="flex gap-4 h-[calc(100vh-220px)]">
    <!-- 左侧：任务列表 -->
    <div class="w-64 border rounded p-3 flex flex-col">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-base font-semibold">任务列表</h3>
        <div class="flex items-center gap-1">
          <el-button
            type="info"
            v-bind="smallIconButtonProps"
            @click="loadTtsTaskList"
            :loading="ttsLoading"
          >
            <el-icon v-if="!ttsLoading">
              <Refresh />
            </el-icon>
          </el-button>
          <el-button type="success" v-bind="smallIconButtonProps" @click="handleTtsCreateTask">
            <el-icon>
              <Plus />
            </el-icon>
          </el-button>
        </div>
      </div>
      <div
        v-if="ttsTaskList && ttsTaskList.length > 0"
        class="flex-1 overflow-y-auto space-y-2 pr-1 min-h-[400px]"
      >
        <div
          v-for="task in ttsTaskList"
          :key="task.task_id"
          class="border rounded px-3 py-2 cursor-pointer hover:bg-gray-50 group min-h-[60px] flex flex-col justify-between"
          :class="{
            'border-blue-500 bg-blue-50': ttsCurrentTask && task.task_id === ttsCurrentTask.task_id,
          }"
          @click="handleTtsViewTask(task.task_id)"
        >
          <!-- 第一行：名称 -->
          <div class="flex items-center justify-between gap-2">
            <div class="text-sm font-medium truncate flex-1 min-w-0" :title="task.name">
              {{ task.name }}
            </div>
            <span v-if="task.duration" class="text-xs text-gray-500 flex-shrink-0">
              {{ formatDuration(task.duration) }}
            </span>
          </div>
          <!-- 第二行：状态、下载按钮、删除按钮 -->
          <div class="flex items-center justify-between gap-2 min-h-[20px]">
            <el-tag
              :type="getTtsStatusTagType(task.status)"
              size="small"
              class="!h-5 !text-xs w-14 text-center"
            >
              {{ getTtsStatusText(task.status) }}
            </el-tag>
            <el-tag
              v-if="task.analysis"
              type="primary"
              size="small"
              effect="dark"
              round
              class="!h-4 !w-4 !text-[10px] mr-1"
            >
              析
            </el-tag>
            <div class="flex items-center justify-end gap-0 flex-shrink-0 w-23">
              <el-button
                v-if="task.output_file"
                type="primary"
                class="!w-6"
                v-bind="smallTextButtonProps"
                @click.stop="handleTtsDownloadFromList(task)"
              >
                <el-icon><Download /></el-icon>
              </el-button>
              <el-button
                type="danger"
                v-bind="smallTextButtonProps"
                class="!w-6"
                @click.stop="handleTtsDeleteTask(task.task_id)"
                :disabled="isTaskBusyForTask(task)"
              >
                <el-icon>
                  <Delete />
                </el-icon>
              </el-button>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="flex-1 flex items-center justify-center text-sm text-gray-400">
        暂无任务，请点击"新建"创建
      </div>
    </div>

    <!-- 中间：任务详情 -->
    <div class="flex-1 border rounded p-3 flex flex-col min-h-0" v-if="ttsCurrentTask">
      <div class="flex items-center mb-3 flex-shrink-0">
        <div class="flex items-center gap-2 flex-1">
          <h3 class="text-base font-semibold">任务详情: {{ ttsCurrentTask.name }}</h3>
          <el-button
            type="default"
            size="small"
            plain
            circle
            :disabled="isTaskBusy"
            @click="handleTtsRenameTask"
            title="编辑名称"
          >
            <el-icon>
              <Edit />
            </el-icon>
          </el-button>
        </div>
      </div>

      <div class="flex-1 flex flex-col gap-3 min-h-0">
        <!-- 任务信息（恢复原位置） -->
        <div class="flex items-center gap-4 flex-shrink-0 flex-wrap">
          <el-tag
            :type="getTtsStatusTagType(ttsCurrentTask.status)"
            size="small"
            class="w-16 text-center"
          >
            {{ getTtsStatusText(ttsCurrentTask.status) }}
          </el-tag>
          <MediaComponent
            v-if="resultFileObject"
            :file="resultFileObject"
            :player="ttsPlayer"
            :disabled="isTaskBusy"
            @play="handleTtsTogglePlayResult"
            @seek="handleResultFileSeek"
          />
          <el-button
            type="primary"
            v-bind="mediumTextButtonProps"
            @click="handleTtsDownload"
            :disabled="isResultActionDisabled"
          >
            下载
          </el-button>
          <span
            v-if="ttsCurrentTask.total_chars !== undefined"
            class="text-xs text-gray-600 ml-auto"
          >
            <template v-if="isTaskProcessing && ttsCurrentTask.generated_chars !== undefined">
              {{ ttsCurrentTask.generated_chars }} / {{ ttsCurrentTask.total_chars }}
            </template>
            <template v-else>
              {{ ttsCurrentTask.total_chars }}
            </template>
          </span>
          <el-tooltip
            v-if="ttsCurrentTask.error_message"
            :content="`错误: ${ttsCurrentTask.error_message}`"
            placement="top"
            class="w-full"
          >
            <span class="text-red-500 text-xs truncate max-w-xs inline-block cursor-help">
              错误: {{ ttsCurrentTask.error_message }}
            </span>
          </el-tooltip>
        </div>
        <!-- 文本输入 -->
        <div class="border rounded p-3 flex flex-col gap-2 flex-1 min-h-0">
          <div class="flex items-center justify-between">
            <h4 class="h-8 text-sm font-semibold">文本内容</h4>
            <div class="flex items-center gap-2">
              <!-- 图片缩略图 -->
              <div v-if="selectedImages.length > 0" class="flex items-center gap-2 mr-2">
                <div
                  v-for="(image, index) in selectedImages"
                  :key="index"
                  class="relative group cursor-pointer"
                  @click="handleImagePreview(index)"
                >
                  <img
                    :src="getImagePreviewUrl(index)"
                    :alt="image.name"
                    class="w-8 h-8 object-cover rounded border border-gray-300 hover:border-blue-500 transition-colors"
                  />
                  <div
                    class="absolute -right-1 -top-1 w-4 h-4 bg-red-500 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    @click.stop="removeImage(index)"
                  >
                    <el-icon class="text-white text-xs">
                      <Close />
                    </el-icon>
                  </div>
                </div>
              </div>
              <input
                ref="imageInputRef"
                type="file"
                accept="image/*"
                multiple
                @change="handleImageSelect"
                class="hidden"
              />
              <el-button
                type="default"
                size="small"
                @click="handleSelectImages"
                :disabled="isTaskBusy"
                class="!p-0"
              >
                <el-icon class="!w-7 !h-6">
                  <Picture class="!w-5 !h-5" />
                </el-icon>
              </el-button>
              <el-button
                type="primary"
                size="small"
                @click="handleOcrRecognize"
                :disabled="isTaskBusy || selectedImages.length === 0 || !ttsCurrentTask"
                :loading="ocrLoading"
              >
                识别
              </el-button>
            </div>
          </div>
          <el-input
            v-model="ttsText"
            type="textarea"
            :autosize="{ minRows: 6, maxRows: 17 }"
            placeholder="请输入要转换为语音的文本"
            :disabled="isTaskBusy"
            @blur="handleTtsTextChange"
            class="flex-1"
          />
        </div>

        <!-- 分析数据（中间列底部） -->
        <div class="border rounded p-3 flex flex-col gap-2 flex-shrink-10 h-[240px]">
          <div class="flex items-center justify-between">
            <h4 class="text-sm font-semibold">分析数据</h4>
            <el-button
              type="primary"
              size="small"
              :loading="analysisLoading"
              :disabled="isTaskBusy || !ttsText.trim()"
              @click="handleTtsAnalysis"
            >
              分析
            </el-button>
          </div>

          <!-- 未选择任务 / 无文本提示 -->
          <div v-if="!ttsCurrentTask" class="text-xs text-gray-400">
            请先在左侧创建或选择一个 TTS 任务。
          </div>
          <div v-else-if="!ttsText.trim()" class="text-xs text-gray-400">
            当前任务还没有可分析的文本，请先在上方输入内容。
          </div>
          <div v-else-if="!ttsCurrentTask.analysis" class="text-xs text-gray-400">
            暂无分析结果，请点击右上角「分析」按钮，稍等几秒后刷新任务即可查看。
          </div>

          <!-- 有分析结果时展示结构化内容 -->
          <div v-else class="text-xs space-y-3 max-h-45 overflow-auto pr-1">
            <!-- 优美词汇 -->
            <div v-if="ttsCurrentTask.analysis.words?.length" class="flex gap-3">
              <!-- 左侧大方块标题（两行文字） -->
              <div
                class="w-10 h-6 rounded-md bg-blue-50 border border-blue-300 flex items-center justify-center flex-shrink-0"
              >
                <span class="text-[11px] leading-tight text-blue-700 text-center"> 美词 </span>
              </div>
              <!-- 右侧正文 -->
              <div class="flex-1 flex flex-wrap gap-1 items-start">
                <el-tag
                  v-for="(w, idx) in ttsCurrentTask.analysis.words"
                  :key="idx"
                  size="small"
                  effect="light"
                  class="!text-xs"
                >
                  {{ w }}
                </el-tag>
              </div>
            </div>

            <!-- 精彩句段 -->
            <div v-if="ttsCurrentTask.analysis.sentence?.length" class="flex gap-3">
              <!-- 左侧大方块标题 -->
              <div
                class="w-10 h-10 rounded-md bg-emerald-50 border border-emerald-300 flex items-center justify-center flex-shrink-0"
              >
                <span class="text-[11px] leading-tight text-emerald-700 text-center">
                  精彩<br />句段
                </span>
              </div>
              <!-- 右侧正文 -->
              <div class="flex-1 space-y-1">
                <p
                  v-for="(s, idx) in ttsCurrentTask.analysis.sentence"
                  :key="idx"
                  class="leading-snug text-gray-700"
                >
                  {{ s }}
                </p>
              </div>
            </div>

            <!-- 好句花园（摘要） -->
            <div v-if="ttsCurrentTask.analysis.abstract" class="flex gap-3">
              <!-- 左侧大方块标题 -->
              <div
                class="w-10 h-10 rounded-md bg-amber-50 border border-amber-300 flex items-center justify-center flex-shrink-0"
              >
                <span class="text-[11px] leading-tight text-amber-700 text-center">
                  好句<br />花园
                </span>
              </div>
              <!-- 右侧正文 -->
              <div class="flex-1">
                <p class="leading-snug text-gray-700">
                  {{ ttsCurrentTask.analysis.abstract }}
                </p>
              </div>
            </div>

            <!-- 涂鸦 -->
            <div v-if="ttsCurrentTask.analysis.doodle" class="flex gap-3">
              <!-- 左侧大方块标题 -->
              <div
                class="w-10 h-6 rounded-md bg-pink-50 border border-pink-300 flex items-center justify-center flex-shrink-0"
              >
                <span class="text-[11px] leading-tight text-pink-700 text-center"> 涂鸦 </span>
              </div>
              <!-- 右侧正文 -->
              <div class="flex-1">
                <p class="leading-snug text-gray-700">
                  {{ ttsCurrentTask.analysis.doodle }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 中间：空状态 -->
    <div class="flex-1 border rounded p-3 flex flex-col" v-else>
      <div class="flex items-center justify-between mb-3 flex-shrink-0">
        <h3 class="text-base font-semibold">任务详情</h3>
      </div>
      <div class="flex-1 flex items-center justify-center text-sm text-gray-400">
        请从左侧选择一个任务查看详情
      </div>
    </div>

    <!-- 右侧：参数和操作 -->
    <div class="w-80 border rounded p-3 flex flex-col" v-if="ttsCurrentTask">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-base font-semibold">参数与生成</h3>
      </div>
      <div class="flex-1 overflow-auto flex flex-col gap-3">
        <!-- 参数设置 -->
        <div class="border rounded p-3 flex flex-col gap-2">
          <h4 class="text-sm font-semibold">参数设置</h4>
          <div class="grid grid-cols-2 gap-3">
            <div class="flex flex-col gap-1">
              <label class="text-xs text-gray-600">模型</label>
              <el-select
                v-model="ttsModel"
                size="small"
                placeholder="默认模型"
                clearable
                :disabled="isTaskBusy"
                @change="handleTtsParamsChange"
                class="w-full"
              >
                <el-option label="cosyvoice-v3-flash" value="cosyvoice-v3-flash" />
                <el-option label="cosyvoice-v3-plus" value="cosyvoice-v3-plus" />
              </el-select>
            </div>
            <div class="flex flex-col gap-1">
              <label class="text-xs text-gray-600">发音人/音色</label>
              <el-select
                v-model="ttsRole"
                size="small"
                placeholder="请选择音色（可选）"
                clearable
                :disabled="isTaskBusy"
                @change="handleTtsRoleChange"
                class="w-full"
              >
                <el-option
                  label="灿灿"
                  value="cosyvoice-v3-plus-leo-34ba9eaebae44039a4a9426af6389dcd"
                />
              </el-select>
            </div>
            <div class="flex flex-col gap-1">
              <label class="text-xs text-gray-600">语速</label>
              <el-input-number
                v-model="ttsSpeed"
                size="small"
                :min="0.5"
                :max="2.0"
                :step="0.1"
                :precision="1"
                :disabled="isTaskBusy"
                @change="handleTtsParamsChange"
                class="w-full"
              />
            </div>
            <div class="flex flex-col gap-1">
              <label class="text-xs text-gray-600">音量</label>
              <el-input-number
                v-model="ttsVol"
                size="small"
                :min="0"
                :max="100"
                :step="1"
                :disabled="isTaskBusy"
                @change="handleTtsParamsChange"
                class="w-full"
              />
            </div>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="border rounded p-3 flex flex-col gap-2 flex-shrink-0">
          <el-tooltip
            v-if="!isTaskProcessing"
            :content="!ttsText.trim() ? '请先输入文本内容' : ''"
            :disabled="!!ttsText.trim()"
            placement="top"
          >
            <el-button
              type="success"
              v-bind="mediumTextButtonProps"
              @click="handleTtsStart"
              :disabled="isStartDisabled"
              class="w-full"
            >
              开始生成
            </el-button>
          </el-tooltip>
          <el-button
            v-else
            type="warning"
            v-bind="mediumTextButtonProps"
            @click="handleTtsStop"
            class="w-full"
          >
            停止生成
          </el-button>
        </div>
      </div>
    </div>

    <!-- 右侧：空状态 -->
    <div class="w-80 border rounded p-3 flex flex-col" v-else>
      <h3 class="text-base font-semibold mb-3">参数与生成</h3>
      <div class="flex-1 flex items-center justify-center text-sm text-gray-400">
        请从左侧选择一个任务查看参数
      </div>
    </div>

    <!-- 创建任务对话框 -->
    <el-dialog
      v-model="ttsCreateTaskDialogVisible"
      title="创建 TTS 任务"
      width="500px"
      @close="handleTtsCreateTaskDialogClose"
    >
      <el-form>
        <el-form-item label="任务名称">
          <el-input
            v-model="ttsNewTaskName"
            placeholder="请输入任务名称"
            @keyup.enter="handleTtsCreateTaskConfirm"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ttsCreateTaskDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleTtsCreateTaskConfirm"> 确定 </el-button>
      </template>
    </el-dialog>

    <!-- 改名对话框 -->
    <el-dialog
      v-model="ttsRenameTaskDialogVisible"
      title="重命名任务"
      width="400px"
      @close="ttsRenameTaskName = ''"
    >
      <el-form>
        <el-form-item label="任务名称">
          <el-input
            v-model="ttsRenameTaskName"
            placeholder="请输入任务名称"
            @keyup.enter="handleTtsRenameTaskConfirm"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ttsRenameTaskDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleTtsRenameTaskConfirm"> 确定 </el-button>
      </template>
    </el-dialog>

    <!-- 图片全屏预览对话框 -->
    <el-dialog
      v-model="imagePreviewVisible"
      :title="previewImageName"
      width="90%"
      align-center
      @close="previewImageIndex = -1"
    >
      <div class="flex items-center justify-center min-h-[400px]">
        <img
          v-if="previewImageIndex >= 0 && selectedImages[previewImageIndex]"
          :src="getImagePreviewUrl(previewImageIndex)"
          :alt="selectedImages[previewImageIndex].name"
          class="max-w-full max-h-[70vh] object-contain"
        />
      </div>
      <template #footer>
        <div class="flex items-center justify-between w-full">
          <div class="flex items-center gap-2">
            <el-button
              @click="previewPreviousImage"
              :disabled="previewImageIndex <= 0"
              size="small"
            >
              上一张
            </el-button>
            <span class="text-sm text-gray-600">
              {{ previewImageIndex + 1 }} / {{ selectedImages.length }}
            </span>
            <el-button
              @click="previewNextImage"
              :disabled="previewImageIndex >= selectedImages.length - 1"
              size="small"
            >
              下一张
            </el-button>
          </div>
          <el-button type="danger" @click="removeImage(previewImageIndex)" size="small">
            删除
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Refresh, Plus, Delete, Edit, Close, Picture, Download } from "@element-plus/icons-vue";
import MediaComponent from "@/components/MediaComponent.vue";
import { getMediaFileUrl } from "@/utils/file";
import { logAndNoticeError } from "@/utils/error";
import { formatDuration } from "@/utils/format";
import { useAudioPlayer } from "@/composables/useAudioPlayer";
import { useControllableInterval } from "@/composables/useInterval";
import { MEDIA_TASK_POLLING_INTERVAL } from "@/constants/media";
import type { TTSTask } from "@/types/tools/tts";
import type { MediaFile } from "@/types/tools";
import {
  getTtsTaskList,
  createTtsTask,
  getTtsTask,
  deleteTtsTask,
  updateTtsTask,
  startTtsTask,
  stopTtsTask,
  getTtsTaskDownloadUrl,
  ocrTtsTask,
  analyzeTtsTask,
} from "@/api/tts";

// TTS 常量配置
const DEFAULT_ROLE = "cosyvoice-v3-plus-leo-34ba9eaebae44039a4a9426af6389dcd"; // 默认音色：灿灿
const DEFAULT_SPEED = 0.8; // 默认语速
const DEFAULT_VOL = 50; // 默认音量

// TTS 相关状态
const ttsLoading = ref(false);
const ttsTaskList = ref<TTSTask[]>([]);
const ttsCurrentTask = ref<TTSTask | null>(null);
const currentFetchingTaskId = ref<string | null>(null); // 当前正在获取的任务ID
const ttsCreateTaskDialogVisible = ref(false);
const ttsNewTaskName = ref("");
const ttsNewTaskText = ref("");
const ttsRenameTaskDialogVisible = ref(false);
const ttsRenameTaskName = ref("");

// 任务参数
const ttsText = ref("");
const ttsRole = ref<string | null>(DEFAULT_ROLE);
const ttsModel = ref<string | null>(null); // 模型选择：cosyvoice-v3-flash 或 cosyvoice-v3-plus
const ttsSpeed = ref(DEFAULT_SPEED);
const ttsVol = ref(DEFAULT_VOL);
const ttsParamsChanged = ref(false);

// OCR 相关状态
const imageInputRef = ref<HTMLInputElement | null>(null);
const selectedImages = ref<File[]>([]);
const imagePreviewUrls = ref<Map<number, string>>(new Map()); // 存储图片预览 URL
const ocrLoading = ref(false);
const analysisLoading = ref(false);
const imagePreviewVisible = ref(false);
const previewImageIndex = ref(-1);

// 统一的播放器相关状态
const ttsPlayer = useAudioPlayer({
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

// 按钮公共属性
const smallIconButtonProps = { size: "small" as const, plain: true, class: "!w-8 !h-6 !p-0" };
const smallTextButtonProps = { size: "small" as const, plain: true, class: "!h-5 !text-xs !px-2" };
const mediumTextButtonProps = { size: "small" as const, plain: true, class: "!h-7 !text-xs" };

// 加载 TTS 任务列表
const loadTtsTaskList = async () => {
  try {
    ttsLoading.value = true;
    const response = await getTtsTaskList();
    if (response.code === 0) {
      ttsTaskList.value = response.data || [];
      if (ttsTaskList.value.length > 0 && !ttsCurrentTask.value) {
        await handleTtsViewTask(ttsTaskList.value[0].task_id);
      }
    } else {
      ElMessage.error(response.msg || "获取任务列表失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "获取任务列表失败");
  } finally {
    ttsLoading.value = false;
  }
};

// 打开创建任务对话框
const handleTtsCreateTask = () => {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  const hours = String(now.getHours()).padStart(2, "0");
  const minutes = String(now.getMinutes()).padStart(2, "0");
  const seconds = String(now.getSeconds()).padStart(2, "0");
  ttsNewTaskName.value = `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
  ttsNewTaskText.value = "";
  ttsCreateTaskDialogVisible.value = true;
};

// 关闭创建任务对话框
const handleTtsCreateTaskDialogClose = () => {
  ttsNewTaskName.value = "";
};

// 确认创建任务
const handleTtsCreateTaskConfirm = async () => {
  try {
    ttsLoading.value = true;
    const response = await createTtsTask({
      text: "", // 创建时不需要文本，可以在创建后编辑
      name: ttsNewTaskName.value.trim() || undefined,
    });

    if (response.code === 0) {
      ElMessage.success("任务创建成功");
      ttsCreateTaskDialogVisible.value = false;
      ttsNewTaskName.value = "";
      await loadTtsTaskList();
      handleTtsViewTask(response.data.task_id);
    } else {
      ElMessage.error(response.msg || "创建任务失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "创建任务失败");
  } finally {
    ttsLoading.value = false;
  }
};

// 更新任务参数到UI（从任务数据）
const updateTaskParamsFromData = (task: TTSTask) => {
  ttsText.value = task.text || "";
  ttsRole.value = task.role || DEFAULT_ROLE;
  ttsModel.value = task.model || null;
  ttsSpeed.value = task.speed ?? DEFAULT_SPEED;
  ttsVol.value = task.vol ?? DEFAULT_VOL;
  ttsParamsChanged.value = false;
};

// 检查是否应该处理请求结果（防止快速切换时的数据覆盖）
const shouldProcessRequest = (taskId: string): boolean => {
  return currentFetchingTaskId.value === taskId;
};

// 更新任务列表中的任务状态
const updateTaskInList = (task: TTSTask) => {
  const taskIndex = ttsTaskList.value.findIndex(t => t.task_id === task.task_id);
  if (taskIndex !== -1) {
    ttsTaskList.value[taskIndex] = { ...task };
  }
};

// 查看 TTS 任务
const handleTtsViewTask = async (taskId: string) => {
  const isTaskSwitching = ttsCurrentTask.value && ttsCurrentTask.value.task_id !== taskId;

  // 如果切换任务，执行清理操作
  if (isTaskSwitching && ttsCurrentTask.value) {
    handleTtsStopPlay();
    clearSelectedImages();
    // 如果当前任务不再“忙”（非 TTS 生成中且非 OCR/分析子任务中），停止轮询
    if (!isTaskBusyInList(ttsCurrentTask.value)) {
      stopTtsPolling();
    }
  }

  // 优化：先从任务列表中查找任务数据，立即更新UI，提升响应速度
  const taskInList = ttsTaskList.value.find(t => t.task_id === taskId);
  if (taskInList) {
    ttsCurrentTask.value = { ...taskInList };
    updateTaskParamsFromData(taskInList);

    // 若任务正在 TTS 生成或 OCR/分析子任务中，启动轮询
    if (isTaskBusyInList(taskInList)) {
      startTtsPollingTaskStatus();
    }
  }

  // 然后在后台异步获取最新的任务详情（静默更新，不显示loading）
  currentFetchingTaskId.value = taskId;
  try {
    const response = await getTtsTask(taskId);

    // 检查是否仍然是当前要获取的任务（用户可能已经切换了）
    if (!shouldProcessRequest(taskId)) {
      return;
    }

    if (response.code === 0) {
      // 双重检查，确保数据一致性
      if (!shouldProcessRequest(taskId)) {
        return;
      }

      const taskData = response.data;
      ttsCurrentTask.value = taskData;
      updateTaskInList(taskData);
      updateTaskParamsFromData(taskData);

      // 若任务正在 TTS 生成或 OCR/分析子任务中，自动开始定时刷新状态
      if (taskData.status === "processing" || taskData.ocr_running || taskData.analysis_running) {
        startTtsPollingTaskStatus();
      }
    }
  } catch (error) {
    // 静默失败，不影响UI显示（因为已经使用了列表中的数据）
    if (shouldProcessRequest(taskId)) {
      console.error(`[TTS] 获取任务详情失败: ${taskId}`, error);
    }
  } finally {
    // 清理标记
    if (shouldProcessRequest(taskId)) {
      currentFetchingTaskId.value = null;
    }
  }
};

// 删除 TTS 任务
const handleTtsDeleteTask = async (taskId: string) => {
  // 如果删除的是当前选中的任务，且该任务不再“忙”，停止轮询
  if (ttsCurrentTask.value && ttsCurrentTask.value.task_id === taskId) {
    if (!isTaskBusyInList(ttsCurrentTask.value)) {
      stopTtsPolling();
    }
  }

  const confirmed = await ElMessageBox.confirm("确定要删除该任务吗？", "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).catch(() => false);

  if (!confirmed) return;

  try {
    ttsLoading.value = true;
    const response = await deleteTtsTask(taskId);
    if (response.code === 0) {
      ElMessage.success("任务删除成功");
      await loadTtsTaskList();
      if (ttsCurrentTask.value && ttsCurrentTask.value.task_id === taskId) {
        if (ttsTaskList.value && ttsTaskList.value.length > 0) {
          await handleTtsViewTask(ttsTaskList.value[0].task_id);
        } else {
          ttsCurrentTask.value = null;
        }
      }
    } else {
      ElMessage.error(response.msg || "删除任务失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "删除任务失败");
  } finally {
    ttsLoading.value = false;
  }
};

// 打开改名对话框
const handleTtsRenameTask = () => {
  if (!ttsCurrentTask.value) {
    return;
  }
  ttsRenameTaskName.value = ttsCurrentTask.value.name;
  ttsRenameTaskDialogVisible.value = true;
};

// 确认改名
const handleTtsRenameTaskConfirm = async () => {
  if (!ttsCurrentTask.value) {
    return;
  }

  if (!ttsRenameTaskName.value.trim()) {
    ElMessage.warning("请输入任务名称");
    return;
  }

  try {
    ttsLoading.value = true;
    const response = await updateTtsTask(ttsCurrentTask.value.task_id, {
      name: ttsRenameTaskName.value.trim(),
    });

    if (response.code === 0) {
      ElMessage.success("任务名称修改成功");
      ttsRenameTaskDialogVisible.value = false;
      ttsRenameTaskName.value = "";
      await handleTtsViewTask(ttsCurrentTask.value.task_id);
    } else {
      ElMessage.error(response.msg || "修改任务名称失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "修改任务名称失败");
  } finally {
    ttsLoading.value = false;
  }
};

// 文本变化处理
const handleTtsTextChange = () => {
  if (!ttsCurrentTask.value) {
    return;
  }
  const currentText = ttsCurrentTask.value.text || "";
  ttsParamsChanged.value = ttsText.value !== currentText;
  if (ttsParamsChanged.value) {
    handleTtsSaveParams();
  }
};

// 音色变化处理（单独处理，避免空字符串警告）
const handleTtsRoleChange = (value: string | null) => {
  ttsRole.value = value;
  handleTtsParamsChange();
};

// 参数变化处理
const handleTtsParamsChange = () => {
  if (!ttsCurrentTask.value) {
    return;
  }
  const currentRole = ttsCurrentTask.value.role || null;
  const currentModel = ttsCurrentTask.value.model || null;
  const currentSpeed = ttsCurrentTask.value.speed ?? DEFAULT_SPEED;
  const currentVol = ttsCurrentTask.value.vol ?? DEFAULT_VOL;
  ttsParamsChanged.value =
    ttsRole.value !== currentRole ||
    ttsModel.value !== currentModel ||
    ttsSpeed.value !== currentSpeed ||
    ttsVol.value !== currentVol;
  if (ttsParamsChanged.value) {
    handleTtsSaveParams();
  }
};

// 保存参数
const handleTtsSaveParams = async () => {
  if (!ttsCurrentTask.value || !ttsParamsChanged.value) {
    return;
  }

  try {
    ttsLoading.value = true;
    // 构建更新参数，只包含变化的字段
    const updateParams: {
      text?: string;
      role?: string;
      model?: string;
      speed?: number;
      vol?: number;
    } = {};

    // 检查文本是否有变化
    const currentText = ttsCurrentTask.value.text || "";
    if (ttsText.value !== currentText) {
      updateParams.text = ttsText.value;
    }

    // 检查角色是否有变化
    const currentRole = ttsCurrentTask.value.role || null;
    if (ttsRole.value !== currentRole) {
      updateParams.role = ttsRole.value || undefined;
    }

    // 检查模型是否有变化
    const currentModel = ttsCurrentTask.value.model || null;
    if (ttsModel.value !== currentModel) {
      updateParams.model = ttsModel.value || undefined;
    }

    // 检查语速是否有变化
    const currentSpeed = ttsCurrentTask.value.speed ?? DEFAULT_SPEED;
    if (ttsSpeed.value !== currentSpeed) {
      updateParams.speed = ttsSpeed.value;
    }

    // 检查音量是否有变化
    const currentVol = ttsCurrentTask.value.vol ?? DEFAULT_VOL;
    if (ttsVol.value !== currentVol) {
      updateParams.vol = ttsVol.value;
    }

    const response = await updateTtsTask(ttsCurrentTask.value.task_id, updateParams);

    if (response.code === 0) {
      ttsParamsChanged.value = false;
      await handleTtsViewTask(ttsCurrentTask.value.task_id);
    } else {
      ElMessage.error(response.msg || "保存参数失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "保存参数失败");
  } finally {
    ttsLoading.value = false;
  }
};

// 开始 TTS 任务
const handleTtsStart = async () => {
  if (!ttsCurrentTask.value) {
    return;
  }

  if (!ttsText.value.trim()) {
    ElMessage.warning("请输入文本内容");
    return;
  }

  // 如果有未保存的参数，先保存
  if (ttsParamsChanged.value) {
    await handleTtsSaveParams();
  }

  const confirmed = await ElMessageBox.confirm(
    `确定要开始生成任务 "${ttsCurrentTask.value.name}" 吗？`,
    "确认生成",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    }
  ).catch(() => false);

  if (!confirmed) return;

  try {
    ttsLoading.value = true;
    const response = await startTtsTask(ttsCurrentTask.value.task_id);
    if (response.code === 0) {
      ElMessage.success("TTS 任务已启动");
      // 刷新任务列表和当前任务状态
      await loadTtsTaskList();
      await handleTtsViewTask(ttsCurrentTask.value.task_id);
      // handleTtsViewTask 中已经会自动开始轮询，这里不需要再次调用
    } else {
      ElMessage.error(response.msg || "启动任务失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "启动任务失败");
  } finally {
    ttsLoading.value = false;
  }
};

// 停止 TTS 任务
const handleTtsStop = async () => {
  if (!ttsCurrentTask.value) {
    return;
  }

  const confirmed = await ElMessageBox.confirm("确定要停止生成吗？", "确认停止", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  }).catch(() => false);

  if (!confirmed) return;

  try {
    ttsLoading.value = true;
    const response = await stopTtsTask(ttsCurrentTask.value.task_id);
    if (response.code === 0) {
      ElMessage.success("任务已停止");
      await loadTtsTaskList();
      await handleTtsViewTask(ttsCurrentTask.value.task_id);
    } else {
      ElMessage.error(response.msg || "停止任务失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "停止任务失败");
  } finally {
    ttsLoading.value = false;
  }
};

// 更新任务详情（不改变当前选中的任务）
const updateTaskDetail = async (taskId: string) => {
  try {
    const response = await getTtsTask(taskId);
    if (response.code === 0) {
      const taskData = response.data;
      updateTaskInList(taskData);

      // 如果这是当前选中的任务，也更新当前任务详情
      if (ttsCurrentTask.value && ttsCurrentTask.value.task_id === taskId) {
        ttsCurrentTask.value = taskData;
        updateTaskParamsFromData(taskData);
      }
    }
  } catch (error) {
    // 静默失败，不影响轮询
    console.error(`[TTS] 更新任务详情失败: ${taskId}`, error);
  }
};

// 任务是否“忙”（TTS 生成中或 OCR/分析子任务运行中）
function isTaskBusyInList(t: TTSTask): boolean {
  return t.status === "processing" || !!t.ocr_running || !!t.analysis_running;
}

// 记录上一次轮询时的“忙”任务 ID 集合
const previousBusyTaskIds = ref<Set<string>>(new Set());

// 轮询 TTS 任务状态（含 OCR/分析子任务：子任务不再改主状态，通过 ocr_running/analysis_running 判断）
const { start: startTtsPolling, stop: stopTtsPolling } = useControllableInterval(
  async () => {
    await loadTtsTaskList();

    const busyTasks = ttsTaskList.value.filter(isTaskBusyInList);
    const currentBusyTaskIds = new Set(busyTasks.map(t => t.task_id));

    // 刚结束“忙”的任务：刷新详情（如 OCR/分析完成后更新文本或 analysis）
    const completedTaskIds = Array.from(previousBusyTaskIds.value).filter(
      taskId => !currentBusyTaskIds.has(taskId)
    );
    for (const taskId of completedTaskIds) {
      await updateTaskDetail(taskId);
    }

    previousBusyTaskIds.value = currentBusyTaskIds;

    if (busyTasks.length === 0) {
      stopTtsPolling();
      previousBusyTaskIds.value.clear();
      return;
    }

    for (const task of busyTasks) {
      await updateTaskDetail(task.task_id);
    }
  },
  MEDIA_TASK_POLLING_INTERVAL,
  { immediate: false }
);

const startTtsPollingTaskStatus = () => {
  const busyTasks = ttsTaskList.value.filter(isTaskBusyInList);
  previousBusyTaskIds.value = new Set(busyTasks.map(t => t.task_id));
  startTtsPolling();
};

// 下载 TTS 结果
const handleTtsDownload = async () => {
  if (!ttsCurrentTask.value?.output_file) return;

  try {
    const url = getTtsTaskDownloadUrl(ttsCurrentTask.value.task_id);
    const response = await fetch(url);

    if (!response.ok) {
      ElMessage.error("下载失败");
      return;
    }

    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);

    // 获取文件扩展名
    const outputFile = ttsCurrentTask.value.output_file;
    const fileExtension = outputFile.includes(".") ? "." + outputFile.split(".").pop() : "";

    // 构建文件名：任务名字 + 原扩展名
    const taskName = ttsCurrentTask.value.name || "tts_output";
    const fileName = `${taskName}${fileExtension}`;

    // 创建下载链接
    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // 清理 blob URL
    URL.revokeObjectURL(blobUrl);
  } catch (error) {
    logAndNoticeError(error as Error, "下载失败");
  }
};

// 从任务列表下载 TTS 结果
const handleTtsDownloadFromList = async (task: TTSTask) => {
  if (!task?.output_file) return;

  try {
    const url = getTtsTaskDownloadUrl(task.task_id);
    const response = await fetch(url);

    if (!response.ok) {
      ElMessage.error("下载失败");
      return;
    }

    const blob = await response.blob();
    const blobUrl = URL.createObjectURL(blob);

    // 获取文件扩展名
    const outputFile = task.output_file;
    const fileExtension = outputFile.includes(".") ? "." + outputFile.split(".").pop() : "";

    // 构建文件名：任务名字 + 原扩展名
    const taskName = task.name || "tts_output";
    const fileName = `${taskName}${fileExtension}`;

    // 创建下载链接
    const link = document.createElement("a");
    link.href = blobUrl;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // 清理 blob URL
    URL.revokeObjectURL(blobUrl);
  } catch (error) {
    logAndNoticeError(error as Error, "下载失败");
  }
};

// 清理浏览器音频播放器状态
const clearBrowserAudioPlayer = () => {
  ttsPlayer.clear();
};

// 停止 TTS 播放
const handleTtsStopPlay = () => {
  clearBrowserAudioPlayer();
};

// 播放/暂停 TTS 结果文件
const handleTtsTogglePlayResult = () => {
  if (!ttsCurrentTask.value || !ttsCurrentTask.value.output_file) {
    ElMessage.warning("结果文件不存在");
    return;
  }

  const resultFilePath = ttsCurrentTask.value.output_file;

  // 如果点击的是正在播放的结果文件，则停止播放
  if (
    ttsPlayer.playingFilePath.value === resultFilePath &&
    ttsPlayer.audio &&
    !ttsPlayer.audio.paused
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
  ttsPlayer.load(audioUrl, {
    playingFilePath: resultFilePath,
  });

  // 开始播放
  ttsPlayer.play().catch(error => {
    logAndNoticeError(error as Error, "播放失败");
    clearBrowserAudioPlayer();
  });
};

// 处理结果文件进度条拖拽
const handleResultFileSeek = (_file: MediaFile, percentage: number) => {
  if (!ttsCurrentTask.value?.output_file) return;
  handleSeekFile({ path: ttsCurrentTask.value.output_file }, percentage);
};

const handleSeekFile = (fileItem: MediaFile, percentage: number) => {
  if (!fileItem) return;
  const filePath = fileItem?.path || fileItem?.name || "";
  ttsPlayer.seekFile(filePath, percentage);
};

// TTS 状态映射
const TTS_STATUS_MAP: Record<string, { tag: string; text: string }> = {
  pending: { tag: "info", text: "等待中" },
  processing: { tag: "warning", text: "处理中" },
  success: { tag: "success", text: "成功" },
  failed: { tag: "danger", text: "失败" },
};

// 获取 TTS 状态标签类型
const getTtsStatusTagType = (status: string): string => {
  return TTS_STATUS_MAP[status]?.tag || "info";
};

// 获取 TTS 状态文本
const getTtsStatusText = (status: string): string => {
  return TTS_STATUS_MAP[status]?.text || "未知";
};

// OCR 相关方法
// 清空选择的图片
const clearSelectedImages = () => {
  // 释放所有预览 URL，避免内存泄漏
  imagePreviewUrls.value.forEach(url => {
    URL.revokeObjectURL(url);
  });
  imagePreviewUrls.value.clear();
  // 清空选择的图片
  selectedImages.value = [];
  // 清空 input 的值，以便可以重新选择相同的文件
  if (imageInputRef.value) {
    imageInputRef.value.value = "";
  }
  // 关闭预览对话框
  if (imagePreviewVisible.value) {
    imagePreviewVisible.value = false;
    previewImageIndex.value = -1;
  }
};

// 选择图片
const handleSelectImages = () => {
  imageInputRef.value?.click();
};

// 处理图片选择
const handleImageSelect = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const files = target.files;
  if (files && files.length > 0) {
    const newFiles = Array.from(files);
    // 为每个新文件创建预览 URL
    newFiles.forEach((file, index) => {
      const actualIndex = selectedImages.value.length + index;
      const url = URL.createObjectURL(file);
      imagePreviewUrls.value.set(actualIndex, url);
    });
    // 追加到现有图片列表
    selectedImages.value.push(...newFiles);
  }
};

// 获取图片预览 URL
const getImagePreviewUrl = (index: number): string => {
  if (imagePreviewUrls.value.has(index)) {
    return imagePreviewUrls.value.get(index)!;
  }
  // 如果找不到，创建新的 URL
  if (index >= 0 && index < selectedImages.value.length) {
    const url = URL.createObjectURL(selectedImages.value[index]);
    imagePreviewUrls.value.set(index, url);
    return url;
  }
  return "";
};

// 移除图片
const removeImage = (index: number) => {
  if (index < 0 || index >= selectedImages.value.length) return;

  // 释放 URL 对象，避免内存泄漏
  if (imagePreviewUrls.value.has(index)) {
    URL.revokeObjectURL(imagePreviewUrls.value.get(index)!);
    imagePreviewUrls.value.delete(index);
  }

  // 如果删除的是预览中的图片，关闭预览
  if (previewImageIndex.value === index) {
    imagePreviewVisible.value = false;
    previewImageIndex.value = -1;
  } else if (previewImageIndex.value > index) {
    // 如果删除的是预览图片之前的图片，调整预览索引
    previewImageIndex.value--;
  }

  // 重新映射 URL（因为索引会变化）
  const newUrls = new Map<number, string>();
  selectedImages.value.forEach((_file, i) => {
    if (i !== index) {
      const oldIndex = i > index ? i : i;
      if (imagePreviewUrls.value.has(oldIndex)) {
        newUrls.set(i > index ? i - 1 : i, imagePreviewUrls.value.get(oldIndex)!);
      }
    }
  });
  imagePreviewUrls.value = newUrls;

  selectedImages.value.splice(index, 1);
  // 清空 input 的值，以便可以重新选择相同的文件
  if (imageInputRef.value) {
    imageInputRef.value.value = "";
  }
};

// 预览图片
const handleImagePreview = (index: number) => {
  previewImageIndex.value = index;
  imagePreviewVisible.value = true;
};

// 预览上一张图片
const previewPreviousImage = () => {
  if (previewImageIndex.value > 0) {
    previewImageIndex.value--;
  }
};

// 预览下一张图片
const previewNextImage = () => {
  if (previewImageIndex.value < selectedImages.value.length - 1) {
    previewImageIndex.value++;
  }
};

// 预览图片名称
const previewImageName = computed(() => {
  if (previewImageIndex.value >= 0 && selectedImages.value[previewImageIndex.value]) {
    return selectedImages.value[previewImageIndex.value].name;
  }
  return "图片预览";
});

// OCR 识别
const handleOcrRecognize = async () => {
  if (selectedImages.value.length === 0) {
    ElMessage.warning("请先选择图片");
    return;
  }

  // 检查是否有当前任务
  if (!ttsCurrentTask.value) {
    ElMessage.warning("请先创建或选择一个 TTS 任务");
    return;
  }

  if (isTaskBusy.value) {
    ElMessage.warning("任务正在处理中或正在执行分析，无法执行 OCR");
    return;
  }

  try {
    ocrLoading.value = true;
    const response = await ocrTtsTask(ttsCurrentTask.value.task_id, selectedImages.value);

    if (response.code === 0) {
      ElMessage.success("OCR 任务已启动，正在后台处理");
      // 清空选择的图片
      clearSelectedImages();

      // 刷新任务信息以获取更新后的文本（OCR 完成后会自动追加）
      await handleTtsViewTask(ttsCurrentTask.value.task_id);
      // 开始轮询任务状态，等待 OCR 完成（轮询会检查所有processing状态的任务）
      startTtsPolling();
    } else {
      ElMessage.error(response.msg || "OCR 识别失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "OCR 识别失败");
  } finally {
    ocrLoading.value = false;
  }
};

// 文本分析（调用 tts/analysis）
const handleTtsAnalysis = async () => {
  if (!ttsCurrentTask.value) {
    ElMessage.warning("请先创建或选择一个 TTS 任务");
    return;
  }

  if (!ttsText.value.trim()) {
    ElMessage.warning("请输入要分析的文本内容");
    return;
  }

  if (isTaskBusy.value) {
    ElMessage.warning("当前任务正在处理中或正在执行 OCR，请稍后再试");
    return;
  }

  const confirmed = await ElMessageBox.confirm(
    `确定要分析当前任务 "${ttsCurrentTask.value.name}" 的文本吗？`,
    "确认分析",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "warning",
    }
  ).catch(() => false);

  if (!confirmed) return;

  try {
    analysisLoading.value = true;
    const response = await analyzeTtsTask(ttsCurrentTask.value.task_id);

    if (response.code === 0) {
      ElMessage.success("分析任务已启动，正在后台处理");
      // 刷新当前任务信息，并启动轮询，等待分析完成
      await handleTtsViewTask(ttsCurrentTask.value.task_id);
      startTtsPollingTaskStatus();
    } else {
      ElMessage.error(response.msg || "分析任务启动失败");
    }
  } catch (error) {
    logAndNoticeError(error as Error, "分析任务启动失败");
  } finally {
    analysisLoading.value = false;
  }
};

// 计算属性
const isTaskProcessing = computed(() => ttsCurrentTask.value?.status === "processing");
/** 当前任务是否正在执行 OCR 或分析子任务（不改变主状态，但锁定更新/启动/删除） */
const isSubtaskRunning = computed(
  () => !!(ttsCurrentTask.value?.ocr_running || ttsCurrentTask.value?.analysis_running)
);
/** 当前任务是否“忙”：TTS 生成中或 OCR/分析子任务运行中，此时禁止更新、启动、删除等 */
const isTaskBusy = computed(() => isTaskProcessing.value || isSubtaskRunning.value);
/** 列表项任务是否忙（用于禁用删除等） */
function isTaskBusyForTask(task: TTSTask): boolean {
  return task.status === "processing" || !!task.ocr_running || !!task.analysis_running;
}
const isStartDisabled = computed(
  () => !ttsText.value.trim() || isTaskProcessing.value || isSubtaskRunning.value
);
const isResultActionDisabled = computed(() => !ttsCurrentTask.value?.output_file);

// 结果文件对象
const resultFile = computed(() => {
  if (!ttsCurrentTask.value?.output_file) return null;
  return {
    path: ttsCurrentTask.value.output_file,
    name: ttsCurrentTask.value.output_file.split("/").pop() || "output.mp3",
  };
});

const resultFileObject = computed(() => {
  if (!resultFile.value) return null;
  return {
    path: resultFile.value.path,
    name: resultFile.value.name,
    duration: ttsCurrentTask.value?.duration || null,
  };
});

onMounted(() => {
  loadTtsTaskList();
});

onUnmounted(() => {
  stopTtsPolling();
  clearBrowserAudioPlayer();
  // 清理所有图片预览 URL，避免内存泄漏
  imagePreviewUrls.value.forEach(url => {
    URL.revokeObjectURL(url);
  });
  imagePreviewUrls.value.clear();
});
</script>
