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
        @retry="retryAiMessage" />
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
    <ChatSetting :is-open="chatSetting.open" @willDismiss="onChatSettingDismiss" />
  </ion-page>
</template>

<script setup lang="ts">
import ChatRoomTab from "./TabChatRoom.vue";
import AiChatTab from "./TabAiChat.vue";
import TtsTasksTab from "./TabTtsTasks.vue";
import type { ChatMsg as AiChatMsg } from "./TabAiChat.vue";
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
import { inject, onBeforeUnmount, onMounted, ref } from "vue";

Recorder.CLog = function () {}; // 屏蔽Recorder的日志输出

const tabsHeight = ref(0);
let observer: MutationObserver | null = null;
let mediaSourceCheckTimer: ReturnType<typeof setInterval> | null = null;

const MSG_TYPE_TRANSLATION = "translation";
const TTS_AUTO = false;
// cSpell: disable-next-line
const TTS_ROLE = "longwan_v2";
const MEDIA_SOURCE_CHECK_MS = 2000;
const SCROLL_TO_BOTTOM_DELAY = 200;
const AI_REPLY_TIMEOUT_MS = 120_000;
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
let aiRequestSeq = 0;
const isRecording = ref(false);
const isOpeningRecorder = ref(false);
const isStoppingRecorder = ref(false);
let recordingPointer: number | null = null;
let recorderDisposed = false;
const SAMPLE_RATE = 16000;
const audioRef = ref<HTMLAudioElement | null>(null);
const audioPlayMsg = ref<AiChatMsg | null>(null);
const lstAudioSrc = ref<string>("");
const chatType = ref(CHAT_TTS_TASKS);
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
}

