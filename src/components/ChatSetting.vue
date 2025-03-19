<template>
  <ion-modal
    ref="modal"
    aria-hidden="false"
    class="bottom-modal"
    @ionModalDidPresent="onModalPresent"
    @ionModalDidDismiss="onModalDismiss">
    <ion-item>
      <ion-title>Chat Setting</ion-title>
    </ion-item>
    <div class="ion-padding">
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
    </div>
    <ion-footer>
      <ion-button class="flex-1 text-gray-400" fill="clear" @click="cancel()">取消</ion-button>
      <ion-button class="flex-1 text-orange-400" fill="clear" @click="confirm()">确定</ion-button>
    </ion-footer>
  </ion-modal>
</template>

<script lang="ts" setup>
import { setChatSetting, getChatSetting } from "@/utils/NetUtil";
import { inject, onMounted, ref } from "vue";

const modal = ref();
const globalVar: any = inject("globalVar");
const chatSetting = ref({
  ttsSpeed: 1.1,
  ttsRole: "longwan_v2",
} as { [key: string]: any });

const cancel = () => {
  modal.value.$el!.dismiss({}, 'cancel');
};
const confirm = () => {
  setChatSetting(globalVar.user.id, JSON.stringify(chatSetting.value))
  modal.value.$el!.dismiss(chatSetting.value, 'confirm');
};

onMounted(async () => {
});
async function onModalPresent() {
  getChatSetting(globalVar.user.id).then((setting) => {
    if (setting) {
      const v = JSON.parse(setting);
      chatSetting.value.ttsSpeed = v.ttsSpeed;
      chatSetting.value.ttsRole = v.ttsRole;
    }
  });
}
const onModalDismiss = () => {
};
function onInputChange(e: any, key: string) {
  chatSetting.value[key] = e.detail.value;
}
</script>

<style scoped>
.option-item::part(label) {
  margin: 0;
  width: 100%;
}
</style>
