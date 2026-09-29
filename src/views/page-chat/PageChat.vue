<template>
  <ion-page class="main-bg" id="main-content">
    <ion-header>
      <ion-toolbar>
        <ion-title class="px-2">Tab Chat</ion-title>
        <ion-buttons slot="end">
          <ServerRemoteBadge />
          <ion-button @click="btnChatSettingClk">
            <Icon icon="weui:setting-outlined" class="h-7 w-7" />
          </ion-button>
        </ion-buttons>
      </ion-toolbar>
    </ion-header>

    <ion-segment :value="chatType" @ionChange="handleSegmentChange">
      <ion-segment-button
        :value="CHAT_ROOM"
        content-id="chat"
        layout="icon-start"
        class="text-blue-500">
        <ion-icon :icon="heartOutline" class="h-4 w-4 mr-1"></ion-icon>
        <ion-label>聊天室</ion-label>
      </ion-segment-button>
      <ion-segment-button
        :value="CHAT_AI"
        content-id="aiChat"
        layout="icon-start"
        class="text-blue-500">
        <ion-icon :icon="heartOutline" class="h-4 w-4 mr-1"></ion-icon>
        <ion-label>AI</ion-label>
      </ion-segment-button>
      <ion-segment-button
        :value="CHAT_TTS_TASKS"
        content-id="ttsTasks"
        layout="icon-start"
        class="text-blue-500">
        <ion-icon :icon="megaphoneOutline" class="h-4 w-4 mr-1"></ion-icon>
        <ion-label>TTS</ion-label>
      </ion-segment-button>
    </ion-segment>
    <ion-segment-view :style="{ height: `calc(100% - ${tabsHeight}px)` }">
      <ChatRoomTab
        ref="chatRoomTabRef"
        :chat-room-id="chatSetting.chatRoomId"
        :user-id="String(globalVar.user?.id ?? '')"
        :get-user-info="getUserInfo"
        @audio-click="btnAudioClk" />
      <AiChatTab
        ref="aiChatTabRef"
        :ai-conversation-id="chatSetting.aiConversationId"
        :user-name="globalVar.user.name"
        @audio-click="btnAudioClk"
        @retry="retryAiMessage"
        @retry-voice="onRetryVoice" />
      <TtsTasksTab :active="chatType === CHAT_TTS_TASKS" />
    </ion-segment-view>
    <audio ref="audioRef" style="width: auto" class="m-2"></audio>
    <ion-item v-if="chatType !== CHAT_TTS_TASKS">
      <div class="flex py-2 w-full h-18" v-if="INPUT_TYPE == 'text'">
        <div
          class="w-12 h-auto flex items-center cursor-pointer"
          :class="chatType === CHAT_ROOM ? 'opacity-50 cursor-not-allowed pointer-events-none' : ''"
          @click="btnChangeMode">
          <Icon icon="weui:voice-outlined" class="h-10 w-10" />
        </div>
        <ion-input
          class="flex-1 mr-1"
          v-model="inputText"
          ref="inputRef"
          placeholder="Type a message"
          fill="solid"
          style="--color: #000"
          @keyup.enter="sendTextMessage"
          mode="md" />
        <ion-button
          @click="isWaitingServer ? stopAiGeneration() : sendTextMessage()"
          :disabled="isWaitingServer ? false : !inputText || !socketReady">
          {{ isWaitingServer ? "停止" : "发送" }}
        </ion-button>
      </div>
      <div class="flex py-2 w-full h-18" v-else>
        <div class="w-12 h-auto flex items-center" @click="btnChangeMode">
          <Icon icon="weui:keyboard-outlined" class="h-10 w-10" />
        </div>
        <button
          type="button"
          class="voice-record-button flex-1 mr-1"
          ref="recBtn"
          @pointerdown="startRecording"
          @contextmenu.prevent
          :class="{ 'is-recording': isRecording }"
          :aria-busy="isOpeningRecorder || isStoppingRecorder">
          <Icon icon="mdi:microphone" class="h-6 w-6" />
          <span class="ml-1 text-sm" aria-live="polite">{{
            isOpeningRecorder ? '正在打开麦克风…' : isStoppingRecorder ? '正在处理…' : isRecording ? '松开发送，移出取消' : '按住说话'
          }}</span>
        </button>
      </div>
    </ion-item>
    <ChatSetting
      :is-open="chatSetting.open"
      :ai-conversation-id="chatSetting.aiConversationId"
      :setting-snapshot="chatSettingSnapshot"
      @willDismiss="onChatSettingDismiss" />
  </ion-page>
</template>

<script setup lang="ts">
import ChatRoomTab from "./TabChatRoom.vue";
import AiChatTab from "./TabAiChat.vue";
import TtsTasksTab from "./TabTtsTasks.vue";
import type { ChatMsg as AiChatMsg } from "./ai-chat-types";
import ChatSetting from "./dialogs/ChatSetting.vue";
import ServerRemoteBadge from "@/components/ServerRemoteBadge.vue";
import { Icon } from "@iconify/vue";
import EventBus, { C_EVENT } from "@/types/event-bus";
import { getApiUrl } from "@/api/api-client";
import { getChatSetting, setChatSetting } from "@/api/api-chat";
import { getUserList } from "@/api/api-user";
import { getNetworkErrorMessage } from "@/utils/net-util";
import {
  IonSegment,
  IonSegmentButton,
  IonSegmentView,
  IonToolbar,
  onIonViewDidEnter,
  onIonViewWillLeave,
} from "@ionic/vue";
import { heartOutline, megaphoneOutline } from "ionicons/icons";
import Recorder from "recorder-core/recorder.wav.min";
import io, { Socket } from "socket.io-client";
import { createAiRequestController } from "@/views/page-chat/ai-chat-request-controller";
import { newBubbleKey } from "@/views/page-chat/ai-chat-reply";
import { computed, inject, onBeforeUnmount, onMounted, ref } from "vue";

Recorder.CLog = function () {}; // 屏蔽Recorder的日志输出

const tabsHeight = ref(0);
let observer: MutationObserver | null = null;
let mediaSourceCheckTimer: ReturnType<typeof setInterval> | null = null;

