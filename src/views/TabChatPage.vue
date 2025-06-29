<template>
  <ion-page class="main-bg" id="main-content">
    <ion-header>
      <ion-toolbar>
        <ion-title>Tab Chat</ion-title>
        <ion-buttons slot="end">
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
        <ion-icon :icon="heartOutline"></ion-icon>
        <ion-label>聊天室</ion-label>
      </ion-segment-button>
      <ion-segment-button
        :value="CHAT_AI"
        content-id="aiChat"
        layout="icon-start"
        class="text-blue-500">
        <ion-icon :icon="heartOutline"></ion-icon>
        <ion-label>AI</ion-label>
      </ion-segment-button>
    </ion-segment>
    <ion-segment-view :style="{ height: `calc(100% - ${tabsHeight}px)` }">
      <!-- 聊天室 -->
      <ion-segment-content id="chat">
        <ion-content class="" ref="chatContent">
          <ion-refresher slot="fixed" @ionRefresh="handleRefresh($event)">
            <ion-refresher-content></ion-refresher-content>
          </ion-refresher>
          <div class="flex flex-col h-full p-2 border-t-1 border-gray-200">
            <div v-for="(msg, idx) in chatMessages" :key="idx" class="p-1.5 w-full">
              <!-- 自己 -->
              <div v-if="msg.role === globalVar.user.id" class="flex">
                <div
                  class="max-w-[70%] min-w-[40px] bg-green-500 text-white p-2 ml-auto rounded-lg shadow-md relative">
                  {{ msg.content }}
                </div>
                <ion-avatar slot="start" class="w-12 h-12 ml-1">
                  <ion-img :src="getUserInfo(msg.role).icon" />
                </ion-avatar>
                <div
                  v-if="!msg.audioSrc"
                  class="absolute -right-10 top-1 rounded-[50%] border border-cyan-950 w-8 h-8 flex items-center justify-center text-black"
                  @click="btnAudioClk(msg)">
                  <Icon icon="mdi:stop-circle-outline" class="w-6 h-6" v-if="msg.playing" />
                  <ion-icon :icon="volumeMediumOutline" class="w-6 h-6" v-else />
                </div>
              </div>
              <!-- 他人 -->
              <div v-else class="flex">
                <ion-avatar slot="start" class="w-12 h-12 mr-1">
                  <ion-img :src="getUserInfo(msg.role).icon" />
                </ion-avatar>
                <div
                  class="max-w-[70%] min-w-[40px] bg-pink-200 p-2 mr-auto rounded-lg shadow-md relative">
                  {{ msg.content }}
                </div>
                <div
                  class="absolute -left-10 top-1 rounded-[50%] border border-cyan-950 w-8 h-8 flex items-center justify-center"
                  @click="btnAudioClk(msg)">
                  <Icon icon="mdi:stop-circle-outline" class="w-6 h-6" v-if="msg.playing" />
                  <ion-icon :icon="volumeMediumOutline" class="w-6 h-6" v-else />
                </div>
              </div>
            </div>
          </div>
        </ion-content>
      </ion-segment-content>
      <!-- AI -->
      <ion-segment-content id="aiChat">
        <ion-content class="" ref="aiChatContent">
          <ion-refresher slot="fixed" @ionRefresh="handleRefresh($event)">
            <ion-refresher-content></ion-refresher-content>
          </ion-refresher>
          <div class="flex flex-col h-full p-2 border-t-1 border-gray-200">
            <div v-for="(msg, idx) in aiChatMessages" :key="idx" class="p-1.5 w-full">
              <div
                v-if="msg.role == 'server'"
                class="w-[80%] bg-pink-200 rounded-lg p-2 shadow-md ml-auto relative">
                {{ msg.content ?? "..." }}
                <div
                  class="absolute -left-10 top-1 rounded-[50%] border border-cyan-950 w-8 h-8 flex items-center justify-center"
                  @click="btnAudioClk(msg)">
                  <Icon icon="mdi:stop-circle-outline" class="w-6 h-6" v-if="msg.playing" />
                  <ion-icon :icon="volumeMediumOutline" class="w-6 h-6" v-else />
                </div>
              </div>
              <div v-else class="w-[80%] bg-green-500 text-white p-2 rounded-lg shadow-md relative">
                {{ msg.content }}
                <div
                  v-if="msg.audioSrc"
                  class="absolute -right-10 top-1 rounded-[50%] border border-cyan-950 w-8 h-8 flex items-center justify-center text-black"
                  @click="btnAudioClk(msg)">
                  <Icon icon="mdi:stop-circle-outline" class="w-6 h-6" v-if="msg.playing" />
                  <ion-icon :icon="volumeMediumOutline" class="w-6 h-6" v-else />
                </div>
              </div>
            </div>
          </div>
        </ion-content>
      </ion-segment-content>
    </ion-segment-view>
    <audio ref="audioRef" style="width: auto" class="m-2"></audio>
    <ion-item>
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
          autofocus="true"
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
import ChatSetting from "@/components/ChatSetting.vue";
import EventBus, { C_EVENT } from "@/modal/EventBus";
import {
  getAiChatMessages,
  getApiUrl,
  getChatMessages,
  getChatSetting,
  getUserList,
  setChatSetting,
} from "@/utils/NetUtil";
import {
  createGesture,
  IonAvatar,
  IonCheckbox,
  IonImg,
  IonRefresher,
  IonRefresherContent,
  IonSegment,
  IonSegmentButton,
  IonSegmentContent,
  IonSegmentView,
  IonToolbar,
  onIonViewDidEnter,
  RefresherCustomEvent,
} from "@ionic/vue";
import { heartOutline, volumeMediumOutline } from "ionicons/icons";
import Recorder from "recorder-core/recorder.wav.min";
import io, { Socket } from "socket.io-client";
import { inject, onBeforeUnmount, onMounted, ref } from "vue";

