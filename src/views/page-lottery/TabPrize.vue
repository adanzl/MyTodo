<template>
  <ion-segment-content id="tabPrize">
    <ion-item>
      <ion-select 
        label="类别" 
        placeholder="选择类别" 
        justify="start" 
        :value="selectValue"
        @ion-change="onCateChange">
        <ion-select-option :value="cate.id" v-for="cate in lotteryCatList" :key="cate.id">
          {{ cate.name }}
        </ion-select-option>
      </ion-select>
      <div class="flex w-1/3 items-center justify-center">
        <Icon icon="mdi:star" class="text-red-500 w-5 h-5" />
        <div class="text-left pl-1 font-bold w-12">{{ userScore }}</div>
      </div>
    </ion-item>
    <ion-content :scrollY="true" class="h-[calc(100%-56px)]">
      <ion-refresher slot="fixed" @ionRefresh="onRefresh">
        <ion-refresher-content></ion-refresher-content>
      </ion-refresher>
      <ion-item
        v-for="item in giftList.data"
        :key="item.id"
        :class="{ '[&::part(native)]:bg-gray-300': !item.enable }"
        button
        @click="openGiftDetail(item)">
        <ion-thumbnail slot="start">
          <img :src="getGiftImgUrl(item)" alt="" />
        </ion-thumbnail>
        <div class="w-full m-2">
          <ion-label>
            <h2 class="flex">
              <div class="w-8 flex items-center text-[11px]">[{{ item.id }}]</div>
              <div class="flex text-[15px] w-full">{{ item.name }}</div>
            </h2>
          </ion-label>
          <div class="flex items-center">
            <Icon icon="mdi:star" class="text-red-500 w-5 h-5" />
            <div class="text-left pl-1 pt-1 font-bold w-12">{{ item.cost }}</div>
            <p class="text-[12px] ml-1 pt-1 w-18">{{ getCateName(item.cate_id) }}</p>
            <p class="text-[10px] ml-1 pt-1"> {{ item.stock ?? 0 }}</p>
          </div>
        </div>
        <div class="flex gap-2" @click.stop>
          <ion-button
            class="w-8 h-10"
            @click="$emit('exchange', item)"
            :disabled="userScore < item.cost || !item.exchange || item.stock <= 0">
            兑
          </ion-button>
          <ion-button class="w-8 h-10" color="warning" @click="$emit('add-wish', item)"
            :disabled="wishList.ids.includes(item.id) || Number(item.wish) === 0">
            愿
          </ion-button>
        </div>
      </ion-item>
      <ion-infinite-scroll
        threshold="150px"
        :disabled="!hasMore"
        @ionInfinite="onLoadMore">
        <ion-infinite-scroll-content
          loading-spinner="crescent"
          loading-text="加载更多..." />
      </ion-infinite-scroll>
    </ion-content>

    <FabButton v-if="isAdmin" @click="openNewGift" class="right-[5%] bottom-[1%]" bottom="1%" right="5%" :hasBar="true">
      <Icon icon="mdi:plus" class="w-8 h-8" />
    </FabButton>

    <DialogGift
      :is-open="isGiftModalOpen"
      :editing-gift="editingGift"
      :lottery-cat-list="lotteryCatList"
      :selected-cate="selectedCate"
      :is-admin="isAdmin"
      @close="closeGiftModal"
      @delete="onDeleteGiftInModal"
      @saved="onGiftSaved"
    />


  </ion-segment-content>
</template>

<script setup lang="ts">
import {
  IonInfiniteScroll,
  IonInfiniteScrollContent,
  IonRefresher,
  IonRefresherContent,
  IonSegmentContent,
  IonSelect,
  IonSelectOption,
  IonThumbnail,
} from "@ionic/vue";
import { Icon } from "@iconify/vue";
import { getPicDisplayUrl } from "@/api/api-pic";
import { PicDisplaySize } from "@/utils/img-mgr";
import { computed, inject, ref, watch } from "vue";
import _ from "lodash";

import DialogGift from "./dialogs/DialogGift.vue";

const props = defineProps<{
  lotteryCatList: any[];
  selectedCate: any;
  giftList: { data: any[] };
  wishList: { ids: number[] };
  userScore: number;
  hasMore?: boolean;
  loadingMore?: boolean;
}>();

const hasMore = computed(() => props.hasMore ?? false);

const emit = defineEmits<{
  (e: "refresh", event: any): void;
  (e: "load-more", event: any): void;
  (e: "cate-change", value: any): void;
  (e: "exchange", item: any): void;
  (e: "add-wish", item: any): void;
  (e: "delete", item: any): void;
}>();

const globalVar: any = inject("globalVar");

const isAdmin = computed(() => globalVar?.user?.admin === 1);

const isGiftModalOpen = ref(false);
const editingGift = ref<any>(null);

// 本地维护 select 的值，避免响应式更新不同步
const selectValue = ref<number | undefined>(undefined);

// 监听 selectedCate 变化，确保它在 lotteryCatList 中存在
watch([() => props.lotteryCatList, () => props.selectedCate], ([catList, selectedCate]) => {
  if (catList && catList.length > 0 && selectedCate) {
    // 检查当前选中的是否在列表中
    const exists = catList.some((item: any) => item.id === selectedCate.id);
    if (!exists) {
      // 如果不存在，通知父组件切换到第一个（"全部"）
      emit("cate-change", catList[0]);
    } else {
      // 存在时才更新本地 select 值（不触发 emit，避免循环）
      selectValue.value = selectedCate.id;
    }
  } else if (catList && catList.length > 0 && !selectedCate) {
    // 如果没有选中项，通知父组件选中第一个（"全部"）
    emit("cate-change", catList[0]);
  }
}, { immediate: true });


function openNewGift() {
  editingGift.value = null;
  isGiftModalOpen.value = true;
}
function openGiftDetail(item: any) {
  editingGift.value = item;
  isGiftModalOpen.value = true;
}
function closeGiftModal() {
  isGiftModalOpen.value = false;
  editingGift.value = null;
}
function onDeleteGiftInModal(item: any) {
  if (item) {
    emit("delete", item);
    closeGiftModal();
  }
}
function onGiftSaved() {
  emit("refresh", { target: { complete: () => { } } });
}


function onRefresh(event: any) {
  emit("refresh", event);
}
function onLoadMore(event: any) {
  emit("load-more", event);
}
function onCateChange(event: any) {
  // event.detail.value 是选中的 id
  const selectedCate = props.lotteryCatList.find((cate: any) => cate.id === event.detail.value);
  if (selectedCate) {
    // 先更新本地值，让 UI 立即响应
    selectValue.value = event.detail.value;
    // 再通知父组件
    emit("cate-change", selectedCate);
  }
}


function getCateName(cateId: number) {
  const cate = _.find(props.lotteryCatList, { id: cateId });
  return cate ? cate.name : "";
}

/** 兼容 img/image 字段，优先使用本地缓存的 data URL，否则返回可展示的图片 URL */
function getGiftImgUrl(item: {
  img?: string;
  image?: string;
  cachedImgUrl?: string;
}) {
  if (item.cachedImgUrl) return item.cachedImgUrl;
  const raw = item.img ?? item.image;
  if (!raw)
    return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='96' height='96' viewBox='0 0 96 96'%3E%3Crect fill='%23e5e7eb' width='96' height='96'/%3E%3C/svg%3E";
  return getPicDisplayUrl(raw, PicDisplaySize.LIST, PicDisplaySize.LIST);
}
</script>