const MSG_TYPE_TRANSLATION = "translation";
const TTS_AUTO = false;
// cSpell: disable-next-line
const TTS_ROLE = "longwan_v3";
const MEDIA_SOURCE_CHECK_MS = 2000;
const SCROLL_TO_BOTTOM_DELAY = 200;
const AI_REPLY_TIMEOUT_MS = 120_000;
const AI_STREAM_IDLE_MS = 60_000;
const AI_SEND_ACK_TIMEOUT_MS = 15_000;
const AI_RETRY_STATUS_TIMEOUT_MS = 8_000;
const AI_ASR_WAIT_MS = 45_000;

const CHAT_ROOM = "chat_room";
const CHAT_AI = "chat_ai";
const CHAT_TTS_TASKS = "tts_tasks";
const chatSetting = ref({
  open: false,
  ttsSpeed: 1.1,
  ttsRole: TTS_ROLE,
  aiConversationId: "",
  chatRoomId: "",
});
const INPUT_TYPE = ref("text");
const inputText = ref("");
const globalVar: any = inject("globalVar");
const inputRef = ref<HTMLElement | null>(null);
const userList = ref<any>([]);

const chatRoomTabRef = ref<InstanceType<typeof ChatRoomTab> | null>(null);
const aiChatTabRef = ref<InstanceType<typeof AiChatTab> | null>(null);

const wsUrl = getApiUrl().replace("api", "");
const recBtn = ref<HTMLButtonElement | null>(null);
const socketRef = ref<Socket>();

const isWaitingServer = ref(false);
const socketHandshakeOk = ref(false);
const socketReady = ref(false);
let aiReplyTimeout: ReturnType<typeof setTimeout> | null = null;
let outboundAckTimeout: ReturnType<typeof setTimeout> | null = null;
let aiWaitStartedAt = 0;
let aiRequestSeq = 0;
const aiRequestController = createAiRequestController();
let pendingVoiceClientRequestId: string | null = null;
let pendingVoiceRetryHint = "";
let pendingOutboundText = "";
/** 一次按住录音从开始到松手共用的 clientRequestId（AI 语音） */
let currentRecordingRequestId: string | null = null;

const chatSettingSnapshot = computed(() => ({
  ttsSpeed: chatSetting.value.ttsSpeed,
  ttsRole: chatSetting.value.ttsRole,
  aiConversationId: chatSetting.value.aiConversationId,
  chatRoomId: chatSetting.value.chatRoomId,
}));
const isRecording = ref(false);
const isOpeningRecorder = ref(false);
const isStoppingRecorder = ref(false);
let recordingPointer: number | null = null;
let recorderDisposed = false;
let recorderOpenAttempt = 0;
let recorderOpenTimeout: ReturnType<typeof setTimeout> | null = null;
const RECORDER_OPEN_TIMEOUT_MS = 15000;
const SAMPLE_RATE = 16000;
const audioRef = ref<HTMLAudioElement | null>(null);
type AudioPlayTarget = Pick<AiChatMsg, "content" | "audioSrc" | "playing" | "id">;
const audioPlayMsg = ref<AudioPlayTarget | null>(null);
const lstAudioSrc = ref<string>("");
let lstAudioObjectUrl: string | null = null;

function setLstAudioBlobUrl(blob: Blob) {
  if (lstAudioObjectUrl) {
    URL.revokeObjectURL(lstAudioObjectUrl);
  }
  lstAudioObjectUrl = URL.createObjectURL(blob);
  lstAudioSrc.value = lstAudioObjectUrl;
}
const chatType = ref(CHAT_AI);
const ttsData = ref<any>({ audioBuffer: null, msg: null, audioEnd: false, mediaSource: null });
const rec = Recorder({
  type: "wav",
  bitRate: 16,
  sampleRate: 16000,
  onProcess: recProcess,
  audioTrackSet: {
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true,
  },
});
let recSampleBuf = new Int16Array();
let playAudioData: ArrayBuffer[] = [];
let activeTtsRequestId: string | null = null;
let ttsRequestSeq = 0;
let ttsMediaObjectUrl: string | null = null;
const chatRequestPollTimers = new Map<string, ReturnType<typeof setInterval>>();
const pendingAiRetryQueries = new Map<
  string,
  { text: string; timer: ReturnType<typeof setTimeout> }
>();

function nextTtsRequestId(): string {
  ttsRequestSeq += 1;
  return `tts-${Date.now()}-${ttsRequestSeq}`;
}

function tryFinalizeTtsPlayback() {
  if (!ttsData.value.audioEnd) return;
  if (playAudioData.length > 0) return;
  const buf = ttsData.value.audioBuffer;
  if (buf?.updating) return;
  const ms = ttsData.value.mediaSource;
  if (ms?.readyState === "open") {
    try {
      ms.endOfStream();
    } catch {
      /* empty */
    }
  }
}

const onAudioEnded = () => {
  if (audioPlayMsg.value) audioPlayMsg.value.playing = false;
  ttsData.value.audioEnd = true;
  ttsData.value.audioBuffer = null;
};

function appendPlayAudioToBuffer() {
  if (
    !ttsData.value.audioBuffer ||
    ttsData.value.audioBuffer.updating ||
    playAudioData.length === 0
  )
    return;
  const combinedBuffer = new Uint8Array(
    playAudioData.reduce((acc, curr) => acc + curr.byteLength, 0)
  );
  let offset = 0;
  playAudioData.forEach((chunk) => {
    combinedBuffer.set(new Uint8Array(chunk), offset);
    offset += chunk.byteLength;
  });
  ttsData.value.audioBuffer.appendBuffer(combinedBuffer);
  playAudioData = [];
  tryFinalizeTtsPlayback();
}

onMounted(async () => {
  const audioEl = audioRef.value;
  if (audioEl) audioEl.addEventListener("ended", onAudioEnded);

  try {
    const setting = await getChatSetting(globalVar.user.id);
    if (setting) {
      const v = JSON.parse(setting);
      chatSetting.value.ttsSpeed = v.ttsSpeed ?? 1.1;
      chatSetting.value.ttsRole = v.ttsRole ?? TTS_ROLE;
      chatSetting.value.aiConversationId = v.aiConversationId;
      chatSetting.value.chatRoomId = v.chatRoomId || "v_chat_room_001";
    } else {
      // 如果没有 setting，设置默认值
      chatSetting.value.chatRoomId = "v_chat_room_001";
    }
  } catch (err) {
    EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
  } finally {
    initSocketIO();
  }

  mediaSourceCheckTimer = setInterval(() => {
    // 不能在 SourceBuffer 仍 updating / 还有待追加音频时直接 endOfStream，
    // 否则长回复或缓存回放容易被截尾。
    tryFinalizeTtsPlayback();
  }, MEDIA_SOURCE_CHECK_MS);

  observer = new MutationObserver(updateTabsHeight);
  observer.observe(document.body, { childList: true, subtree: true });
});

