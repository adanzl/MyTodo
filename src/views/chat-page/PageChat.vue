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
        @audio-click="btnAudioClk" />
      <TtsTasksTab :active="chatType === CHAT_TTS_TASKS" />
    </ion-segment-view>
    <audio ref="audioRef" style="width: auto" class="m-2"></audio>
    <ion-item v-if="chatType !== CHAT_TTS_TASKS">
      <div class="flex py-2 w-full h-[72px]" v-if="INPUT_TYPE == 'text'">
        <div class="w-12 h-auto flex items-center" @click="btnChangeMode">
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
        <ion-button @click="sendTextMessage">发送</ion-button>
      </div>
      <div class="flex py-2 w-full h-[72px]" v-else>
        <div class="w-12 h-auto flex items-center" @click="btnChangeMode">
          <Icon icon="weui:keyboard-outlined" class="h-10 w-10" />
        </div>
        <ion-button
          class="flex-1 mr-1"
          ref="recBtn"
          @pointerdown="startRecording"
          :color="isRecording ? 'warning' : 'primary'">
          <div v-if="isRecording" class="flex items-center">
            <Icon icon="mdi:stop-circle-outline" class="h-6 w-6" />
            <label class="ml-1 text-sm">松开发送</label>
          </div>
          <div v-else class="flex items-center">
            <Icon icon="mdi:microphone" class="h-6 w-6" />
            <label class="ml-1 text-sm">按住说话</label>
          </div>
        </ion-button>
        <div class="w-12 flex flex-col pl-2">
          <ion-checkbox
            class="ml-1 h-8"
            style="--size: 22px"
            :checked="AUDIO_TYPE == 'hold'"
            alignment="center"
            @ionChange="onAudioTypeChange" />
          <span>hold</span>
        </div>
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
import ChatSetting from "@/components/ChatSetting.vue";
import ServerRemoteBadge from "@/components/ServerRemoteBadge.vue";
import { Icon } from "@iconify/vue";
import EventBus, { C_EVENT } from "@/types/EventBus";
import { getApiUrl } from "@/api/api-client";
import { getChatSetting, setChatSetting } from "@/api/chat";
import { getUserList } from "@/api/user";
import { getNetworkErrorMessage } from "@/utils/NetUtil";
import {
  createGesture,
  IonCheckbox,
  IonSegment,
  IonSegmentButton,
  IonSegmentView,
  IonToolbar,
  onIonViewDidEnter,
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
const AUDIO_TYPE = ref("hold");
const inputText = ref("");
const globalVar: any = inject("globalVar");
const inputRef = ref<HTMLElement | null>(null);
const userList = ref<any>([]);

const chatRoomTabRef = ref<InstanceType<typeof ChatRoomTab> | null>(null);
const aiChatTabRef = ref<InstanceType<typeof AiChatTab> | null>(null);

const wsUrl = getApiUrl().replace("api", "");
const recBtn = ref<any>();
const socketRef = ref<Socket>();

const isWaitingServer = ref(false);
const isRecording = ref(false);
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
      chatSetting.value.chatRoomId = v.chatRoomId;
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
  window.removeEventListener("resize", updateTabsHeight);
  if (observer) {
    observer.disconnect();
    observer = null;
  }
  if (mediaSourceCheckTimer != null) {
    clearInterval(mediaSourceCheckTimer);
    mediaSourceCheckTimer = null;
  }
  const audioEl = audioRef.value;
  if (audioEl) audioEl.removeEventListener("ended", onAudioEnded);
  if (socketRef.value) {
    socketRef.value.removeAllListeners();
    socketRef.value.disconnect();
  }
});

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
    aiChatTabRef.value?.scrollToBottom(SCROLL_TO_BOTTOM_DELAY);
  });
  socketRef.value.on("msgAsr", (data) => {
    if (data.content) {
      aiChatTabRef.value?.addMessage({
        id: "",
        content: data.content,
        role: "me",
        audioSrc: lstAudioSrc.value,
      });
    }
    aiChatTabRef.value?.scrollToBottom(SCROLL_TO_BOTTOM_DELAY);
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
      const aiTab = aiChatTabRef.value;
      const last = aiTab?.getLastMessage?.();
      if (!last || last.role === "me") {
        const msg: AiChatMsg = {
          id: data.id,
          content: data.content,
          role: "server",
          playing: TTS_AUTO,
        };
        aiChatTabRef.value?.addMessage(msg);
        if (TTS_AUTO) {
          audioPlayMsg.value = msg;
        }
      } else {
        aiChatTabRef.value?.appendLastMessageContent(data.content);
      }
      if (data.aiConversationId != chatSetting.value.aiConversationId) {
        chatSetting.value.aiConversationId = data.aiConversationId;
        setChatSetting(globalVar.user.id, JSON.stringify(chatSetting.value));
      }
      aiChatTabRef.value?.scrollToBottom(SCROLL_TO_BOTTOM_DELAY);
    }
  });
  socketRef.value.on("endChat", (data: any) => {
    console.log("==> MSG_TYPE_CHAT_END", data.content);
    isWaitingServer.value = false;
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
  socketRef.value.on("handshakeResponse", () => {});
  socketRef.value.on("disconnect", () => console.log("Disconnected from the server."));
  socketRef.value.on("error", (error) => console.error("msg error:", error));
  socketRef.value.on("close", () => console.log("WebSocket connection closed."));
}

async function handleSegmentChange(event: any) {
  chatType.value = event.detail.value;
}

const sendTextMessage = () => {
  if (inputText.value && !isWaitingServer.value) {
    if (chatType.value === CHAT_AI) {
      aiChatTabRef.value?.addMessage({
        id: "",
        content: inputText.value,
        role: "me",
      });
      aiChatTabRef.value?.scrollToBottom(SCROLL_TO_BOTTOM_DELAY);
    } else if (chatType.value === CHAT_ROOM) {
      chatRoomTabRef.value?.addMessage({
        id: "",
        content: inputText.value,
        role: globalVar.user.id,
      });
      chatRoomTabRef.value?.scrollToBottom(SCROLL_TO_BOTTOM_DELAY);
    }

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
  }
};

function sendAudioData(data: string, finish: boolean = false, cancel = false) {
  if (!socketRef.value!.connected) {
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

async function startRecording() {
  if (!isWaitingServer.value) {
    console.log("==> startRecording");
    try {
      rec.open(
        () => {
          console.info("Recording started");
          rec.start();
          const gesture = createGesture({
            el: recBtn.value.$el,
            gestureName: "longPress",
            threshold: 0,
            onStart: () => {},
            onMove: (ev) => {
              const rect = recBtn.value.$el.getBoundingClientRect();
              const isOutside =
                ev.currentX < rect.left ||
                ev.currentX > rect.right ||
                ev.currentY < rect.top ||
                ev.currentY > rect.bottom;

              if (isOutside) {
                stopRecording(true);
                gesture.destroy();
              }
            },
            onEnd: () => {
              stopRecording(false);
              gesture.destroy();
            },
          });
          gesture.enable();
          isRecording.value = true;
        },
        () => {
          console.error("Recording failed");
        }
      );
    } catch (error) {
      console.error("Error starting recording:", error);
      isRecording.value = false;
    }
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
      rec.close();
    },
    (errMsg: any) => console.log("errMsg: " + errMsg)
  );
  isRecording.value = false;
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
    audioRef.value.pause();
    audioRef.value!.src = "";
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
  if (INPUT_TYPE.value == "text") {
    INPUT_TYPE.value = "voice";
  } else {
    INPUT_TYPE.value = "text";
  }
}

function onAudioTypeChange() {
  if (AUDIO_TYPE.value == "hold") {
    AUDIO_TYPE.value = "stream";
  } else {
    AUDIO_TYPE.value = "hold";
  }
}

function btnChatSettingClk() {
  chatSetting.value.open = true;
}

function onChatSettingDismiss(e: any) {
  if (e.detail.role === "confirm") {
    updateChatSetting();
    socketRef.value!.emit("config", {
      ttsSpeed: chatSetting.value.ttsSpeed,
      ttsRole: chatSetting.value.ttsRole,
      aiConversationId: chatSetting.value.aiConversationId,
      chatRoomId: chatSetting.value.chatRoomId,
    });
  }
  chatSetting.value.open = false;
}
</script>
