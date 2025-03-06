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
    <audio ref="audioRef" type="audio/wav" controls style="width: auto;" class="m-2"></audio>
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
// const url = "http://127.0.0.1:8000/";
const socket = io(url);
const isWaitingForTranslation = ref(false);
const recorder = ref<RecordRTC | null>();
const isRecording = ref(false);
const SAMPLE_RATE = 48000;
const audioRef = ref<HTMLAudioElement | null>(null);

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
socket.on("disconnect", () => {
  console.log("Disconnected from the server.");
});
socket.on("error", (error) => {
  console.error("WebSocket error:", error);
});
socket.on("close", () => {
  console.log("WebSocket connection closed.");
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
  console.log("==> sendData audio ", data.length, finish);
  socket.emit("message", message);
}
async function startRecording() {
  if (!isWaitingForTranslation.value) {
    try {
      // 请求麦克风权限
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const config = {
        type: "audio",
        // mimeType: "audio/webm; codecs=opus", // 使用Opus编码更高效
        mimeType: "audio/wav",
        recorderType: RecordRTC.StereoAudioRecorder,
        sampleRate: SAMPLE_RATE, // 16kHz采样率
        numberOfAudioChannels: 1,
      };

      recorder.value = new RecordRTC(stream, config as RecordRTC.Options);
      recorder.value.startRecording();
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
    recorder.value.stopRecording(async () => {
      // 处理数据块
      // e.arrayBuffer().then((buffer) => {
      //   audioBuffer.value.push(buffer);
      //   processBuffer();
      // });
      // 获取录制的音频文件
      const blob = await recorder.value!.getBlob();
      // 创建音频 URL
      const audioUrl = URL.createObjectURL(blob);
      // 将 URL 赋值给 <audio> 标签
      if (audioRef.value) {
        audioRef.value.src = audioUrl;
      }
      // 将音频文件转换为 Base64 编码
      const reader = new FileReader();
      reader.onloadend = () => {
        if (typeof reader.result === "string") {
          const base64Data = reader.result!.split(",")[1];
          // 通过 WebSocket 发送 Base64 编码的音频数据
          sendData(base64Data, true);
        }
      };
      reader.readAsDataURL(blob);
    });
  }
  isRecording.value = false;
}
</script>