const updateTabsHeight = () => {
  const tabs = document.querySelector("ion-tab-bar");
  if (tabs) {
    tabsHeight.value = tabs.clientHeight;
  }
};

async function updateChatSetting() {
  try {
    const setting = await getChatSetting(globalVar.user.id);
    if (setting) {
      const v = JSON.parse(setting);
      chatSetting.value = Object.assign({}, chatSetting.value, v);
    } else {
      // 如果没有 setting，设置默认值
      chatSetting.value.chatRoomId = "v_chat_room_001";
    }
  } catch (err) {
    EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
  }
}

async function refreshUserList() {
  try {
    const uList = await getUserList();
    userList.value = [...uList.data];
  } catch (err) {
    EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
  }
}

function getUserInfo(userId: string) {
  if (userId === "me") {
    return globalVar.user;
  }
  return userList.value.find((u: any) => u.id === userId);
}

onBeforeUnmount(() => {
  for (const rid of chatRequestPollTimers.keys()) {
    stopChatRequestPoll(rid);
  }
  recorderDisposed = true;
  cancelRecording();
  window.removeEventListener("resize", updateTabsHeight);
  if (observer) {
    observer.disconnect();
    observer = null;
  }
  if (mediaSourceCheckTimer != null) {
    clearInterval(mediaSourceCheckTimer);
    mediaSourceCheckTimer = null;
  }
  clearAiReplyTimeout();
  clearOutboundAckTimeout();
  clearPendingAiRetryQueries();
  const audioEl = audioRef.value;
  if (audioEl) audioEl.removeEventListener("ended", onAudioEnded);
  if (socketRef.value) {
    socketRef.value.removeAllListeners();
    socketRef.value.disconnect();
  }
});

onIonViewWillLeave(cancelRecording);

const hasChatTabEnteredBefore = ref(false);
onIonViewDidEnter(async () => {
  if (hasChatTabEnteredBefore.value) {
    await updateChatSetting();
  } else {
    hasChatTabEnteredBefore.value = true;
  }
  await refreshUserList();
  chatRoomTabRef.value?.loadInitial();
});

function updateSocketReady() {
  socketReady.value = Boolean(socketRef.value?.connected && socketHandshakeOk.value);
}

function clearAiReplyTimeout() {
  if (aiReplyTimeout != null) {
    clearTimeout(aiReplyTimeout);
    aiReplyTimeout = null;
  }
}

function clearOutboundAckTimeout() {
  if (outboundAckTimeout != null) {
    clearTimeout(outboundAckTimeout);
    outboundAckTimeout = null;
  }
}

function syncWaitingFlag() {
  isWaitingServer.value = aiRequestController.isInFlight();
}

function beginOutboundAckWait(clientRequestId: string) {
  clearOutboundAckTimeout();
  syncWaitingFlag();
  outboundAckTimeout = setTimeout(() => {
    if (!aiRequestController.accepts(clientRequestId)) return;
    if (!aiRequestController.isAwaitingServerAck()) return;
    const restored = aiChatTabRef.value?.failUserSend(
      clientRequestId,
      "未收到服务器确认，请检查网络后重试"
    );
    if (restored) {
      inputText.value = restored;
      pendingOutboundText = "";
    }
    aiRequestController.dismiss(clientRequestId, "failed");
    syncWaitingFlag();
    EventBus.$emit(C_EVENT.TOAST, "未收到服务器确认");
  }, AI_SEND_ACK_TIMEOUT_MS);
}

function onMsgAccepted(data: {
  clientRequestId?: string;
  kind?: string;
  attempt?: number;
}) {
  const rid = data.clientRequestId;
  if (!rid || !aiRequestController.accepts(rid)) return;
  if (!aiRequestController.markAccepted(rid, data.attempt)) return;
  clearOutboundAckTimeout();
  aiChatTabRef.value?.confirmUserSent(rid);
  if (data.kind === "text") {
    const rec = aiRequestController.get(rid);
    const retryText = rec?.retryText ?? pendingOutboundText;
    pendingOutboundText = "";
    if (retryText) inputText.value = "";
    aiChatTabRef.value?.ensureAwaitingReply(rid, retryText);
    beginAiWait(rid, AI_STREAM_IDLE_MS);
  } else if (data.kind === "audio") {
    beginAiWait(rid, AI_ASR_WAIT_MS, { asrPhase: true });
  }
  syncWaitingFlag();
  aiChatTabRef.value?.scrollToBottomIfNeeded(SCROLL_TO_BOTTOM_DELAY);
}

function beginAiWait(
  clientRequestId: string,
  timeoutMs = AI_STREAM_IDLE_MS,
  opts?: { asrPhase?: boolean; resetClock?: boolean }
) {
  syncWaitingFlag();
  clearAiReplyTimeout();
  const asrPhase = opts?.asrPhase === true;
  if (opts?.resetClock !== false) aiWaitStartedAt = Date.now();
  aiReplyTimeout = setTimeout(() => {
    if (!aiRequestController.accepts(clientRequestId)) return;
    const overTotal = Date.now() - aiWaitStartedAt >= AI_REPLY_TIMEOUT_MS;
    endAiWait({
      failed: true,
      message: asrPhase
        ? "语音识别超时，请重试"
        : overTotal
          ? "回复超时，请重试"
          : "长时间未收到回复，请重试",
      clientRequestId,
      retryText: asrPhase ? undefined : pendingVoiceRetryHint || undefined,
    });
    if (asrPhase) {
      EventBus.$emit(C_EVENT.TOAST, "语音识别超时");
    } else {
      EventBus.$emit(C_EVENT.TOAST, overTotal ? "AI 回复超时" : "回复似乎已中断");
    }
  }, timeoutMs);
}

function bumpAiReplyIdleTimeout(clientRequestId: string) {
  if (!aiRequestController.accepts(clientRequestId)) return;
  if (Date.now() - aiWaitStartedAt >= AI_REPLY_TIMEOUT_MS) {
    endAiWait({
      failed: true,
      message: "回复超时，请重试",
      clientRequestId,
      retryText: pendingVoiceRetryHint || undefined,
    });
    EventBus.$emit(C_EVENT.TOAST, "AI 回复超时");
    return;
  }
  beginAiWait(clientRequestId, AI_STREAM_IDLE_MS, { resetClock: false });
}

