<template>
  <el-dialog
    v-model="visible"
    title="视频详情"
    align-center
    width="1200px"
    destroy-on-close
    @close="handleClose"
  >
    <div v-loading="detailLoading" element-loading-text="加载中..." class="flex min-h-100 h-[80vh] flex-col gap-4">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="名称" min-width="60">{{ matData?.name }}</el-descriptions-item>
        <el-descriptions-item label="操作" min-width="60">
          <div class="flex gap-2">
            <el-button type="primary" size="small" plain @click="playVideo">
              <el-icon :size="16"><VideoPlay /></el-icon>
            </el-button>
            <el-button type="primary" size="small" plain @click="gotoEditVideo">
              <el-icon :size="16"><Edit /></el-icon>
            </el-button>
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="路径" min-width="60">{{ matData?.path }}</el-descriptions-item>
      </el-descriptions>

      <div class="flex min-h-0 flex-1 flex-col gap-3 overflow-hidden">
        <div class="flex max-h-36 shrink-0 flex-col overflow-hidden rounded border border-gray-200">
          <div class="flex flex-wrap items-center justify-between gap-2 border-b border-gray-200 bg-gray-50 px-4 py-3 font-bold">
            <span>本地字幕 ({{ sidecarSubtitles.length }})</span>
            <div class="flex items-center gap-2">
              <el-select v-model="recognizeLang" size="small" style="width: 88px">
                <el-option label="en" value="en" />
                <el-option label="zh" value="zh" />
              </el-select>
              <el-button
                type="warning"
                size="small"
                plain
                :loading="recognizeLoading"
                @click="runRecognize"
              >
                语音识别
              </el-button>
              <el-button type="primary" size="small" plain @click="openSubtitleSearch">
                搜索字幕
              </el-button>
            </div>
          </div>
          <div class="overflow-y-auto p-3">
            <div
              v-for="(sub, index) in sidecarSubtitles"
              :key="`${sub.path}-${index}`"
              class="mb-2 rounded border border-gray-200 p-2 text-xs"
            >
              <div class="font-medium text-gray-800">{{ sub.label || sub.path }}</div>
              <div class="mt-1 truncate text-gray-500" :title="sub.path">{{ sub.path }}</div>
              <div v-if="sub.lang" class="mt-1 text-gray-400">语言: {{ sub.lang }}</div>
            </div>
            <el-empty v-if="sidecarSubtitles.length === 0" description="暂无本地字幕" :image-size="48" />
          </div>
        </div>

        <div
          v-show="subtitleSearchActive"
          v-loading="subtitleSearchLoading"
          class="flex min-h-0 flex-1 flex-col overflow-hidden rounded border border-gray-200"
        >
          <div class="flex flex-wrap items-center gap-2 border-b border-gray-200 bg-gray-50 px-4 py-3 font-bold">
            <span>在线搜索（ASSRT）</span>
            <span v-if="subtitleSearchTotal > 0" class="text-xs font-normal text-gray-500">
              共 {{ subtitleSearchTotal }} 条
            </span>
          </div>
          <div class="flex shrink-0 gap-2 border-b border-gray-200 p-3">
            <el-input
              v-model="subtitleSearchQuery"
              placeholder="输入关键词搜索"
              clearable
              class="flex-1"
              @keyup.enter="() => runSubtitleTextSearch()"
            />
            <el-button type="primary" @click="() => runSubtitleTextSearch()">搜索</el-button>
          </div>
          <el-table :data="subtitleSearchRows" max-height="320" empty-text="未找到字幕">
            <el-table-column prop="language" label="语言" width="72" />
            <el-table-column prop="release" label="版本" min-width="160" show-overflow-tooltip />
            <el-table-column prop="fileName" label="文件名" min-width="180" show-overflow-tooltip />
            <el-table-column label="操作" width="88" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" link @click="downloadSubtitle(row)">
                  下载
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="subtitleSearchTotal > 0" class="flex justify-end border-t border-gray-200 p-2">
            <el-pagination
              v-model:current-page="subtitleSearchPage"
              :page-size="subtitleSearchPerPage"
              :total="subtitleSearchTotal"
              layout="prev, pager, next"
              small
              @current-change="onSubtitleSearchPageChange"
            />
          </div>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { ElMessage } from "element-plus";
