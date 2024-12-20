<template>
  <ion-page>
    <ion-header>
      <ion-toolbar>
        <ion-title>Tab 2</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content :fullscreen="true">
      <ion-header collapse="condense">
        <ion-toolbar>
          <ion-title size="large">Tab 2</ion-title>
        </ion-toolbar>
      </ion-header>
      <ExploreContainer name="Tab 2 page" />
      <ion-button @click="loadImage">选择图片</ion-button>
      <canvas ref="canvasRef" :width="canvasWidth" :height="canvasHeight" />
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import ExploreContainer from "@/components/ExploreContainer.vue";
import { IonContent, IonHeader, IonPage, IonTitle, IonToolbar } from "@ionic/vue";
import { ref } from "vue";

const canvasRef = ref<HTMLCanvasElement>();
const canvasWidth = ref(400); // 设置canvas的宽度
const canvasHeight = ref(300); // 设置canvas的高度

const loadImage = () => {
  const fileInput = document.createElement("input");
  fileInput.type = "file";
  fileInput.accept = "image/*";
  fileInput.addEventListener("change", async (event: any) => {
    const file = event.target?.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      const imageUrl = e.target!.result as string;
      const img = new Image();
      img.src = imageUrl;
      img.onload = () => {
        if (canvasRef.value) {
          const ctx = canvasRef.value.getContext("2d");
          if (ctx) {
            ctx.drawImage(img, 0, 0, canvasWidth.value, canvasHeight.value);
            canvasRef.value.toBlob((blob: any) => {
              const reader = new FileReader();
              reader.onload = () => {
                const base64 = reader.result as string;
                console.log("Base64 WebP Image:", base64);
                // 在这里可以使用 base64 字符串
              };
              reader.readAsDataURL(blob);
            }, "image/webp");
          }
        }
      };
    };
    reader.readAsDataURL(file);
  });
  fileInput.click();
};
</script>