function endAiWait(opts?: {
  failed?: boolean;
  message?: string;
  stopped?: boolean;
  clientRequestId?: string;
  retryText?: string;
}) {
  const rid = opts?.clientRequestId ?? aiRequestController.getActive();
  if (!rid) {
    clearAiReplyTimeout();
    clearOutboundAckTimeout();
    isWaitingServer.value = false;
    return;
  }
  const wasOutbound = aiRequestController.get(rid)?.phase === "outbound";
  clearAiReplyTimeout();
  clearOutboundAckTimeout();
  aiWaitStartedAt = 0;
  if (opts?.failed) {
    aiRequestController.dismiss(rid, "failed");
  } else if (opts?.stopped) {
    aiRequestController.dismiss(rid, "cancelled");
  } else {
    aiRequestController.release(rid);
  }
  syncWaitingFlag();
  const aiTab = aiChatTabRef.value;
  if (opts?.failed) {
    if (wasOutbound) {
      const restored = aiTab?.failUserSend(
        rid,
        opts.message ?? "请求失败，请重试"
      );
      if (restored) inputText.value = restored;
    } else {
      aiTab?.failActiveReply(
        rid,
        opts.message ?? "请求失败，请重试",
        opts.retryText ?? (pendingVoiceRetryHint || undefined)
      );
    }
  } else {
    aiTab?.finishActiveReply(rid, { stopped: opts?.stopped });
  }
  if (pendingVoiceClientRequestId === rid) {
    pendingVoiceClientRequestId = null;
    pendingVoiceRetryHint = "";
  }
  pendingOutboundText = "";
  aiRequestController.purge(rid);
}

function nextAiClientRequestId(): string {
  aiRequestSeq += 1;
  return `ai-${Date.now()}-${aiRequestSeq}`;
}

function stopChatRequestPoll(clientRequestId: string) {
  const timer = chatRequestPollTimers.get(clientRequestId);
  if (timer) clearInterval(timer);
  chatRequestPollTimers.delete(clientRequestId);
}

function startChatRequestPoll(clientRequestId: string) {
  if (!socketRef.value?.connected) return;
  stopChatRequestPoll(clientRequestId);
  chatRequestPollTimers.set(
    clientRequestId,
    setInterval(() => {
      socketRef.value?.emit(
        "queryChatRequest",
        JSON.stringify({ clientRequestIds: [clientRequestId] })
      );
    }, 2000)
  );
}

function clearPendingAiRetryQuery(clientRequestId: string) {
  const pending = pendingAiRetryQueries.get(clientRequestId);
  if (pending) clearTimeout(pending.timer);
  pendingAiRetryQueries.delete(clientRequestId);
}

function clearPendingAiRetryQueries() {
  for (const rid of pendingAiRetryQueries.keys()) {
    clearPendingAiRetryQuery(rid);
  }
}

function beginAiRetryStatusQuery(text: string, clientRequestId: string) {
  const trimmed = text.trim();
  if (!trimmed || pendingAiRetryQueries.has(clientRequestId)) return;
  if (!socketRef.value?.connected || !socketHandshakeOk.value) {
    EventBus.$emit(C_EVENT.TOAST, "聊天服务未就绪，请稍后再试");
    return;
  }
  const timer = setTimeout(() => {
    pendingAiRetryQueries.delete(clientRequestId);
    EventBus.$emit(C_EVENT.TOAST, "无法确认上一条请求状态，请稍后重试");
  }, AI_RETRY_STATUS_TIMEOUT_MS);
  pendingAiRetryQueries.set(clientRequestId, { text: trimmed, timer });
  socketRef.value.emit(
    "queryChatRequest",
    JSON.stringify({ clientRequestIds: [clientRequestId] })
  );
}

/**
 * 手动重试先以服务端状态为准：处理中/完成则恢复原轮次；
 * failed/cancelled 才创建新 attempt；无服务端记录则按原 ID 首次发送。
 */
function handlePendingAiRetryStatus(item: {
  clientRequestId?: string;
  phase?: string | null;
  attempt?: number;
}): boolean {
  const rid = item.clientRequestId;
  if (!rid) return false;
  const pending = pendingAiRetryQueries.get(rid);
  if (!pending) return false;

  const phase = item.phase;
  if (phase && !aiRequestController.acceptsQueryResult(rid, item.attempt, phase)) {
    // 旧快照不能决定重试语义；继续等本次查询的有效结果或超时。
    return true;
  }

  if (!phase) {
    clearPendingAiRetryQuery(rid);
    sendAiText(pending.text, { clientRequestId: rid, requireNewAttempt: false });
    return true;
  }

  if (phase === "failed" || phase === "cancelled") {
    clearPendingAiRetryQuery(rid);
    // 先记住服务端当前轮次，再由明确重试等待服务端确认更大的 attempt。
    aiRequestController.restore(rid, "text", pending.text, item.attempt);
    aiRequestController.markTerminal(rid, phase);
    aiRequestController.purge(rid);
    sendAiText(pending.text, { clientRequestId: rid, requireNewAttempt: true });
    return true;
  }

  // accepted/asr/ai/done 走正常状态恢复，不重新发 message。
  clearPendingAiRetryQuery(rid);
  return false;
}

function syncPendingChatRequestsAfterHandshake() {
  if (chatType.value !== CHAT_AI || !socketRef.value?.connected) return;
  const ids = aiChatTabRef.value?.getPendingClientRequestIds?.() ?? [];
  if (ids.length === 0) return;
  socketRef.value.emit(
    "queryChatRequest",
    JSON.stringify({ clientRequestIds: ids })
  );
}

