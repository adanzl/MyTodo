<template>
  <ion-modal
    ref="modal"
    id="subtaskPopModal"
    mode="ios"
    aria-hidden="false"
    class="backdrop"
    @willDismiss="onModalDismiss">
    <ion-item>
      <ion-title>子任务</ion-title>
    </ion-item>
    <ion-content class="ion-padding">
      <ion-item>
        <Icon icon="mdi:card-text-outline" class="w-[1.6em] h-[1.6em]" slot="start" />
        <ion-input v-model="valueRef.name" placeholder="输入子任务名称" size="5"> </ion-input>
      </ion-item>
      <ion-item @click="btnRewardClk" detail="true">
        <Icon icon="mdi:gift-outline" class="text-red-500 w-[1.6em] h-[1.6em]" slot="start" />
        <ion-label>奖励</ion-label>
        <div slot="end" class="flex items-center">
          <Icon icon="mdi:star" class="text-red-500 w-5 h-5" />
          <ion-label class="w-5 text-right">{{ valueRef.score ?? 0 }}</ion-label>
        </div>
      </ion-item>
      <ion-item lines="none">
        <div class="pre-img-block" v-for="(img, idx) in imgList" :key="idx">
          <img :src="img.data" @click="onImgClk($event, img)" />
        </div>
        <div class="pre-img-block" id="btnAdd">
          <ion-icon :icon="add" color="success" />
        </div>
      </ion-item>
    </ion-content>
    <ion-footer class="!flex">
      <ion-button class="flex-1 text-gray-400" fill="clear" @click="cancel()"> 取消 </ion-button>
      <ion-button class="flex-1 text-orange-400" fill="clear" @click="confirm()"> 确定 </ion-button>
    </ion-footer>
    <ion-action-sheet
      trigger="btnAdd"
      header="选取图片"
      :buttons="actionSheetButtons"></ion-action-sheet>
    <!-- preview -->
    <ion-modal
      class="preview-modal backdrop transparent"
      :isOpen="openPreview"
      @willDismiss="onPreviewDismiss">
      <div class="flex justify-center items-center h-full" @click="onPreviewClk">
        <img class="object-contain w-full max-w-[90%]" :src="curImage.data" />
      </div>
      <ion-header>
        <ion-toolbar class="transparent">
          <ion-button @click="btnDelImgClk($event, curImage)" slot="end">
            <ion-icon :icon="trashOutline"></ion-icon>
          </ion-button>
        </ion-toolbar>
      </ion-header>
    </ion-modal>
  </ion-modal>
</template>

<script lang="ts" setup>
import { Subtask } from "@/types/UserData";
import { cameraAndSetImage, getImage, loadAndSetImage } from "@/utils/ImgMgr";
import { createTriggerController } from "@/utils/Overlay";
import { alertController, IonActionSheet, IonInput, IonToolbar } from "@ionic/vue";
import { add, trashOutline } from "ionicons/icons";
import { inject, onMounted, ref, watch } from "vue";

const props = defineProps({
  trigger: {
    type: String,
    default: "",
  },
  value: {
    type: Object,
  },
});
const globalVar = inject("globalVar") as any;
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
      console.log("set props.value", v);
      valueRef.value = Subtask.Copy(v as Subtask);
      imgList.value = [];
      for (const imgId of v!.imgIds) {
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
      "取消",
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
function onModalDismiss() {}
const onPreviewDismiss = () => (openPreview.value = false);
const onPreviewClk = () => {
  openPreview.value = false;
};

async function btnRewardClk() {
  if (globalVar!.user?.admin !== 1) return;
  const alert = await alertController.create({
    header: "日程奖励",
    inputs: [{ type: "number", value: valueRef.value.score, placeholder: "奖励积分" }],
    buttons: [
      {
        text: "取消",
        role: "cancel",
      },
      {
        text: "确定",
        handler: (e) => {
          valueRef.value.score = parseInt(e[0]);
        },
      },
    ],
  });
  await alert.present();
}
</script>

<style scoped>
ion-modal {
  --height: 50%;
  --width: 95%;
}

.preview-modal {
  --height: 100%;
  --width: 95%;
}
</style>
