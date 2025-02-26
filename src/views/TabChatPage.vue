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
import { IonToolbar } from "@ionic/vue";
import { onMounted, ref } from "vue";
import io from "socket.io-client";
import { getApiUrl } from "@/utils/NetUtil";
import MdiMicrophone from "~icons/mdi/microphone";
import MdiStopCircleOutline from "~icons/mdi/stop-circle-outline";
// import { trashOutline, createOutline } from "ionicons/icons";

// 存储识别结果的变量
const inputText = ref("");
const messages = ref<any>([]);
const url = getApiUrl().replace("api", "");
// const url = http://127.0.0.1:8000/;
const socket = io(url);
const isWaitingForTranslation = ref(false);
const mediaRecorder = ref<MediaRecorder | null>(null);
const recordedChunks = ref<any>([]);
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
async function startRecording() {
  if (!isWaitingForTranslation.value) {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: {
            sampleRate: SAMPLE_RATE,
            channelCount: 1
        } });
      mediaRecorder.value = new MediaRecorder(stream);
      recordedChunks.value = [];

      mediaRecorder.value.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunks.value.push(event.data);
        }
      };

      mediaRecorder.value.onstop = () => {
        const blob = new Blob(recordedChunks.value, { type: "audio/wav" });
        const reader = new FileReader();
        reader.onloadend = () => {
          if (typeof reader.result === "string") {
            const base64Data = reader.result!.split(",")[1];
            const message = JSON.stringify({ type: "audio", content: base64Data });
            socket.emit("message", message);
            console.log("Audio sent:", message.length);
            isWaitingForTranslation.value = true;
          } else {
            console.error("Error converting audio to base64");
          }
        };
        reader.readAsDataURL(blob);
      };
      // 将mediaRecorder的切片间隔设置为300ms（与FunASR的流式窗口匹配）
      mediaRecorder.value.start(300);
      isRecording.value = true;
    } catch (error) {
      console.error("Error starting recording:", error);
      isRecording.value = false;
    }
  }
}

function stopRecording() {
  console.log("stopRecording");
  if (mediaRecorder.value && mediaRecorder.value.state === "recording") {
    mediaRecorder.value!.stop();
  }
  isRecording.value = false;
}
</script>
