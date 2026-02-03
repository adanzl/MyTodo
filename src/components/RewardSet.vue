<template>
  <ion-modal
    ref="modal"
    aria-hidden="false"
    class="bottom-modal"
    @didPresent="onModalPresent"
    @didDismiss="onModalDismiss">
    <ion-item>
      <ion-title>设定星星数量</ion-title>
    </ion-item>
    <div class="ion-padding">
      <ion-item lines="none" v-for="(u, idx) in userList" :key="idx">
        <ion-avatar slot="start" class="w-12 h-12">
          <ion-img :src="u.icon" />
        </ion-avatar>
        <div class="w-64 ml-3">{{ u.name }}</div>
        <ion-input
          :value="u.score"
          class="m-1"
          fill="outline"
          mode="md"
          type="number"
          @ionChange="onInputChange($event, u)"></ion-input>
      </ion-item>
    </div>
    <ion-footer>
      <ion-button class="flex-1 text-gray-400" fill="clear" @click="cancel()">取消</ion-button>
      <ion-button class="flex-1 text-orange-400" fill="clear" @click="confirm()">确定</ion-button>
    </ion-footer>
  </ion-modal>
</template>

<script lang="ts" setup>
import { User } from "@/types/UserData";
import { addScore, getUserList } from "@/api/user";
import { IonAvatar, IonImg } from "@ionic/vue";
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
    });
  });
  // console.log("userList", uList);
}
async function onModalDismiss() {
  // console.log("didDismiss", userList.value);
  modifyUser.forEach((u: User) => {
    addScore(u.id, "appAdmin", u.dScore, "app管理变更" + globalVar.user.name);
  });
  modifyUser.clear();
}
function onInputChange(e: any, u: User) {
  u.dScore += Number(e.detail.value) - u.score;
  u.score = Number(e.detail.value);
  modifyUser.set(u.id, u);
}
</script>

<style scoped>
.option-item::part(label) {
  margin: 0;
  width: 100%;
}
</style>
