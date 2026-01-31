<template>
  <ion-page id="main-content" class="main-bg">
    <ion-header>
      <ion-toolbar>
        <ion-title class="px-2">Secret Room</ion-title>
        <ion-buttons slot="end">
          <ServerRemoteBadge />
          <ion-button @click="btnSettingClk">
            <Icon icon="weui:setting-outlined" class="w-7 h-7" />
          </ion-button>
        </ion-buttons>
      </ion-toolbar>
    </ion-header>

    <ion-segment value="lotterySpecial" @ionChange="handleSegmentChange">
      <ion-segment-button
        value="lotterySpecial"
        content-id="lotterySpecial"
        layout="icon-start"
        class="text-blue-500">
        <ion-icon :icon="heartOutline" class="w-4 h-4"></ion-icon>
        <ion-label class="ml-1">抽取奖励</ion-label>
      </ion-segment-button>
      <ion-segment-button value="shop" content-id="shop" layout="icon-start" class="text-blue-500">
        <ion-icon :icon="giftOutline" class="w-4 h-4"></ion-icon>
        <ion-label class="ml-1">积分兑换</ion-label>
      </ion-segment-button>
      <ion-segment-button
        value="history"
        content-id="history"
        layout="icon-start"
        class="text-blue-500">
        <Icon icon="material-symbols:history" class="w-4 h-4" />
        <ion-label class="ml-1">积分历史</ion-label>
      </ion-segment-button>
    </ion-segment>
    <ion-segment-view :style="{ height: `calc(100% - ${tabsHeight}px)` }">
      <LotteryTab
        :lottery-cat-list="lotteryCatList"
        :selected-cate="selectedCate"
        :wish-list="wishList"
        :lottery-data="lotteryDate"
        :user-score="globalVar.user.score"
        @cate-change="handleShopCateChange"
        @lottery="btnLotteryClk"
        @remove-wish="btnRemoveWishClk" />
      <ShopTab
        :lottery-cat-list="lotteryCatList"
        :selected-cate="selectedCate"
        :gift-list="giftList"
        :wish-list="wishList"
        :user-score="globalVar.user.score"
        @refresh="onRefresh"
        @cate-change="handleShopCateChange"
        @exchange="btnExchangeClk"
        @add-wish="btnAddWishClk" />
      <HistoryTab
        :user-list="userList"
        :selected-user="selectedUser"
        :score-history-list="scoreHistoryList"
        :user-score="globalVar.user.score"
        @refresh="onRefresh"
        @user-change="handleUserChange" />
    </ion-segment-view>
    <LotterySetting :is-open="lotterySetting.open" @willDismiss="onSettingDismiss" />
  </ion-page>
</template>

<script setup lang="ts">
import ServerRemoteBadge from "@/components/ServerRemoteBadge.vue";
import { Icon } from "@iconify/vue";
import EventBus, { C_EVENT } from "@/modal/EventBus";
import {
  doLottery,
  getGiftData,
  getList,
  getLotteryData,
  getUserList,
  setUserData,
} from "@/utils/NetUtil";
import {
  IonButton,
  IonHeader,
  IonIcon,
  IonPage,
  IonSegment,
  IonSegmentButton,
  IonSegmentView,
} from "@ionic/vue";
import { giftOutline, heartOutline } from "ionicons/icons";
import _ from "lodash";
import { inject, onBeforeUnmount, onMounted, ref } from "vue";
import LotteryTab from "./LotteryTab.vue";
import ShopTab from "./ShopTab.vue";
import HistoryTab from "./HistoryTab.vue";

const PAGE_SIZE = 20;
const lotterySetting = ref({ open: false });
const globalVar: any = inject("globalVar");
const lotteryDate = ref<any>({});

const wishList = ref<any>({
  progress: 30.2,
  ids: [],
  data: [],
});
const giftList = ref<any>({
  data: [],
  pageNum: 1,
  pageSize: PAGE_SIZE,
  totalCount: 0,
  totalPage: 0,
});
const scoreHistoryList = ref<any>({
  data: [],
  pageNum: 1,
  pageSize: PAGE_SIZE,
  totalCount: 0,
  totalPage: 0,
});
const lotteryCatList = ref<any>([]);
const userList = ref<any>([]);
const selectedCate = ref<any>({ id: 0, name: "全部", cost: lotteryDate.value.fee || 10 });
const selectedUser = ref<any>({ id: 0, name: "全部", score: 0 });
const tabsHeight = ref(0);
let observer: MutationObserver | null = null;

const updateTabsHeight = () => {
  const tabs = document.querySelector("ion-tab-bar");
  if (tabs) {
    tabsHeight.value = tabs.clientHeight;
  }
};

onMounted(async () => {
  await refreshUserList();
  handleRefresh({ target: { complete: () => {} } });

  observer = new MutationObserver(() => {
    updateTabsHeight();
  });
  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });
  updateTabsHeight();
  window.addEventListener("resize", updateTabsHeight);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", updateTabsHeight);
  if (observer) {
    observer.disconnect();
    observer = null;
  }
});

function onRefresh(event: any) {
  handleRefresh(event);
}

function handleRefresh(event: any) {
  refreshGiftList(undefined, 1);
  refreshCateList();
  refreshScoreHistoryList(undefined, 1);
  getLotteryData()
    .then((data: any) => {
      lotteryDate.value = JSON.parse(data);
      if (selectedCate.value.id == 0) {
        selectedCate.value.cost = lotteryDate.value.fee;
      }
    })
    .catch((err) => {
      EventBus.$emit(C_EVENT.TOAST, JSON.stringify(err));
    })
    .finally(() => event.target.complete());
}

