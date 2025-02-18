<template>
  <!-- 暂时不用了 -->
  <ion-page class="main-bg" id="main-content">
    <ion-header>
      <ion-toolbar>
        <ion-title>Tab Pic</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content class="ion-padding">
      <ion-textarea ref="historyText" placeholder="语音识别结果将显示在这里"></ion-textarea>
      <!-- 语音输入按钮 -->
      <XunfeiIat />
      <!-- 模拟发送按钮 -->
      <ion-button expand="full" @click="sendMessage" :disabled="!historyText">发送</ion-button>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import { IonToolbar, IonTextarea } from "@ionic/vue";
import { onMounted, ref } from "vue";
import XunfeiIat from "@/components/XunfeiIat.vue";
// import { trashOutline, createOutline } from "ionicons/icons";

// 存储识别结果的变量
const historyText = ref("");

onMounted(() => {});

// 模拟发送消息
const sendMessage = () => {
  if (historyText.value) {
    console.log("发送的消息:", historyText.value);
    historyText.value = "";
  }
};
</script>
