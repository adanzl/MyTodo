<template>
  <el-dialog
    v-model="visible"
    title="素材详情"
    align-center
    width="1200px"
    destroy-on-close
    @close="handleClose"
  >
    <div v-loading="pdfLoading" element-loading-text="加载中..." class="min-h-170 h-[80vh] flex flex-col gap-3">
      <!-- 基本信息 -->
      <div class="">
        <el-descriptions :column="4" border>
          <el-descriptions-item label="名称">{{ materialData?.name }}</el-descriptions-item>
          <el-descriptions-item label="类型">
            <el-tag :type="materialData?.type === 0 ? 'success' : 'warning'" size="small">
              {{ materialData?.type === 0 ? 'PDF' : 'Video' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="路径">{{ materialData?.path }}</el-descriptions-item>
          <el-descriptions-item label="操作">
            <el-button type="primary" size="small" plain @click="playMaterial">
              <el-icon :size="16" ><Reading /></el-icon>
            </el-button>
            <el-button type="primary" size="small" plain @click="gotoEditMaterial">
              <el-icon :size="16"><Edit /></el-icon>
            </el-button>
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- 三栏布局 -->
      <div class="flex flex-1 gap-4 overflow-hidden">
        <!-- 左侧：图片列表 + 备注 -->
        <div class="w-50 border border-gray-200 rounded flex flex-col shrink-0" :class="{ 'opacity-50 pointer-events-none': isDeleteMode }">
          <div class="flex items-center px-4 py-3 bg-gray-50 border-b border-gray-200 font-bold">
            <span>页面列表 ({{ pdfPages.length }})</span>
          </div>
          <div class="flex-1 overflow-y-auto p-3">
            <div
              v-for="(page, index) in pdfPages"
              :key="page.id"
              class="flex items-center p-2 mb-2 border rounded cursor-pointer transition-all hover:border-blue-500 hover:shadow"
              :class="{ 'border-blue-500 bg-blue-50': selectedPageIndex === index }"
              @click="selectPage(index)"
            >
              <div class="flex items-center gap-2 flex-1">
                <div class="w-6 h-6 flex items-center justify-center bg-blue-500 text-white rounded-full text-xs font-bold shrink-0">
                  {{ index + 1 }}
                </div>
                <div class="w-16 h-12 shrink-0">
                  <el-image
                    :src="page.thumbnail"
                    fit="cover"
                    class="w-full h-full rounded bg-gray-100"
                  >
                    <template #error>
                      <div class="w-full h-full flex items-center justify-center bg-gray-100 text-lg text-gray-400">
                        <el-icon><Picture /></el-icon>
                      </div>
                    </template>
                  </el-image>
                </div>
              </div>
            </div>
            <el-empty v-if="pdfPages.length === 0" description="暂无图片" />
          </div>
          <!-- 备注信息 -->
          <div class="border-t border-gray-200 p-3">
            <h4 class="text-xs font-semibold mb-2 text-gray-700">备注</h4>
            <el-input
              v-model="coursewareForm.remark"
              type="textarea"
              :rows="4"
              placeholder="请输入备注"
              class="text-xs"
            />
          </div>
        </div>

        <!-- 中间：页面预览 -->
        <div class="flex-1 border border-gray-200 rounded flex flex-col" :class="{ 'opacity-50 pointer-events-none': isDeleteMode }">
          <div class="flex items-center px-4 py-3 bg-gray-50 border-b border-gray-200 font-bold">
            <span>页面预览</span>
            <span v-if="selectedPageIndex !== null" class="ml-2 text-sm font-normal text-gray-600">
              - 第 {{ selectedPageIndex + 1 }} 页
            </span>
          </div>
          <div class="flex-1 overflow-y-auto p-4 flex items-center justify-center bg-gray-100">
            <div v-if="selectedPageIndex !== null && pdfPages[selectedPageIndex]" class="max-w-full max-h-full">
              <el-image
                :src="pdfPages[selectedPageIndex].thumbnail"
                fit="contain"
                class="max-w-full max-h-[calc(80vh-150px)] shadow-lg"
              >
                <template #error>
                  <div class="w-150 h-150 flex items-center justify-center bg-white text-8xl text-gray-400">
                    <el-icon><Picture /></el-icon>
                  </div>
                </template>
              </el-image>
            </div>
            <el-empty v-else description="请选择一个页面" />
          </div>
        </div>

        <!-- 右侧：音频列表 -->
        <div class="w-80 border border-gray-200 rounded flex flex-col shrink-0">
          <div class="flex items-center justify-between px-4 py-3 bg-gray-50 border-b border-gray-200 font-bold">
            <span>音频列表 ({{ allAudios.length }})</span>
            <div class="flex gap-2">
              <el-button
                size="small"
                :type="isDeleteMode ? 'warning' : ''"
                @click="toggleDeleteMode"
              >
                {{ isDeleteMode ? '退出删除' : '删除模式' }}
              </el-button>
              <el-button
                size="small"
                @click="handleDeleteSelectedAudios"
                :disabled="!isDeleteMode || selectedAudioIds.length === 0"
                type="danger"
                :icon="Delete"
              />
              <el-button
                size="small"
                type="primary"
                @click="openAudioFileDialog"
                :icon="Plus"
                :disabled="isDeleteMode"
              />
            </div>
          </div>
          <div class="flex-1 overflow-y-auto p-3">
            <!-- 已绑定的音频（排在前面） -->
            <div
              v-for="(audio, index) in boundAudios"
              :key="audio.id"
              class="flex items-center p-3 mb-2 border border-blue-300 rounded bg-blue-50"
            >
              <div class="flex items-center gap-2 flex-1">
                <el-checkbox
                  :model-value="selectedAudioIds.includes(audio.id)"
                  @change="handleCheckboxChange(audio.id, $event)"
                />
                <el-icon><Headset /></el-icon>
                <span class="text-sm text-gray-800">{{ audio.name }}</span>
                <span class="text-xs text-gray-500">{{ audio.duration }}</span>
              </div>
              <div class="flex items-center gap-1">
                <el-button
                  link
                  type="primary"
                  size="small"
                  @click="moveAudioUp(index)"
                  :disabled="index === 0 || isDeleteMode"
                >
                  <el-icon :size="16"><ArrowUp /></el-icon>
                </el-button>
                <el-button
                  link
                  type="primary"
                  size="small"
                  @click="moveAudioDown(index)"
                  :disabled="index === boundAudios.length - 1 || isDeleteMode"
                >
                  <el-icon :size="16"><ArrowDown /></el-icon>
                </el-button>
                <el-button link type="primary" size="small" @click="playAudio(audio)" :disabled="isDeleteMode">
                  <el-icon :size="16"><VideoPlay /></el-icon>
                </el-button>
              </div>
            </div>
            <!-- 未绑定的音频（排在后面） -->
            <div
              v-for="audio in unboundAudios"
              :key="audio.id"
              class="flex items-center p-3 mb-2 border border-gray-200 rounded bg-white"
            >
              <div class="flex items-center gap-2 flex-1">
                <el-checkbox
                  :model-value="selectedAudioIds.includes(audio.id)"
                  @change="handleCheckboxChange(audio.id, $event)"
                />
                <el-icon><Headset /></el-icon>
                <span class="text-sm text-gray-800">{{ audio.name }}</span>
                <span class="text-xs text-gray-500">{{ audio.duration }}</span>
              </div>
              <div class="w-15 flex items-center justify-end">
                <el-button link type="primary" size="small" @click="playAudio(audio)" :disabled="isDeleteMode">
                  <el-icon :size="16"><VideoPlay /></el-icon>
                </el-button>
              </div>
            </div>
            <el-empty v-if="allAudios.length === 0" description="暂无音频" />
          </div>
          <!-- 底部按钮 -->
          <div class="border-t border-gray-200 p-3">
            <el-button
              size="small"
              type="warning"
              class="w-full"
              @click="handleUpdatePageBinding"
              :disabled="isDeleteMode || selectedPageIndex === null"
            >
              更新页面绑定
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 音频文件选择对话框 -->
    <FileDialog
      v-model:visible="audioFileDialogVisible"
      title="选择音频文件"
      extensions=".mp3,.wav,.m4a,.flac,.aac"
      mode="file"
      :multiple="true"
      @confirm="handleAudioFileConfirm"
    />
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed, nextTick } from "vue";
import { ElLoading, ElMessage } from "element-plus";
import { useRouter } from "vue-router";
import { Picture, Headset, VideoPlay, Edit, Delete, Plus, ArrowUp, ArrowDown, Reading } from "@element-plus/icons-vue";
import type { Material } from "@/api/api-task";
import { updateMaterial } from "@/api/api-task";
import { getAudioDuration } from "@/api/api-common";
import type { AudioFile, TaskDetail } from "@/types/tasks/taskDetail";
import * as pdfjsLib from "pdfjs-dist";
import { getMediaFileUrl } from "@/utils/file";
import { formatDuration } from "@/utils/format";
import { useAudioPlayer } from "@/composables/useAudioPlayer";
import FileDialog from "@/views/dialogs/FileDialog.vue";

// 设置 PDF.js worker - 使用本地 worker
import pdfWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url";
pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorker;

interface Props {
  modelValue: boolean;
  materialData?: Partial<Material> | null;
}

interface Emits {
  (e: "update:modelValue", value: boolean): void;
  (e: "edit", material: Material): void;
}

const props = withDefaults(defineProps<Props>(), {
  materialData: null,
});

const emit = defineEmits<Emits>();

const router = useRouter();
const visible = ref(false);

// 课件表单
const coursewareForm = ref({
  name: "",
  remark: "",
});

// PDF页面列表
interface PdfPage {
  id: string;
  name: string;
  thumbnail: string;
}

const pdfPages = ref<PdfPage[]>([]);
const allAudios = ref<AudioFile[]>([]);
const pdfLoading = ref(false);
const audioFileDialogVisible = ref(false);
const selectedAudioIds = ref<string[]>([]);
const selectedPageIndex = ref<number | null>(null);
const isDeleteMode = ref(false);

// 音频播放器
const audioPlayer = useAudioPlayer({
  callbacks: {
    onPlay: () => {
      ElMessage.success("开始播放");
    },
    onError: () => {
      ElMessage.error("播放失败");
    },
    onEnded: () => {
      // 播放结束
    },
  },
});

// 当前页面绑定的音频ID列表
const currentPageAudioIds = computed(() => {
  if (selectedPageIndex.value === null || !taskDetailData.value?.pages) {
    return [];
  }
  const page = taskDetailData.value.pages[selectedPageIndex.value];
  return page?.audioIds || [];
});

// 已绑定的音频（按 pages 中的顺序）
const boundAudios = computed(() => {
  const ids = currentPageAudioIds.value;
  return ids.map(id => allAudios.value.find(a => a.id === id)).filter(Boolean) as AudioFile[];
});

// 未绑定的音频
const unboundAudios = computed(() => {
  const boundIds = new Set(currentPageAudioIds.value);
  return allAudios.value.filter(audio => !boundIds.has(audio.id));
});

// TaskDetail 数据
const taskDetailData = ref<TaskDetail | null>(null);

// 监听 modelValue 变化
watch(
  () => props.modelValue,
  (val) => {
    visible.value = val;
    if (val && props.materialData) {
      initDetail();
    }
  }
);

// 监听 selectedAudioIds 变化，自动绑定/解绑音频到当前页面
let previousSelectedIds = new Set<string>();
let isInitializing = false; // 标记是否正在初始化
watch(
  selectedAudioIds,
  (newIds) => {
    // 如果删除模式开启或正在初始化，不处理绑定逻辑
    if (isDeleteMode.value || isInitializing || selectedPageIndex.value === null || !taskDetailData.value) {
      previousSelectedIds = new Set(newIds);
      return;
    }

    const page = taskDetailData.value.pages[selectedPageIndex.value];
    if (!page) {
      previousSelectedIds = new Set(newIds);
      return;
    }

    const newSet = new Set(newIds);
    const oldSet = previousSelectedIds;

    // 找出新增的 ID（需要绑定）
    const addedIds = newIds.filter(id => !oldSet.has(id));
    // 找出移除的 ID（需要解绑）
    const removedIds = Array.from(oldSet).filter(id => !newSet.has(id));

    let hasChanges = false;

    // 处理新增绑定
    if (addedIds.length > 0) {
      addedIds.forEach(id => {
        if (!page.audioIds.includes(id)) {
          page.audioIds.push(id);
          hasChanges = true;
        }
      });
    }

    // 处理解绑
    if (removedIds.length > 0) {
      removedIds.forEach(id => {
        const index = page.audioIds.indexOf(id);
        if (index !== -1) {
          page.audioIds.splice(index, 1);
          hasChanges = true;
        }
      });
    }

    // 如果有变化，保存到后端
    if (hasChanges) {
      saveMaterial();
    }

    // 更新之前的选中状态
    previousSelectedIds = newSet;
  },
  { deep: true }
);

// 监听 visible 变化
watch(visible, (val) => {
  emit("update:modelValue", val);
});

// 加载 PDF 并生成缩略图
const loadPdfPages = async (pdfPath: string) => {
  pdfLoading.value = true;
  try {
    // 转换文件路径为 URL
    const pdfUrl = getMediaFileUrl(pdfPath);

    if (!pdfUrl) {
      console.error("无法生成 PDF URL:", pdfPath);
      pdfPages.value = [];
      return;
    }

    const loadingTask = pdfjsLib.getDocument({
      url: pdfUrl,
      cMapUrl: "//cdnjs.cloudflare.com/ajax/libs/pdf.js/" + pdfjsLib.version + "/cmaps/",
      cMapPacked: true,
    });

    const pdf = await loadingTask.promise;
    console.log("PDF 加载成功，页数:", pdf.numPages);

    const pages: PdfPage[] = [];

    // 遍历所有页面生成缩略图
    for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
      const page = await pdf.getPage(pageNum);

      // 设置缩放比例生成缩略图（增大到 1.0）
      const viewport = page.getViewport({ scale: 1.0 });
      const canvas = document.createElement("canvas");
      const context = canvas.getContext("2d");

      if (context) {
        canvas.height = viewport.height;
        canvas.width = viewport.width;

        await page.render({
          canvasContext: context,
          viewport: viewport,
          canvas: canvas as any,
        }).promise;

        // 转换为 base64
        const thumbnail = canvas.toDataURL("image/jpeg", 0.9);

        pages.push({
          id: String(pageNum),
          name: `第${pageNum}页`,
          thumbnail: thumbnail,
        });
      }
    }

    pdfPages.value = pages;

    // 更新 taskDetail 的 pdfLength
    if (taskDetailData.value) {
      taskDetailData.value.pdfLength = pages.length;
    }

    // 默认选中第一页
    if (pages.length > 0 && selectedPageIndex.value === null) {
      selectPage(0);
    }
  } catch (error) {
    console.error("加载 PDF 失败:", error);
    pdfPages.value = [];
  } finally {
    pdfLoading.value = false;
  }
};

