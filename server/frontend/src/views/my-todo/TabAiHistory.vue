<template>
  <div class="p-2">
    <!-- 工具栏 -->
    <div class="flex items-center h-10 mb-2">
      <div class="flex flex-1 flex-wrap items-center gap-4">
        <el-button type="primary" plain size="small" :icon="Refresh" @click="loadActive" />
        <el-radio-group v-model="userName" size="small" @change="loadActive">
          <el-radio-button v-for="name in USER_OPTIONS" :key="name" :value="name">
            {{ name }}
          </el-radio-button>
        </el-radio-group>
        <el-tag v-if="conversationId" type="success" effect="plain" size="small">
          会话 {{ shortId(conversationId) }}
        </el-tag>
        <el-tag v-else type="info" effect="plain" size="small">未绑定会话</el-tag>
      </div>
    </div>

    <!-- 消息列表：第 1 页是最新的，倒序 -->
    <el-table
      :data="rows"
      v-loading="loading || pageLoading"
      stripe
      border
      style="width: 100%"
      :max-height="tableMaxHeight">
      <el-table-column label="序号" width="70" align="center">
        <template #default="{ $index }">
          {{ (pageNum - 1) * pageSize + $index + 1 }}
        </template>
      </el-table-column>
      <el-table-column
        :label="`${userName}说的话`"
        min-width="180"
        :show-overflow-tooltip="OVERFLOW_TOOLTIP">
        <template #default="{ row }">{{ row.query || "（空）" }}</template>
      </el-table-column>
      <el-table-column label="回答" min-width="320" :show-overflow-tooltip="OVERFLOW_TOOLTIP">
        <template #default="{ row }">
          <span v-if="row.answer">{{ row.answer }}</span>
          <!-- 生成失败时 answer 为空，把原因显示出来，否则只会看到一个空单元格 -->
          <span v-else-if="row.error" class="text-red-500">失败：{{ row.error }}</span>
          <span v-else class="text-gray-400 italic">（无回复）</span>
        </template>
      </el-table-column>
      <el-table-column label="时间" width="170">
        <template #default="{ row }">{{ formatTs(row.created_at) }}</template>
      </el-table-column>
      <template #empty>
        <div class="py-6 text-gray-500">{{ emptyHint }}</div>
      </template>
    </el-table>

    <!--
      分页：与后台其它页面同一写法（el-pagination + sizes/prev/pager/next + background）。
      Dify 不返回消息总数，所以不传 total，改用 page-count 直接给「页数」；
      页数随往下翻逐页增长，列出的页码都是真实可点的页。
      layout 里的 `->` 是组件内置的右对齐分隔符，配合默认插槽把「已加载条数」贴到该行最右。
    -->
    <el-pagination
      layout="sizes, prev, pager, next, ->, slot"
      :page-count="pageCount"
      v-model:page-size="pageSize"
      :page-sizes="[10, 20, 50]"
      :current-page="pageNum"
      class="mt-2"
      background
      @size-change="handleSizeChange"
      @current-change="handlePageChange">
      <span class="text-sm text-gray-500">已加载 {{ loadedCount }} 条</span>
    </el-pagination>
  </div>
</template>

<script setup lang="ts">
import { getConversationMessages } from "@/api/api-ai-chat";
import { getRdsData } from "@/api/api-rds";
import { useUserStore } from "@/stores/user";
import type { DifyMessage } from "@/types/ai";
import { Refresh } from "@element-plus/icons-vue";
import dayjs from "dayjs";
import { ElMessage } from "element-plus";
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";

const REFRESH_EVENT = "refresh-ai-history-tab";

/**
 * 单元格保持单行，超出显示省略号，悬停出 tooltip。
 * popperClass 配合文件末尾的全局样式，让 tooltip 保留回答里的换行，读起来更像原文。
 */
const OVERFLOW_TOOLTIP = {
  popperClass: "ai-history-tooltip",
  showAfter: 200,
};

/** 本页只需查看这两位用户的 AI 对话记录，固定枚举，不由用户列表决定 */
const USER_OPTIONS = ["昭昭", "灿灿"] as const;

interface PageState {
  /** 该页消息，接口返回为时间正序 */
  items: DifyMessage[];
  /** 是否还有更早的一页 */
  hasMore: boolean;
  /** 本页最旧一条的 id，作为「更早一页」的游标 */
  oldestId?: string;
}

const userStore = useUserStore();

const userName = ref<string>(USER_OPTIONS[0]);
const pageSize = ref(20);
const loading = ref(false);
const pageLoading = ref(false);
const tableMaxHeight = ref<number>(0);

/** 当前活跃会话 id：来自 chatSetting.aiConversationId */
const conversationId = ref("");
/** 已加载的页，下标 0 即第 1 页（最新的一页）；往前翻直接读缓存，不重复请求 */
const pages = ref<PageState[]>([]);
const pageNum = ref(1);

