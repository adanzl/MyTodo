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
            :disabled="!effectiveConversationId"
            class="p-2"
            @ionChange="onMemChange($event)"></ion-textarea>
          <p v-if="!effectiveConversationId" class="px-2 text-sm text-gray-500">
            当前没有 AI 会话，请先发送一条消息后再编辑 Memory。
          </p>
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
import EventBus, { C_EVENT } from "@/types/event-bus";
import { getChatMem, getChatSetting, setChatMem, setChatSetting } from "@/api/api-chat";
import { getNetworkErrorMessage } from "@/utils/net-util";
import { computed, inject, ref } from "vue";
import { IonTextarea, loadingController } from "@ionic/vue";

const props = defineProps<{
  aiConversationId?: string;
  settingSnapshot?: {
    ttsSpeed: number;
    ttsRole: string;
    aiConversationId: string;
    chatRoomId: string;
  };
}>();

const modal = ref();
const globalVar: any = inject("globalVar");
const textareaMem = ref("");
const chatSetting = ref({
  ttsSpeed: 1.1,
  ttsRole: "longwan_v2",
} as { [key: string]: any });

const effectiveConversationId = computed(
  () => (props.aiConversationId || props.settingSnapshot?.aiConversationId || "").trim()
);

const cancel = () => {
  modal.value.$el!.dismiss({}, "cancel");
};
const confirm = async () => {
  try {
    const existingRaw = await getChatSetting(globalVar.user.id);
    const existing = existingRaw ? JSON.parse(existingRaw) : {};
    const snapshot = props.settingSnapshot ?? {};
    const merged = {
      ...existing,
      ...snapshot,
      ttsSpeed: chatSetting.value.ttsSpeed,
      ttsRole: chatSetting.value.ttsRole,
    };
    await setChatSetting(globalVar.user.id, JSON.stringify(merged));
    if (effectiveConversationId.value) {
      await setChatMem(effectiveConversationId.value, textareaMem.value);
    } else if (textareaMem.value.trim()) {
      EventBus.$emit(C_EVENT.TOAST, "未找到当前会话，Memory 未保存");
      return;
    }
    modal.value.$el!.dismiss(merged, "confirm");
  } catch (err) {
    EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
  }
};

async function onModalPresent() {
  const loading = await loadingController.create({
    message: "Loading...",
  });
  loading.present();
  try {
    const setting = await getChatSetting(globalVar.user.id);
    if (setting) {
      const v = JSON.parse(setting);
      chatSetting.value.ttsSpeed = v.ttsSpeed ?? props.settingSnapshot?.ttsSpeed ?? 1.1;
      chatSetting.value.ttsRole = v.ttsRole ?? props.settingSnapshot?.ttsRole ?? "longwan_v2";
    } else if (props.settingSnapshot) {
      chatSetting.value.ttsSpeed = props.settingSnapshot.ttsSpeed;
      chatSetting.value.ttsRole = props.settingSnapshot.ttsRole;
    }
    if (effectiveConversationId.value) {
      const mem = await getChatMem(effectiveConversationId.value);
      textareaMem.value = mem ?? "";
    } else {
      textareaMem.value = "";
    }
  } catch (err) {
    EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
  } finally {
    loading.dismiss();
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