// 初始化详情
const initDetail = async () => {
  if (!props.materialData) return;

  coursewareForm.value.name = props.materialData.name || "";

  // 解析 data 字段
  let taskDetail: TaskDetail | null = null;
  if (typeof props.materialData.data === 'string') {
    try {
      taskDetail = JSON.parse(props.materialData.data);
    } catch (e) {
      console.error('解析 data 失败:', e);
    }
  } else {
    taskDetail = props.materialData.data || null;
  }

  coursewareForm.value.remark = taskDetail?.remark || "";

  // 保存 taskDetail 数据
  taskDetailData.value = taskDetail;

  // 根据素材类型加载不同的数据
  if (props.materialData.type === 0 && props.materialData.path) {
    // PDF 类型 - 使用 pdf.js 加载
    await loadPdfPages(props.materialData.path);
    // 从 data 中加载音频列表
    allAudios.value = taskDetail?.audioList || [];

    // 确保 pages 数组存在且长度足够
    if (taskDetail) {
      if (!taskDetail.pages) {
        taskDetail.pages = [];
      }
      // 扩展 pages 数组以匹配 PDF 页数
      while (taskDetail.pages.length < pdfPages.value.length) {
        taskDetail.pages.push({ audioIds: [] });
      }
      // 更新 pdfLength
      taskDetail.pdfLength = pdfPages.value.length;
    }
  } else {
    // Video 类型 - 清空数据
    pdfPages.value = [];
    allAudios.value = [];
  }

  // 重置选中状态和删除模式
  isInitializing = true;
  selectedAudioIds.value = [];
  isDeleteMode.value = false;
  previousSelectedIds = new Set<string>();
  setTimeout(() => {
    isInitializing = false;
  }, 0);
};

