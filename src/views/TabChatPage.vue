<template>
  <!-- 暂时不用了 -->
  <ion-page class="main-bg" id="main-content">
    <ion-header>
      <ion-toolbar>
        <ion-title>Tab Pic</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content class="ion-padding">
      <ion-list>
        <ion-item v-for="(msg, idx) in messages" :key="idx">
          {{ msg.content }}
        </ion-item>
      </ion-list>
    </ion-content>
    <audio ref="audioRef" type="audio/wav" controls style="width: auto" class="m-2"></audio>
    <ion-item>
      <div class="flex p-2 w-full">
        <ion-input
          class="flex-1 mr-1"
          v-model="inputText"
          placeholder="Type a message"
          fill="solid"
          style="--color: #000"
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
import { getApiUrl } from "@/utils/NetUtil";
import { IonToolbar } from "@ionic/vue";
import io from "socket.io-client";
import Recorder from "recorder-core/recorder.wav.min";
Recorder.CLog = function () {}; // 屏蔽Recorder的日志输出
import { onMounted, ref } from "vue";
import MdiMicrophone from "~icons/mdi/microphone";
import MdiStopCircleOutline from "~icons/mdi/stop-circle-outline";

// 存储识别结果的变量
const inputText = ref("");
const messages = ref<any>([]);
const url = getApiUrl().replace("api", "");
// const url = "http://127.0.0.1:8000/";
const socket = io(url);
const isWaitingForTranslation = ref(false);
const isRecording = ref(false);
const SAMPLE_RATE = 16000;
const audioRef = ref<HTMLAudioElement | null>(null);
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
let sampleBuf = new Int16Array();

onMounted(() => {});
// 发送握手请求
socket.on("connect", () => {
  console.log("Connected to the server. Sending handshake...");
  socket.emit("handshake", { key: "123456" });
});
socket.on("message", (data) => {
  console.log("Received message:", data);
  if (data.type === "recognition") {
    if (data.content) {
      messages.value.push({ content: `Recognition: ${data.content}` });
    }
  } else if (data.type === "translation") {
    messages.value.push({ content: `Translation: ${data.content}` });
    isWaitingForTranslation.value = false;
  } else {
    messages.value.push({ content: `Unknown: ${JSON.stringify(data)}` });
    isWaitingForTranslation.value = false;
  }
});
socket.on("handshake_response", (data) => console.log("handshake:", data));
socket.on("disconnect", () => console.log("Disconnected from the server."));
socket.on("error", (error) => console.error("WebSocket error:", error));
socket.on("close", () => console.log("WebSocket connection closed."));

// 模拟发送消息
const sendTextMessage = () => {
  if (inputText.value && !isWaitingForTranslation.value) {
    const message = JSON.stringify({ type: "text", content: inputText.value });
    socket.emit("message", message);
    isWaitingForTranslation.value = true;
    inputText.value = "";
  }
};
function sendData(data: string, finish: boolean = false) {
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
  if (!isWaitingForTranslation.value) {
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

  sampleBuf = Int16Array.from([...sampleBuf, ...data_16k]);
  const chunk_size = 960; // for asr chunk_size [5, 10, 5]
  // info_div.innerHTML = "" + bufferDuration / 1000 + "s";
  while (sampleBuf.length >= chunk_size) {
    const sendBuf = sampleBuf.slice(0, chunk_size);
    sampleBuf = sampleBuf.slice(chunk_size, sampleBuf.length);
    const uint8 = new Uint8Array(sendBuf.buffer);
    const base64Data = btoa(String.fromCharCode(...uint8));
    // console.log("==> recProcess ", base64Data);
    // 通过 WebSocket 发送 Base64 编码的音频数据
    sendData(base64Data);
  }
}

function stopRecording() {
  console.log("==> stopRecording");
  if (isRecording.value === false) return;
  rec.stop(
    (blob: Blob) => {
      audioRef.value!.src = (window.URL || webkitURL).createObjectURL(blob);
      // 将音频文件转换为 Base64 编码
      // const reader = new FileReader();
      // reader.onloadend = () => {
      //   if (typeof reader.result === "string") {
      //     const base64Data = reader.result!.split(",")[1];
      //     // 通过 WebSocket 发送 Base64 编码的音频数据
      //     sendData(base64Data, true);
      //   }
      // };
      // reader.readAsDataURL(blob);
      if (sampleBuf.length) {
        const sendBuf = sampleBuf;
        sampleBuf = new Int16Array();
        const uint8 = new Uint8Array(sendBuf.buffer);
        const base64Data = btoa(String.fromCharCode(...uint8));
        sendData(base64Data);
      }
      sendData("", true);
    },
    (errMsg: any) => console.log("errMsg: " + errMsg)
  );
  isRecording.value = false;
}
</script>