function applyChatRequestStatusItem(item: {
  clientRequestId?: string;
  phase?: string | null;
  replyText?: string;
  errorMessage?: string;
  attempt?: number;
}) {
  const rid = item.clientRequestId;
  const phase = item.phase;
  if (!rid || !phase) return;
  if (!aiRequestController.acceptsQueryResult(rid, item.attempt, phase)) return;
  const aiTab = aiChatTabRef.value;
  if (!aiTab) return;

  if (phase === "done") {
    stopChatRequestPoll(rid);
    aiRequestController.restore(rid, "text", aiTab.getRequestRetryText(rid), item.attempt);
    aiTab.confirmUserSent(rid);
    if (item.replyText) {
      aiTab.restoreServerReply(rid, item.replyText, true);
    }
    aiTab.finishActiveReply(rid);
    endAiWait({ clientRequestId: rid });
    aiRequestController.purge(rid);
    syncWaitingFlag();
    return;
  }
  if (phase === "failed") {
    stopChatRequestPoll(rid);
    aiRequestController.restore(rid, "text", aiTab.getRequestRetryText(rid), item.attempt);
    const retryText = aiTab.getRequestRetryText(rid);
    aiTab.failActiveReply(rid, item.errorMessage || "生成失败，请重试", retryText);
    endAiWait({ failed: true, message: item.errorMessage || "生成失败", clientRequestId: rid });
    aiRequestController.markTerminal(rid, "failed");
    syncWaitingFlag();
    return;
  }
  if (phase === "cancelled") {
    stopChatRequestPoll(rid);
    aiTab.finishActiveReply(rid, { stopped: true });
    aiRequestController.purge(rid);
    syncWaitingFlag();
    return;
  }
  if (phase === "accepted" || phase === "asr" || phase === "ai") {
    const retryText = aiTab.getRequestRetryText(rid);
    const kind = phase === "asr" ? "voice" : "text";
    if (!aiRequestController.accepts(rid)) {
      aiRequestController.restore(rid, kind, retryText, item.attempt);
    }
    aiRequestController.markAccepted(rid, item.attempt);
    if (phase === "ai") aiRequestController.markAiPhase(rid);
    aiTab.confirmUserSent(rid);
    if (phase !== "asr") {
      aiTab.ensureAwaitingReply(rid, retryText);
    }
    if (item.replyText) {
      aiTab.restoreServerReply(rid, item.replyText, false);
    }
    if (phase === "asr") {
      beginAiWait(rid, AI_ASR_WAIT_MS, { asrPhase: true });
    } else {
      beginAiWait(rid, AI_STREAM_IDLE_MS);
    }
    if (phase === "ai") {
      startChatRequestPoll(rid);
    }
    if (phase !== "ai") {
      EventBus.$emit(C_EVENT.TOAST, "仍在处理上一条消息，请稍候");
    }
  }
}

function onChatRequestStatus(data: {
  items?: {
    clientRequestId?: string;
    phase?: string | null;
    replyText?: string;
    errorMessage?: string;
    attempt?: number;
  }[];
}) {
  const list = Array.isArray(data?.items) ? data.items : [];
  for (const item of list) {
    if (handlePendingAiRetryStatus(item)) continue;
    applyChatRequestStatusItem(item);
  }
}

function emitHandshake() {
  socketHandshakeOk.value = false;
  updateSocketReady();
  const chatConfig = {
    key: "123456",
    ttsAuto: TTS_AUTO,
    ttsRole: chatSetting.value.ttsRole,
    ttsSpeed: chatSetting.value.ttsSpeed,
    ttsVol: 50,
    aiConversationId: chatSetting.value.aiConversationId,
    chatRoomId: chatSetting.value.chatRoomId,
    user: globalVar.user.name,
  };
  socketRef.value!.emit("handshake", chatConfig);
}

function initSocketIO() {
  socketRef.value = io(wsUrl, {
    transports: ["websocket"],
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
    secure: true,
    rejectUnauthorized: false,
  });
  socketRef.value.on("connect", () => {
    emitHandshake();
  });
  socketRef.value.on("message", (data) => {
    console.log("==> message", data);
    if (data.type === MSG_TYPE_TRANSLATION) {
      aiChatTabRef.value?.addMessage({
        bubbleKey: newBubbleKey("srv"),
        id: "",
        content: `Translation: ${data.content}`,
        role: "server",
      });
      isWaitingServer.value = false;
    } else {
      aiChatTabRef.value?.addMessage({
        bubbleKey: newBubbleKey("srv"),
        id: "",
        content: `Unknown: ${JSON.stringify(data)}`,
        role: "server",
      });
    }
    aiChatTabRef.value?.scrollToBottomIfNeeded(SCROLL_TO_BOTTOM_DELAY);
  });
  socketRef.value.on("msgAccepted", (data: { clientRequestId?: string; kind?: string }) => {
    onMsgAccepted(data);
  });
  socketRef.value.on("msgAsr", (data: { content?: string; clientRequestId?: string }) => {
    const rid = data.clientRequestId;
    if (!rid || !aiRequestController.accepts(rid)) return;
    if (!data.content) return;
    aiRequestController.markAiPhase(rid);
    pendingVoiceRetryHint = data.content;
    aiChatTabRef.value?.onAsrResult(rid, data.content, lstAudioSrc.value);
    aiChatTabRef.value?.startAwaitingReply(rid, data.content);
    beginAiWait(rid, AI_STREAM_IDLE_MS);
    aiChatTabRef.value?.scrollToBottomIfNeeded(SCROLL_TO_BOTTOM_DELAY);
  });
  socketRef.value.on("msgChat", async (data) => {
    console.log("==> msgChat", data);
    if (data.chat_type === CHAT_ROOM) {
      chatRoomTabRef.value?.addMessage({
        id: data.id,
        content: data.content,
        role: data.user_id,
        ts: data.ts,
        type: data.type,
      });
    } else {
      if (!aiRequestController.acceptsEvent(data.clientRequestId, data.attempt))
        return;
      bumpAiReplyIdleTimeout(data.clientRequestId);
      aiChatTabRef.value?.applyChatChunk({
        clientRequestId: data.clientRequestId,
        id: data.id,
        content: data.content,
      });
      if (TTS_AUTO) {
        const last = aiChatTabRef.value?.getLastMessage?.();
        if (last?.role === "server") audioPlayMsg.value = last;
      }
      if (data.aiConversationId != chatSetting.value.aiConversationId) {
        chatSetting.value.aiConversationId = data.aiConversationId;
        setChatSetting(globalVar.user.id, JSON.stringify(chatSetting.value));
      }
      aiChatTabRef.value?.scrollToBottomIfNeeded(SCROLL_TO_BOTTOM_DELAY);
    }
  });
  socketRef.value.on(
    "endChat",
    (data: { clientRequestId?: string; chat_type?: string; attempt?: number }) => {
    console.log("==> MSG_TYPE_CHAT_END", data);
    if (!data.clientRequestId) {
      if (chatType.value === CHAT_ROOM) {
        clearAiReplyTimeout();
        isWaitingServer.value = false;
      }
      return;
    }
    if (!aiRequestController.acceptsEvent(data.clientRequestId, data.attempt))
      return;
    endAiWait({ clientRequestId: data.clientRequestId });
    }
  );
  socketRef.value.on("dataAudio", (data: any) => {
    if (data.type === "tts") {
      if (data.ttsRequestId && data.ttsRequestId !== activeTtsRequestId) return;
      const chunk = data.data;
      if (chunk instanceof ArrayBuffer) {
        playAudioData.push(chunk);
        appendPlayAudioToBuffer();
      } else {
        console.warn("未知的数据类型");
      }
    } else {
      console.warn("Unknown bin data", data);
    }
  });
  socketRef.value.on("endAudio", (data: any) => {
    if (data.ttsRequestId && data.ttsRequestId !== activeTtsRequestId) return;
    ttsData.value.audioEnd = true;
    console.log("==> end_audio", data.content);
    tryFinalizeTtsPlayback();
  });
  socketRef.value.on("chatRequestStatus", onChatRequestStatus);
  socketRef.value.on("handshakeResponse", () => {
    socketHandshakeOk.value = true;
    updateSocketReady();
    syncPendingChatRequestsAfterHandshake();
  });
  socketRef.value.on("disconnect", () => {
    console.log("Disconnected from the server.");
    socketHandshakeOk.value = false;
    updateSocketReady();
    const hadRetryQuery = pendingAiRetryQueries.size > 0;
    clearPendingAiRetryQueries();
    const rid = aiRequestController.getActive();
    if (rid) {
      endAiWait({ failed: true, message: "连接已断开，请重试", clientRequestId: rid });
    }
    if (rid || hadRetryQuery) {
      EventBus.$emit(C_EVENT.TOAST, "聊天连接已断开");
    }
  });
  socketRef.value.on(
    "error",
    (error:
      | { type?: string; content?: string; clientRequestId?: string; attempt?: number }
      | string) => {
      console.error("msg error:", error);
      const message =
        typeof error === "string"
          ? error
          : error?.content || "AI 请求出错，请重试";
      const rid =
        typeof error === "string" ? aiRequestController.getActive() : error?.clientRequestId;
      const attempt = typeof error === "string" ? undefined : error?.attempt;
      if (!rid || !aiRequestController.acceptsEvent(rid, attempt)) return;
      endAiWait({ failed: true, message, clientRequestId: rid });
      EventBus.$emit(C_EVENT.TOAST, message);
    }
  );
  socketRef.value.on("close", () => console.log("WebSocket connection closed."));
}

