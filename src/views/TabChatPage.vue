<template>
  <ion-page class="main-bg" id="main-content">
    <ion-header>
      <ion-toolbar>
        <ion-title>Tab Chat</ion-title>
        <ion-buttons slot="end">
          <ion-button @click="btnChatSettingClk">
            <WeuiSettingOutlined class="button-native" width="30" height="30" />
          </ion-button>
          <ion-button @click="btnNewChatClk">
            <WeuiAdd2Outlined class="button-native" width="30" height="30" />
          </ion-button>
        </ion-buttons>
      </ion-toolbar>
    </ion-header>
    <ion-content class="" ref="chatContent">
      <ion-refresher slot="fixed" @ionRefresh="handleRefresh($event)">
        <ion-refresher-content></ion-refresher-content>
      </ion-refresher>
      <ion-segment value="chat" @ionChange="handleSegmentChange">
        <ion-segment-button value="chat" content-id="chat" layout="icon-start">
          <ion-icon :icon="heartOutline"></ion-icon>
          <ion-label>聊天室</ion-label>
        </ion-segment-button>
        <ion-segment-button value="aiChat" content-id="aiChat" layout="icon-start">
          <ion-icon :icon="heartOutline"></ion-icon>
          <ion-label>AI</ion-label>
        </ion-segment-button>
      </ion-segment>
      <ion-segment-view :style="{ height: `calc(100% - ${tabsHeight}px)` }">
        <!-- 聊天室 -->
        <ion-segment-content id="chat">
          <div class="flex h-full p-2">chat</div>
        </ion-segment-content>
        <!-- AI -->
        <ion-segment-content id="aiChat">
          <div class="flex h-full p-2">
            <ion-list class="bg-transparent">
              <div v-for="(msg, idx) in messages" :key="idx" class="p-1.5 w-full">
                <div
                  v-if="msg.role == 'server'"
                  class="w-[80%] bg-pink-200 rounded-lg p-2 shadow-md ml-auto relative">
                  {{ msg.content ?? "..." }}
                  <div
                    class="absolute -left-10 top-1 rounded-[50%] border border-cyan-950 w-8 h-8 flex items-center justify-center"
                    @click="btnAudioClk(msg)">
                    <MdiStopCircleOutline width="24" height="24" v-if="msg.playing" />
                    <ion-icon :icon="volumeMediumOutline" class="w-6 h-6" v-else />
                  </div>
                </div>
                <div
                  v-else
                  class="w-[80%] bg-green-500 text-white p-2 rounded-lg shadow-md relative">
                  {{ msg.content }}
                  <div
                    v-if="msg.audioSrc"
                    class="absolute -right-10 top-1 rounded-[50%] border border-cyan-950 w-8 h-8 flex items-center justify-center text-black"
                    @click="btnAudioClk(msg)">
                    <MdiStopCircleOutline width="24" height="24" v-if="msg.playing" />
                    <ion-icon :icon="volumeMediumOutline" class="w-6 h-6" v-else />
                  </div>
                </div>
              </div>
            </ion-list>
          </div>
        </ion-segment-content>
      </ion-segment-view>
    </ion-content>
    <audio ref="audioRef" style="width: auto" class="m-2"></audio>
    <ion-item>
      <div class="flex py-2 w-full h-[72px]" v-if="INPUT_TYPE == 'text'">
        <div class="w-12 h-auto flex items-center" @click="btnChangeMode">
          <WeuiVoiceOutlined width="40" height="40" />
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
          <WeuiKeyboardOutlined width="40" height="40" />
        </div>
        <ion-button
          class="flex-1 mr-1"
          ref="recBtn"
          @pointerdown="startRecording"
          :color="isRecording ? 'warning' : 'primary'">
          <div v-if="isRecording" class="flex items-center">
            <MdiStopCircleOutline width="24" height="24" />
            <label class="ml-1 text-sm">松开发送</label>
          </div>
          <div v-else class="flex items-center">
            <MdiMicrophone width="24" height="24" />
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
import {
  getApiUrl,
  getChatMessages,
  getChatSetting,
  getConversationId,
  setConversationId,
} from "@/utils/NetUtil";
import {
  IonToolbar,
  onIonViewDidEnter,
  IonCheckbox,
  createGesture,
  RefresherCustomEvent,
  IonRefresher,
  IonRefresherContent,
  IonSegment,
  IonSegmentButton,
  IonSegmentContent,
  IonSegmentView,
} from "@ionic/vue";
import { heartOutline } from "ionicons/icons";
import io, { Socket } from "socket.io-client";
import Recorder from "recorder-core/recorder.wav.min";
Recorder.CLog = function () {}; // 屏蔽Recorder的日志输出
import ChatSetting from "@/components/ChatSetting.vue";
import { inject, onBeforeUnmount, onMounted, ref } from "vue";
import WeuiAdd2Outlined from "~icons/weui/add2-outlined";
import WeuiSettingOutlined from "~icons/weui/setting-outlined";
import MdiMicrophone from "~icons/mdi/microphone";
import MdiStopCircleOutline from "~icons/mdi/stop-circle-outline";
import WeuiVoiceOutlined from "~icons/weui/voice-outlined";
import WeuiKeyboardOutlined from "~icons/weui/keyboard-outlined";
import { volumeMediumOutline } from "ionicons/icons";

