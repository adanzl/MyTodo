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
    <ion-segment-view :style="segmentViewStyle">
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
    <!-- 待处理图片预览条：只做本地预览，尚未接入上传/发送。
         input 必须在 v-if 之外，否则没有图片时 ref 为空、点按钮无法拉起选择器。 -->
    <input
      ref="imageInputRef"
      type="file"
      accept="image/*"
      multiple
      class="hidden"
      @change="onImageFileChange" />
    <div
      v-if="showImagePreview"
      class="h-20 shrink-0 w-full flex items-center gap-2 px-2 overflow-x-auto bg-gray-200"
      data-testid="pending-image-strip">
      <div
        v-for="(item, idx) in pendingImages"
        :key="item.previewUrl"
        class="relative w-16 h-16 shrink-0"
        :title="item.error || item.file.name">
        <img
          :src="item.previewUrl"
          :alt="item.file.name"
          class="w-full h-full object-cover rounded-md border cursor-zoom-in"
          :class="item.error ? 'border-red-500' : 'border-gray-300'"
          @click="openPendingPreview(idx)" />
        <div
          v-if="item.uploading"
          class="absolute inset-0 rounded-md bg-black/40 flex items-center justify-center pointer-events-none">
          <div class="w-5 h-5 rounded-full border-2 border-white/70 border-t-transparent animate-spin"></div>
        </div>
        <!-- 失败时整块可点：重试上传。发送时会被拦住并提示，但用户需要一个恢复入口，
             否则只能删掉重选（重选还会多出一项）。 -->
        <button
          v-else-if="item.error"
          type="button"
          class="absolute inset-0 rounded-md bg-red-600/85 text-white text-[10px] leading-tight flex items-center justify-center"
          aria-label="重试上传"
          data-testid="retry-upload-button"
          :title="item.error"
          @click="btnRetryUpload(idx)">
          重试
        </button>
        <button
          type="button"
          class="absolute top-0 right-0 w-5 h-5 rounded-full bg-black/70 text-white flex items-center justify-center"
          aria-label="移除图片"
          @click="btnRemovePendingImage(idx)">
          <ion-icon :icon="closeOutline" class="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
    <ChatImagePreview
      v-model:is-open="pendingPreview.open"
      v-model:index="pendingPreview.index"
      :images="pendingPreviewImages" />
    <audio ref="audioRef" class="sr-only" aria-hidden="true" tabindex="-1" />
    <ion-item
      v-if="chatType !== CHAT_TTS_TASKS"
      lines="none"
      class="h-14 max-h-14 shrink-0 [--background:var(--color-gray-200)] [--min-height:0]! [--padding-top:0] [--padding-bottom:0] [--inner-padding-top:0] [--inner-padding-bottom:0] [&::part(native)]:h-full! [&::part(native)]:min-h-0! [&::part(native)]:py-0">
      <div class="flex h-full w-full items-center" v-if="INPUT_TYPE == 'text'">
        <div
          class="w-12 flex items-center cursor-pointer"
          :class="chatType === CHAT_ROOM ? 'opacity-50 cursor-not-allowed pointer-events-none' : ''"
          @click="btnChangeMode">
          <Icon icon="weui:voice-outlined" class="h-10 w-10" />
        </div>
        <ion-input
          class="min-h-10! min-w-0 flex-1 mr-1 text-sm [--color:#000] [--padding-top:6px] [--padding-bottom:6px] [--padding-start:10px] [--padding-end:10px]"
          v-model="inputText"
          ref="inputRef"
          placeholder="Type a message"
          fill="solid"
          @keyup.enter="sendTextMessage"
          mode="md" />
        <ion-button
          class="m-0 h-10 min-h-10! mr-1 shrink-0"
          @click="isWaitingServer ? stopAiGeneration() : sendTextMessage()"
          :disabled="isWaitingServer ? false : !inputText || !socketReady">
          {{ isWaitingServer ? "停止" : "发送" }}
        </ion-button>
        <!-- 与「发送」成对：同样是 ion-button，圆角/高度/按压反馈才一致；
             用 outline 与实心的发送按钮区分主次，避免两个实心块抢视觉 -->
        <ion-button
          fill="outline"
          class="m-0 h-10 min-h-10! w-10 shrink-0 [--padding-start:0] [--padding-end:0]"
          aria-label="添加图片"
          data-testid="pick-image-button"
          @click="pickImages">
          <ion-icon slot="icon-only" :icon="imageOutline" class="h-5 w-5" />
        </ion-button>
      </div>
      <div class="flex h-full w-full items-center" v-else>
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
import ChatImagePreview from "./ChatImagePreview.vue";
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
import { closeOutline, heartOutline, imageOutline, megaphoneOutline } from "ionicons/icons";
import Recorder from "recorder-core/recorder.wav.min";
import io, { Socket } from "socket.io-client";
import { createAiRequestController } from "@/views/page-chat/ai-chat-request-controller";
import { newBubbleKey } from "@/views/page-chat/ai-chat-reply";
import {
  addPendingImages,
  buildChatImageName,
  clearPendingImages,
  DEFAULT_MAX_PENDING_IMAGES,
  discardPendingImages,
  hasFailedImages,
  hasUploadingImages,
  normalizeMaxImages,
  readyImageFilenames,
  removePendingImage,
  type PendingImage,
} from "@/views/page-chat/chat-image-picker";
import { deletePicFile, uploadPic } from "@/api/api-pic";
import { getAccessToken } from "@/utils/auth-util";
import { resizeImageToFile } from "@/utils/img-mgr";
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
// 只发图片、不打字时的占位文案（与后端 chat_mgr.EMPTY_QUERY_PLACEHOLDER 保持一致）：
// Dify 的 query 不允许为空，这个文案会作为该轮的提问进入历史。
const EMPTY_QUERY_PLACEHOLDER = "[图片]";