import { VideoPlay, Edit } from "@element-plus/icons-vue";
import { type Material } from "@/api/api-task";
import type { MaterialDetail, SubtitleFile } from "@/types/tasks/materialDetail";
import {
  downloadSubtitleToSidecar,
  listSidecarSubtitles,
  recognizeSubtitle,
  waitRecognizeSubtitleDone,
  searchSubtitles,
  type SubtitleSearchRow,
} from "@/utils/subtitle";

interface Props {
  modelValue: boolean;
  matData?: Partial<Material> | null;
}

interface Emits {
  (e: "update:modelValue", value: boolean): void;
  (e: "edit", material: Material): void;
  (e: "play", material: Material): void;
}

const props = withDefaults(defineProps<Props>(), {
  matData: null,
});

const emit = defineEmits<Emits>();

const visible = ref(false);
const detailLoading = ref(false);
const videoDetailForm = ref({ remark: "" });
const videoDetailData = ref<MaterialDetail | null>(null);
const sidecarSubtitles = ref<SubtitleFile[]>([]);

const recognizeLang = ref("en");
const recognizeLoading = ref(false);

const subtitleSearchActive = ref(false);
const subtitleSearchLoading = ref(false);
const subtitleSearchQuery = ref("");
const subtitleSearchRows = ref<SubtitleSearchRow[]>([]);
const subtitleSearchTotal = ref(0);
const subtitleSearchPage = ref(1);
const subtitleSearchPerPage = ref(20);

function parseVideoDetailData(raw: Material["data"]): MaterialDetail | null {
  if (!raw) return null;
  if (typeof raw === "string") {
    try {
      return JSON.parse(raw);
    } catch (e) {
      console.error("解析 data 失败:", e);
      return null;
    }
  }
  return raw;
}

async function refreshSidecarList(videoPath: string) {
  const tracks = await listSidecarSubtitles(videoPath);
  sidecarSubtitles.value = tracks.map((t) => ({
    path: t.path,
    label: t.label,
    lang: t.lang,
    ext: t.ext,
  }));
}

const initVideoDetail = async () => {
  if (!props.matData) return;

  detailLoading.value = true;
  try {
    const detail = parseVideoDetailData(props.matData.data);
    videoDetailData.value = detail;
    videoDetailForm.value.remark = detail?.remark || "";

    if (props.matData.path) {
      await refreshSidecarList(props.matData.path);
    } else {
      sidecarSubtitles.value = [];
    }

    if (sidecarSubtitles.value.length === 0 && detail?.subtitleList?.length) {
      sidecarSubtitles.value = [...detail.subtitleList];
    }
  } catch (e) {
    console.error("加载视频详情失败:", e);
    const detail = parseVideoDetailData(props.matData?.data);
    sidecarSubtitles.value = detail?.subtitleList ? [...detail.subtitleList] : [];
  } finally {
    detailLoading.value = false;
  }
};

watch(
  () => props.modelValue,
  (val) => {
    visible.value = val;
    if (val && props.matData) {
      initVideoDetail();
    }
  },
  { immediate: true }
);

watch(
  () => props.matData?.id,
  () => {
    if (visible.value && props.matData) {
      initVideoDetail();
    }
  }
);

watch(visible, (val) => {
  emit("update:modelValue", val);
});

const handleClose = () => {
  visible.value = false;
  subtitleSearchActive.value = false;
  resetSubtitleSearch();
  videoDetailForm.value = { remark: "" };
  videoDetailData.value = null;
  sidecarSubtitles.value = [];
  detailLoading.value = false;
};