const tabsHeight = ref(0);
let observer: MutationObserver | null = null;

const MSG_TYPE_TRANSLATION = "translation";
const TTS_AUTO = true;
// cSpell: disable-next-line
const TTS_ROLE = "longwan_v2";
// const TTS_SPEED = 1.1;
const chatSetting = ref({ open: false, ttsSpeed: 1.1, ttsRole: TTS_ROLE });
const INPUT_TYPE = ref("audio");
const AUDIO_TYPE = ref("hold");
// 存储识别结果的变量
const inputText = ref("");
const globalVar: any = inject("globalVar");
const aiConversationId = ref("");
const inputRef = ref<HTMLElement | null>(null);
class MSG {
  id?: string;
  content: string = "";
  role: string = "";
  audioSrc?: string = "";
  playing? = false;
}
const messages = ref<MSG[]>([]);
const url = getApiUrl().replace("api", "");
const recBtn = ref<any>();
// const url = "http://127.0.0.1:8000/";
const aiSocketRef = ref<Socket>();

const isWaitingServer = ref(false);
const isRecording = ref(false);
const SAMPLE_RATE = 16000;
const audioRef = ref<HTMLAudioElement | null>(null);
const audioPlayMsg = ref<MSG | null>(null);
const lstAudioSrc = ref<string>("");
const chatContent = ref<any>(null);
// const ttsAudioBuffer = ref<SourceBuffer | null>(null);
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
    audioPlayMsg.value!.playing = false;
    ttsData.value.audioEnd = true;
    ttsData.value.audioBuffer = null;
  });
  await getChatSetting(globalVar.user.id).then((setting) => {
    if (setting) {
      const v = JSON.parse(setting);
      chatSetting.value.ttsSpeed = v.ttsSpeed;
      chatSetting.value.ttsRole = v.ttsRole;
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
  aiConversationId.value = (await getConversationId(globalVar.user.id)) || "";
});
function initSocketIO() {
  aiSocketRef.value = io(url, {
    transports: ["websocket"], // 强制使用 WebSocket 传输
  });
  // 发送握手请求
  aiSocketRef.value.on("connect", () => {
    const msg = {
      key: "123456",
      ttsAuto: TTS_AUTO,
      ttsRole: chatSetting.value.ttsRole,
      ttsSpeed: chatSetting.value.ttsSpeed,
      ttsVol: 50,
      aiConversationId: aiConversationId.value,
      user: globalVar.user.name,
    };

    // console.log("Connected to the server. Sending handshake...", msg);
    aiSocketRef.value!.emit("handshake", msg);
  });
  aiSocketRef.value.on("message", (data) => {
    if (data.type === MSG_TYPE_TRANSLATION) {
      messages.value.push({ id: "", content: `Translation: ${data.content}`, role: "server" });
      isWaitingServer.value = false;
    } else {
      messages.value.push({ id: "", content: `Unknown: ${JSON.stringify(data)}`, role: "server" });
    }
    chatContent.value.$el.scrollToBottom(200);
  });
  // 处理asr结果
  aiSocketRef.value.on("msgAsr", (data) => {
    if (data.content) {
      messages.value.push({
        id: "",
        content: data.content,
        role: "me",
        audioSrc: lstAudioSrc.value,
      });
    }
    chatContent.value.$el.scrollToBottom(200);
  });
  // 处理ai chat结果
  aiSocketRef.value.on("msgChat", (data) => {
    if (messages.value.length === 0 || messages.value[messages.value.length - 1].role === "me") {
      const msg = { id: data.id, content: data.content, role: "server", playing: TTS_AUTO };
      messages.value.push(msg);
      if (TTS_AUTO) {
        audioPlayMsg.value = msg;
      }
    } else {
      messages.value[messages.value.length - 1].content += data.content;
    }
    if (data.aiConversationId != aiConversationId.value) {
      aiConversationId.value = data.aiConversationId;
      setConversationId(globalVar.user.id, aiConversationId.value);
    }
    chatContent.value.$el.scrollToBottom(200);
  });
  aiSocketRef.value.on("endChat", (data: any) => {
    console.log("==> MSG_TYPE_CHAT_END", data.content);
    isWaitingServer.value = false;
    // playAudio(messages.value[messages.value.length - 1]);
  });
  // 处理tts结果
  aiSocketRef.value.on("dataAudio", (data: any) => {
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
  aiSocketRef.value.on("endAudio", (data: any) => {
    ttsData.value.audioEnd = true;
    console.log("==> end_audio", data.content);
  });
  aiSocketRef.value.on("handshakeResponse", (data) => console.log("handshake:", data));
  aiSocketRef.value.on("disconnect", () => console.log("Disconnected from the server."));
  aiSocketRef.value.on("error", (error) => console.error("msg error:", error));
  aiSocketRef.value.on("close", () => console.log("WebSocket connection closed."));
}

async function handleSegmentChange() {
  // console.log("segment change", event);
}

// 模拟发送消息
const sendTextMessage = () => {
  if (inputText.value && !isWaitingServer.value) {
    const message = JSON.stringify({
      type: "text",
      content: inputText.value,
    });
    messages.value.push({ id: "", content: inputText.value, role: "me" });

    isWaitingServer.value = true;
    inputText.value = "";
    chatContent.value.$el.scrollToBottom(200);
    if (TTS_AUTO) {
      streamAudio(() => {
        aiSocketRef.value!.emit("message", message);
      });
    } else {
      aiSocketRef.value!.emit("message", message);
    }
  }
};
function sendAudioData(data: string, finish: boolean = false, cancel = false) {
  if (!aiSocketRef.value!.connected) {
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
  aiSocketRef.value!.emit("message", message);
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
        aiSocketRef.value!.emit("tts", payload);
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
    aiSocketRef.value!.emit("ttsCancel", {});
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
function btnNewChatClk() {}
function btnChatSettingClk() {
  chatSetting.value.open = true;
}
function onChatSettingDismiss(e: any) {
  // console.log("onChatSettingDismiss", e);
  if (e.detail.rol === "confirm") {
    chatSetting.value.ttsSpeed = e.detail.data.ttsSpeed;
    chatSetting.value.ttsRole = e.detail.data.ttsRole;
    aiSocketRef.value!.emit("config", {
      ttsSpeed: e.detail.data.ttsSpeed,
      ttsRole: e.detail.data.ttsRole,
    });
  }
  chatSetting.value.open = false;
}
function handleRefresh(e: RefresherCustomEvent) {
  let firstId = undefined;
  if (messages.value.length > 0) {
    firstId = messages.value[0].id;
  }
  getChatMessages(aiConversationId.value, 3, globalVar.user.name, firstId).then((data: any) => {
    // messages;
    try {
      data.data.reverse().forEach((item: any) => {
        // console.log(item);
        if (item.answer === "") {
          return;
        }
        messages.value.unshift({
          id: item.id,
          content: item.answer,
          role: "server",
        });
        messages.value.unshift({
          id: item.id,
          content: item.query,
          role: "me",
        });
      });
      // chatContent.value.$el.scrollToBottom(200);
    } finally {
      e.target.complete();
    }
  });
}
</script>