// 处理 checkbox 变化
const handleCheckboxChange = (audioId: string, checked: boolean) => {
  if (checked) {
    // 勾选：添加到选中列表
    if (!selectedAudioIds.value.includes(audioId)) {
      selectedAudioIds.value.push(audioId);
    }
  } else {
    // 取消勾选：从选中列表移除
    const index = selectedAudioIds.value.indexOf(audioId);
    if (index !== -1) {
      selectedAudioIds.value.splice(index, 1);
    }
  }
};

// 选择页面
const selectPage = async (index: number) => {
  if (isDeleteMode.value) return; // 删除模式下禁用

  // 标记为初始化状态，避免触发 watch 中的保存逻辑
  isInitializing = true;
  selectedPageIndex.value = index;

  // 更新选中的音频ID列表为当前页面绑定的音频
  if (taskDetailData.value && taskDetailData.value.pages[index]) {
    const newIds = [...taskDetailData.value.pages[index].audioIds];
    // 先清空再赋值，确保响应式更新
    selectedAudioIds.value = [];
    await nextTick();
    selectedAudioIds.value = newIds;
    previousSelectedIds = new Set(selectedAudioIds.value);
  } else {
    selectedAudioIds.value = [];
    previousSelectedIds = new Set();
  }

  // 延迟取消初始化标记，确保 watch 不会触发
  setTimeout(() => {
    isInitializing = false;
  }, 0);
};