function handleSegmentChange(event: any) {
  if (event.detail.value === "shop") {
    refreshGiftList(selectedCate.value.id);
  }
}

function btnSettingClk() {
  lotterySetting.value.open = true;
}
function onSettingDismiss(event: any) {
  lotterySetting.value.open = false;
  if (event.detail.role === "cancel") {
    return;
  }
}

function refreshScoreHistoryList(userId: number | undefined, pageNum: number) {
  let filter = undefined;
  if (userId) {
    filter = { user_id: userId };
  }
  getList("t_score_history", filter, pageNum, PAGE_SIZE)
    .then((data) => {
      scoreHistoryList.value = data;
    })
    .catch((err) => {
      EventBus.$emit(C_EVENT.TOAST, JSON.stringify(err));
    });
}
function refreshCateList() {
  getList("t_gift_category")
    .then((data) => {
      const d = data.data;
      lotteryCatList.value = [...d];
      lotteryCatList.value.unshift({ id: 0, name: "全部", cost: lotteryDate.value.fee || 100 });
      if (selectedCate.value.id == 0) {
        selectedCate.value = lotteryCatList.value[0];
      }
    })
    .catch((err) => {
      EventBus.$emit(C_EVENT.TOAST, JSON.stringify(err));
    });
}
async function refreshUserList() {
  await getUserList()
    .then((uList) => {
      userList.value = [...uList.data];
      userList.value.unshift({ id: 0, name: "全部", score: 0 });
      if (selectedUser.value.id == 0) {
        selectedUser.value = userList.value[0];
      }

      const sUser = _.find(uList.data, (u) => u.id === globalVar.user.id);
      if (sUser) {
        wishList.value.progress = sUser.wish_progress ?? 0;
        if (sUser.wish_list) {
          wishList.value.ids = sUser.wish_list;
          wishList.value.data = [];
          _.forEach(wishList.value.ids, async (gId) => {
            const item = await getGiftData(gId);
            wishList.value.data.push({
              id: item.id,
              name: item.name,
              img: item.image,
            });
          });
        }
      }
    })
    .catch((err) => {
      EventBus.$emit(C_EVENT.TOAST, JSON.stringify(err));
    });
}

function refreshGiftList(cateId?: number | undefined, pageNum?: number) {
  const filter = { enable: 1 };
  if (cateId) {
    filter["cate_id"] = cateId;
  }
  getList("t_gift", filter, pageNum, PAGE_SIZE)
    .then((data) => {
      const d = data.data;
      giftList.value.data = [];
      giftList.value.pageNum = data.pageNum;
      giftList.value.pageSize = data.pageSize;
      giftList.value.totalCount = data.totalCount;
      giftList.value.totalPage = data.totalPage;

      _.forEach(d, (item) => {
        giftList.value.data.push({
          id: item.id,
          name: item.name,
          img: item.image,
          cate_id: item.cate_id,
          cost: item.cost,
          edited: false,
        });
      });
    })
    .catch((err) => {
      EventBus.$emit(C_EVENT.TOAST, JSON.stringify(err));
    });
}

function handleShopCateChange(value: any) {
  selectedCate.value = value;
  refreshGiftList(value?.id);
}
function handleUserChange(value: any) {
  selectedUser.value = value;
  refreshScoreHistoryList(value?.id, 1);
}

function btnLotteryClk() {
  doLottery(globalVar.user.id, selectedCate.value.id)
    .then((data) => {
      console.log("lottery data", data);
      EventBus.$emit(C_EVENT.REWARD, {
        value: data.gift.name,
        img: data.gift.image,
        rewardType: "gift",
      });
    })
    .catch((err) => {
      EventBus.$emit(C_EVENT.TOAST, JSON.stringify(err));
    });
}

async function btnRemoveWishClk(item: any) {
  const { alertController } = await import("@ionic/vue");
  const alert = await alertController.create({
    header: "Confirm",
    subHeader: "确认移除心愿单",
    message: "[" + item.id + "] " + item.name,
    buttons: [
      {
        text: "OK",
        handler: () => {
          _.remove(globalVar.user.wish_list, (i: number) => i === item.id);
          setUserData(globalVar.user)
            .then(() => {
              EventBus.$emit(C_EVENT.TOAST, "移除心愿成功");
              _.remove(wishList.value.ids, (i: number) => i === item.id);
              _.remove(wishList.value.data, (i: any) => i.id === item.id);
            })
            .catch((err) => {
              EventBus.$emit(C_EVENT.TOAST, JSON.stringify(err));
            });
        },
      },
      "Cancel",
    ],
  });
  await alert.present();
}

async function btnAddWishClk(item: any) {
  if (globalVar.user.wish_list === undefined) {
    globalVar.user.wish_list = [];
  }
  globalVar.user.wish_list.push(item.id);
  setUserData(globalVar.user)
    .then(() => {
      EventBus.$emit(C_EVENT.TOAST, "添加心愿成功");
      wishList.value.ids.push(item.id);
      wishList.value.data.push({
        id: item.id,
        name: item.name,
        img: item.img,
      });
    })
    .catch((err) => {
      EventBus.$emit(C_EVENT.TOAST, JSON.stringify(err));
    });
}

async function btnExchangeClk(item: any) {
  const { alertController } = await import("@ionic/vue");
  const alert = await alertController.create({
    header: "Confirm",
    subHeader: "确认兑换: " + item.name + "",
    message: "花费：" + item.cost + " 积分",
    buttons: [
      {
        text: "OK",
        handler: () => {
          console.log("cost");
        },
      },
      "Cancel",
    ],
  });
  await alert.present();
}
</script>