Recorder.CLog = function () {}; // 屏蔽Recorder的日志输出

const tabsHeight = ref(0);
let observer: MutationObserver | null = null;

const MSG_TYPE_TRANSLATION = "translation";
const TTS_AUTO = false;
// cSpell: disable-next-line
const TTS_ROLE = "longwan_v2";
// const TTS_SPEED = 1.1;

const CHAT_ROOM = "chat_room";
const CHAT_AI = "chat_ai";
const chatSetting = ref({
  open: false,
  ttsSpeed: 1.1,
  ttsRole: TTS_ROLE,
  aiConversationId: "",
  chatRoomId: "",
});
const INPUT_TYPE = ref("text");
const AUDIO_TYPE = ref("hold");
// 存储识别结果的变量
const inputText = ref("");
const globalVar: any = inject("globalVar");
const inputRef = ref<HTMLElement | null>(null);
const userList = ref<any>([]);
class MSG {
  id?: string | number;
  content: string = "";
  role: string = "";
  audioSrc?: string = "";
  playing? = false;
  ts?: string;
  type?: string = "text";
}
const aiChatMessages = ref<MSG[]>([]);
const aiChatContent = ref<any>(null);
const chatMessages = ref<MSG[]>([]);
const chatContent = ref<any>(null);

const wsUrl = getApiUrl().replace("api", "");
// const wsUrl = "localhost:8000"; // 使用 /api 前缀
// console.log(getApiUrl());
const recBtn = ref<any>();
const socketRef = ref<Socket>();

const isWaitingServer = ref(false);
const isRecording = ref(false);
const SAMPLE_RATE = 16000;
const audioRef = ref<HTMLAudioElement | null>(null);
const audioPlayMsg = ref<MSG | null>(null);
const lstAudioSrc = ref<string>("");
const chatType = ref(CHAT_AI);
const ttsData = ref<any>({ audioBuffer: null, msg: null, audioEnd: false, mediaSource: null });
const rec = Recorder({
  type: "wav",
  bitRate: 16,
  sampleRate: 16000,
  onProcess: recProcess,
  audioTrackSet: {
    echoCancellation: true, //回声消除（AEC）开关，不设置时由浏览器控制（一般为默认自动打开），设为true明确打开，设为false明确关闭
    noiseSuppression: true, //降噪（ANS）开关，取值和回声消除开关一样
    autoGainControl: true, //自动增益（AGC）开关，取值和回声消除开关一样
  },
});
let recSampleBuf = new Int16Array();
let playAudioData: ArrayBuffer[] = [];