const currentPage = computed(() => pages.value[pageNum.value - 1]);
/** 倒序：最新的在最前 */
const rows = computed(() => (currentPage.value?.items ?? []).slice().reverse());
/** 最后一页是否还有更早的 */
const lastHasMore = computed(() => Boolean(pages.value[pages.value.length - 1]?.hasMore));
/**
 * 页数 = 已加载页数，再算上「已知还有一页」。
 * Dify 不返回总数，只能随着往下翻逐页递增；0 表示还没有可展示的页。
 */
const pageCount = computed(
  () => pages.value.length + (lastHasMore.value ? 1 : 0)
);
/** 已加载条数：Dify 没有总数，只能统计已拉取到的部分 */
const loadedCount = computed(() =>
  pages.value.reduce((sum, p) => sum + (p?.items?.length ?? 0), 0)
);

const emptyHint = computed(() =>
  conversationId.value
    ? `「${userName.value}」这个会话还没有消息`
    : `「${userName.value}」还没有进行中的 AI 对话（chatSetting 未绑定会话）`
);

// 计算表格最大高度（与阅读任务页保持一致的算法）
const calculateTableHeight = () => {
  nextTick(() => {
    const windowHeight = window.innerHeight;
    const reservedSpace = 300;
    tableMaxHeight.value = windowHeight - reservedSpace;
  });
};

function formatTs(ts?: number): string {
  if (!ts) return "-";
  // Dify 返回的是秒级时间戳，必须用 unix() 而非 dayjs(ms)
  return dayjs.unix(ts).format("YYYY-MM-DD HH:mm:ss");
}

function shortId(id?: string): string {
  if (!id) return "-";
  return id.length > 8 ? id.slice(0, 8) : id;
}

/** 读 chatSetting，取出当前绑定的会话 id */
async function readActiveConversationId(id: number): Promise<string> {
  const raw = await getRdsData<string>("chatSetting", id);
  if (!raw) return "";
  const setting = typeof raw === "string" ? JSON.parse(raw) : raw;
  const cid = (setting as { aiConversationId?: string } | null)?.aiConversationId;
  return (cid ?? "").trim();
}

/**
 * 拉取指定页。第 1 页不带游标（Dify 返回最新的 N 条），
 * 更早的页用上一页最旧一条的 id 作为 first_id。
 * 只有「下一页」需要请求，回到已加载的页直接读缓存。
 */
async function fetchPage(target: number): Promise<void> {
  if (!conversationId.value) return;
  if (target < 1 || pages.value[target - 1]) return;

  const prev = pages.value[target - 2];
  if (target > 1 && !prev) return;

  pageLoading.value = true;
  try {
    const page = await getConversationMessages(
      conversationId.value,
      pageSize.value,
      userName.value,
      target === 1 ? undefined : prev.oldestId
    );
    const list = Array.isArray(page?.data) ? page.data : [];

    // 接口按时间正序返回，list[0] 即本页最旧一条
    pages.value[target - 1] = {
      items: list,
      hasMore: Boolean(page?.has_more) && list.length > 0,
      oldestId: list[0]?.id,
    };
    pageNum.value = target;
  } catch (error) {
    ElMessage.error((error as Error).message || "获取会话消息失败");
  } finally {
    pageLoading.value = false;
  }
}

/**
 * 重置并加载第 1 页。
 * 本页不展示会话列表，chatSetting.aiConversationId 即「当前正在继续的对话」的唯一来源。
 */
async function loadActive(): Promise<void> {
  conversationId.value = "";
  pages.value = [];
  pageNum.value = 1;
  loading.value = true;

  try {
    if (userStore.userList.length === 0) {
      await userStore.refreshUserList();
    }
    const user = userStore.userList.find((u) => u.name === userName.value);
    if (!user) {
      ElMessage.error(`未在用户列表中找到「${userName.value}」`);
      return;
    }

    conversationId.value = await readActiveConversationId(user.id);
    if (!conversationId.value) return;

    await fetchPage(1);
  } catch (error) {
    ElMessage.error((error as Error).message || "获取会话消息失败");
  } finally {
    loading.value = false;
  }
}

function handlePageChange(page: number): void {
  if (page === pageNum.value) return;
  // 已加载过就直接展示；只有往后一页才需要请求
  if (pages.value[page - 1]) {
    pageNum.value = page;
    return;
  }
  void fetchPage(page);
}

/** 改每页条数会改变分页边界，游标随之失效，必须从第 1 页重新拉 */
function handleSizeChange(): void {
  pages.value = [];
  pageNum.value = 1;
  void fetchPage(1);
}

onMounted(() => {
  calculateTableHeight();
  window.addEventListener("resize", calculateTableHeight);
  window.addEventListener(REFRESH_EVENT, loadActive);

  loadActive();
});

onUnmounted(() => {
  window.removeEventListener("resize", calculateTableHeight);
  window.removeEventListener(REFRESH_EVENT, loadActive);
});
</script>

<style>
/*
 * el-table 的 show-overflow-tooltip 会把 popper 挂到 body 上，
 * scoped 样式选不中，因此这里用全局样式。
 * pre-wrap 保留回答里的换行，避免整段被压成一行。
 */
.ai-history-tooltip {
  max-width: 620px;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
