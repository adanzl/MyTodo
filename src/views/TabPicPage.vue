<template>
  <!-- 暂时不用了 -->
  <ion-page class="main-bg" id="main-content">
    <ion-header>
      <ion-toolbar>
        <ion-title>Tab Pic</ion-title>
        <ion-buttons slot="end">
          <ServerRemoteBadge />
        </ion-buttons>
      </ion-toolbar>
    </ion-header>
    <ion-item collapse="condense">
      <ion-toolbar>
        <h2 size="large">Tab</h2>
        <ion-buttons slot="end">
          <ion-button @click="loadImage">选择图片</ion-button>
        </ion-buttons>
      </ion-toolbar>
    </ion-item>
    <canvas ref="canvasRef" :width="canvasWidth" :height="canvasHeight" />
    <ion-content>
      <ion-list>
        <ion-item-sliding v-for="(item, idx) in picList" :key="idx">
          <ion-item @click="onItemClk($event, item)">
            <ion-label>{{ item.id }}</ion-label>
            <img :src="item.data" class="max-w-16 max-h-16" />
          </ion-item>
          <ion-item-options side="end">
            <ion-item-option @click="btnModifyClk($event, item)">
              <ion-icon :icon="createOutline"></ion-icon>
            </ion-item-option>
            <ion-item-option color="danger" @click="btnRemoveClk($event, item)">
              <ion-icon :icon="trashOutline"></ion-icon>
            </ion-item-option>
          </ion-item-options>
        </ion-item-sliding>
      </ion-list>
    </ion-content>
  </ion-page>
</template>

<script setup lang="ts">
import ServerRemoteBadge from "@/components/ServerRemoteBadge.vue";
import { getPicList } from "@/utils/NetUtil";
import {
  IonItemSliding,
  IonPage,
  IonToolbar,
  IonItemOption,
  IonItemOptions,
  alertController,
} from "@ionic/vue";
import { onMounted, ref } from "vue";
import { trashOutline, createOutline } from "ionicons/icons";
import { calcImgPos } from "@/utils/Math";
import { loadAndSetImage, delImage } from "@/utils/ImgMgr";

const canvasRef = ref<HTMLCanvasElement>();
const canvasWidth = ref(400); // 设置canvas的宽度
const canvasHeight = ref(300); // 设置canvas的高度
const picList = ref<{ id: number; data: string }[]>([]);

onMounted(() => {
  getPicList().then((res) => {
    picList.value = res.data;
    console.log("picList", picList.value);
  });
});
const loadImage = async () => {
  loadAndSetImage(undefined, canvasHeight.value, canvasWidth.value).then((res) => {
    console.log("setPic id: ", res);
    if (res !== null) {
      getPicList().then((res) => {
        picList.value = res.data;
      });
    }
  });
};
const onItemClk = (event: any, item: any) => {
  const img = new Image();
  img.src = item.data;
  img.onload = () => {
    if (canvasRef.value) {
      const ctx = canvasRef.value.getContext("2d");
      if (ctx) {
        const { dx, dy, drawWidth, drawHeight } = calcImgPos(
          img,
          canvasWidth.value,
          canvasHeight.value
        );
        ctx.clearRect(0, 0, canvasWidth.value, canvasHeight.value);
        ctx.drawImage(img, dx, dy, drawWidth, drawHeight);
      }
    }
  };
};
const btnRemoveClk = async (_event: any, item: any) => {
  const alert = await alertController.create({
    header: "Confirm",
    message: "确认删除这张图片么 [" + item.id + "]",
    buttons: [
      {
        text: "OK",
        handler: () => {
          console.log("btnRemoveClk", item.id);
          delImage(item.id).then((res) => {
            console.log("delPic", res);
            getPicList().then((res) => {
              picList.value = res.data;
            });
          });
        },
      },
      "Cancel",
    ],
  });
  await alert.present();
};
const btnModifyClk = (event: any, item: any) => {
  loadAndSetImage(item.id, canvasHeight.value, canvasWidth.value).then((res) => {
    console.log("setPic id: ", res);
    if (res !== null) {
      getPicList().then((res) => {
        picList.value = res.data;
      });
    }
  });
};
</script>