onMounted(async () => {
  // messages.value.push({ id: "", content: "你好，我是楠楠，和我聊点什么吧", role: "server" });
  audioRef.value!.addEventListener("ended", () => {
    console.log("==> event audio ended");
    audioPlayMsg.value!.playing = false;
    ttsData.value.audioEnd = true;
    ttsData.value.audioBuffer = null;
  });
  await getChatSetting(globalVar.user.id).then((setting) => {
    if (setting) {
      const v = JSON.parse(setting);
      chatSetting.value.ttsSpeed = v.ttsSpeed;
      chatSetting.value.ttsRole = v.ttsRole;
      chatSetting.value.aiConversationId = v.aiConversationId;
      chatSetting.value.chatRoomId = v.chatRoomId;
    }
  });
  initSocketIO();
  setInterval(() => {
    if (
      ttsData.value.audioEnd &&
      ttsData.value.mediaSource &&
      ttsData.value.mediaSource.readyState === "open"
    ) {
      ttsData.value.mediaSource.endOfStream();
    }
  }, 2000);
  // 创建 MutationObserver 监听 tabs 元素
  observer = new MutationObserver(() => {
    updateTabsHeight();
  });
  // 开始监听 body 的变化，因为 tabs 可能还没有渲染
  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });
});
const updateTabsHeight = () => {
  const tabs = document.querySelector("ion-tab-bar");
  if (tabs) {
    tabsHeight.value = tabs.clientHeight;
  }
};
const updateChatSetting = async () => {
  await getChatSetting(globalVar.user.id).then((setting) => {
    if (setting) {
      const v = JSON.parse(setting);
      chatSetting.value = Object.assign({}, chatSetting.value, v);
    }
  });
};
async function refreshUserList() {
  await getUserList()
    .then((uList) => {
      userList.value = [...uList.data];
    })
    .catch((err) => {
      EventBus.$emit(C_EVENT.TOAST, JSON.stringify(err));
    });
}

