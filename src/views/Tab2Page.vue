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
          <ion-buttons slot="end">
            <ion-button @click="loadImage">选择图片</ion-button>
          </ion-buttons>
        </ion-toolbar>
      </ion-header>
      <canvas ref="canvasRef" :width="canvasWidth" :height="canvasHeight" />
      <ion-list>
        <ion-item-sliding v-for="(item, idx) in picList" :key="idx">
          <ion-item @click="onItemClk($event, item)">
            <ion-label>{{ item.id }}</ion-label>
            <img :src="item.data" style="height: 60px" />
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
import { delPic, getPicList, setPic } from "@/modal/NetUtil";
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

const canvasRef = ref<HTMLCanvasElement>();
const canvasWidth = ref(400); // 设置canvas的宽度
const canvasHeight = ref(300); // 设置canvas的高度
const picList = ref<{ id: number; data: string }[]>([]);

const calcPos = (img: HTMLImageElement, canvasWidth: number, canvasHeight: number) => {
  // 计算图像的宽高比
  const imageRatio = img.width / img.height;
  // 计算画布的宽高比
  const canvasRatio = canvasWidth / canvasHeight;

  let drawWidth, drawHeight;

  if (imageRatio > canvasRatio) {
    // 如果图像的宽高比大于画布的宽高比，则以画布的宽度为基准计算绘制的高度
    drawWidth = canvasWidth;
    drawHeight = canvasWidth / imageRatio;
  } else {
    // 如果图像的宽高比小于或等于画布的宽高比，则以画布的高度为基准计算绘制的宽度
    drawHeight = canvasHeight;
    drawWidth = canvasHeight * imageRatio;
  }
  // 计算图像在画布上的绘制位置，使其居中显示
  const dx = (canvasWidth - drawWidth) / 2;
  const dy = (canvasHeight - drawHeight) / 2;
  return { dx, dy, drawWidth, drawHeight };
};

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
            const { dx, dy, drawWidth, drawHeight } = calcPos(
              img,
              canvasWidth.value,
              canvasHeight.value
            );
            ctx.clearRect(0, 0, canvasWidth.value, canvasHeight.value);
            ctx.drawImage(img, dx, dy, drawWidth, drawHeight);
            canvasRef.value.toBlob((blob: any) => {
              const reader = new FileReader();
              reader.onload = () => {
                const base64 = reader.result as string;
                setPic(undefined, base64).then((res) => {
                  console.log("setPic", res);
                  getPicList().then((res) => {
                    picList.value = res;
                  });
                });
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
onMounted(() => {
  getPicList().then((res) => {
    picList.value = res;
    console.log("picList", picList.value);
  });
});
const onItemClk = (event: any, item: any) => {
  const img = new Image();
  img.src = item.data;
  img.onload = () => {
    if (canvasRef.value) {
      const ctx = canvasRef.value.getContext("2d");
      if (ctx) {
        const { dx, dy, drawWidth, drawHeight } = calcPos(
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
          delPic(item.id).then((res) => {
            console.log("delPic", res);
            getPicList().then((res) => {
              picList.value = res;
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
            const { dx, dy, drawWidth, drawHeight } = calcPos(
              img,
              canvasWidth.value,
              canvasHeight.value
            );
            ctx.clearRect(0, 0, canvasWidth.value, canvasHeight.value);
            ctx.drawImage(img, dx, dy, drawWidth, drawHeight);
            canvasRef.value.toBlob((blob: any) => {
              const reader = new FileReader();
              reader.onload = () => {
                const base64 = reader.result as string;
                setPic(item.id, base64).then((res) => {
                  console.log("setPic", res);
                  getPicList().then((res) => {
                    picList.value = res;
                  });
                });
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
