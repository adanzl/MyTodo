<template>
  <ion-modal
    ref="modal"
    aria-hidden="false"
    id="main"
    mode="ios"
    @ionModalDidPresent="onModalPresent"
    @ionModalDidDismiss="onModalDismiss">
    <ion-header>
      <ion-toolbar>
        <ion-title>Lottery Setting</ion-title>
      </ion-toolbar>
    </ion-header>
    <canvas ref="canvasRef" :width="canvasWidth" :height="canvasHeight" />
    <ion-button @click="btnModifyClk()" :disabled="curItem === null">Set Img</ion-button>
    <ion-content>
      <ion-grid>
        <ion-row>
          <ion-col size="2"> - </ion-col>
          <ion-col size="5"> 名称 </ion-col>
          <ion-col size="2"> 权重 </ion-col>
          <ion-col> 操作 </ion-col>
        </ion-row>
        <ion-row>
          <ion-col size="2" @click="onItemClk($event, nLottery)">
            <img :src="avatar" class="max-w-8 max-h-8" />
          </ion-col>
          <ion-col size="5">
            <ion-input
              class="w-full text-xs h-8 min-h-0 color-name"
              fill="solid"
              mode="md"
              placeholder="新建"
              :value="nLottery.name"
              @ionChange="onInputChange($event, nLottery, 'name')" />
          </ion-col>
          <ion-col size="2">
            <ion-input
              mode="md"
              class="w-full grow h-8 min-h-0"
              fill="outline"
              :value="nLottery.weight"
              @ionChange="onInputChange($event, nLottery, 'weight')" />
          </ion-col>
          <ion-col>
            <button class="w-8 h-full" @click="btnSaveClk($event, nLottery, -1)">
              <ion-icon :icon="saveOutline" />
            </button>
          </ion-col>
        </ion-row>
        <ion-row v-for="(lottery, idx) in lotteryData.giftList" :key="idx">
          <ion-col size="2" @click="onItemClk($event, lottery)">
            <img :src="lottery.img || avatar" class="max-w-8 max-h-8" />
          </ion-col>
          <ion-col size="5">
            <ion-input
              class="w-full text-xs h-8 min-h-0 color-name"
              fill="solid"
              mode="md"
              :value="lottery.name"
              @ionChange="onInputChange($event, lottery, 'name')" />
          </ion-col>
          <ion-col size="2">
            <ion-input
              mode="md"
              class="w-full grow h-8 min-h-0"
              fill="outline"
              :value="lottery.weight"
              @ionChange="onInputChange($event, lottery, 'weight')" />
          </ion-col>
          <ion-col>
            <button class="w-8 h-full pt-1" @click="btnRemoveClk($event, lottery, idx)">
              <ion-icon :icon="removeCircleOutline" class="w-5 h-5" />
            </button>
          </ion-col>
        </ion-row>
      </ion-grid>
    </ion-content>
    <ion-footer>
      <div class="flex">
        <ion-button class="flex-1 text-gray-400" fill="clear" @click="cancel()">取消</ion-button>
        <ion-button class="flex-1 text-orange-400" fill="clear" @click="confirm()">确定</ion-button>
      </div>
    </ion-footer>
  </ion-modal>
</template>

<script lang="ts" setup>
import avatar from "@/assets/images/avatar.svg";
import EventBus, { C_EVENT } from "@/types/EventBus";
import { getLotteryData, getNetworkErrorMessage, setLotteryData } from "@/utils/NetUtil";
import { removeCircleOutline, saveOutline } from "ionicons/icons";
import { onMounted, ref } from "vue";
import { alertController, loadingController, IonGrid, IonCol, IonRow } from "@ionic/vue";
import { calcImgPos } from "@/utils/Math";
import { getImage, loadAndSetImage } from "@/utils/ImgMgr";
import { LotteryData } from "@/types/UserData";

const modal = ref();
const canvasWidth = ref(400); // 设置canvas的宽度
const canvasHeight = ref(300); // 设置canvas的高度
const canvasRef = ref<HTMLCanvasElement>();
const lotteryData = ref<{ fee: 10; giftList: [{ icon: ""; name: ""; weight: 1 }] } | any>({
  fee: 10,
  giftList: [],
});
const nLottery = ref(new LotteryData());
const bModify = ref(false);
const curItem = ref<LotteryData | null>(null);

const cancel = async () => {
  const alert = await alertController.create({
    header: "Confirm",
    message: "确认 放弃修改",
    buttons: [
      {
        text: "OK",
        handler: () => {
          modal.value.$el!.dismiss({}, "cancel");
        },
      },
      "Cancel",
    ],
  });
  if (bModify.value) {
    await alert.present();
  } else {
    modal.value.$el!.dismiss({}, "cancel");
  }
};
const confirm = async () => {
  setLotteryData(JSON.stringify(lotteryData.value))
    .then(() => {
      modal.value.$el!.dismiss(lotteryData.value, "confirm");
    })
    .catch((err) => {
      EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
    });
};

onMounted(async () => {});
async function onModalPresent() {
  bModify.value = false;
  // 加载数据
  const loading = await loadingController.create({
    message: "Loading...",
  });
  loading.present();
  // 获取数据
  getLotteryData()
    .then((data: any) => {
      if (data) {
        lotteryData.value = JSON.parse(data);
        lotteryData.value.giftList.forEach(async (item) => {
          item.img = await getImage(item.imgId);
        });
      }
    })
    .catch((err) => {
      EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
    })
    .finally(() => {
      loading.dismiss();
    });
}
const onModalDismiss = () => {};
function onInputChange(e: any, lottery: any, key: string) {
  lottery[key] = e.detail.value;
  bModify.value = true;
}

async function btnModifyClk() {
  if (curItem.value === null) {
    return;
  }
  const imgId = await loadAndSetImage(curItem.value.imgId, canvasHeight.value, canvasWidth.value);
  if (imgId !== null) {
    curItem.value.imgId = imgId;
    curItem.value.img = await getImage(imgId);
    onItemClk(null, curItem.value);
  }
}

async function btnRemoveClk(_event: any, item: any, idx: number | string) {
  bModify.value = true;
  const index = typeof idx === "number" ? idx : parseInt(String(idx), 10);
  lotteryData.value.splice(index, 1);
  if (curItem.value === item) {
    curItem.value = null;
  }
}

async function onItemClk(_event: any, item: LotteryData) {
  curItem.value = item;
  const img = new Image();
  img.src = item.img! || avatar;
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
}

async function btnSaveClk(_event: any, item: any, idx: number) {
  console.log("btnSaveClk", item);
  if (item.name === "") {
    return;
  }
  bModify.value = true;
  if (idx === -1) {
    lotteryData.value.push(item);
    nLottery.value = new LotteryData();
  }
}
</script>

<style scoped>
.option-item::part(label) {
  margin: 0;
  width: 100%;
}

ion-modal#main::part(content) {
  max-width: 500px;
}

ion-modal#main {
  --height: 100%;
}
</style>