const CHAT_ROOM = "chat_room";
const CHAT_AI = "chat_ai";
const CHAT_TTS_TASKS = "tts_tasks";
const chatSetting = ref({
  open: false,
  ttsSpeed: 1.1,
  ttsRole: TTS_ROLE,
  aiConversationId: "",
  chatRoomId: "",
  /** 单次对话可发图片数上限；存在 setting 里，无 UI，改的是数据 */
  maxImages: DEFAULT_MAX_PENDING_IMAGES,
});
const INPUT_TYPE = ref("text");
const inputText = ref("");
const globalVar: any = inject("globalVar");
const inputRef = ref<HTMLElement | null>(null);
const userList = ref<any>([]);

/** 已选中待处理的图片（当前只做本地预览，未接入上传/发送） */
const pendingImages = ref<PendingImage[]>([]);
const imageInputRef = ref<HTMLInputElement | null>(null);
/** 预览条的实际高度（h-20 = 80px），用于同步压缩上方消息区高度 */
const IMAGE_PREVIEW_STRIP_HEIGHT = 80;
const showImagePreview = computed(
  () => pendingImages.value.length > 0 && chatType.value !== CHAT_TTS_TASKS
);

/** 待发图片的数量上限，取自 chat setting（无 UI，改数据即可生效） */
const pendingImageLimit = computed(() =>
  normalizeMaxImages(chatSetting.value.maxImages)
);

/** 待发图片的大图预览状态（索引对应 pendingImages） */
const pendingPreview = ref({ open: false, index: 0 });
const pendingPreviewImages = computed(() =>
  pendingImages.value.map((item) => ({
    src: item.previewUrl,
    alt: item.file.name,
  }))
);
const segmentViewStyle = computed(() => ({
  height: `calc(100% - ${
    tabsHeight.value + (showImagePreview.value ? IMAGE_PREVIEW_STRIP_HEIGHT : 0)
  }px)`,
}));

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

/**
 * 传给 ChatSetting 弹窗的快照：弹窗会把「服务端现有值 + 本快照」合并后整体写回，
 * 所以**不要**把只想当数据用的字段（如 `maxImages`）放进来——放进来就等于用内存里的
 * 旧值覆写服务端的新值。`maxImages` 因此只由 updateChatSetting / backfill 维护。
 */
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
type AudioPlayTarget = Pick<
  AiChatMsg,
  "content" | "audioSrc" | "audioLoading" | "playing" | "id"
>;
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
  { text: string; images: string[]; timer: ReturnType<typeof setTimeout> }
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
  if (audioPlayMsg.value) {
    audioPlayMsg.value.playing = false;
    audioPlayMsg.value.audioLoading = false;
  }
  ttsData.value.audioEnd = true;
  ttsData.value.audioBuffer = null;
};

function markTtsPlaybackStarted() {
  if (!audioPlayMsg.value?.audioLoading) return;
  audioPlayMsg.value.audioLoading = false;
  audioPlayMsg.value.playing = true;
}

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
      await backfillMaxImages(v);
    } else {
      // 如果没有 setting，设置默认值
      chatSetting.value.chatRoomId = "v_chat_room_001";
    }
  } catch (err) {
    EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
  }
}

