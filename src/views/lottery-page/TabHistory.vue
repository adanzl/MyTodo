<template>
  <ion-segment-content id="tabHistory">
    <ion-item>
      <ion-select
        label="用户"
        :model-value="selectedUser"
        @ionChange="onUserChange"
        justify="start">
        <ion-select-option :value="item" v-for="item in userList" :key="item.id">
          {{ item.name }}
        </ion-select-option>
      </ion-select>
      <div class="flex w-1/3 items-center justify-center">
        <Icon icon="mdi:star" class="text-red-500 w-5 h-5" />
        <div class="text-left pl-1 font-bold w-12">{{ userScore }}</div>
      </div>
    </ion-item>
    <ion-content :scrollY="true" :style="{ height: 'calc(100% - 56px)' }">
      <ion-refresher slot="fixed" @ionRefresh="onRefresh">
        <ion-refresher-content></ion-refresher-content>
      </ion-refresher>
      <ion-item v-for="item in scoreHistoryList.data" :key="item.id">
        <ion-avatar slot="start" class="w-12 h-12">
          <img :src="getUserInfo(item.user_id).icon" />
        </ion-avatar>
        <div class="flex flex-col w-full">
          <div class="flex">
            <div class="ml-2 flex items-center w-1/4">
              <ion-icon
                :icon="item.value >= 0 ? caretUpOutline : caretDownOutline"
                :class="item.value >= 0 ? 'text-green-500' : 'text-red-500'"
                class="w-5 h-5"></ion-icon>
              {{ item.value }}
            </div>
            <div class="ml-2 flex items-center text-sm">
              <ion-icon class="mr-1 h-4.5 w-4.5" :icon="timeOutline"></ion-icon>
              {{ formatDate(item.dt) }}
            </div>
          </div>
          <div class="flex mb-2">
            <div class="ml-2 flex items-center w-1/4">
              <Icon icon="mdi:star" class="text-red-500 w-5 h-5" />
              {{ item.current }}
            </div>
            <div class="ml-2 flex items-center">
              <ion-icon class="mr-1" :icon="chatbubbleEllipsesOutline"></ion-icon>
              {{ item.msg }}
            </div>
          </div>
        </div>
      </ion-item>
    </ion-content>
  </ion-segment-content>
</template>

<script setup lang="ts">
import {
  IonAvatar,
  IonContent,
  IonIcon,
  IonItem,
  IonRefresher,
  IonRefresherContent,
  IonSegmentContent,
  IonSelect,
  IonSelectOption,
} from "@ionic/vue";
import { Icon } from "@iconify/vue";
import {
  caretDownOutline,
  caretUpOutline,
  chatbubbleEllipsesOutline,
  timeOutline,
} from "ionicons/icons";
import dayjs from "dayjs";

const props = defineProps<{
  userList: any[];
  selectedUser: any;
  scoreHistoryList: { data: any[] };
  userScore: number;
}>();

const emit = defineEmits<{
  (e: "refresh", event: any): void;
  (e: "user-change", value: any): void;
}>();

function onRefresh(event: any) {
  emit("refresh", event);
}
function onUserChange(event: any) {
  emit("user-change", event.detail.value);
}

function getUserInfo(userId: number) {
  return props.userList.find((u: any) => u.id === userId) || { icon: "" };
}
function formatDate(dateStr: string) {
  if (!dateStr) return dateStr;
  return dayjs(dateStr).format("YYYY-MM-DD HH:mm:ss");
}
</script>
