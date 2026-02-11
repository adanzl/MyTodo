<template>
  <ion-segment-content id="tabPrize">
    <ion-item>
      <ion-select label="类别" placeholder="选择类别" justify="start" :model-value="selectedCate" @ionChange="onCateChange">
        <ion-select-option :value="cate" v-for="cate in lotteryCatList" :key="cate.id">
          {{ cate.name }}
        </ion-select-option>
      </ion-select>
      <ion-button class="ml-2" size="small" @click="isManageOpen = true">管理</ion-button>
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
              <div class="w-8">[{{ item.id }}]</div>
              {{ item.name }}
            </h2>
          </ion-label>
          <div class="flex items-center">
            <Icon icon="mdi:star" class="text-red-500 w-5 h-5" />
            <div class="text-left pl-1 pt-1 font-bold w-12">{{ item.cost }}</div>
            <p class="text-sm ml-2 pt-1 w-20">{{ getCateName(item.cate_id) }}</p>
            <p class="text-sm ml-2 pt-1"> {{ item.stock ?? 0 }}</p>
          </div>
        </div>
        <div class="flex gap-2" @click.stop>
          <ion-button
            class="w-10 h-10"
            @click="$emit('exchange', item)"
            :disabled="userScore < item.cost || !item.exchange || item.stock <= 0">
            兑
          </ion-button>
          <ion-button class="w-10 h-10" color="warning" @click="$emit('add-wish', item)"
            :disabled="wishList.ids.includes(item.id)">
            愿
          </ion-button>
        </div>
      </ion-item>
      <ion-infinite-scroll
        :disabled="!hasMore || loadingMore"
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

    <ion-modal :is-open="isManageOpen"
      class="[--width:100%] [--height:100%] [--max-width:100%] [--max-height:100%] [--border-radius:0]"
      @willDismiss="onManageDismiss">
      <ion-header>
        <ion-toolbar>
          <ion-title>类别管理</ion-title>
          <ion-buttons slot="start">
            <ion-button @click="closeManage">
              <ion-icon :icon="closeOutline" />
            </ion-button>
          </ion-buttons>
        </ion-toolbar>
      </ion-header>
      <ion-content>
        <div class="p-4">
          <ion-button size="small" fill="outline" @click="addCate">添加类别</ion-button>
          <ion-list lines="full" class="mt-2 w-full">
            <ion-item v-for="(cate, idx) in manageCatList" :key="cate.id ?? 'new-' + idx" mode="ios">
              <div class="flex flex-col items-stretch w-full ">
                <div class="flex items-center gap-2 mb-1">
                  <span class="text-sm text-gray-500 w-12">ID: {{ cate.id ?? -1 }}</span>
                  <ion-input :model-value="cate.name" @ionInput="cate.name = $event.detail.value" placeholder="类别名称"
                    class="flex-1 min-w-0 flex-1 " fill="outline" />
                </div>
                <div class="flex flex-wrap items-center gap-2 w-full">
                  <span class="text-sm text-gray-500 w-12">积分:</span>
                  <ion-input type="number" :model-value="cate.cost" @ionInput="cate.cost = +$event.detail.value"
                    placeholder="消耗积分" class="w-24! " fill="outline" />
                  <div class="ml-auto flex gap-2">
                    <ion-button size="small" color="primary" @click="saveCate(cate, idx)">更新</ion-button>
                    <ion-button v-if="cate.id === -1 || cate.id == null" size="small" fill="outline"
                      @click="cancelAddCate(idx)">
                      取消
                    </ion-button>
                    <ion-button v-if="cate.id !== -1 && cate.id != null" size="small" color="danger" fill="outline"
                      @click="deleteCate(cate)">
                      删除
                    </ion-button>
                  </div>
                </div>
              </div>
            </ion-item>
          </ion-list>
        </div>
      </ion-content>
    </ion-modal>
  </ion-segment-content>
</template>