onMounted(async () => {
  const audioEl = audioRef.value;
  if (audioEl) audioEl.addEventListener("ended", onAudioEnded);

  try {
    const setting = await getChatSetting(globalVar.user.id);
    if (setting) {
      const v = JSON.parse(setting);
      chatSetting.value.ttsSpeed = v.ttsSpeed;
      chatSetting.value.ttsRole = v.ttsRole;
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
    if (ttsData.value.audioEnd && ttsData.value.mediaSource?.readyState === "open") {
      ttsData.value.mediaSource.endOfStream();
    }
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

function beginAiWait() {
  isWaitingServer.value = true;
  clearAiReplyTimeout();
  aiReplyTimeout = setTimeout(() => {
    if (!isWaitingServer.value) return;
    endAiWait({ failed: true, message: "回复超时，请重试" });
    EventBus.$emit(C_EVENT.TOAST, "AI 回复超时");
  }, AI_REPLY_TIMEOUT_MS);
}

function endAiWait(opts?: { failed?: boolean; message?: string }) {
  clearAiReplyTimeout();
  isWaitingServer.value = false;
  const aiTab = aiChatTabRef.value;
  if (opts?.failed) {
    aiTab?.failActiveReply(opts.message ?? "请求失败，请重试");
  } else {
    aiTab?.finishActiveReply();
  }
}

function nextAiClientRequestId(): string {
  aiRequestSeq += 1;
  return `ai-${Date.now()}-${aiRequestSeq}`;
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
        id: "",
        content: `Translation: ${data.content}`,
        role: "server",
      });
      isWaitingServer.value = false;
    } else {
      aiChatTabRef.value?.addMessage({
        id: "",
        content: `Unknown: ${JSON.stringify(data)}`,
        role: "server",
      });
    }
    aiChatTabRef.value?.scrollToBottomIfNeeded(SCROLL_TO_BOTTOM_DELAY);
  });
  socketRef.value.on("msgAsr", (data) => {
    if (chatType.value !== CHAT_AI) return;
    if (data.content) {
      aiChatTabRef.value?.addMessage({
        id: "",
        content: data.content,
        role: "me",
        audioSrc: lstAudioSrc.value,
      });
      const clientRequestId = nextAiClientRequestId();
      aiChatTabRef.value?.startAwaitingReply(clientRequestId, data.content);
      beginAiWait();
    }
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
      aiChatTabRef.value?.applyChatChunk({
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
  socketRef.value.on("endChat", (data: any) => {
    console.log("==> MSG_TYPE_CHAT_END", data.content);
    endAiWait();
  });
  socketRef.value.on("dataAudio", (data: any) => {
    if (data.type === "tts") {
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
    ttsData.value.audioEnd = true;
    console.log("==> end_audio", data.content);
  });
  socketRef.value.on("handshakeResponse", () => {
    socketHandshakeOk.value = true;
    updateSocketReady();
  });
  socketRef.value.on("disconnect", () => {
    console.log("Disconnected from the server.");
    socketHandshakeOk.value = false;
    updateSocketReady();
    if (isWaitingServer.value) {
      endAiWait({ failed: true, message: "连接已断开，请重试" });
      EventBus.$emit(C_EVENT.TOAST, "聊天连接已断开");
    }
  });
  socketRef.value.on("error", (error: { type?: string; content?: string } | string) => {
    console.error("msg error:", error);
    const message =
      typeof error === "string"
        ? error
        : error?.content || "AI 请求出错，请重试";
    if (isWaitingServer.value) {
      endAiWait({ failed: true, message });
      EventBus.$emit(C_EVENT.TOAST, message);
    }
  });
  socketRef.value.on("close", () => console.log("WebSocket connection closed."));
}

async function handleSegmentChange(event: any) {
  cancelRecording();
  chatType.value = event.detail.value;
}

function sendAiText(text: string, opts?: { showUserBubble?: boolean }) {
  const trimmed = text.trim();
  if (!trimmed || isWaitingServer.value) return false;
  if (!socketRef.value?.connected || !socketHandshakeOk.value) {
    EventBus.$emit(C_EVENT.TOAST, "聊天服务未就绪，请稍后再试");
    return false;
  }
  if (opts?.showUserBubble !== false) {
    aiChatTabRef.value?.addMessage({
      id: "",
      content: trimmed,
      role: "me",
    });
  }
  const clientRequestId = nextAiClientRequestId();
  aiChatTabRef.value?.startAwaitingReply(clientRequestId, trimmed);
  aiChatTabRef.value?.scrollToBottomIfNeeded(SCROLL_TO_BOTTOM_DELAY);
  const message = JSON.stringify({
    type: "text",
    content: trimmed,
    chatType: CHAT_AI,
    roomId: chatSetting.value.chatRoomId,
    userId: globalVar.user.id,
  });
  socketRef.value!.emit("message", message);
  beginAiWait();
  return true;
}

function retryAiMessage(text: string) {
  if (isWaitingServer.value) return;
  sendAiText(text);
}

function stopAiGeneration() {
  if (!isWaitingServer.value) return;
  socketRef.value?.emit("chatCancel");
  endAiWait();
}

const sendTextMessage = () => {
  if (!inputText.value || isWaitingServer.value) return;
  if (chatType.value === CHAT_AI) {
    const text = inputText.value;
    if (sendAiText(text)) inputText.value = "";
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

function sendAudioData(data: string, finish: boolean = false, cancel = false) {
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

function cancelRecording() {
  clearRecordingPointer();
  stopRecording(true);
}

function onRecordingVisibilityChange() {
  if (document.hidden) cancelRecording();
}

function onRecordingPointerUp(event: PointerEvent) {
  if (event.pointerId !== recordingPointer) return;
  clearRecordingPointer();
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
  if (!socketRef.value?.connected) {
    EventBus.$emit(C_EVENT.TOAST, '聊天服务未连接，请连接后再录音');
    return;
  }
  recordingPointer = event.pointerId;
  isOpeningRecorder.value = true;
  // 在异步权限请求前监听松手，避免授权完成后开始一次已经结束的按压。
  window.addEventListener('pointerup', onRecordingPointerUp, true);
  window.addEventListener('pointercancel', onRecordingPointerCancel, true);
  window.addEventListener('pointermove', onRecordingPointerMove, true);
  window.addEventListener('blur', cancelRecording);
  document.addEventListener('visibilitychange', onRecordingVisibilityChange);
  const fail = (message: unknown, denied = false) => {
    clearRecordingPointer();
    isOpeningRecorder.value = false;
    isRecording.value = false;
    rec.close();
    if (!recorderDisposed) EventBus.$emit(C_EVENT.TOAST, denied
      ? '麦克风权限被拒绝，请在浏览器或系统设置中允许麦克风访问'
      : `无法开始录音：${String(message)}`);
  };
  try {
    rec.open(() => {
      isOpeningRecorder.value = false;
      if (recordingPointer === null || recorderDisposed) {
        rec.close();
        if (!recorderDisposed) EventBus.$emit(C_EVENT.TOAST, '麦克风已就绪，请重新按住说话');
        return;
      }
      try {
        recSampleBuf = new Int16Array();
        rec.start();
        isRecording.value = true;
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
    sendAudioData(base64Data);
  }
}

function stopRecording(cancel = false) {
  if (isRecording.value === false) return;
  isRecording.value = false;
  isStoppingRecorder.value = true;
  console.log("==> stopRecording", cancel);
  rec.stop(
    (blob: Blob) => {
      lstAudioSrc.value = (window.URL || webkitURL).createObjectURL(blob);
      if (recSampleBuf.length) {
        const sendBuf = recSampleBuf;
        recSampleBuf = new Int16Array();
        const uint8 = new Uint8Array(sendBuf.buffer);
        const base64Data = btoa(String.fromCharCode(...uint8));
        sendAudioData(base64Data);
      }
      sendAudioData("", true, cancel);
      if (TTS_AUTO && !cancel) {
        streamAudio(() => {});
      }
      if (!cancel && chatType.value === CHAT_AI) {
        isWaitingServer.value = true;
        clearAiReplyTimeout();
        aiReplyTimeout = setTimeout(() => {
          if (!isWaitingServer.value) return;
          endAiWait({ failed: true, message: "语音识别超时，请重试" });
          EventBus.$emit(C_EVENT.TOAST, "语音识别超时");
        }, AI_ASR_WAIT_MS);
      }
      rec.close();
      isStoppingRecorder.value = false;
    },
    (errMsg: any) => {
      sendAudioData('', true, true);
      recSampleBuf = new Int16Array();
      rec.close();
      isStoppingRecorder.value = false;
      if (!cancel && !recorderDisposed) EventBus.$emit(C_EVENT.TOAST, `录音失败：${errMsg}`);
    }
  );
}

async function btnAudioClk(msg: AiChatMsg) {
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
      const payload = JSON.stringify({
        content: msg.content,
        role: chatSetting.value.ttsRole,
        id: msg.id,
      });
      streamAudio(() => {
        socketRef.value!.emit("tts", payload);
      });
    }
  }
}

async function stopAndClearAudio() {
  if (audioRef.value) {
    try {
      audioRef.value.pause();
      audioRef.value!.src = "";
    } catch (e) {
      /* empty */
    }
  }
  if (ttsData.value.audioBuffer) {
    ttsData.value.audioBuffer = null;
    console.log("==> ttsCancel");
    socketRef.value!.emit("ttsCancel", {});
  }
  if (audioPlayMsg.value) {
    audioPlayMsg.value.playing = false;
  }
  audioPlayMsg.value = null;
  if (ttsData.value.mediaSource) {
    if (ttsData.value.mediaSource.readyState === "open") {
      ttsData.value.mediaSource.endOfStream();
    }
    ttsData.value.mediaSource = null;
  }
}

function streamAudio(f = () => {}) {
  const mediaSource = new MediaSource();
  audioRef.value!.pause();
  audioRef.value!.src = URL.createObjectURL(mediaSource);
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
      if (ttsData.value.audioEnd && ttsData.value.mediaSource) {
        try {
          ttsData.value.mediaSource.endOfStream();
        } catch {
          /* empty */
        }
      }
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
