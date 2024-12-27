<template>
  <ion-modal ref="modal" id="subtaskPopModal" mode="ios">
    <ion-item>
      <ion-title>子任务</ion-title>
    </ion-item>
    <ion-content class="ion-padding">
      <ion-item>
        <ion-input v-model="valueRef.name" placeholder="添加子任务" size="5"> </ion-input>
      </ion-item>
      <ion-item>
        <div class="pre-img-block" v-for="(img, idx) in imgList" :key="idx">
          <img :src="img.data" @click="onImgClk($event, img)" />
        </div>
        <div class="pre-img-block" id="btnAdd">
          <ion-icon :icon="add" color="primary"></ion-icon>
        </div>
      </ion-item>
    </ion-content>
    <div id="button-group" class="button-group ion-button">
      <ion-button class="alert-button" fill="clear" @click="cancel()"> 取消 </ion-button>
      <ion-button class="alert-button" fill="clear" @click="confirm()"> 确定 </ion-button>
    </div>
    <ion-action-sheet
      trigger="btnAdd"
      header="选取图片"
      :buttons="actionSheetButtons"></ion-action-sheet>
    <!-- preview -->
    <ion-modal class="preview-modal" :isOpen="openPreview" @willDismiss="onPreviewDismiss">
      <ion-content @click="onPreviewClk">
        <img class="preview-img" :src="curImage.data" />
      </ion-content>
      <ion-header>
        <ion-toolbar style="--background: transparent">
          <ion-button @click="btnDelImgClk($event, curImage)" slot="end">
            <ion-icon :icon="trashOutline"></ion-icon>
          </ion-button>
        </ion-toolbar>
      </ion-header>
    </ion-modal>
  </ion-modal>
</template>

<script lang="ts" setup>
import { Subtask } from "@/modal/UserData";
import { cameraAndSetImage, getImage, loadAndSetImage } from "@/utils/ImgMgr";
import { createTriggerController } from "@/utils/Overlay";
import { alertController, IonInput, IonToolbar, IonActionSheet } from "@ionic/vue";
import { add, trashOutline } from "ionicons/icons";
import { onMounted, ref, watch } from "vue";

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

const btnDelImgClk = async (event: any, img: any) => {
  const alert = await alertController.create({
    header: "确认删除",
    buttons: [
      {
        text: "确定",
        handler: () => {
          const imgId = img.id;
          console.log("imgId", imgId);
          for (let i = 0; i < valueRef.value.imgIds.length; i++) {
            if (valueRef.value.imgIds[i] === imgId) {
              valueRef.value.imgIds.splice(i, 1);
              imgList.value.splice(i, 1);
              break;
            }
          }
          openPreview.value = false;
        },
      },
      "取消",
    ],
  });
  await alert.present();
};

const actionSheetButtons = [
  {
    text: "拍照",
    handler: async () => {
      const imgId = await cameraAndSetImage(undefined, canvasHeight.value, canvasWidth.value);
      console.log("newImgId", imgId);
      if (imgId === null) return;
      imgList.value.push({
        id: imgId,
        data: await getImage(imgId),
      });
      valueRef.value.imgIds.push(imgId);
    },
  },
  {
    text: "相册",
    handler: async () => {
      const imgId = await loadAndSetImage(undefined, canvasHeight.value, canvasWidth.value);
      console.log("newImgId", imgId);
      if (imgId === null) return;
      imgList.value.push({
        id: imgId,
        data: await getImage(imgId),
      });
      valueRef.value.imgIds.push(imgId);
    },
  },
  {
    text: "取消",
    role: "cancel",
  },
];

const onImgClk = (_event: any, img: any) => {
  openPreview.value = true;
  curImage.value = img;
};

const onPreviewDismiss = () => (openPreview.value = false);
const onPreviewClk = () => {
  openPreview.value = false;
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
  --height: 100%;
  --width: 95%;
}
.preview-modal img {
  /* max-height: 100%; */
  /* max-width: 100%; */
  width: 100%;
  height: 100%;
  object-fit: contain;

  max-height: 90vh;
  max-width: 90vw;
}

.preview-modal ion-content::part(scroll) {
  display: flex;
  align-items: center;
  justify-content: center;
}
.preview-modal ion-content::part(background) {
  background-color: transparent !important;
}
.preview-modal::part(content) {
  /* padding: 10px 10px 10px 10px; */
  /* position: absolute; */
  /* left: 0; */
  /* right: 0; */
  /* top: 0; */
  /* bottom: 0; */
  /* display: flex; */
  /* flex-direction: column; */
  width: 100%;
  /* height: auto; */
  background-color: transparent !important;
  max-height: 100%;
  /* align-items: center; */
  /* justify-content: center; */
}
.preview-modal::part(backdrop) {
  background-color: var(--ion-color-dark) !important;
  opacity: 0.3 !important;
}
</style>
