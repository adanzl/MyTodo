<template>
  <ion-modal
    ref="modal"
    aria-hidden="false"
    class="bottom-modal"
    @ionModalDidDismiss="onModalDismiss">
    <ion-item>
      <ion-title>设定星星数量</ion-title>
    </ion-item>
    <div class="ion-padding">
      <ion-item lines="none" v-for="(u, idx) in userList" :key="idx">
        <ion-avatar slot="start" class="w-12 h-12">
          <ion-img :src="u.icon" />
        </ion-avatar>
        <div class="w-64">{{ u.name }}</div>
        <ion-input :value="u.score" fill="outline" type="number"  @ionChange="onInputChange($event, u)""></ion-input>
      </ion-item>
    </div>
    <ion-footer>
      <ion-button class="flex-1 text-gray-400" fill="clear" @click="cancel()">取消</ion-button>
      <ion-button class="flex-1 text-orange-400" fill="clear" @click="confirm()">确定</ion-button>
    </ion-footer>
  </ion-modal>
</template>

<script lang="ts" setup>
import { User } from "@/modal/UserData";
import { getUserList } from "@/utils/NetUtil";
import { onIonViewDidEnter, IonAvatar, IonImg } from "@ionic/vue";
import { onMounted, ref } from "vue";

const modal = ref();
const userList = ref<any>([]);

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
  console.log("confirm", userList.value);
  modal.value.$el!.dismiss();
};

onMounted(async () => {
  const uList = await getUserList();
  console.log("userList", uList);
  userList.value = uList.data;
});
onIonViewDidEnter(async () => {
  userList.value = await getUserList();
  console.log("userList", userList.value);
});
const onModalDismiss = () => {
  // valueRef.value = props.value;
};
function onInputChange(e: any, u: User) {
  u.score = e.detail.value;
  
}
</script>

<style scoped>
.option-item::part(label) {
  margin: 0;
  width: 100%;
}
</style>
