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
    <div class="ion-padding">
      <ion-item lines="none">
        <div class="w-64 ml-3">普通抽奖费用</div>
        <ion-input
          type="number"
          :value="lotteryData.fee"
          fill="outline"
          mode="ios"
          @ionChange="onFeeChange" />
      </ion-item>
    </div>
    <ion-footer>
      <div class="flex">
        <ion-button class="flex-1 text-gray-400" fill="clear" @click="cancel()">取消</ion-button>
        <ion-button class="flex-1 text-orange-400" fill="clear" @click="confirm()">确定</ion-button>
      </div>
    </ion-footer>
  </ion-modal>
</template>

<script lang="ts" setup>
import EventBus, { C_EVENT } from "@/types/EventBus";
import { getLotteryData, setLotteryData } from "@/api/lottery";
import { getNetworkErrorMessage } from "@/utils/NetUtil";
import { ref } from "vue";
import { alertController, loadingController } from "@ionic/vue";

const modal = ref();
const lotteryData = ref<{ fee: number; giftList: any[] }>({
  fee: 10,
  giftList: [],
});
const bModify = ref(false);

const cancel = async () => {
  if (bModify.value) {
    const alert = await alertController.create({
      header: "Confirm",
      message: "确认放弃修改",
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

async function onModalPresent() {
  bModify.value = false;
  const loading = await loadingController.create({
    message: "Loading...",
  });
  loading.present();
  getLotteryData()
    .then((data: any) => {
      if (data) {
        const parsed = JSON.parse(data);
        lotteryData.value = {
          fee: parsed.fee ?? 10,
          giftList: parsed.giftList ?? [],
        };
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

function onFeeChange(e: any) {
  lotteryData.value.fee = Number(e.detail.value) || 10;
  bModify.value = true;
}
</script>

<style scoped>
ion-modal#main::part(content) {
  max-width: 500px;
}

ion-modal#main {
  --height: auto;
}
</style>
