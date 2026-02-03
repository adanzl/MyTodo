<template>
  <ion-segment-content id="shop">
    <ion-item>
      <ion-select
        label="类别"
        placeholder="选择类别"
        justify="start"
        :model-value="selectedCate"
        @ionChange="onCateChange">
        <ion-select-option :value="cate" v-for="cate in lotteryCatList" :key="cate.id">
          {{ cate.name }}
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
      <ion-item v-for="item in giftList.data" :key="item.id" class="">
        <ion-thumbnail slot="start">
          <img :src="item.img" />
        </ion-thumbnail>
        <div class="w-full m-2">
          <ion-label>
            <h2 class="flex">
              <div class="w-8">[{{ item.id }}]</div>
              {{ item.name }}
            </h2>
          </ion-label>
          <div class="flex items-center">
            <Icon icon="mdi:star" class="text-red-500 w-5 h-5" />
            <div class="text-left pl-1 pt-1 font-bold w-12">{{ item.cost }}</div>
            <p class="text-sm ml-2 pt-1">{{ getCateName(item.cate_id) }}</p>
          </div>
        </div>
        <ion-button
          class="w-14 h-10"
          @click="$emit('exchange', item)"
          :disabled="userScore < item.cost">
          兑
        </ion-button>
        <ion-button
          class="w-14 h-10 ml-2"
          color="warning"
          @click="$emit('add-wish', item)"
          :disabled="wishList.ids.includes(item.id)">
          愿
        </ion-button>
      </ion-item>
    </ion-content>
  </ion-segment-content>
</template>

<script setup lang="ts">
import {
  IonButton,
  IonContent,
  IonItem,
  IonLabel,
  IonRefresher,
  IonRefresherContent,
  IonSegmentContent,
  IonSelect,
  IonSelectOption,
  IonThumbnail,
} from "@ionic/vue";
import { Icon } from "@iconify/vue";
import _ from "lodash";

const props = defineProps<{
  lotteryCatList: any[];
  selectedCate: any;
  giftList: { data: any[] };
  wishList: { ids: number[] };
  userScore: number;
}>();

const emit = defineEmits<{
  (e: "refresh", event: any): void;
  (e: "cate-change", value: any): void;
  (e: "exchange", item: any): void;
  (e: "add-wish", item: any): void;
}>();

function onRefresh(event: any) {
  emit("refresh", event);
}
function onCateChange(event: any) {
  emit("cate-change", event.detail.value);
}

function getCateName(cateId: number) {
  const cate = _.find(props.lotteryCatList, { id: cateId });
  return cate ? cate.name : "";
}
</script>