const playVideo = () => {
  if (!props.matData) return;
  handleClose();
  emit("play", props.matData as Material);
};

const gotoEditVideo = () => {
  if (!props.matData) return;
  handleClose();
  emit("edit", props.matData as Material);
};

const resetSubtitleSearch = () => {
  subtitleSearchRows.value = [];
  subtitleSearchTotal.value = 0;
  subtitleSearchPage.value = 1;
  subtitleSearchQuery.value = "";
};

const applySubtitleSearchResult = (result: Awaited<ReturnType<typeof searchSubtitles>>) => {
  subtitleSearchRows.value = result.data;
  subtitleSearchTotal.value = result.total_count;
  subtitleSearchPage.value = result.page;
  subtitleSearchPerPage.value = result.per_page ?? 20;
};

function normalizeSearchPage(page: unknown): number {
  return typeof page === "number" && page >= 1 ? Math.floor(page) : 1;
}

const runSubtitleTextSearch = async (page?: number) => {
  const p = normalizeSearchPage(page);
  const query = subtitleSearchQuery.value.trim() || props.matData?.name?.trim() || "";
  if (!query) {
    ElMessage.warning("请输入搜索关键词");
    return;
  }
  subtitleSearchLoading.value = true;
  try {
    const result = await searchSubtitles({ query, page: p });
    applySubtitleSearchResult(result);
    if (result.data.length === 0) {
      ElMessage.info("未找到匹配字幕");
    }
  } catch (e: any) {
    console.error("字幕搜索失败:", e);
    ElMessage.error(e.message || "字幕搜索失败");
    subtitleSearchRows.value = [];
    subtitleSearchTotal.value = 0;
  } finally {
    subtitleSearchLoading.value = false;
  }
};

const onSubtitleSearchPageChange = (page: number) => {
  runSubtitleTextSearch(page);
};

const openSubtitleSearch = () => {
  if (!props.matData?.path) {
    ElMessage.warning("请先配置视频路径");
    return;
  }
  subtitleSearchQuery.value = props.matData.name || "";
  subtitleSearchActive.value = true;
};

const runRecognize = async () => {
  const videoPath = props.matData?.path;
  if (!videoPath) {
    ElMessage.warning("请先配置视频路径");
    return;
  }
  recognizeLoading.value = true;
  try {
    await recognizeSubtitle({
      video_path: videoPath,
      language: recognizeLang.value || "en",
    });
    ElMessage.info("已加入识别队列，请稍候…");
    await waitRecognizeSubtitleDone(videoPath);
    ElMessage.success("语音识别完成，字幕已保存");
    await refreshSidecarList(videoPath);
  } catch (e: any) {
    console.error("语音识别失败:", e);
    ElMessage.error(e.message || "语音识别失败");
  } finally {
    recognizeLoading.value = false;
  }
};

const downloadSubtitle = async (row: SubtitleSearchRow) => {
  const videoPath = props.matData?.path;
  if (!videoPath) {
    ElMessage.warning("请先配置视频路径");
    return;
  }
  if (!row.id) {
    ElMessage.warning("无效的字幕条目");
    return;
  }
  subtitleSearchLoading.value = true;
  try {
    const track = await downloadSubtitleToSidecar({
      video_path: videoPath,
      subtitle_id: row.id,
    });
    ElMessage.success("字幕已保存到视频同目录");
    await refreshSidecarList(videoPath);
    if (!sidecarSubtitles.value.some((s) => s.path === track.path) && track.path) {
      sidecarSubtitles.value.push({
        path: track.path,
        label: track.label,
        lang: track.lang,
        ext: track.ext,
      });
    }
  } catch (e: any) {
    console.error("字幕下载失败:", e);
    ElMessage.error(e.message || "字幕下载失败");
  } finally {
    subtitleSearchLoading.value = false;
  }
};
</script>

<style scoped></style>