/**
 * `maxImages` 只存在于设置数据里、没有 UI，所以旧数据里不会有这个键。
 * 缺失时补写一次，让它成为可读可改的数据，而不是只藏在代码常量里。
 *
 * 非关键路径：写失败也不影响本次使用（内存里已有默认值），因此只记日志。
 */
async function backfillMaxImages(raw: Record<string, unknown>) {
  if (raw.maxImages !== undefined) return;
  try {
    await setChatSetting(
      globalVar.user.id,
      JSON.stringify({ ...raw, maxImages: pendingImageLimit.value })
    );
  } catch (err) {
    console.warn("补写 chat setting 的 maxImages 失败:", err);
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
  // 组件销毁后这些图片不可能再被发送，服务器上的副本一并删掉
  discardAllPendingImages();
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

function beginAiRetryStatusQuery(
  text: string,
  clientRequestId: string,
  images: string[] = []
) {
  const trimmed = text.trim();
  // 只发图片不打字的轮次，text 是占位文案，同样允许重试
  if ((!trimmed && images.length === 0) || pendingAiRetryQueries.has(clientRequestId)) {
    return;
  }
  if (!socketRef.value?.connected || !socketHandshakeOk.value) {
    EventBus.$emit(C_EVENT.TOAST, "聊天服务未就绪，请稍后再试");
    return;
  }
  const timer = setTimeout(() => {
    pendingAiRetryQueries.delete(clientRequestId);
    EventBus.$emit(C_EVENT.TOAST, "无法确认上一条请求状态，请稍后重试");
  }, AI_RETRY_STATUS_TIMEOUT_MS);
  pendingAiRetryQueries.set(clientRequestId, { text: trimmed, images, timer });
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
    sendAiText(pending.text, {
      clientRequestId: rid,
      requireNewAttempt: false,
      imageFilenames: pending.images,
    });
    return true;
  }

  if (phase === "failed" || phase === "cancelled") {
    clearPendingAiRetryQuery(rid);
    // 先记住服务端当前轮次，再由明确重试等待服务端确认更大的 attempt。
    aiRequestController.restore(rid, "text", pending.text, item.attempt);
    aiRequestController.markTerminal(rid, phase);
    aiRequestController.purge(rid);
    sendAiText(pending.text, {
      clientRequestId: rid,
      requireNewAttempt: true,
      imageFilenames: pending.images,
    });
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
        ...(Array.isArray(data.files) && data.files.length > 0
          ? {
              images: data.files
                .map((f: any) => (typeof f === "string" ? f : f?.filename))
                .filter((n: any): n is string => Boolean(n)),
            }
          : {}),
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
        markTtsPlaybackStarted();
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
    if (audioPlayMsg.value?.audioLoading) {
      audioPlayMsg.value.audioLoading = false;
      audioPlayMsg.value.playing = false;
    }
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
    imageFilenames?: string[];
  }
) {
  const trimmed = text.trim();
  // 只发图片、不打字是允许的，所以「有没有内容」要把图片算进去
  const images = opts?.imageFilenames ?? [];
  const hasImages = images.length > 0;
  if ((!trimmed && !hasImages) || isWaitingServer.value) return false;
  if (!socketRef.value?.connected || !socketHandshakeOk.value) {
    EventBus.$emit(C_EVENT.TOAST, "聊天服务未就绪，请稍后再试");
    return false;
  }
  // 服务端会做同样兜底（Dify 的 query 不允许为空），这里先填好，保证气泡与历史一致
  const content = trimmed || EMPTY_QUERY_PLACEHOLDER;
  const reuseId = opts?.clientRequestId?.trim();
  const clientRequestId = reuseId || nextAiClientRequestId();
  const isResend = Boolean(reuseId);
  aiRequestController.register(clientRequestId, "text", content, {
    requireNewAttempt: Boolean(opts?.requireNewAttempt),
  });
  pendingOutboundText = content;
  pendingVoiceRetryHint = content;
  if (isResend) {
    aiChatTabRef.value?.prepareForResend(clientRequestId, content);
  } else if (opts?.showUserBubble !== false) {
    aiChatTabRef.value?.addMessage({
      bubbleKey: newBubbleKey("me"),
      content,
      role: "me",
      clientRequestId,
      status: "sending",
      images: hasImages ? images : undefined,
    });
  }
  aiChatTabRef.value?.scrollToBottomIfNeeded(SCROLL_TO_BOTTOM_DELAY);
  const message = JSON.stringify({
    type: "text",
    content,
    chatType: CHAT_AI,
    roomId: chatSetting.value.chatRoomId,
    userId: globalVar.user.id,
    clientRequestId,
    // 只传文件名；服务端据此把图片换成 Dify 的文件 id
    files: hasImages ? images.map((filename) => ({ type: "image", filename })) : [],
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
  // 图片在发送时就从输入区清空了，气泡上的 images 是唯一凭证：
  // 不带回去的话，重试会变成"只有文字、没有图片"。
  const images = aiChatTabRef.value?.getRequestImages?.(rid) ?? [];
  beginAiRetryStatusQuery(text, rid, images);
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
  if (chatType.value === CHAT_AI) {
    if (isWaitingServer.value) return;
    if (hasUploadingImages(pendingImages.value)) {
      EventBus.$emit(C_EVENT.TOAST, "图片还在上传，请稍候");
      return;
    }
    if (hasFailedImages(pendingImages.value)) {
      EventBus.$emit(C_EVENT.TOAST, "有图片上传失败，请先移除后再发送");
      return;
    }
    const images = readyImageFilenames(pendingImages.value);
    if (!inputText.value.trim() && images.length === 0) return;
    const sent = sendAiText(inputText.value, { imageFilenames: images });
    // 图片已在气泡里可见，发送后即从待发区移除（重试只重发文本，不重发图片）
    if (sent && images.length > 0) clearPendingImages(pendingImages.value);
    return;
  }
  if (isWaitingServer.value) return;
  if (!socketRef.value?.connected || !socketHandshakeOk.value) {
    EventBus.$emit(C_EVENT.TOAST, "聊天服务未就绪，请稍后再试");
    return;
  }
  // 聊天室同样支持发图：图片已在选图时上传到本服务，这里只把文件名广播出去，
  // 对端收到后拼 /pic/view?name= 渲染（与 AI 对话共用同一套上传/预览链路）。
  if (hasUploadingImages(pendingImages.value)) {
    EventBus.$emit(C_EVENT.TOAST, "图片还在上传，请稍候");
    return;
  }
  if (hasFailedImages(pendingImages.value)) {
    EventBus.$emit(C_EVENT.TOAST, "有图片上传失败，请先移除后再发送");
    return;
  }
  const images = readyImageFilenames(pendingImages.value);
  if (!inputText.value && images.length === 0) return;
  chatRoomTabRef.value?.addMessage({
    id: "",
    content: inputText.value,
    role: globalVar.user.id,
    ...(images.length > 0 ? { images } : {}),
  });
  chatRoomTabRef.value?.scrollToBottom(SCROLL_TO_BOTTOM_DELAY);
  const message = JSON.stringify({
    type: "text",
    content: inputText.value,
    chatType: chatType.value,
    roomId: chatSetting.value.chatRoomId,
    userId: globalVar.user.id,
    files: images.map((filename) => ({ type: "image", filename })),
  });
  inputText.value = "";
  // 图片已进入气泡，从待发区移除（不删服务器文件：已被消息引用）
  if (images.length > 0) clearPendingImages(pendingImages.value);
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
  if (msg.playing || msg.audioLoading) {
    msg.playing = false;
    msg.audioLoading = false;
    stopAndClearAudio();
  } else {
    stopAndClearAudio();
    audioPlayMsg.value = msg;
    if (msg.audioSrc) {
      msg.playing = true;
      audioRef.value!.src = msg.audioSrc;
      audioRef.value!.play();
    } else {
      msg.audioLoading = true;
      msg.playing = false;
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
    audioPlayMsg.value.audioLoading = false;
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

/**
 * 拉起系统图片选择：手机上同时提供「拍照 / 相册」，PC 上弹出文件选择框。
 * 由隐藏的 file input 承担，点击必须发生在用户手势内，否则 iOS 会拦截。
 */
function pickImages() {
  imageInputRef.value?.click();
}

function onImageFileChange(e: Event) {
  const input = e.target as HTMLInputElement;
  const files = Array.from(input.files ?? []);
  // 立即清空，否则再次选择同一张图片不会触发 change
  input.value = "";
  if (files.length === 0) return;

  const { added, rejected, overflow } = addPendingImages(
    pendingImages.value,
    files,
    undefined,
    pendingImageLimit.value
  );
  if (rejected > 0) EventBus.$emit(C_EVENT.TOAST, "只能添加图片文件");
  if (overflow > 0) {
    EventBus.$emit(C_EVENT.TOAST, `最多添加 ${pendingImageLimit.value} 张图片`);
  }
  if (added > 0) {
    // 预览条会占用消息区高度，把最新消息顶出可视区时顺手滚到底
    if (chatType.value === CHAT_ROOM) {
      chatRoomTabRef.value?.scrollToBottom(SCROLL_TO_BOTTOM_DELAY);
    } else if (chatType.value === CHAT_AI) {
      aiChatTabRef.value?.scrollToBottom(SCROLL_TO_BOTTOM_DELAY);
    }
    // 选完立刻后台上传：发送时只剩「换 Dify 文件 id」这一步，几乎不用等；
    // 也能让格式/大小问题尽早暴露。
    for (const item of pendingImages.value) {
      if (!item.filename && !item.uploading && !item.error) void uploadPendingImage(item);
    }
  }
}

/**
 * 把待发图片上传到本服务（复用既有 `/pic/upload`），结果写回 filename/error。
 *
 * 先经 `resizeImageToFile` 归一：把 bmp/heic 之类转成 jpeg 并压到 1920×1080 内，
 * 顺便规避 Dify 的格式白名单与 10MB 上限；再统一改名为
 * `chat-<userId>-<时间戳>.<ext>`，不让用户原始文件名进 pic 目录与 Dify 历史。
 */
async function uploadPendingImage(item: PendingImage) {
  // 上传接口要求鉴权。未登录时直接标记失败：发出去只会拿到 401，而 401 会触发
  // 全局"登录已过期"并跳登录页——选个图不该把人踢出去。
  if (!getAccessToken()) {
    if (pendingImages.value.includes(item)) {
      item.error = "登录状态已失效，请重新登录";
    }
    return;
  }
  item.uploading = true;
  item.error = undefined;
  try {
    const prepared = await resizeImageToFile(item.file);
    const named = new File(
      [prepared],
      buildChatImageName(globalVar.user?.id ?? "", prepared),
      { type: prepared.type || item.file.type }
    );
    const res = await uploadPic(named);
    if (pendingImages.value.includes(item)) {
      item.filename = res.filename;
    } else {
      // 上传期间用户已经点 X 撤掉了这张图：本地预览已释放、拿不到 filename，
      // 只能在这里补删服务器上刚生成的副本，否则它会一直留在 pic 目录里。
      void deleteUploadedImage(res.filename, { quiet: true });
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : "上传失败";
    if (pendingImages.value.includes(item)) item.error = message;
    EventBus.$emit(C_EVENT.TOAST, `图片上传失败：${message}`);
  } finally {
    item.uploading = false;
  }
}

/**
 * 删除服务器上的一份图片副本。
 *
 * `quiet` 用于用户感知不到的场景（例如上传晚到后的补删）：失败只记日志，不弹提示。
 */
async function deleteUploadedImage(filename: string, opts?: { quiet?: boolean }) {
  // 该接口现在要求鉴权。未登录时直接跳过：发出去也只会拿到 401，而 401 会触发
  // 全局"登录已过期"并跳登录页——一个后台清理动作不该把用户踢出去。
  if (!getAccessToken()) return;
  try {
    await deletePicFile(filename);
  } catch (err) {
    const message = err instanceof Error ? err.message : "删除失败";
    // 文件已经不存在等同于删除成功（重复清理、服务端重启等），不必打扰用户
    if (message.includes("文件不存在")) return;
    console.warn("deleteUploadedImage 失败:", filename, message);
    if (!opts?.quiet) EventBus.$emit(C_EVENT.TOAST, `删除图片失败：${message}`);
  }
}

function btnRemovePendingImage(index: number) {
  const removed = removePendingImage(pendingImages.value, index);
  // 图片在选图时就已经传到服务器了，用户撤掉它就必须把那份副本删掉
  if (removed?.filename) void deleteUploadedImage(removed.filename);
}

/**
 * 重试上传失败的图片。
 *
 * 自动上传的循环里有 `!item.error` 条件，失败项不会再被自动重试（否则会无限重试），
 * 所以需要这个显式的恢复入口。
 */
function btnRetryUpload(index: number) {
  const item = pendingImages.value[index];
  if (!item || item.uploading) return;
  void uploadPendingImage(item);
}

/** 点待发区缩略图看大图（用本地预览 URL，不必再请求服务器） */
function openPendingPreview(index: number) {
  pendingPreview.value = { open: true, index };
}

/** 丢弃所有待发图片（均未发送）：本地释放预览，服务器上的副本一并删除。 */
function discardAllPendingImages() {
  for (const filename of discardPendingImages(pendingImages.value)) {
    void deleteUploadedImage(filename, { quiet: true });
  }
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
  min-height: 2.5rem;
  border-radius: 0.5rem;
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

