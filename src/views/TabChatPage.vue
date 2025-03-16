<template>
  <!-- 暂时不用了 -->
  <ion-page class="main-bg" id="main-content">
    <ion-header>
      <ion-toolbar>
        <ion-title>Tab Chat</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content class="ion-padding" ref="chatContent">
      <ion-list class="bg-transparent">
        <div v-for="(msg, idx) in messages" :key="idx" class="p-1.5 w-full">
          <div
            v-if="msg.role == 'server'"
            class="w-[80%] bg-pink-200 rounded-lg p-2 shadow-md ml-auto relative">
            {{ msg.content }}
            <div
              class="absolute -left-10 top-1 rounded-[50%] border border-cyan-950 w-8 h-8 flex items-center justify-center"
              @click="playAudio(msg)">
              <ion-icon :icon="volumeMediumOutline" class="w-6 h-6" />
              <audio type="audio/wav" style="width: auto" class="m-2"></audio>
            </div>
          </div>
          <div v-else class="w-[80%] bg-green-500 text-white p-2 rounded-lg shadow-md relative">
            {{ msg.content }}
            <div
              v-if="msg.audioSrc"
              class="absolute -right-10 top-1 rounded-[50%] border border-cyan-950 w-8 h-8 flex items-center justify-center text-black"
              @click="playAudio(msg)">
              <ion-icon :icon="volumeMediumOutline" class="w-6 h-6" />
              <audio type="audio/wav" style="width: auto" class="m-2"></audio>
            </div>
          </div>
        </div>
      </ion-list>
    </ion-content>
    <audio ref="audioRef" style="width: auto" class="m-2"></audio>
    <ion-item>
      <div class="flex p-2 w-full">
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
        <ion-button @click="stopRecording" v-if="isRecording">
          <MdiStopCircleOutline width="24" height="24" />
        </ion-button>
        <ion-button @click="startRecording" v-else>
          <MdiMicrophone width="24" height="24" />
        </ion-button>
      </div>
    </ion-item>
  </ion-page>
</template>

<script setup lang="ts">
import { getApiUrl, getConversationId, setConversationId } from "@/utils/NetUtil";
import { IonToolbar, onIonViewDidEnter } from "@ionic/vue";
import io from "socket.io-client";
import Recorder from "recorder-core/recorder.wav.min";
Recorder.CLog = function () {}; // 屏蔽Recorder的日志输出
import { inject, onMounted, ref } from "vue";
import MdiMicrophone from "~icons/mdi/microphone";
import MdiStopCircleOutline from "~icons/mdi/stop-circle-outline";
import { volumeMediumOutline } from "ionicons/icons";