// 切换删除模式
const toggleDeleteMode = async () => {
  isDeleteMode.value = !isDeleteMode.value;
  // 进入删除模式时，清空所有选中
  if (isDeleteMode.value) {
    isInitializing = true;
    selectedAudioIds.value = [];
    previousSelectedIds = new Set<string>();
    setTimeout(() => {
      isInitializing = false;
    }, 0);
  } else {
    // 退出删除模式时，恢复当前页面绑定的音频选中状态
    isInitializing = true;
    if (selectedPageIndex.value !== null && taskDetailData.value && taskDetailData.value.pages[selectedPageIndex.value]) {
      const newIds = [...taskDetailData.value.pages[selectedPageIndex.value].audioIds];
      // 先清空再赋值，确保响应式更新
      selectedAudioIds.value = [];
      await nextTick();
      selectedAudioIds.value = newIds;
      previousSelectedIds = new Set(selectedAudioIds.value);
    } else {
      selectedAudioIds.value = [];
      previousSelectedIds = new Set();
    }
    setTimeout(() => {
      isInitializing = false;
    }, 0);
  }
};

// 向上移动音频
const moveAudioUp = (index: number) => {
  if (!taskDetailData.value || selectedPageIndex.value === null) return;

  const page = taskDetailData.value.pages[selectedPageIndex.value];
  if (!page) return;

  // 交换位置
  [page.audioIds[index], page.audioIds[index - 1]] = [page.audioIds[index - 1], page.audioIds[index]];

  // 保存
  saveMaterial();
};

