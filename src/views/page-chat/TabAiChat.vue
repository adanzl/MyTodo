<template>
  <ion-segment-content id="aiChat">
    <ion-content
      class="relative"
      ref="contentRef"
      scroll-events
      @ionScroll="onContentScroll">
      <ion-refresher slot="fixed" @ionRefresh="onRefresh">
        <ion-refresher-content></ion-refresher-content>
      </ion-refresher>
      <div
        v-if="networkError"
        class="mx-2 mt-2 p-2 rounded-lg bg-amber-100 text-amber-800 text-sm flex items-center justify-between">
        <span>加载失败，请检查网络后下拉刷新</span>
        <ion-button size="small" fill="clear" @click="retryRefresh">重试</ion-button>
      </div>
      <div class="flex flex-col h-full p-2 border-t border-gray-200 gap-2">
        <div v-for="(msg, idx) in messages" :key="msg.clientRequestId ?? msg.id ?? idx" class="p-1.5 w-full flex">
          <div
            v-if="msg.role == 'server'"
            class="max-w-[80%] bg-pink-200 rounded-lg p-2 shadow-md relative inline-block">
            <span
              v-if="msg.status === 'thinking'"
              class="text-gray-600 italic animate-pulse">
              {{ msg.content || "正在思考…" }}
            </span>
            <span v-else-if="msg.status === 'error'" class="text-red-800">
              {{ msg.content }}
            </span>
            <span v-else>{{ msg.content ?? "..." }}</span>
            <ion-button
              v-if="msg.status === 'error' && msg.retryText"
              size="small"
              fill="clear"
              class="mt-1 h-8"
              @click="$emit('retry', msg.retryText!)">
              重试
            </ion-button>
            <div
              v-if="msg.status !== 'error'"
              class="absolute -right-10 top-1 rounded-[50%] border border-cyan-950 w-8 h-8 flex items-center justify-center"
              @click="$emit('audio-click', msg)">
              <Icon icon="mdi:stop-circle-outline" class="w-6 h-6" v-if="msg.playing" />
              <ion-icon :icon="volumeMediumOutline" class="w-6 h-6" v-else />
            </div>
          </div>
          <div v-else class="max-w-[80%] bg-green-500 text-white p-2 rounded-lg shadow-md relative ml-auto inline-block">
            {{ msg.content }}
            <div
              v-if="msg.audioSrc"
              class="absolute -left-10 top-1 rounded-[50%] border border-cyan-950 w-8 h-8 flex items-center justify-center text-black"
              @click="$emit('audio-click', msg)">
              <Icon icon="mdi:stop-circle-outline" class="w-6 h-6" v-if="msg.playing" />
              <ion-icon :icon="volumeMediumOutline" class="w-6 h-6" v-else />
            </div>
          </div>
        </div>
      </div>
      <button
        v-if="showNewReplyHint"
        type="button"
        class="sticky bottom-2 left-1/2 -translate-x-1/2 z-10 px-3 py-1.5 rounded-full bg-blue-600 text-white text-sm shadow-md"
        @click="scrollToBottomAndClearHint">
        有新回复 ↓
      </button>
    </ion-content>
  </ion-segment-content>
</template>

<script setup lang="ts">
import {
  IonButton,
  IonContent,
  IonRefresher,
  IonRefresherContent,
  IonSegmentContent,
} from "@ionic/vue";
import { Icon } from "@iconify/vue";
import { volumeMediumOutline } from "ionicons/icons";
import { ref, watch } from "vue";
import EventBus, { C_EVENT } from "@/types/event-bus";
import { getAiChatMessages } from "@/api/api-chat";
import {
  AI_HISTORY_MAX_PAGES,
  AI_HISTORY_PAGE_SIZE,
  oldestHistoryId,
  prependHistoryTurns,
  type DifyHistoryItem,
} from "@/views/page-chat/ai-chat-history";
import { getNetworkErrorMessage } from "@/utils/net-util";
import type { RefresherCustomEvent } from "@ionic/vue";

export type ChatMsgStatus = "thinking" | "streaming" | "done" | "error";

export interface ChatMsg {
  id?: string | number;
  content: string;
  role: string;
  audioSrc?: string;
  playing?: boolean;
  ts?: string;
  type?: string;
  status?: ChatMsgStatus;
  clientRequestId?: string;
  retryText?: string;
}

const props = defineProps<{
  aiConversationId: string;
  userName: string;
}>();

defineEmits<{
  (e: "audio-click", msg: ChatMsg): void;
  (e: "retry", text: string): void;
}>();

const SCROLL_NEAR_BOTTOM_PX = 80;

const contentRef = ref<InstanceType<typeof IonContent> | null>(null);
const messages = ref<ChatMsg[]>([]);
const networkError = ref(false);
const userNearBottom = ref(true);
const showNewReplyHint = ref(false);
/** 已拉到的最旧一条 Dify 消息 id。连续下拉时用它翻页；空回答不展示，但不能停在失败记录上。 */
const historyCursor = ref<string | number | undefined>(undefined);
/** 当前等待中的 AI 回复（占位气泡） */
const activeReplyClientId = ref<string | undefined>(undefined);

