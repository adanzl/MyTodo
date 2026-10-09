<template>
  <div class="p-2">
    <!-- 工具栏 -->
    <div class="flex flex-wrap items-center gap-2 mb-2">
      <el-select
        v-model="userName"
        filterable
        allow-create
        default-first-option
        placeholder="选择或输入用户名"
        style="width: 200px"
        @change="loadFirstPage">
        <el-option v-for="name in userOptions" :key="name" :label="name" :value="name" />
      </el-select>
      <el-select v-model="pageSize" style="width: 110px" @change="loadFirstPage">
        <el-option :value="10" label="10 条/页" />
        <el-option :value="20" label="20 条/页" />
        <el-option :value="50" label="50 条/页" />
      </el-select>
      <el-button type="primary" plain size="small" :icon="Refresh" @click="loadFirstPage" />
      <el-tag type="info" effect="plain" size="small">{{ appHint }}</el-tag>
    </div>

    <!-- 会话列表 -->
    <el-table
      :data="conversations"
      v-loading="loading"
      stripe
      border
      style="width: 100%"
      :max-height="tableMaxHeight">
      <el-table-column prop="name" label="会话名称" min-width="200" show-overflow-tooltip />
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ formatTs(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="更新时间" width="170">
        <template #default="{ row }">{{ formatTs(row.updated_at) }}</template>
      </el-table-column>
      <el-table-column label="会话 ID" width="150">
        <template #default="{ row }">
          <span class="font-mono text-xs">{{ shortId(row.id) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="90" align="center">
        <template #default="{ row }">
          <el-button link type="primary" @click="openMessages(row)">查看</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <div class="py-6 text-gray-500">{{ emptyHint }}</div>
      </template>
    </el-table>

    <!-- 翻页 -->
    <div class="flex items-center justify-between mt-2">
      <el-button v-if="hasMore" size="small" :loading="loading" @click="loadMore">
        加载更多
      </el-button>
      <span v-else class="text-sm text-gray-400">
        {{ conversations.length ? "已到最早" : "" }}
      </span>
      <span class="text-sm text-gray-500">已加载 {{ conversations.length }} 个会话</span>
    </div>

    <!-- 消息抽屉 -->
    <el-drawer v-model="drawerOpen" :title="current?.name || '会话消息'" size="60%">
      <div v-loading="msgLoading" class="h-full flex flex-col">
        <div class="flex-1 overflow-y-auto pr-1">
          <el-button
            v-if="msgHasMore"
            size="small"
            class="mb-3 w-full"
            :loading="msgLoading"
            @click="loadOlderMessages">
            加载更早
          </el-button>

          <div v-for="msg in messages" :key="msg.id" class="mb-4">
            <div class="text-xs text-gray-400 mb-1 text-center">
              {{ formatTs(msg.created_at) }}
            </div>
            <div class="flex justify-end mb-1">
              <div
                class="max-w-[80%] bg-green-500 text-white rounded-lg px-3 py-2 whitespace-pre-wrap break-words">
                {{ msg.query }}
              </div>
            </div>
            <div class="flex">
              <div
                class="max-w-[80%] bg-pink-100 rounded-lg px-3 py-2 whitespace-pre-wrap break-words">
                <template v-if="msg.answer">{{ msg.answer }}</template>
                <span v-else class="text-gray-400 italic">（无回复）</span>
              </div>
            </div>
            <div v-if="msg.error" class="mt-1 text-xs text-red-500">失败：{{ msg.error }}</div>
            <div class="mt-1 text-xs text-gray-400">
              tokens {{ msg.message_tokens ?? 0 }} + {{ msg.answer_tokens ?? 0 }} =
              {{ msg.total_tokens ?? 0 }}
              <span v-if="msg.provider_response_latency !== undefined">
                · {{ msg.provider_response_latency?.toFixed(1) }}s
              </span>
              <span v-if="msg.total_price"> · ${{ msg.total_price }}</span>
            </div>
          </div>

          <div v-if="!messages.length && !msgLoading" class="py-6 text-center text-gray-500">
            没有消息
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { getConversationMessages, getConversations } from "@/api/api-ai-chat";
import { useUserStore } from "@/stores/user";
import type { DifyConversation, DifyMessage } from "@/types/ai";
import { Refresh } from "@element-plus/icons-vue";
import dayjs from "dayjs";
import { ElMessage } from "element-plus";
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";

const REFRESH_EVENT = "refresh-ai-history-tab";

const userStore = useUserStore();

const userName = ref("");
const pageSize = ref(20);
const conversations = ref<DifyConversation[]>([]);
const hasMore = ref(false);
const loading = ref(false);
const tableMaxHeight = ref(0);
/** 会话翻页游标：上一页最后一条的 id */
const convCursor = ref<string | undefined>(undefined);

const drawerOpen = ref(false);
const current = ref<DifyConversation | null>(null);
const messages = ref<DifyMessage[]>([]);
const msgHasMore = ref(false);
const msgLoading = ref(false);
/** 消息翻页游标：已加载消息里最旧一条的 id */
const msgCursor = ref<string | undefined>(undefined);

const userOptions = computed(() =>
  userStore.userList.map((u) => u.name).filter((n): n is string => Boolean(n))
);

const appHint = computed(() =>
  userName.value.trim().toLowerCase() === "leo"
    ? "leo → leo 的 Dify 应用"
    : "其他人 → 豆豆的 Dify 应用"
);

const emptyHint = computed(() => {
  const uid = userName.value.trim();
  if (!uid) return "请先选择或输入用户名";
  return `「${uid}」在当前 Dify 应用下没有会话。注意 leo 与其他用户名走的是不同应用，用户名写错会得到空列表`;
});

function formatTs(ts?: number): string {
  if (!ts) return "-";
  // Dify 返回的是秒级时间戳，必须用 unix() 而非 dayjs(ms)
  return dayjs.unix(ts).format("YYYY-MM-DD HH:mm:ss");
}

function shortId(id?: string): string {
  if (!id) return "-";
  return id.length > 8 ? id.slice(0, 8) : id;
}

async function fetchConversations(reset: boolean): Promise<void> {
  const uid = userName.value.trim();
  if (!uid) {
    conversations.value = [];
    hasMore.value = false;
    return;
  }

  const lastId = reset ? undefined : convCursor.value;
  loading.value = true;
  try {
    const page = await getConversations(uid, pageSize.value, lastId);
    const list = Array.isArray(page?.data) ? page.data : [];

    if (reset) {
      conversations.value = list;
    } else {
      const seen = new Set(conversations.value.map((c) => c.id));
      conversations.value = [
        ...conversations.value,
        ...list.filter((c) => !seen.has(c.id)),
      ];
    }

    // 游标必须前进，否则会出现「has_more 一直为真但拿不到新数据」的死循环
    const nextCursor = list[list.length - 1]?.id;
    const progressed = Boolean(nextCursor) && nextCursor !== lastId;
    hasMore.value = Boolean(page?.has_more) && list.length > 0 && progressed;
    if (progressed) convCursor.value = nextCursor;
  } catch (error) {
    ElMessage.error((error as Error).message || "获取会话列表失败");
    if (reset) conversations.value = [];
    hasMore.value = false;
  } finally {
    loading.value = false;
  }
}

function loadFirstPage(): void {
  if (!userName.value.trim()) {
    ElMessage.warning("请先选择或输入用户名");
    return;
  }
  convCursor.value = undefined;
  drawerOpen.value = false;
  current.value = null;
  messages.value = [];
  msgCursor.value = undefined;
  msgHasMore.value = false;
  void fetchConversations(true);
}

function loadMore(): void {
  if (!convCursor.value) return;
  void fetchConversations(false);
}

async function fetchMessages(reset: boolean): Promise<void> {
  const conv = current.value;
  if (!conv) return;

  const firstId = reset ? undefined : msgCursor.value;
  msgLoading.value = true;
  try {
    const page = await getConversationMessages(
      conv.id,
      pageSize.value,
      userName.value.trim(),
      firstId
    );
    const list = Array.isArray(page?.data) ? page.data : [];

    if (reset) {
      messages.value = list;
    } else {
      const seen = new Set(messages.value.map((m) => m.id));
      messages.value = [...list.filter((m) => !seen.has(m.id)), ...messages.value];
    }

    // 消息按时间正序返回，list[0] 即本页最旧一条，作为往更早翻的游标
    const nextCursor = list[0]?.id;
    const progressed = Boolean(nextCursor) && nextCursor !== firstId;
    msgHasMore.value = Boolean(page?.has_more) && list.length > 0 && progressed;
    if (progressed) msgCursor.value = nextCursor;
  } catch (error) {
    ElMessage.error((error as Error).message || "获取会话消息失败");
    if (reset) messages.value = [];
    msgHasMore.value = false;
  } finally {
    msgLoading.value = false;
  }
}

function openMessages(row: DifyConversation): void {
  current.value = row;
  messages.value = [];
  msgCursor.value = undefined;
  msgHasMore.value = false;
  drawerOpen.value = true;
  void fetchMessages(true);
}

function loadOlderMessages(): void {
  if (!msgCursor.value) return;
  void fetchMessages(false);
}

const calculateTableHeight = (): void => {
  nextTick(() => {
    tableMaxHeight.value = window.innerHeight - 320;
  });
};

onMounted(async () => {
  calculateTableHeight();
  window.addEventListener("resize", calculateTableHeight);
  window.addEventListener(REFRESH_EVENT, loadFirstPage);

  if (userStore.userList.length === 0) {
    await userStore.refreshUserList();
  }
  const initial = userStore.curUser.name || userStore.userList[0]?.name || "";
  if (initial) {
    userName.value = initial;
    loadFirstPage();
  }
});

onUnmounted(() => {
  window.removeEventListener("resize", calculateTableHeight);
  window.removeEventListener(REFRESH_EVENT, loadFirstPage);
});
</script>