<script setup lang="ts">
import {
  IonButtons,
  IonHeader,
  IonInfiniteScroll,
  IonInfiniteScrollContent,
  IonInput,
  IonList,
  IonModal,
  IonRefresher,
  IonRefresherContent,
  IonSegmentContent,
  IonSelect,
  IonSelectOption,
  IonThumbnail,
  IonTitle,
  IonToolbar,
} from "@ionic/vue";
import { Icon } from "@iconify/vue";
import { setData, delData } from "@/api/data";
import { getPicDisplayUrl } from "@/api/pic";
import { PicDisplaySize } from "@/utils/ImgMgr";
import EventBus, { C_EVENT } from "@/types/EventBus";
import { getNetworkErrorMessage } from "@/utils/NetUtil";
import _ from "lodash";
import { computed, inject, ref, watch } from "vue";
import { closeOutline } from "ionicons/icons";
import DialogGift from "./dialogs/dialog-gift.vue";

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
const loadingMore = computed(() => props.loadingMore ?? false);

const emit = defineEmits<{
  (e: "refresh", event: any): void;
  (e: "load-more", event: any): void;
  (e: "cate-change", value: any): void;
  (e: "exchange", item: any): void;
  (e: "add-wish", item: any): void;
  (e: "delete", item: any): void;
}>();

const globalVar: any = inject("globalVar");
const isManageOpen = ref(false);
const manageCatList = ref<Array<{ id?: number; name?: string; cost?: number }>>([]);
const isAdmin = computed(() => globalVar?.user?.admin === 1);

const isGiftModalOpen = ref(false);
const editingGift = ref<any>(null);

watch(
  () => [isManageOpen.value, props.lotteryCatList],
  () => {
    if (isManageOpen.value) {
      const list = props.lotteryCatList.filter((c: any) => c.id !== 0);
      manageCatList.value = list.map((c: any) => ({
        id: c.id,
        name: c.name,
        cost: c.cost ?? 0,
      }));
    }
  },
  { immediate: true }
);

function closeManage() {
  isManageOpen.value = false;
}
function onManageDismiss(event: any) {
  isManageOpen.value = false;
  if (event.detail?.role) return;
}

function addCate() {
  manageCatList.value.push({ id: -1, name: "", cost: 0 });
}
function cancelAddCate(idx: number) {
  manageCatList.value.splice(idx, 1);
}
async function saveCate(cate: any, _idx: number) {
  if (!cate.name?.trim()) {
    EventBus.$emit(C_EVENT.TOAST, "请输入类别名称");
    return;
  }
  try {
    await setData("t_gift_category", {
      id: cate.id === -1 ? undefined : cate.id,
      name: cate.name.trim(),
      cost: Number(cate.cost) || 0,
    });
    EventBus.$emit(C_EVENT.TOAST, "更新成功");
    emit("refresh", { target: { complete: () => { } } });
  } catch (err) {
    EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
  }
}

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
async function deleteCate(cate: any) {
  if (cate.id === -1 || cate.id == null) return;
  const { alertController } = await import("@ionic/vue");
  const alert = await alertController.create({
    header: "确认删除",
    message: `确定删除类别「${cate.name}」吗？`,
    buttons: [
      { text: "取消", role: "cancel" },
      {
        text: "确定",
        role: "confirm",
        handler: async () => {
          try {
            await delData("t_gift_category", cate.id);
            EventBus.$emit(C_EVENT.TOAST, "删除成功");
            _.remove(manageCatList.value, (x) => x.id === cate.id);
            emit("refresh", { target: { complete: () => { } } });
          } catch (err) {
            EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
          }
        },
      },
    ],
  });
  await alert.present();
}

function onRefresh(event: any) {
  emit("refresh", event);
}
function onLoadMore(event: any) {
  emit("load-more", event);
}
function onCateChange(event: any) {
  emit("cate-change", event.detail.value);
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
