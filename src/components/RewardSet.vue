<template>
  <ion-modal
    ref="modal"
    aria-hidden="false"
    mode="ios"
    class="bottom-modal"
    @didPresent="onModalPresent"
    @didDismiss="onModalDismiss">
    <ion-item>
      <ion-title>设定星星和硬币</ion-title>
    </ion-item>
    <div class="ion-padding">
      <div class="flex pl-35 pr-5">
        <div class="mx-auto flex items-center gap-1">
          <Icon icon="mdi:coin" class="text-yellow-500 w-5 h-5 shrink-0" />
          硬币
        </div>
        <div class="mx-auto flex items-center gap-1">
          <Icon icon="mdi:star" class="text-red-500 w-5 h-5 shrink-0" />
          星星
        </div>
      </div>
      <ion-item lines="none" v-for="(u, idx) in userList" :key="idx">
        <ion-avatar slot="start" class="w-12 h-12">
          <ion-img :src="u.icon" />
        </ion-avatar>
        <div class="w-40 ml-3">{{ u.name }}</div>
        <ion-input
          :value="u.coin"
          class="m-1"
          fill="outline"
          mode="md"
          readonly
          @click="openCoinEditAlert(u)"></ion-input>
        <ion-input
          :value="u.score"
          class="m-1"
          fill="outline"
          mode="md"
          type="number"
          @ionChange="onScoreChange($event, u)"></ion-input>
      </ion-item>
    </div>
    <ion-footer>
      <ion-button class="flex-1 text-gray-400" fill="clear" @click="cancel()">取消</ion-button>
      <ion-button class="flex-1 text-orange-400" fill="clear" @click="confirm()">确定</ion-button>
    </ion-footer>
  </ion-modal>
</template>

<script lang="ts" setup>
import { User } from "@/types/user-data";
import { addCoin, addScore, getUserList } from "@/api/api-user";
import { alertController, IonAvatar, IonImg } from "@ionic/vue";
import EventBus, { C_EVENT } from "@/types/event-bus";
import { inject, onMounted, ref } from "vue";

const modal = ref();
const userList = ref<any>([]);
const modifyUser = new Map<number, User>();
const globalVar: any = inject("globalVar");

const cancel = () => {
  modal.value.$el!.dismiss();
};
const confirm = () => {
  //   buttons: [
  //     {
  //       text: "取消",
  //       role: "cancel",
  //     },
  //     {
  //       text: "确定",
  //       handler: (e) => {
  //         curUser.value.score = parseInt(e[0]);
  //         setUserInfo(curUser.value.id, curUser.value.score).then((res) => {
  //           console.log("setUserInfo", res);
  //         });
  //       },
  //     },
  //   ],
  // });
  // console.log("confirm", userList.value);
  modal.value.$el!.dismiss();
};

onMounted(async () => {
  // const uList = await getUserList();
  // console.log("userList", uList);
  // userList.value = uList.data;
});
async function onModalPresent() {
  getUserList().then((uList) => {
    userList.value = uList.data;
    userList.value.forEach((u: User) => {
      u.dScore = 0;
      u.dCoin = 0;
      u.coinMsg = "";
    });
  });
  // console.log("userList", uList);
}
async function onModalDismiss() {
  // console.log("didDismiss", userList.value);
  modifyUser.forEach((u: User) => {
    if (u.dScore !== 0) {
      addScore(u.id, "appAdmin", u.dScore, "app管理变更" + globalVar.user.name);
    }
    if (u.dCoin !== 0) {
      const msg =
        u.coinMsg?.trim() ||
        `app管理变更${globalVar.user.name}`;
      addCoin(u.id, "appAdmin", u.dCoin, msg);
    }
  });
  modifyUser.clear();
}
function onScoreChange(e: any, u: User) {
  u.dScore += Number(e.detail.value) - u.score;
  u.score = Number(e.detail.value);
  modifyUser.set(u.id, u);
}
function applyCoinValue(u: User, newCoin: number, remark: string) {
  u.dCoin += newCoin - u.coin;
  u.coin = newCoin;
  u.coinMsg = remark.trim();
  modifyUser.set(u.id, u);
}

async function openCoinEditAlert(u: User) {
  const alert = await alertController.create({
    header: `${u.name} · 金币`,
    subHeader: `当前 ${u.coin}`,
    inputs: [
      {
        name: "coinValue",
        type: "number",
        placeholder: "新金币值",
        value: String(u.coin),
      },
      {
        name: "remark",
        type: "textarea",
        placeholder: "备注（选填）",
      },
    ],
    buttons: [
      { text: "取消", role: "cancel" },
      {
        text: "确定",
        handler: (data) => {
          const newCoin = Number(data.coinValue);
          const remark = String(data.remark ?? "").trim();
          if (Number.isNaN(newCoin)) {
            EventBus.$emit(C_EVENT.TOAST, "请输入有效的金币数值");
            return false;
          }
          applyCoinValue(u, newCoin, remark);
        },
      },
    ],
  });
  await alert.present();
}
</script>

<style scoped>
.option-item::part(label) {
  margin: 0;
  width: 100%;
}
</style>
