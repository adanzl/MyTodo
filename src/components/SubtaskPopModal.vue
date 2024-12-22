<template>
  <ion-modal ref="modal" aria-hidden="true" id="subtaskPopModal" mode="ios">
    <ion-item>
      <ion-title>子任务</ion-title>
    </ion-item>
    <ion-content class="ion-padding">
      <ion-item>
        <ion-input v-model="valueRef.name" placeholder="添加子任务"> </ion-input>
      </ion-item>
      <ion-item>
        <div class="pre-img-block" v-for="(img, idx) in imgList" :key="idx">
          <img :src="img.data" @click="onImgClk($event, img)" />
        </div>
        <div class="pre-img-block" @click="btnAddImgClk">
          <ion-icon :icon="add"></ion-icon>
        </div>
      </ion-item>
    </ion-content>
    <div id="button-group" class="button-group ion-button">
      <ion-button class="alert-button" fill="clear" @click="cancel()"> 取消 </ion-button>
      <ion-button class="alert-button" fill="clear" @click="confirm()"> 确定 </ion-button>
    </div>
    <ion-modal
      class="preview-modal"
      :isOpen="openPreview"
      @willDismiss="
        () => {
          openPreview = false;
        }
      ">
      <img :src="curImage.data" />
      <ion-button style="position: relative" @click="btnModifyImgClk($event, curImage)">
        Modify Image</ion-button
      >
    </ion-modal>
  </ion-modal>
</template>

<script lang="ts" setup>
import { getImage, setImage } from "@/utils/ImgCache";
import { createTriggerController } from "@/utils/Overlay";
import { Subtask } from "@/modal/UserData";
import { IonInput } from "@ionic/vue";
import { add } from "ionicons/icons";
import { onMounted, ref, watch } from "vue";
import { calcImgPos } from "@/utils/Math";

const props = defineProps({
  trigger: {
    type: String,
    default: "",
  },
  value: {
    type: Object,
    default: new Subtask(),
  },
});
const triggerController = createTriggerController();
const modal = ref();
const valueRef = ref<Subtask>(new Subtask()); // 子任务结构
const imgList = ref<{ id: number; data: string }[]>([]);
const canvasHeight = ref(400);
const canvasWidth = ref(400);
const openPreview = ref(false);
const curImage = ref();

const cancel = () => {
  modal.value.$el!.dismiss();
};
const confirm = () => {
  emits("update:value", valueRef.value);
  modal.value.$el!.dismiss();
};

const emits = defineEmits(["update:value"]);
onMounted(() => {
  watch(
    () => props.value,
    async (v) => {
      if (!v) {
        valueRef.value = new Subtask();
        imgList.value = [];
        return;
      }
      valueRef.value = Subtask.Copy(v as Subtask);
      imgList.value = [];
      for (const imgId of v.imgIds) {
        imgList.value.push({
          id: parseInt(imgId),
          data: await getImage(parseInt(imgId)),
        });
      }
    }
  );
  watch(
    () => props.trigger,
    (newValue) => {
      if (newValue) {
        triggerController.addClickListener(modal.value!.$el!, newValue);
      }
    },
    { immediate: true } // 立即执行一次 watcher
  );
});

const loadImage = async (imgId?: number): Promise<number | null> => {
  return new Promise((resolve) => {
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = "image/*";
    fileInput.addEventListener("change", async (event: any) => {
      const file = event.target?.files[0];
      if (!file) {
        resolve(null);
        return;
      }
      const reader = new FileReader();
      reader.onload = (e) => {
        const imageUrl = e.target!.result as string;
        const img = new Image();
        img.src = imageUrl;
        img.onload = () => {
          const canvas = document.createElement("canvas");
          const ctx = canvas.getContext("2d");
          if (!ctx) {
            resolve(null);
            return;
          }
          const { dx, dy, drawWidth, drawHeight } = calcImgPos(
            img,
            canvasWidth.value,
            canvasHeight.value
          );
          ctx.clearRect(0, 0, canvasWidth.value, canvasHeight.value);
          ctx.drawImage(img, dx, dy, drawWidth, drawHeight);
          canvas.toBlob((blob: any) => {
            const reader = new FileReader();
            reader.onload = async () => {
              const base64 = reader.result as string;
              const ret = await setImage(imgId, base64);
              return resolve(parseInt(ret));
            };
            reader.readAsDataURL(blob);
          }, "image/webp");
        };
      };
      reader.readAsDataURL(file);
    });
    fileInput.click();
  });
};
const btnAddImgClk = async () => {
  const newImgId = await loadImage(undefined);
  console.log("newImgId", newImgId);
  // imgList.value.push({
  //   id: parseInt(newImgId),
  //   data: await getImage(parseInt(newImgId)),
  // });
  // valueRef.value.imgIds.push(parseInt(newImgId));
};

const btnModifyImgClk = async (event: any, img: any) => {
  const imgId = await loadImage(img.id);
  console.log("imgId", imgId);
  if (imgId === null) return;
  for (const item of imgList.value) {
    if (item.id == img.id) {
      item.data = await getImage(imgId);
      break;
    }
  }
};

const onImgClk = (_event: any, img: any) => {
  openPreview.value = true;
  curImage.value = img;
};
</script>

<style scoped>
ion-modal {
  --height: 50%;
  --width: 95%;
}
.option-item {
  display: block;
  overflow: hidden;
}
.option-item::part(label) {
  margin: 0;
  width: 100%;
}

.button-group {
  display: flex !important;
  flex-direction: row;
  padding-inline-start: 8px;
  padding-inline-end: 8px;
  margin: 0;
  border-radius: 0;
  min-width: 50%;
  border-top: 0.55px solid rgba(var(--ion-text-color-rgb, 0, 0, 0), 0.2);
  border-right: 0.55px solid rgba(var(--ion-text-color-rgb, 0, 0, 0), 0.2);
  background-color: transparent;
  color: var(--ion-color-primary, #0054e9);
  overflow: hidden;
}
.button-group ion-button {
  flex-basis: auto;
  flex-grow: 1;
  flex-shrink: 1;
}
.preview-modal {
  --height: auto;
  --width: auto;
}
.preview-modal::part(content) {
  padding: 10px;
}
.preview-modal::part(backdrop) {
  background-color: var(--ion-color-dark) !important;
  opacity: 0.3 !important;
}
</style>