async function handleSegmentChange(event: any) {
  cancelRecording();
  chatType.value = event.detail.value;
}

function sendAiText(
  text: string,
  opts?: {
    showUserBubble?: boolean;
    clientRequestId?: string;
    requireNewAttempt?: boolean;
  }
) {
  const trimmed = text.trim();
  if (!trimmed || isWaitingServer.value) return false;
  if (!socketRef.value?.connected || !socketHandshakeOk.value) {
    EventBus.$emit(C_EVENT.TOAST, "聊天服务未就绪，请稍后再试");
    return false;
  }
  const reuseId = opts?.clientRequestId?.trim();
  const clientRequestId = reuseId || nextAiClientRequestId();
  const isResend = Boolean(reuseId);
  aiRequestController.register(clientRequestId, "text", trimmed, {
    requireNewAttempt: Boolean(opts?.requireNewAttempt),
  });
  pendingOutboundText = trimmed;
  pendingVoiceRetryHint = trimmed;
  if (isResend) {
    aiChatTabRef.value?.prepareForResend(clientRequestId, trimmed);
  } else if (opts?.showUserBubble !== false) {
    aiChatTabRef.value?.addMessage({
      bubbleKey: newBubbleKey("me"),
      content: trimmed,
      role: "me",
      clientRequestId,
      status: "sending",
    });
  }
  aiChatTabRef.value?.scrollToBottomIfNeeded(SCROLL_TO_BOTTOM_DELAY);
  const message = JSON.stringify({
    type: "text",
    content: trimmed,
    chatType: CHAT_AI,
    roomId: chatSetting.value.chatRoomId,
    userId: globalVar.user.id,
    clientRequestId,
  });
  socketRef.value!.emit("message", message);
  beginOutboundAckWait(clientRequestId);
  return true;
}

function retryAiMessage(text: string, clientRequestId?: string) {
  if (isWaitingServer.value) return;
  const rid = clientRequestId?.trim();
  if (!rid) {
    sendAiText(text);
    return;
  }
  beginAiRetryStatusQuery(text, rid);
}

function onRetryVoice() {
  if (isWaitingServer.value) return;
  INPUT_TYPE.value = "voice";
  EventBus.$emit(C_EVENT.TOAST, "请重新按住说话");
}

function stopAiGeneration() {
  const rid = aiRequestController.getActive();
  if (!rid || !isWaitingServer.value) return;
  socketRef.value?.emit(
    "chatCancel",
    JSON.stringify({ clientRequestId: rid })
  );
  endAiWait({ stopped: true, clientRequestId: rid });
}

const sendTextMessage = () => {
  if (!inputText.value || isWaitingServer.value) return;
  if (chatType.value === CHAT_AI) {
    const text = inputText.value;
    sendAiText(text);
    return;
  }
  if (!socketRef.value?.connected || !socketHandshakeOk.value) {
    EventBus.$emit(C_EVENT.TOAST, "聊天服务未就绪，请稍后再试");
    return;
  }
  chatRoomTabRef.value?.addMessage({
    id: "",
    content: inputText.value,
    role: globalVar.user.id,
  });
  chatRoomTabRef.value?.scrollToBottom(SCROLL_TO_BOTTOM_DELAY);
  const message = JSON.stringify({
    type: "text",
    content: inputText.value,
    chatType: chatType.value,
    roomId: chatSetting.value.chatRoomId,
    userId: globalVar.user.id,
  });
  inputText.value = "";
  isWaitingServer.value = true;
  socketRef.value!.emit("message", message);
};