const MSG_TYPE_TRANSLATION = "translation";
const TTS_AUTO = true;
// cSpell: disable-next-line
const TTS_ROLE = "cosyvoice-woman-8a96d641d8d0491984c085d98870b79d";
// 存储识别结果的变量
const inputText = ref("");
const globalVar: any = inject("globalVar");
const aiConversationId = ref("");
const inputRef = ref<HTMLElement | null>(null);
const messages = ref<any>([]);
const url = getApiUrl().replace("api", "");
// const url = "http://127.0.0.1:8000/";
const socket = io(url, {
  transports: ["websocket"], // 强制使用 WebSocket 传输
});
const isWaitingServer = ref(false);
const isRecording = ref(false);
const SAMPLE_RATE = 16000;
const audioRef = ref<HTMLAudioElement | null>(null);
const lstAudioSrc = ref<string>("");
const chatContent = ref<any>(null);
// const ttsAudioBuffer = ref<SourceBuffer | null>(null);
const ttsData = ref<any>({ audioBuffer: null, msg: null });
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
  messages.value.push({ content: "你好，我是楠楠，和我聊点什么吧", role: "server" });
});
onIonViewDidEnter(async () => {
  aiConversationId.value = (await getConversationId(globalVar.user.id)) || "";
});
// 发送握手请求
socket.on("connect", () => {
  const msg = {
    key: "123456",
    ttsAuto: TTS_AUTO,
    ttsRole: TTS_ROLE,
    ttsSpeed: 1.0,
    ttsVol: 50,
    aiConversationId: aiConversationId.value,
    user: globalVar.user.name,
  };

  console.log("Connected to the server. Sending handshake...", msg);
  socket.emit("handshake", msg);
});
socket.on("message", (data) => {
  if (data.type === MSG_TYPE_TRANSLATION) {
    messages.value.push({ content: `Translation: ${data.content}`, role: "server" });
    isWaitingServer.value = false;
  } else {
    messages.value.push({ content: `Unknown: ${JSON.stringify(data)}`, role: "server" });
  }
  chatContent.value.$el.scrollToBottom(200);
});
// 处理asr结果
socket.on("msgAsr", (data) => {
  if (data.content) {
    messages.value.push({ content: data.content, role: "me", audioSrc: lstAudioSrc.value });
  }
  chatContent.value.$el.scrollToBottom(200);
});
// 处理ai chat结果
socket.on("msgChat", (data) => {
  if (messages.value.length === 0 || messages.value[messages.value.length - 1].role === "me") {
    messages.value.push({ content: data.content, role: "server" });
  } else {
    messages.value[messages.value.length - 1].content += data.content;
  }
  if (data.aiConversationId != aiConversationId.value) {
    aiConversationId.value = data.aiConversationId;
    setConversationId(globalVar.user.id, aiConversationId.value);
  }
  chatContent.value.$el.scrollToBottom(200);
});
socket.on("endChat", (data: any) => {
  console.log("==> MSG_TYPE_CHAT_END", data.content);
  isWaitingServer.value = false;
  // playAudio(messages.value[messages.value.length - 1]);
});
// 处理tts结果
socket.on("dataAudio", (data: any) => {
  if (data.type === "tts") {
    const chunk = data.data; // 接收的是二进制数据
    // console.log(chunk.length, data.data);
    if (chunk instanceof ArrayBuffer) {
      playAudioData.push(chunk);
      // 如果数据是 ArrayBuffer
      if (!ttsData.value.audioBuffer!.updating) {
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
socket.on("endAudio", (data: any) => {
  console.log("==> end_audio", data.content);
});
socket.on("handshakeResponse", (data) => console.log("handshake:", data));
socket.on("disconnect", () => console.log("Disconnected from the server."));
socket.on("error", (error) => console.error("msg error:", error));
socket.on("close", () => console.log("WebSocket connection closed."));

// 模拟发送消息
const sendTextMessage = () => {
  if (inputText.value && !isWaitingServer.value) {
    const message = JSON.stringify({
      type: "text",
      content: inputText.value,
    });
    messages.value.push({ content: inputText.value, role: "me" });

    isWaitingServer.value = true;
    inputText.value = "";
    chatContent.value.$el.scrollToBottom(200);
    if (TTS_AUTO) {
      streamAudio(() => {
        socket.emit("message", message);
      });
    } else {
      socket.emit("message", message);
    }
  }
};
function sendAudioData(data: string, finish: boolean = false) {
  if (!socket.connected) {
    console.warn("WebSocket未连接，稍后重试");
    return;
  }
  const message = JSON.stringify({
    type: "audio",
    sample: SAMPLE_RATE,
    content: data,
    finish: finish,
  });
  // console.log("==> sendData audio ", data.length, finish);
  socket.emit("message", message);
}
async function startRecording() {
  if (!isWaitingServer.value) {
    try {
      rec.open(() => {
        rec.start();
      });
      isRecording.value = true;
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

function stopRecording() {
  console.log("==> stopRecording");
  if (isRecording.value === false) return;
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
      sendAudioData("", true);
      if (TTS_AUTO) {
        streamAudio(() => {});
      }
    },
    (errMsg: any) => console.log("errMsg: " + errMsg)
  );
  isRecording.value = false;
}

function playAudio(msg: any) {
  if (isWaitingServer.value) return;
  console.log("==> playAudio", msg);
  ttsData.value.msg = msg;
  if (msg.audioSrc) {
    const audio = new Audio(msg.audioSrc); // 替换为你的音频文件路径
    audio.volume = 1; // 音量范围是0到1
    audio.play();
  } else {
    const payload = JSON.stringify({
      content: msg.content,
      role: TTS_ROLE,
    });
    streamAudio(() => {
      socket.emit("tts", payload);
    });
  }
}

function streamAudio(f = () => {}) {
  const mediaSource = new MediaSource();
  audioRef.value!.src = URL.createObjectURL(mediaSource);
  playAudioData = [];

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
      }
    });

    audioRef.value!.play();
    f();
  });
}
</script>
