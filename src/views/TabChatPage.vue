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
import RecordRTC from "recordrtc";
import { onMounted, ref } from "vue";
import MdiMicrophone from "~icons/mdi/microphone";
import MdiStopCircleOutline from "~icons/mdi/stop-circle-outline";

// 存储识别结果的变量
const inputText = ref("");
const messages = ref<any>([]);
const url = getApiUrl().replace("api", "");
// const url = http://127.0.0.1:8000/;
const socket = io(url);
const isWaitingForTranslation = ref(false);
const audioBuffer = ref<ArrayBuffer[]>([]); // 缓冲区数组
const recorder = ref<RecordRTC | null>();
const isRecording = ref(false);
const SAMPLE_RATE = 16000;

onMounted(() => {});
// 发送握手请求
socket.on("connect", () => {
  console.log("Connected to the server. Sending handshake...");
  socket.emit("handshake", { key: "123456" });
});
socket.on("message", (data) => {
  console.log("Received message:", data);
  if (data.type === "recognition") {
    messages.value.push({ content: `Recognition: ${data.content}` });
  } else if (data.type === "translation") {
    messages.value.push({ content: `Translation: ${data.content}` });
    isWaitingForTranslation.value = false;
  } else {
    messages.value.push({ content: `Unknown: ${JSON.stringify(data)}` });
    isWaitingForTranslation.value = false;
  }
});
socket.on("handshake_response", (data) => {
  console.log("handshake:", data);
});

// 模拟发送消息
const sendTextMessage = () => {
  if (inputText.value && !isWaitingForTranslation.value) {
    const message = JSON.stringify({ type: "text", content: inputText.value });
    socket.emit("message", message);
    isWaitingForTranslation.value = true;
    inputText.value = "";
  }
};
function sendData(data: ArrayBuffer) {
  if (!socket.connected) {
    console.warn("WebSocket未连接，稍后重试");
    return;
  }
  const message = JSON.stringify({ type: "audio", simple: SAMPLE_RATE, content: data });
  console.log("==> sendData", message);
  socket.emit("message", message);
}
function processBuffer(chunk_size: number = 4 * 1024) {
  if (chunk_size === -1) chunk_size = audioBuffer.value.length;
  while (audioBuffer.value.length && audioBuffer.value.length >= chunk_size) {
    // 每4KB发送一次
    const chunk: any = audioBuffer.value.splice(0, chunk_size);
    audioBuffer.value = audioBuffer.value.splice(chunk.length);
    sendData(chunk);
  }
}
async function startRecording() {
  if (!isWaitingForTranslation.value) {
    try {
      // 请求麦克风权限
      navigator.mediaDevices
        .getUserMedia({ audio: true })
        .then((stream) => {
          const config = {
            type: "audio",
            // mimeType: "audio/webm; codecs=opus", // 使用Opus编码更高效
            mimeType: "audio/webm;codecs=pcm",
            sampleRate: SAMPLE_RATE, // 16kHz采样率
            timeSlice: 200,
            ondataavailable: (e: Blob) => {
              // 处理数据块
              e.arrayBuffer().then((buffer) => {
                audioBuffer.value.push(buffer);
                processBuffer();
              });
            },
          };

          recorder.value = new RecordRTC(stream, config as RecordRTC.Options);
          recorder.value.startRecording();
        })
        .catch((error) => {
          console.error("麦克风权限获取失败", error);
          isRecording.value = false;
        });
      isRecording.value = true;
    } catch (error) {
      console.error("Error starting recording:", error);
      isRecording.value = false;
    }
  }
}

function stopRecording() {
  console.log("==> stopRecording");
  if (isRecording.value === false) return;
  if (recorder.value) {
    recorder.value.stopRecording();
  }
  processBuffer(-1);
  isRecording.value = false;
}
</script>