function sendAudioData(
  data: string,
  finish: boolean = false,
  cancel = false,
  clientRequestId?: string
) {
  if (!socketRef.value?.connected) {
    console.warn("WebSocket未连接，稍后重试");
    return;
  }
  const message = JSON.stringify({
    type: "audio",
    sample: SAMPLE_RATE,
    content: data,
    finish: finish,
    cancel: cancel,
    ...(clientRequestId ? { clientRequestId } : {}),
  });
  socketRef.value!.emit("message", message);
}

function clearRecordingPointer() {
  recordingPointer = null;
  window.removeEventListener('pointerup', onRecordingPointerUp, true);
  window.removeEventListener('pointercancel', onRecordingPointerCancel, true);
  window.removeEventListener('pointermove', onRecordingPointerMove, true);
  window.removeEventListener('blur', cancelRecording);
  document.removeEventListener('visibilitychange', onRecordingVisibilityChange);
}

function clearRecorderOpenTimeout() {
  if (recorderOpenTimeout !== null) {
    clearTimeout(recorderOpenTimeout);
    recorderOpenTimeout = null;
  }
}

function cancelOpeningRecorder() {
  if (!isOpeningRecorder.value) return false;
  recorderOpenAttempt += 1;
  clearRecorderOpenTimeout();
  isOpeningRecorder.value = false;
  try {
    rec.close();
  } catch (error) {
    console.warn('==> close opening recorder failed', error);
  }
  return true;
}

function abortActiveVoiceRequest(requestId?: string | null) {
  const id = requestId ?? currentRecordingRequestId;
  if (!id) return;
  if (aiRequestController.accepts(id)) {
    aiRequestController.dismiss(id, "cancelled");
    syncWaitingFlag();
  }
}

function cancelRecording() {
  clearRecordingPointer();
  if (cancelOpeningRecorder()) return;
  stopRecording(true);
}

function onRecordingVisibilityChange() {
  if (document.hidden) cancelRecording();
}

function onRecordingPointerUp(event: PointerEvent) {
  if (event.pointerId !== recordingPointer) return;
  clearRecordingPointer();
  if (cancelOpeningRecorder()) return;
  stopRecording();
}

function onRecordingPointerCancel(event: PointerEvent) {
  if (event.pointerId === recordingPointer) cancelRecording();
}

function onRecordingPointerMove(event: PointerEvent) {
  if (event.pointerId !== recordingPointer) return;
  const rect = recBtn.value?.getBoundingClientRect();
  const tolerance = 40;
  if (rect && (event.clientX < rect.left - tolerance || event.clientX > rect.right + tolerance ||
    event.clientY < rect.top - tolerance || event.clientY > rect.bottom + tolerance)) {
    cancelRecording();
  }
}

function startRecording(event: PointerEvent) {
  if (!event.isPrimary || event.button !== 0) return;
  event.preventDefault();
  if (isOpeningRecorder.value || isStoppingRecorder.value || isRecording.value) return;
  if (isWaitingServer.value) {
    EventBus.$emit(C_EVENT.TOAST, '正在等待回复，请稍后再录音');
    return;
  }
  if (!window.isSecureContext) {
    EventBus.$emit(C_EVENT.TOAST, '当前页面不是安全连接，请使用 HTTPS 地址打开后录音');
    return;
  }
  if (!socketReady.value) {
    EventBus.$emit(C_EVENT.TOAST, '聊天服务未就绪，请稍后再录音');
    return;
  }
  recordingPointer = event.pointerId;
  const openAttempt = ++recorderOpenAttempt;
  isOpeningRecorder.value = true;
  // 在异步权限请求前监听松手，避免授权完成后开始一次已经结束的按压。
  window.addEventListener('pointerup', onRecordingPointerUp, true);
  window.addEventListener('pointercancel', onRecordingPointerCancel, true);
  window.addEventListener('pointermove', onRecordingPointerMove, true);
  window.addEventListener('blur', cancelRecording);
  document.addEventListener('visibilitychange', onRecordingVisibilityChange);
  const settleOpening = () => {
    if (openAttempt !== recorderOpenAttempt) return false;
    clearRecorderOpenTimeout();
    isOpeningRecorder.value = false;
    return true;
  };
  const fail = (message: unknown, denied = false) => {
    if (!settleOpening()) return;
    clearRecordingPointer();
    isRecording.value = false;
    rec.close();
    if (!recorderDisposed) EventBus.$emit(C_EVENT.TOAST, denied
      ? '麦克风权限被拒绝，请在浏览器或系统设置中允许麦克风访问'
      : `无法开始录音：${String(message)}`);
  };
  recorderOpenTimeout = setTimeout(() => {
    fail('打开麦克风超时，请检查浏览器或系统麦克风权限后重试');
  }, RECORDER_OPEN_TIMEOUT_MS);
  try {
    rec.open(() => {
      if (!settleOpening()) {
        rec.close();
        return;
      }
      if (recordingPointer === null || recorderDisposed) {
        rec.close();
        if (!recorderDisposed) EventBus.$emit(C_EVENT.TOAST, '麦克风已就绪，请重新按住说话');
        return;
      }
      try {
        recSampleBuf = new Int16Array();
        rec.start();
        isRecording.value = true;
        if (chatType.value === CHAT_AI) {
          currentRecordingRequestId = nextAiClientRequestId();
          aiRequestController.register(currentRecordingRequestId, "voice");
          syncWaitingFlag();
        }
      } catch (error) {
        fail(error);
      }
    }, fail);
  } catch (error) {
    fail(error);
  }
}

function recProcess(buffer: any, powerLevel: any, bufferDuration: any, bufferSampleRate: any) {
  const data_48k = buffer[buffer.length - 1];
  const array_48k = new Array(data_48k);
  const data_16k = Recorder.SampleData(array_48k, bufferSampleRate, SAMPLE_RATE).data;

  recSampleBuf = Int16Array.from([...recSampleBuf, ...data_16k]);
  const chunk_size = 960;
  while (recSampleBuf.length >= chunk_size) {
    const sendBuf = recSampleBuf.slice(0, chunk_size);
    recSampleBuf = recSampleBuf.slice(chunk_size, recSampleBuf.length);
    const uint8 = new Uint8Array(sendBuf.buffer);
    const base64Data = btoa(String.fromCharCode(...uint8));
    sendAudioData(
      base64Data,
      false,
      false,
      currentRecordingRequestId ?? undefined
    );
  }
}