// 向下移动音频
const moveAudioDown = (index: number) => {
  if (!taskDetailData.value || selectedPageIndex.value === null) return;

  const page = taskDetailData.value.pages[selectedPageIndex.value];
  if (!page) return;

  // 交换位置
  [page.audioIds[index], page.audioIds[index + 1]] = [page.audioIds[index + 1], page.audioIds[index]];

  // 保存
  saveMaterial();
};

// 更新页面绑定
const handleUpdatePageBinding = async () => {
  if (selectedPageIndex.value === null || !taskDetailData.value) return;

  try {
    // 保存当前的绑定关系到后端
    await saveMaterial();
    ElMessage.success('页面绑定已更新');
  } catch (error: any) {
    console.error('更新页面绑定失败:', error);
    ElMessage.error(error.message || '更新失败');
  }
};

// 播放音频
const playAudio = (audio: AudioFile) => {
  if (!audio.path) {
    ElMessage.warning("音频文件路径无效");
    return;
  }

  const mediaUrl = getMediaFileUrl(audio.path);
  if (!mediaUrl) {
    ElMessage.error("无法生成音频URL");
    return;
  }

  // 如果点击的是正在播放的音频，则停止
  if (audioPlayer.playingFilePath.value === audio.path && audioPlayer.audio && !audioPlayer.audio.paused) {
    audioPlayer.clear();
    ElMessage.info("已停止播放");
    return;
  }

  // 加载并播放
  audioPlayer.load(mediaUrl, {
    playingFilePath: audio.path,
  });

  audioPlayer.play().catch((error) => {
    console.error("播放失败:", error);
    ElMessage.error("播放失败");
    audioPlayer.clear();
  });
};

