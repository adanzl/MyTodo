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
        <ion-title>Chat Setting</ion-title>
      </ion-toolbar>
    </ion-header>
    <div class="ion-padding h-full flex flex-col">
      <ion-item lines="none">
        <div class="w-64 ml-3">语音速度</div>
        <ion-input
          :value="chatSetting.ttsSpeed"
          class="m-1"
          fill="outline"
          mode="md"
          @ionChange="onInputChange($event, 'ttsSpeed')" />
      </ion-item>
      <ion-item lines="none">
        <div class="w-64 ml-3">语音角色</div>
        <ion-input
          :value="chatSetting.ttsRole"
          class="m-1"
          fill="outline"
          mode="md"
          @ionChange="onInputChange($event, 'ttsRole')" />
      </ion-item>
      <div class="flex-1 pt-2">
        <ion-content>
          <ion-textarea
            label="Chat Memory"
            label-placement="floating"
            :value="textareaMem"
            :auto-grow="true"
            class="p-2"
            @ionChange="onMemChange($event)"></ion-textarea>
        </ion-content>
      </div>
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
import { setChatSetting, getChatSetting, getChatMem, getConversationId } from "@/utils/NetUtil";
import { inject, onMounted, ref } from "vue";
import { IonTextarea, loadingController } from "@ionic/vue";

const modal = ref();
const globalVar: any = inject("globalVar");
const textareaMem = ref("");
const chatSetting = ref({
  ttsSpeed: 1.1,
  ttsRole: "longwan_v2",
} as { [key: string]: any });

const cancel = () => {
  modal.value.$el!.dismiss({}, "cancel");
};
const confirm = () => {
  setChatSetting(globalVar.user.id, JSON.stringify(chatSetting.value));
  modal.value.$el!.dismiss(chatSetting.value, "confirm");
};

onMounted(async () => {});
async function onModalPresent() {
  const loading = await loadingController.create({
    message: "Loading...",
  });
  loading.present();
  getChatSetting(globalVar.user.id).then((setting) => {
    if (setting) {
      const v = JSON.parse(setting);
      chatSetting.value.ttsSpeed = v.ttsSpeed;
      chatSetting.value.ttsRole = v.ttsRole;
    }
  }).finally(() => {
    loading.dismiss();
  });
  const aiConversationId = (await getConversationId(globalVar.user.id)) || "";
  if (aiConversationId) {
    getChatMem(aiConversationId)
      .then((mem) => {
        textareaMem.value = mem;
      })
      .finally(() => {
        loading.dismiss();
      });
  }
}
const onModalDismiss = () => {};
function onInputChange(e: any, key: string) {
  chatSetting.value[key] = e.detail.value;
}
function onMemChange(e: any) {
  textareaMem.value = e.detail.value;
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