function stopRecording(cancel = false) {
  if (isRecording.value === false) return;
  isRecording.value = false;
  isStoppingRecorder.value = true;
  console.log("==> stopRecording", cancel);
  rec.stop(
    (blob: Blob) => {
      setLstAudioBlobUrl(blob);
      if (recSampleBuf.length) {
        const sendBuf = recSampleBuf;
        recSampleBuf = new Int16Array();
        const uint8 = new Uint8Array(sendBuf.buffer);
        const base64Data = btoa(String.fromCharCode(...uint8));
        sendAudioData(
          base64Data,
          false,
          false,
          currentRecordingRequestId ?? undefined
        );
      }
      const voiceRequestId = currentRecordingRequestId;
      currentRecordingRequestId = null;
      if (cancel && voiceRequestId) {
        abortActiveVoiceRequest(voiceRequestId);
      }
      if (!cancel && chatType.value === CHAT_AI && voiceRequestId) {
        pendingVoiceClientRequestId = voiceRequestId;
        pendingVoiceRetryHint = "";
        aiChatTabRef.value?.startVoiceRecognizing(voiceRequestId, lstAudioSrc.value);
        aiChatTabRef.value?.scrollToBottomIfNeeded(SCROLL_TO_BOTTOM_DELAY);
        if (aiRequestController.isAwaitingServerAck()) {
          beginOutboundAckWait(voiceRequestId);
        }
      }
      sendAudioData("", true, cancel, voiceRequestId ?? undefined);
      if (TTS_AUTO && !cancel) {
        streamAudio(() => {});
      }
      rec.close();
      isStoppingRecorder.value = false;
    },
    (errMsg: any) => {
      const voiceRequestId = currentRecordingRequestId;
      currentRecordingRequestId = null;
      sendAudioData("", true, true, voiceRequestId ?? undefined);
      recSampleBuf = new Int16Array();
      rec.close();
      isStoppingRecorder.value = false;
      if (voiceRequestId) abortActiveVoiceRequest(voiceRequestId);
      if (!cancel && !recorderDisposed) {
        EventBus.$emit(C_EVENT.TOAST, `录音失败：${errMsg}`);
      }
    }
  );
}

async function btnAudioClk(msg: AudioPlayTarget) {
  if (isWaitingServer.value) return;
  console.log("==> playAudio", msg);
  if (msg.playing) {
    msg.playing = false;
    stopAndClearAudio();
  } else {
    stopAndClearAudio();
    msg.playing = true;
    audioPlayMsg.value = msg;
    if (msg.audioSrc) {
      audioRef.value!.src = msg.audioSrc;
      audioRef.value!.play();
    } else {
      ttsData.value.msg = msg;
      activeTtsRequestId = nextTtsRequestId();
      const payload = JSON.stringify({
        content: msg.content,
        role: chatSetting.value.ttsRole,
        speed: chatSetting.value.ttsSpeed,
        id: msg.id,
        ttsRequestId: activeTtsRequestId,
      });
      streamAudio(() => {
        socketRef.value!.emit("tts", payload);
      });
    }
  }
}

function revokeTtsMediaObjectUrl() {
  if (ttsMediaObjectUrl) {
    URL.revokeObjectURL(ttsMediaObjectUrl);
    ttsMediaObjectUrl = null;
  }
}

async function stopAndClearAudio() {
  activeTtsRequestId = null;
  playAudioData = [];
  revokeTtsMediaObjectUrl();
  if (audioRef.value) {
    try {
      audioRef.value.pause();
      audioRef.value!.src = "";
    } catch (e) {
      /* empty */
    }
  }
  const sourceBuffer = ttsData.value.audioBuffer;
  if (sourceBuffer) {
    console.log("==> ttsCancel");
    socketRef.value!.emit("ttsCancel", {});
  }
  if (audioPlayMsg.value) {
    audioPlayMsg.value.playing = false;
  }
  audioPlayMsg.value = null;
  if (ttsData.value.mediaSource) {
    if (ttsData.value.mediaSource.readyState === "open") {
      try {
        if (!sourceBuffer?.updating) {
          ttsData.value.mediaSource.endOfStream();
        }
      } catch {
        /* 中止播放时 MediaSource/SourceBuffer 可能正切换状态，忽略即可。 */
      }
    }
    ttsData.value.mediaSource = null;
  }
  ttsData.value.audioBuffer = null;
}

function streamAudio(f = () => {}) {
  revokeTtsMediaObjectUrl();
  const mediaSource = new MediaSource();
  audioRef.value!.pause();
  ttsMediaObjectUrl = URL.createObjectURL(mediaSource);
  audioRef.value!.src = ttsMediaObjectUrl;
  playAudioData = [];
  ttsData.value.audioEnd = false;
  ttsData.value.mediaSource = mediaSource;

  mediaSource.addEventListener("sourceopen", () => {
    ttsData.value.audioBuffer = mediaSource.addSourceBuffer("audio/mpeg");
    ttsData.value.audioBuffer.addEventListener("error", (e: any) => {
      console.error("SourceBuffer 错误:", e);
    });
    ttsData.value.audioBuffer.addEventListener("updateend", () => {
      appendPlayAudioToBuffer();
      tryFinalizeTtsPlayback();
    });
    try {
      audioRef.value!.play();
    } catch (e) {
      /* empty */
    }
    f();
  });
}

function btnChangeMode() {
  cancelRecording();
  if (INPUT_TYPE.value == "text") {
    INPUT_TYPE.value = "voice";
  } else {
    INPUT_TYPE.value = "text";
  }
}

function btnChatSettingClk() {
  chatSetting.value.open = true;
}

async function onChatSettingDismiss(e: any) {
  if (e.detail.role === "confirm") {
    await updateChatSetting();
    if (socketRef.value?.connected) {
      socketRef.value.emit("config", {
        ttsSpeed: chatSetting.value.ttsSpeed,
        ttsRole: chatSetting.value.ttsRole,
        aiConversationId: chatSetting.value.aiConversationId,
        chatRoomId: chatSetting.value.chatRoomId,
      });
    }
  }
  chatSetting.value.open = false;
}
</script>

<style scoped>
.voice-record-button {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  border-radius: 4px;
  background: var(--ion-color-primary);
  color: var(--ion-color-primary-contrast);
  touch-action: none;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
}
.voice-record-button.is-recording {
  background: var(--ion-color-warning);
  color: var(--ion-color-warning-contrast);
}
</style>
