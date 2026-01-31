<template>
  <ion-segment-content id="chat">
    <ion-content class="" ref="contentRef">
      <ion-refresher slot="fixed" @ionRefresh="onRefresh">
        <ion-refresher-content></ion-refresher-content>
      </ion-refresher>
      <div
        v-if="networkError"
        class="mx-2 mt-2 p-2 rounded-lg bg-amber-100 text-amber-800 text-sm flex items-center justify-between">
        <span>加载失败，请检查网络后下拉刷新</span>
        <ion-button size="small" fill="clear" @click="retryLoad">重试</ion-button>
      </div>
      <div class="flex flex-col h-full p-2 border-t-1 border-gray-200">
        <div v-for="(msg, idx) in messages" :key="idx" class="p-1.5 w-full">
          <!-- 自己 -->
          <div v-if="String(msg.role) === userIdStr" class="flex">
            <div
              class="max-w-[70%] min-w-[40px] bg-green-500 text-white p-2 ml-auto rounded-lg shadow-md relative">
              {{ msg.content }}
            </div>
            <ion-avatar slot="start" class="w-12 h-12 ml-1">
              <ion-img :src="(getUserInfo(msg.role)?.icon) ?? DEFAULT_AVATAR" />
            </ion-avatar>
            <div
              v-if="!msg.audioSrc"
              class="absolute -right-10 top-1 rounded-[50%] border border-cyan-950 w-8 h-8 flex items-center justify-center text-black"
              @click="$emit('audio-click', msg)">
              <Icon icon="mdi:stop-circle-outline" class="w-6 h-6" v-if="msg.playing" />
              <ion-icon :icon="volumeMediumOutline" class="w-6 h-6" v-else />
            </div>
          </div>
          <!-- 他人 -->
          <div v-else class="flex">
            <ion-avatar slot="start" class="w-12 h-12 mr-1">
              <ion-img :src="(getUserInfo(msg.role)?.icon) ?? DEFAULT_AVATAR" />
            </ion-avatar>
            <div
              class="max-w-[70%] min-w-[40px] bg-pink-200 p-2 mr-auto rounded-lg shadow-md relative">
              {{ msg.content }}
            </div>
            <div
              class="absolute -left-10 top-1 rounded-[50%] border border-cyan-950 w-8 h-8 flex items-center justify-center"
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
import {
  IonAvatar,
  IonButton,
  IonContent,
  IonImg,
  IonRefresher,
  IonRefresherContent,
  IonSegmentContent,
} from "@ionic/vue";
import { Icon } from "@iconify/vue";
import { volumeMediumOutline } from "ionicons/icons";
import { computed, ref, watch } from "vue";
import EventBus, { C_EVENT } from "@/types/EventBus";
import { getChatMessages, getNetworkErrorMessage } from "@/utils/NetUtil";
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

const DEFAULT_AVATAR = new URL("../../assets/images/avatar.svg", import.meta.url).href;

const props = defineProps<{
  chatRoomId: string;
  /** 支持 string 或 number，内部会转为 string 使用 */
  userId: string | number;
  getUserInfo: (userId: string) => { icon?: string; [key: string]: unknown } | undefined;
}>();

const userIdStr = computed(() => String(props.userId ?? ""));

defineEmits<{
  (e: "audio-click", msg: ChatMsg): void;
}>();

const contentRef = ref<InstanceType<typeof IonContent> | null>(null);
const messages = ref<ChatMsg[]>([]);
const networkError = ref(false);

function scrollToBottom(duration = 200) {
  contentRef.value?.$el?.scrollToBottom?.(duration);
}

function addMessage(msg: ChatMsg) {
  messages.value.push(msg);
}

async function loadInitial() {
  if (!props.chatRoomId) return;
  networkError.value = false;
  try {
    const data: any = await getChatMessages(props.chatRoomId, -1, 3);
    messages.value = [];
    const list = data?.data ?? [];
    list.reverse().forEach((item: any) => {
      const d = typeof item === "string" ? JSON.parse(item) : item;
      messages.value.unshift({
        id: d.id,
        content: d.content,
        role: d.user_id,
        ts: d.ts,
        type: d.type,
      });
    });
  } catch (err) {
    networkError.value = true;
    EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
  }
}

function retryLoad() {
  networkError.value = false;
  loadInitial();
}

async function onRefresh(e: RefresherCustomEvent) {
  if (!props.chatRoomId) {
    e.target.complete();
    return;
  }
  networkError.value = false;
  const firstId = messages.value.length + 1;
  try {
    const data: any = await getChatMessages(props.chatRoomId, -firstId, 3);
    const list = data?.data ?? [];
    list.reverse().forEach((item: any) => {
      const d = typeof item === "string" ? JSON.parse(item) : item;
      messages.value.unshift({
        id: d.id,
        content: d.content,
        role: d.user_id,
        ts: d.ts,
        type: d.type,
      });
    });
  } catch (err) {
    networkError.value = true;
    EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
  } finally {
    e.target.complete();
  }
}

watch(() => props.chatRoomId, (id) => {
  if (id) loadInitial();
}, { immediate: true });

defineExpose({ scrollToBottom, addMessage, loadInitial });
</script>
