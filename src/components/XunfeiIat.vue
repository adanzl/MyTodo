<template>
  <div>
    <ion-button @click="startRecording" :disabled="isRecording">开始录音</ion-button>
    <ion-button @click="stopRecording" :disabled="!isRecording">停止录音</ion-button>
    <pre>{{ result }}</pre>
  </div>
</template>

<script lang="ts" setup>
import { ref } from "vue";
import CryptoJS from "crypto-js";

// 从环境变量或配置文件中获取 APPID、API Key 和 API Secret
const appId = "5167a2f1";
const apiKey = "274b9ed8d21525ebb0e4ef276b0c68dc";
const apiSecret = "ca61f5b7e311b574986d095e44665d64";

const result = ref<string>("");
const isRecording = ref(false);
let mediaRecorder: MediaRecorder | null = null;
let ws: WebSocket;

// 生成带有签名的 WebSocket 握手 URL
function generateWsUrl(apiKey: string, apiSecret: string): string {
  let url = "wss://iat-api.xfyun.cn/v2/iat";
  const host = "iat-api.xfyun.cn";
  const date = new Date().toUTCString();
  const algorithm = "hmac-sha256";
  const headers = "host date request-line";
  const signatureOrigin = `host: ${host}\ndate: ${date}\nGET /v2/iat HTTP/1.1`;
  const signatureSha = CryptoJS.HmacSHA256(signatureOrigin, apiSecret);
  const signature = CryptoJS.enc.Base64.stringify(signatureSha);
  const authorizationOrigin = `api_key="${apiKey}", algorithm="${algorithm}", headers="${headers}", signature="${signature}"`;
  const authorization = btoa(authorizationOrigin);
  url = `${url}?authorization=${authorization}&date=${encodeURIComponent(date)}&host=${host}`;
  return url;
}

// 开始录音
const startRecording = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);

    const wsUrl = generateWsUrl(apiKey, apiSecret);
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log("WebSocket 连接已建立");
      sendInitMessage(ws);
      isRecording.value = true;

      mediaRecorder?.start();

      mediaRecorder?.addEventListener("dataavailable", (event) => {
        if (event.data.size > 0) {
          const reader = new FileReader();
          reader.onload = (e) => {
            const buffer = new Uint8Array(e.target?.result as ArrayBuffer);
            const message = {
              data: {
                status: 1,
                format: "audio/L16;rate=16000",
                encoding: "raw",
                audio: btoa(String.fromCharCode.apply(null, Array.from(buffer))),
              },
            };
            ws?.send(JSON.stringify(message));
          };
          reader.readAsArrayBuffer(event.data);
        }
      });

      mediaRecorder?.addEventListener("stop", () => {
        const endMessage = {
          data: {
            status: 2,
            format: "audio/L16;rate=16000",
            encoding: "raw",
            audio: "",
          },
        };
        ws?.send(JSON.stringify(endMessage));
      });
    };

    ws.onmessage = (event) => {
      if (typeof event.data === "string") {
        try {
          const response = JSON.parse(event.data);
          result.value += JSON.stringify(response, null, 2);
          if (response.code === 0 && response.data.status === 2) {
            console.log("所有结果已返回，关闭连接");
            ws?.close(1000);
          }
        } catch (error) {
          console.error("解析服务器响应时出错:", error);
        }
      }
    };

    ws.onclose = (event: CloseEvent) => {
      console.log(`WebSocket 连接已关闭，代码: ${event.code}，原因: ${event.reason}`);
      isRecording.value = false;
    };

    ws.onerror = (error: Event) => {
      console.error("WebSocket 连接出错:", error);
      isRecording.value = false;
    };
  } catch (error) {
    console.error("开始录音失败:", error);
  }
};

// 停止录音
const stopRecording = () => {
  mediaRecorder?.stop();
};

// 发送初始化消息
const sendInitMessage = (ws: WebSocket) => {
  const initMessage = {
    common: {
      app_id: appId,
    },
    business: {
      language: "zh_cn",
      domain: "iat",
      accent: "mandarin",
      vinfo: 1, // cSpell: disable-line
      vad_eos: 5000,
    },
    data: {
      status: 0,
      format: "audio/L16;rate=16000",
      encoding: "raw",
      audio: "",
    },
  };
  ws.send(JSON.stringify(initMessage));
};
</script>

<style scoped>
/* 可以添加样式 */
</style>