function getUserInfo(userId: string) {
  // console.log("==> getUserInfo", userId);
  if (userId === "me") {
    return globalVar.user;
  }
  return userList.value.find((u: any) => u.id === userId);
}
onBeforeUnmount(() => {
  // 移除事件监听
  window.removeEventListener("resize", updateTabsHeight);
  // 断开 observer
  if (observer) {
    observer.disconnect();
    observer = null;
  }
});
onIonViewDidEnter(async () => {
  await updateChatSetting();
  await refreshUserList();
  getChatMessages(chatSetting.value.chatRoomId, -1, 3).then((data: any) => {
    // console.log("==> handleRefresh", data);
    chatMessages.value = [];
    data.data.reverse().forEach((item: any) => {
      const d = JSON.parse(item);
      // console.log("==> getChatMessages", d);
      chatMessages.value.unshift({
        id: d.id,
        content: d.content,
        role: d.user_id,
        ts: d.ts,
        type: d.type,
      });
    });
  });
});
function initSocketIO() {
  socketRef.value = io(wsUrl, {
    transports: ["websocket"], // 强制使用 WebSocket 传输
    // path: "/api/socket.io/",
    reconnection: true,
    reconnectionAttempts: 5, // 最大重连次数
    reconnectionDelay: 1000, // 重连延迟时间
    secure: true,
    rejectUnauthorized: false,
  });
  // 发送握手请求
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

    // console.log("Connected to the server. Sending handshake...", chatConfig);
    socketRef.value!.emit("handshake", chatConfig);
  });
  socketRef.value.on("message", (data) => {
    console.log("==> message", data);
    if (data.type === MSG_TYPE_TRANSLATION) {
      aiChatMessages.value.push({
        id: "",
        content: `Translation: ${data.content}`,
        role: "server",
      });
      isWaitingServer.value = false;
    } else {
      aiChatMessages.value.push({
        id: "",
        content: `Unknown: ${JSON.stringify(data)}`,
        role: "server",
      });
    }
    aiChatContent.value.$el.scrollToBottom(200);
  });
  // 处理asr结果
  socketRef.value.on("msgAsr", (data) => {
    if (data.content) {
      aiChatMessages.value.push({
        id: "",
        content: data.content,
        role: "me",
        audioSrc: lstAudioSrc.value,
      });
    }
    aiChatContent.value.$el.scrollToBottom(200);
  });
  // 处理ai chat结果
  socketRef.value.on("msgChat", async (data) => {
    console.log("==> msgChat", data);
    if (data.chat_type === CHAT_ROOM) {
      chatMessages.value.push({
        id: data.id,
        content: data.content,
        role: data.user_id,
        ts: data.ts,
        type: data.type,
      });
    } else {
      if (
        aiChatMessages.value.length === 0 ||
        aiChatMessages.value[aiChatMessages.value.length - 1].role === "me"
      ) {
        const msg = { id: data.id, content: data.content, role: "server", playing: TTS_AUTO };
        aiChatMessages.value.push(msg);
        if (TTS_AUTO) {
          audioPlayMsg.value = msg;
        }
      } else {
        aiChatMessages.value[aiChatMessages.value.length - 1].content += data.content;
      }
      if (data.aiConversationId != chatSetting.value.aiConversationId) {
        chatSetting.value.aiConversationId = data.aiConversationId;
        setChatSetting(globalVar.user.id, JSON.stringify(chatSetting.value));
      }
      aiChatContent.value.$el.scrollToBottom(200);
    }
  });
  socketRef.value.on("endChat", (data: any) => {
    console.log("==> MSG_TYPE_CHAT_END", data.content);
    isWaitingServer.value = false;
    // playAudio(messages.value[messages.value.length - 1]);
  });
  // 处理tts结果
  socketRef.value.on("dataAudio", (data: any) => {
    if (data.type === "tts") {
      const chunk = data.data; // 接收的是二进制数据
      // console.log(chunk.length, data.data);
      if (chunk instanceof ArrayBuffer) {
        playAudioData.push(chunk);
        // 如果数据是 ArrayBuffer
        if (ttsData.value.audioBuffer && !ttsData.value.audioBuffer.updating) {
          // ttsAudioBuffer.value!.appendBuffer(chunk);
          const combinedBuffer = new Uint8Array(
            playAudioData.reduce((acc, curr) => acc + curr.byteLength, 0)
          );
          let offset = 0;
          // 将所有数据块合并为一个 Uint8Array
          playAudioData.forEach((chunk) => {
            combinedBuffer.set(new Uint8Array(chunk), offset);
            offset += chunk.byteLength;
          });
          ttsData.value.audioBuffer.appendBuffer(combinedBuffer); // 直接添加 ArrayBuffer 数据
          // 清空已处理的数据
          playAudioData = [];
        }
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
    // console.log("handshake:", data)
  });
  socketRef.value.on("disconnect", () => console.log("Disconnected from the server."));
  socketRef.value.on("error", (error) => console.error("msg error:", error));
  socketRef.value.on("close", () => console.log("WebSocket connection closed."));
}

async function handleSegmentChange(event: any) {
  // console.log("segment change", event);
  chatType.value = event.detail.value;
}

// 模拟发送消息
const sendTextMessage = () => {
  if (inputText.value && !isWaitingServer.value) {
    if (chatType.value === CHAT_AI) {
      aiChatMessages.value.push({ id: "", content: inputText.value, role: "me" });
      aiChatContent.value.$el.scrollToBottom(200);
    } else if (chatType.value === CHAT_ROOM) {
      chatMessages.value.push({ id: "", content: inputText.value, role: globalVar.user.id });
      chatContent.value.$el.scrollToBottom(200);
    }

    const message = JSON.stringify({
      type: "text",
      content: inputText.value,
      chatType: chatType.value,
      roomId: chatSetting.value.chatRoomId,
      userId: globalVar.user.id,
    });
    // EventBus.$emit(C_EVENT.TOAST, inputText.value);
    inputText.value = "";
    isWaitingServer.value = true;
    // if (TTS_AUTO) {
    //   streamAudio(() => {
    //     socketRef.value!.emit("message", message);
    //   });
    // } else {
    socketRef.value!.emit("message", message);
    // }
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
  // console.log("==> sendData audio ", data.length, finish);
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
          // 创建手势
          const gesture = createGesture({
            el: recBtn.value.$el, // 目标元素
            gestureName: "longPress", // 手势名称
            threshold: 0, // 触发距离阈值
            onStart: () => {},
            onMove: (ev) => {
              // 检查是否移动出按钮范围
              const rect = recBtn.value.$el.getBoundingClientRect();
              const isOutside =
                ev.currentX < rect.left ||
                ev.currentX > rect.right ||
                ev.currentY < rect.top ||
                ev.currentY > rect.bottom;

              if (isOutside) {
                stopRecording(true); // 移动出按钮范围时取消录制
                gesture.destroy();
              }
            },
            onEnd: () => {
              stopRecording(false); // 长按结束时触发
              gesture.destroy();
            },
          });

          // 启用手势
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
function recProcess(
  buffer: any, // 缓冲的PCM数据块(16位小端LE)，为从开始录音到现在的所有pcm片段，每次回调可能增加0-n个不定量的pcm片段。
  powerLevel: any, // 当前缓冲的音量级别0-100。
  bufferDuration: any, // 已缓冲时长
  bufferSampleRate: any
  // _newBufferIdx: any,
  // _asyncEnd: any
) {
  const data_48k = buffer[buffer.length - 1];

  const array_48k = new Array(data_48k);
  const data_16k = Recorder.SampleData(array_48k, bufferSampleRate, SAMPLE_RATE).data;

  recSampleBuf = Int16Array.from([...recSampleBuf, ...data_16k]);
  const chunk_size = 960; // for asr chunk_size [5, 10, 5]
  // info_div.innerHTML = "" + bufferDuration / 1000 + "s";
  while (recSampleBuf.length >= chunk_size) {
    const sendBuf = recSampleBuf.slice(0, chunk_size);
    recSampleBuf = recSampleBuf.slice(chunk_size, recSampleBuf.length);
    const uint8 = new Uint8Array(sendBuf.buffer);
    const base64Data = btoa(String.fromCharCode(...uint8));
    // console.log("==> recProcess ", base64Data);
    // 通过 WebSocket 发送 Base64 编码的音频数据
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

async function btnAudioClk(msg: MSG) {
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
    // ttsData.value.audioBuffer.abort();
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

  // 等待 MediaSource 打开
  mediaSource.addEventListener("sourceopen", () => {
    ttsData.value.audioBuffer = mediaSource.addSourceBuffer("audio/mpeg");
    // 错误处理
    ttsData.value.audioBuffer.addEventListener("error", (e: any) => {
      console.error("SourceBuffer 错误:", e);
    });
    ttsData.value.audioBuffer.addEventListener("updateend", () => {
      // 如果还有数据未处理，可以继续添加
      if (playAudioData.length > 0 && !ttsData.value.audioBuffer.updating) {
        const combinedBuffer = new Uint8Array(
          playAudioData.reduce((acc, curr) => acc + curr.byteLength, 0)
        );
        let offset = 0;
        // 将所有数据块合并为一个 Uint8Array
        playAudioData.forEach((chunk) => {
          combinedBuffer.set(new Uint8Array(chunk), offset);
          offset += chunk.byteLength;
        });
        ttsData.value.audioBuffer.appendBuffer(combinedBuffer); // 直接添加 ArrayBuffer 数据
        // 清空已处理的数据
        playAudioData = [];
      } else if (ttsData.value.audioEnd) {
        if (ttsData.value.mediaSource) {
          try {
            ttsData.value.mediaSource.endOfStream();
          } catch (ignore) {
            /* empty */
          }
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
  // console.log("onChatSettingDismiss", e);
  if (e.detail.rol === "confirm") {
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
function handleRefresh(e: RefresherCustomEvent) {
  if (chatType.value === CHAT_ROOM) {
    const firstId = chatMessages.value.length + 1;
    // console.log("==> handleRefresh", chatSetting.value);
    getChatMessages(chatSetting.value.chatRoomId, -firstId, 3)
      .then((data: any) => {
        // console.log("==> handleRefresh", data);
        data.data.reverse().forEach((item: any) => {
          const d = JSON.parse(item);
          console.log(d);
          chatMessages.value.unshift({
            id: d.id,
            content: d.content,
            role: d.user_id,
            ts: d.ts,
            type: d.type,
          });
        });
      })
      .finally(() => {
        e.target.complete();
      });
  } else if (chatType.value === CHAT_AI) {
    let firstId = undefined;
    if (aiChatMessages.value.length > 0) {
      firstId = aiChatMessages.value[0].id;
    }
    getAiChatMessages(chatSetting.value.aiConversationId, 3, globalVar.user.name, firstId).then(
      (data: any) => {
        // messages;
        try {
          data.data.reverse().forEach((item: any) => {
            // console.log(item);
            if (item.answer === "") {
              return;
            }
            aiChatMessages.value.unshift({
              id: item.id,
              content: item.answer,
              role: "server",
            });
            aiChatMessages.value.unshift({
              id: item.id,
              content: item.query,
              role: "me",
            });
          });
          // chatContent.value.$el.scrollToBottom(200);
        } finally {
          e.target.complete();
        }
      }
    );
  }
}
</script>
