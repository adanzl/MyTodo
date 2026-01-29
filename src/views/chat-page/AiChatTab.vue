<template>
  <ion-segment-content id="aiChat">
    <ion-content class="" ref="contentRef">
      <ion-refresher slot="fixed" @ionRefresh="onRefresh">
        <ion-refresher-content></ion-refresher-content>
      </ion-refresher>
      <div class="flex flex-col h-full p-2 border-t-1 border-gray-200">
        <div v-for="(msg, idx) in messages" :key="idx" class="p-1.5 w-full">
          <div
            v-if="msg.role == 'server'"
            class="w-[80%] bg-pink-200 rounded-lg p-2 shadow-md ml-auto relative">
            {{ msg.content ?? "..." }}
            <div
              class="absolute -left-10 top-1 rounded-[50%] border border-cyan-950 w-8 h-8 flex items-center justify-center"
              @click="$emit('audio-click', msg)">
              <Icon icon="mdi:stop-circle-outline" class="w-6 h-6" v-if="msg.playing" />
              <ion-icon :icon="volumeMediumOutline" class="w-6 h-6" v-else />
            </div>
          </div>
          <div v-else class="w-[80%] bg-green-500 text-white p-2 rounded-lg shadow-md relative">
            {{ msg.content }}
            <div
              v-if="msg.audioSrc"
              class="absolute -right-10 top-1 rounded-[50%] border border-cyan-950 w-8 h-8 flex items-center justify-center text-black"
              @click="$emit('audio-click', msg)">
              <Icon icon="mdi:stop-circle-outline" class="w-6 h-6" v-if="msg.playing" />
              <ion-icon :icon="volumeMediumOutline" class="w-6 h-6" v-else />
            </div>
          </div>
        </div>
      </div>
    </ion-content>
  </ion-segment-content>
</template>

<script setup lang="ts">
import { IonContent, IonRefresher, IonRefresherContent, IonSegmentContent } from "@ionic/vue";
import { Icon } from "@iconify/vue";
import { volumeMediumOutline } from "ionicons/icons";
import { ref } from "vue";
import { getAiChatMessages } from "@/utils/NetUtil";
import type { RefresherCustomEvent } from "@ionic/vue";

export interface ChatMsg {
  id?: string | number;
  content: string;
  role: string;
  audioSrc?: string;
  playing?: boolean;
  ts?: string;
  type?: string;
}

const props = defineProps<{
  aiConversationId: string;
  userName: string;
}>();

defineEmits<{
  (e: "audio-click", msg: ChatMsg): void;
}>();

const contentRef = ref<InstanceType<typeof IonContent> | null>(null);
const messages = ref<ChatMsg[]>([]);

function scrollToBottom(duration = 200) {
  contentRef.value?.$el?.scrollToBottom?.(duration);
}

function addMessage(msg: ChatMsg) {
  messages.value.push(msg);
}

function appendLastMessageContent(text: string) {
  if (messages.value.length === 0) return;
  const last = messages.value[messages.value.length - 1];
  if (last.role === "server") {
    last.content = (last.content ?? "") + text;
  }
}

function getLastMessage(): ChatMsg | undefined {
  return messages.value[messages.value.length - 1];
}

async function onRefresh(e: RefresherCustomEvent) {
  if (!props.aiConversationId) {
    e.target.complete();
    return;
  }
  const firstId = messages.value.length > 0 ? messages.value[0].id : undefined;
  try {
    const data: any = await getAiChatMessages(
      props.aiConversationId,
      3,
      props.userName,
      firstId
    );
    data.data.reverse().forEach((item: any) => {
      if (item.answer === "") return;
      messages.value.unshift({
        id: item.id,
        content: item.answer,
        role: "server",
      });
      messages.value.unshift({
        id: item.id,
        content: item.query,
        role: "me",
      });
    });
  } finally {
    e.target.complete();
  }
}

defineExpose({
  scrollToBottom,
  addMessage,
  appendLastMessageContent,
  getLastMessage,
});
</script>