// 关闭对话框
const handleClose = () => {
  visible.value = false;
  // 重置状态
  pdfPages.value = [];
  allAudios.value = [];
  coursewareForm.value = { name: "", remark: "" };
  pdfLoading.value = false;
  selectedAudioIds.value = [];
  selectedPageIndex.value = null;
  isDeleteMode.value = false;
  previousSelectedIds = new Set<string>();
  taskDetailData.value = null;
  // 停止音频播放
  audioPlayer.clear();
};

// 打开音频文件选择
const openAudioFileDialog = () => {
  audioFileDialogVisible.value = true;
};

// 处理音频文件选择
const handleAudioFileConfirm = async (filePaths: string[]) => {
  if (!filePaths || filePaths.length === 0) return;

  const loading = ElLoading.service({
    lock: true,
    text: '正在获取音频时长...',
    background: 'rgba(0, 0, 0, 0.7)',
  });

  try {
    const newAudios: AudioFile[] = [];

    for (const filePath of filePaths) {
      const fileName = filePath.split('/').pop() || '';
      const duration = await getAudioDuration(filePath);
      const formattedDuration = formatDuration(duration || 0);

      newAudios.push({
        id: `audio-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`,
        name: fileName,
        duration: formattedDuration,
        path: filePath,
      });
    }

    allAudios.value.push(...newAudios);
    audioFileDialogVisible.value = false;

    // 确保 pages 数组存在且长度足够
    if (taskDetailData.value && pdfPages.value.length > 0) {
      if (!taskDetailData.value.pages) {
        taskDetailData.value.pages = [];
      }
      // 扩展 pages 数组以匹配 PDF 页数
      while (taskDetailData.value.pages.length < pdfPages.value.length) {
        taskDetailData.value.pages.push({ audioIds: [] });
      }
    }

    // 保存到后端
    await saveMaterial();
  } finally {
    loading.close();
  }
};

// 保存音频列表
const saveMaterial = async () => {
  if (!props.materialData?.id) return;

  try {
    // 解析现有 data
    let existingData: TaskDetail = { pages: [] };
    if (typeof props.materialData.data === 'string') {
      try {
        existingData = JSON.parse(props.materialData.data);
      } catch (e) {
        console.error('解析 data 失败:', e);
      }
    } else if (props.materialData.data) {
      existingData = props.materialData.data;
    }

    // 确保 pages 数组存在
    if (!existingData.pages) {
      existingData.pages = [];
    }

    // 如果有 taskDetailData，使用最新的数据
    if (taskDetailData.value) {
      existingData.pages = taskDetailData.value.pages;
    }

    const updatedData: TaskDetail = {
      ...existingData,
      audioList: allAudios.value,
      pdfLength: existingData.pdfLength,
      remark: coursewareForm.value.remark,
    };

    await updateMaterial({
      id: props.materialData.id,
      name: props.materialData.name || '',
      path: props.materialData.path || '',
      cate_id: props.materialData.cate_id || 0,
      type: props.materialData.type ?? 0,
      data: JSON.stringify(updatedData), // 序列化为 JSON 字符串
    });

    // 更新本地的 materialData.data
    if (props.materialData) {
      props.materialData.data = JSON.stringify(updatedData);
    }
  } catch (error: any) {
    console.error('保存音频列表失败:', error);
    ElMessage.error(error.message || '保存失败');
  }
};

// 删除选中的音频
const handleDeleteSelectedAudios = async () => {
  if (selectedAudioIds.value.length === 0) return;

  allAudios.value = allAudios.value.filter(
    (audio) => !selectedAudioIds.value.includes(audio.id)
  );
  selectedAudioIds.value = [];

  // 保存到后端
  await saveMaterial();
};

const playMaterial = () => {
  if (!props.materialData?.id) return;

  // 关闭弹窗
  handleClose();

  // 跳转到每日打卡预览页面，携带素材ID
  router.push({
    path: "/pdf-checkin",
    query: {
      materialId: props.materialData.id,
    },
  });
};

// 跳转到编辑
const gotoEditMaterial = () => {
  if (!props.materialData) return;

  // 关闭详情弹窗
  handleClose();

  // 触发编辑事件，由父组件打开编辑弹窗
  emit("edit", props.materialData as Material);
};
</script>

<style scoped></style>