watch(
  () => props.aiConversationId,
  () => {
    historyCursor.value = undefined;
  }
);

async function measureNearBottom(): Promise<boolean> {
  const el = await contentRef.value?.$el?.getScrollElement?.();
  if (!el) return true;
  const { scrollTop, scrollHeight, clientHeight } = el;
  return scrollHeight - scrollTop - clientHeight <= SCROLL_NEAR_BOTTOM_PX;
}

function onContentScroll() {
  void measureNearBottom().then((near) => {
    userNearBottom.value = near;
    if (near) showNewReplyHint.value = false;
  });
}

function scrollToBottom(duration = 200) {
  contentRef.value?.$el?.scrollToBottom?.(duration);
}

function scrollToBottomIfNeeded(duration = 200) {
  if (userNearBottom.value) {
    scrollToBottom(duration);
    showNewReplyHint.value = false;
  } else {
    showNewReplyHint.value = true;
  }
}

function scrollToBottomAndClearHint() {
  showNewReplyHint.value = false;
  userNearBottom.value = true;
  scrollToBottom(200);
}

function addMessage(msg: ChatMsg) {
  messages.value.push(msg);
}

function findActiveServerMessage(): ChatMsg | undefined {
  if (activeReplyClientId.value) {
    const byClient = messages.value.find(
      (m) => m.role === "server" && m.clientRequestId === activeReplyClientId.value
    );
    if (byClient) return byClient;
  }
  for (let i = messages.value.length - 1; i >= 0; i--) {
    const m = messages.value[i];
    if (
      m.role === "server" &&
      (m.status === "thinking" || m.status === "streaming")
    ) {
      return m;
    }
  }
  return undefined;
}

function startAwaitingReply(clientRequestId: string, retryText: string) {
  activeReplyClientId.value = clientRequestId;
  messages.value.push({
    role: "server",
    content: "正在思考…",
    status: "thinking",
    clientRequestId,
    retryText,
  });
}

function applyChatChunk(data: { id?: string | number; content?: string }) {
  const chunk = data.content ?? "";
  if (!chunk) return;
  let target = findActiveServerMessage();
  if (data.id !== undefined && data.id !== "") {
    const byId = messages.value.find((m) => m.role === "server" && m.id === data.id);
    if (byId) target = byId;
  }
  if (!target) {
    const msg: ChatMsg = {
      id: data.id,
      content: chunk,
      role: "server",
      status: "streaming",
    };
    addMessage(msg);
    return;
  }
  if (data.id !== undefined && data.id !== "") target.id = data.id;
  if (target.status === "thinking") {
    target.status = "streaming";
    target.content = chunk;
  } else {
    target.content = (target.content ?? "") + chunk;
  }
}

function finishActiveReply() {
  const target = findActiveServerMessage();
  if (target) target.status = "done";
  activeReplyClientId.value = undefined;
}

function failActiveReply(message: string) {
  const target = findActiveServerMessage();
  if (target) {
    target.status = "error";
    target.content = message;
  } else {
    messages.value.push({
      role: "server",
      content: message,
      status: "error",
    });
  }
  activeReplyClientId.value = undefined;
}

/** @deprecated 保留兼容；新逻辑请用 applyChatChunk */
function appendLastMessageContent(text: string) {
  applyChatChunk({ content: text });
}

function getLastMessage(): ChatMsg | undefined {
  return messages.value[messages.value.length - 1];
}

function initialCursor(): string | number | undefined {
  if (historyCursor.value) return historyCursor.value;
  const first = messages.value.find((msg) => msg.id !== undefined && msg.id !== "");
  return first?.id;
}

async function doRefresh(e: RefresherCustomEvent) {
  if (!props.aiConversationId) {
    e.target.complete();
    return;
  }
  networkError.value = false;
  let cursor = initialCursor();
  try {
    for (let page = 0; page < AI_HISTORY_MAX_PAGES; page++) {
      const data = (await getAiChatMessages(
        props.aiConversationId,
        AI_HISTORY_PAGE_SIZE,
        props.userName,
        cursor
      )) as { data?: DifyHistoryItem[]; has_more?: boolean } | null;
      const list = Array.isArray(data?.data) ? data.data : [];
      if (list.length === 0) break;

      const oldest = oldestHistoryId(list);
      if (oldest !== undefined && oldest === cursor) break;
      if (oldest !== undefined) historyCursor.value = oldest;

      const { messages: next, added } = prependHistoryTurns(messages.value, list);
      messages.value = next;
      cursor = historyCursor.value;
      if (added > 0 || !data?.has_more) break;
    }
  } catch (err) {
    networkError.value = true;
    EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
  } finally {
    e.target.complete();
  }
}

function onRefresh(e: RefresherCustomEvent) {
  doRefresh(e);
}

function retryRefresh() {
  networkError.value = false;
  doRefresh({ target: { complete: () => {} } } as RefresherCustomEvent);
}

defineExpose({
  scrollToBottom,
  scrollToBottomIfNeeded,
  addMessage,
  appendLastMessageContent,
  applyChatChunk,
  startAwaitingReply,
  finishActiveReply,
  failActiveReply,
  getLastMessage,
});
</script>
