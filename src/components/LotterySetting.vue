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
    <ion-content>
      <ion-grid>
        <ion-row>
          <ion-col size="1"> - </ion-col>
          <ion-col size="5"> 名称 </ion-col>
          <ion-col size="3"> 权重 </ion-col>
          <ion-col> 操作 </ion-col>
        </ion-row>
        <ion-row>
          <ion-col size="1"> <span class="v-dot w-in" /> </ion-col>
          <ion-col size="5">
            <ion-input
              class="w-full text-xs h-8 min-h-0 color-name"
              fill="solid"
              mode="md"
              placeholder="新建"
              :value="nLottery.name"
              @ionChange="onInputChange($event, nLottery, 'name')" />
          </ion-col>
          <ion-col size="3">
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
        <ion-row v-for="(lottery, idx) in lotteryData" :key="idx">
          <ion-col size="1"> <span class="v-dot w-in" /> </ion-col>
          <ion-col size="5">
            <ion-input
              class="w-full text-xs h-8 min-h-0 color-name"
              fill="solid"
              mode="md"
              :value="lottery.name"
              @ionChange="onInputChange($event, lottery, 'name')" />
          </ion-col>
          <ion-col size="3">
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
import { getLotteryData, setLotteryData } from "@/utils/NetUtil";
import { removeCircleOutline, saveOutline } from "ionicons/icons";
import { onMounted, ref } from "vue";
import { alertController, loadingController, IonGrid, IonCol, IonRow } from "@ionic/vue";

const modal = ref();
const lotteryData = ref<[{ icon: ""; name: ""; weight: 1 }] | any[]>([]);
const nLottery = ref({ icon: "", name: "", weight: 1 });
const bModify = ref(false);

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
  setLotteryData(JSON.stringify(lotteryData.value));
  modal.value.$el!.dismiss(lotteryData.value, "confirm");
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
      }
      // console.log(userData.value);
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

async function btnRemoveClk(_event: any, item: any, idx: number) {
  bModify.value = true;
  lotteryData.value.splice(idx, 1);
  console.log("btnRemoveClk", item);
  // console.log("btnRemoveClk", color.id);
  // const alert = await alertController.create({
  //   header: "Confirm",
  //   message: "确认删除 [" + color.label + "]",
  //   buttons: [
  //     {
  //       text: "OK",
  //       handler: () => {
  //         console.log("btnRemoveClk", color.id);
  //         // delColor(color.id).then(async () => {
  //         //   LoadColorData();
  //         // });
  //       },
  //     },
  //     "Cancel",
  //   ],
  // });
  // await alert.present();
}

async function btnSaveClk(_event: any, item: any, idx: number) {
  console.log("btnSaveClk", item);
  if (item.name === "") {
    return;
  }
  bModify.value = true;
  if (idx === -1) {
    lotteryData.value.push(item);
    nLottery.value = { icon: "", name: "", weight: 1 };
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
