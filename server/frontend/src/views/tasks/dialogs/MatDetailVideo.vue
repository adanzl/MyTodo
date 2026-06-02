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
          <div class="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-4 py-3 font-bold">
            <span>本地字幕 ({{ sidecarSubtitles.length }})</span>
            <el-button type="primary" size="small" plain :loading="subtitleSearchLoading" @click="addSubtitle">
              搜索字幕
            </el-button>
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
            <span>在线搜索字幕</span>
            <el-tag v-if="subtitleSearchMode === 'hash'" type="info" size="small">Hash 匹配</el-tag>
            <el-tag v-else type="warning" size="small">文字搜索</el-tag>
            <span v-if="subtitleSearchTotal > 0" class="text-xs font-normal text-gray-500">
              共 {{ subtitleSearchTotal }} 条
            </span>
          </div>
          <div class="flex shrink-0 gap-2 border-b border-gray-200 p-3">
            <el-input
              v-model="subtitleSearchQuery"
              placeholder="按标题关键词搜索（可选）"
              clearable
              class="flex-1"
              @keyup.enter="() => runSubtitleTextSearch()"
            />
            <el-button @click="() => runSubtitleTextSearch()">文字搜索</el-button>
            <el-button type="primary" @click="() => runSubtitleHashSearch()">Hash 搜索</el-button>
          </div>
          <el-table :data="subtitleSearchRows" max-height="320" empty-text="未找到字幕">
            <el-table-column prop="language" label="语言" width="72" />
            <el-table-column prop="release" label="版本" min-width="160" show-overflow-tooltip />
            <el-table-column prop="fileName" label="文件名" min-width="180" show-overflow-tooltip />
            <el-table-column label="操作" width="88" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" size="small" link disabled @click="downloadSubtitle(row)">
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

const subtitleSearchActive = ref(false);
const subtitleSearchLoading = ref(false);
const subtitleSearchMode = ref<'hash' | 'text'>('hash');
const subtitleSearchQuery = ref('');
const subtitleSearchRows = ref<SubtitleSearchRow[]>([]);
const subtitleSearchTotal = ref(0);
const subtitleSearchPage = ref(1);
const subtitleSearchPerPage = ref(20);
const subtitleSearchTotalPages = ref(0);

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

const initVideoDetail = async () => {
  if (!props.matData) return;

  detailLoading.value = true;
  try {
    const detail = parseVideoDetailData(props.matData.data);
    videoDetailData.value = detail;
    videoDetailForm.value.remark = detail?.remark || "";

    if (props.matData.path) {
      const tracks = await listSidecarSubtitles(props.matData.path);
      sidecarSubtitles.value = tracks.map((t) => ({
        path: t.path,
        label: t.label,
        lang: t.lang,
      }));
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
  subtitleSearchTotalPages.value = 0;
  subtitleSearchQuery.value = '';
  subtitleSearchMode.value = 'hash';
};

const applySubtitleSearchResult = (result: Awaited<ReturnType<typeof searchSubtitles>>) => {
  subtitleSearchRows.value = result.data;
  subtitleSearchTotal.value = result.total_count;
  subtitleSearchPage.value = result.page;
  subtitleSearchPerPage.value = result.per_page ?? 20;
  subtitleSearchTotalPages.value = result.total_pages;
  if (result.mode === 'text' || result.mode === 'hash') {
    subtitleSearchMode.value = result.mode;
  }
};

function normalizeSearchPage(page: unknown): number {
  return typeof page === 'number' && page >= 1 ? Math.floor(page) : 1;
}

const runSubtitleHashSearch = async (page?: number) => {
  const p = normalizeSearchPage(page);
  const videoPath = props.matData?.path;
  if (!videoPath) {
    ElMessage.warning('请先配置视频路径');
    return;
  }
  subtitleSearchLoading.value = true;
  subtitleSearchMode.value = 'hash';
  try {
    const result = await searchSubtitles({ mode: 'hash', video_path: videoPath, page: p });
    applySubtitleSearchResult(result);
    if (result.data.length === 0) {
      ElMessage.info('未找到匹配字幕，可尝试文字搜索');
    }
  } catch (e: any) {
    console.error('字幕 Hash 搜索失败:', e);
    ElMessage.error(e.message || '字幕搜索失败');
    subtitleSearchRows.value = [];
    subtitleSearchTotal.value = 0;
  } finally {
    subtitleSearchLoading.value = false;
  }
};

const runSubtitleTextSearch = async (page?: number) => {
  const p = normalizeSearchPage(page);
  const query = subtitleSearchQuery.value.trim() || props.matData?.name?.trim() || '';
  if (!query) {
    ElMessage.warning('请输入搜索关键词');
    return;
  }
  subtitleSearchLoading.value = true;
  subtitleSearchMode.value = 'text';
  try {
    const result = await searchSubtitles({ mode: 'text', query, page: p });
    applySubtitleSearchResult(result);
    if (result.data.length === 0) {
      ElMessage.info('未找到匹配字幕');
    }
  } catch (e: any) {
    console.error('字幕文字搜索失败:', e);
    ElMessage.error(e.message || '字幕搜索失败');
    subtitleSearchRows.value = [];
    subtitleSearchTotal.value = 0;
  } finally {
    subtitleSearchLoading.value = false;
  }
};

const onSubtitleSearchPageChange = (page: number) => {
  if (subtitleSearchMode.value === 'hash') {
    runSubtitleHashSearch(page);
  } else {
    runSubtitleTextSearch(page);
  }
};

const addSubtitle = async () => {
  if (!props.matData?.path) {
    ElMessage.warning('请先配置视频路径');
    return;
  }
  subtitleSearchQuery.value = props.matData.name || '';
  subtitleSearchActive.value = true;
  await runSubtitleHashSearch();
};

const downloadSubtitle = async (row: SubtitleSearchRow) => {
  const videoPath = props.matData?.path;
  if (!videoPath) {
    ElMessage.warning('请先配置视频路径');
    return;
  }
  if (!row.id) {
    ElMessage.warning('无效的字幕条目');
    return;
  }
  subtitleSearchLoading.value = true;
  try {
    const track = await downloadSubtitleToSidecar({
      video_path: videoPath,
      subtitle_id: row.id,
    });
    ElMessage.success('字幕已保存到视频同目录');
    const tracks = await listSidecarSubtitles(videoPath);
    sidecarSubtitles.value = tracks.map((t) => ({
      path: t.path,
      label: t.label,
      lang: t.lang,
      ext: t.ext,
    }));
    if (!sidecarSubtitles.value.some((s) => s.path === track.path) && track.path) {
      sidecarSubtitles.value.push({
        path: track.path,
        label: track.label,
        lang: track.lang,
        ext: track.ext,
      });
    }
  } catch (e: any) {
    console.error('字幕下载失败:', e);
    ElMessage.error(e.message || '字幕下载失败');
  } finally {
    subtitleSearchLoading.value = false;
  }
};
</script>

<style scoped></style>
