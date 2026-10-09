<template>
  <div class="p-2 flex flex-col">
    <!-- 工具栏 -->
    <div class="flex flex-wrap items-center gap-2 mb-2 shrink-0">
      <el-radio-group v-model="userName" @change="loadActive" size="small">
        <el-radio-button v-for="name in USER_OPTIONS" :key="name" :value="name">
          {{ name }}
        </el-radio-button>
      </el-radio-group>
      <el-select v-model="pageSize" style="width: 140px" size="small">
        <el-option :value="10" label="消息 10 条/页" />
        <el-option :value="20" label="消息 20 条/页" />
        <el-option :value="50" label="消息 50 条/页" />
      </el-select>
      <el-button type="primary" plain size="small" :icon="Refresh" @click="loadActive" />
      <el-tag v-if="conversationId" type="success" effect="plain" size="small">
        会话 {{ shortId(conversationId) }}
      </el-tag>
      <el-tag v-else type="info" effect="plain" size="small">未绑定会话</el-tag>
    </div>

    <!-- 会话内容：直接展示 -->
    <div
      ref="scroller"
      v-loading="loading || msgLoading"
      class="overflow-y-auto rounded border border-gray-200 bg-white p-3"
      :style="{ height: `${scrollerHeight}px` }">
      <!-- 加载更早 -->
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

      <div
        v-if="!messages.length && !msgLoading && !loading"
        class="py-10 text-center text-gray-500">
        {{ emptyHint }}
      </div>
    </div>
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

/** 本页只需查看这两位用户的 AI 对话记录，固定枚举，不由用户列表决定 */
const USER_OPTIONS = ["昭昭", "灿灿"] as const;

const userStore = useUserStore();

const userName = ref<string>(USER_OPTIONS[0]);
const pageSize = ref(20);
const loading = ref(false);
const scroller = ref<HTMLElement | null>(null);
/** 消息区高度：el-tab-pane 不提供高度，按窗口高度算（与 TabTaskHistory 同法） */
const scrollerHeight = ref(400);

/** 当前活跃会话 id：来自 chatSetting.aiConversationId */
const conversationId = ref("");
const messages = ref<DifyMessage[]>([]);
const msgHasMore = ref(false);
const msgLoading = ref(false);
/** 消息翻页游标：已加载消息里最旧一条的 id */
const msgCursor = ref<string | undefined>(undefined);

const emptyHint = computed(() =>
  conversationId.value
    ? `「${userName.value}」这个会话还没有消息`
    : `「${userName.value}」还没有进行中的 AI 对话（chatSetting 未绑定会话）`
);

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

function scrollToBottom(): void {
  nextTick(() => {
    const el = scroller.value;
    if (el) el.scrollTop = el.scrollHeight;
  });
}

/**
 * 直接加载 chatSetting.aiConversationId 绑定会话的消息。
 * 本页不展示会话列表，该字段即「当前正在继续的对话」的唯一来源。
 */
async function loadActive(): Promise<void> {
  conversationId.value = "";
  messages.value = [];
  msgCursor.value = undefined;
  msgHasMore.value = false;
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

    await fetchMessages(true);
    scrollToBottom();
  } catch (error) {
    ElMessage.error((error as Error).message || "获取会话消息失败");
  } finally {
    loading.value = false;
  }
}

async function fetchMessages(reset: boolean): Promise<void> {
  if (!conversationId.value) return;

  const firstId = reset ? undefined : msgCursor.value;
  msgLoading.value = true;
  try {
    const page = await getConversationMessages(
      conversationId.value,
      pageSize.value,
      userName.value,
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

function loadOlderMessages(): void {
  if (!msgCursor.value) return;
  const el = scroller.value;
  const prevHeight = el?.scrollHeight ?? 0;
  void fetchMessages(false).then(() => {
    // 往更早翻时保持视口位置，避免跳到顶部
    nextTick(() => {
      if (el) el.scrollTop = el.scrollHeight - prevHeight;
    });
  });
}

const updateScrollerHeight = (): void => {
  // 视口减去外层 header、页签栏、工具栏与内边距
  scrollerHeight.value = Math.max(200, window.innerHeight - 300);
};

onMounted(() => {
  updateScrollerHeight();
  window.addEventListener("resize", updateScrollerHeight);
  window.addEventListener(REFRESH_EVENT, loadActive);
  loadActive();
});

onUnmounted(() => {
  window.removeEventListener("resize", updateScrollerHeight);
  window.removeEventListener(REFRESH_EVENT, loadActive);
});
</script>
