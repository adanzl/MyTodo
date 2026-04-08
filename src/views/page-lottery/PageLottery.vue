<template>
  <ion-page id="main-content" class="main-bg">
    <ion-header>
      <ion-toolbar>
        <ion-title class="px-2">Secret Room</ion-title>
        <ion-buttons slot="end">
          <ServerRemoteBadge />
          <ion-button @click="btnSettingClk" :disabled="!isAdmin">
            <Icon icon="weui:setting-outlined" class="w-7 h-7" />
          </ion-button>
        </ion-buttons>
      </ion-toolbar>
    </ion-header>

    <ion-segment :value="segmentValue" @ionChange="handleSegmentChange">
      <ion-segment-button
        value="lotterySpecial"
        content-id="tabLottery"
        layout="icon-start"
        class="text-blue-500">
        <ion-icon :icon="heartOutline" class="w-4 h-4"></ion-icon>
        <ion-label class="ml-1">抽奖</ion-label>
      </ion-segment-button>
      <ion-segment-button value="shop" content-id="tabPrize" layout="icon-start" class="text-blue-500">
        <ion-icon :icon="giftOutline" class="w-4 h-4"></ion-icon>
        <ion-label class="ml-1">商店</ion-label>
      </ion-segment-button>
      <ion-segment-button
        value="history"
        content-id="tabHistory"
        layout="icon-start"
        class="text-blue-500">
        <Icon icon="material-symbols:history" class="w-4 h-4" />
        <ion-label class="ml-1">积分历史</ion-label>
      </ion-segment-button>
    </ion-segment>
    <ion-segment-view :style="{ height: `calc(100% - ${tabsHeight}px)` }">
      <LotteryTab
        :pool-list="poolList"
        :selected-pool="selectedPool"
        :wish-list="wishList"
        :lottery-data="lotteryDate"
        :user-score="globalVar.user.score"
        @pool-change="handlePoolChange"
        @lottery="btnLotteryClk"
        @remove-wish="btnRemoveWishClk"
        @open-pool="btnPoolClk" />
      <TabPrize
        :lottery-cat-list="lotteryCatList"
        :selected-cate="selectedCate"
        :gift-list="giftList"
        :wish-list="wishList"
        :user-score="globalVar.user.score"
        :has-more="giftListHasMore"
        :loading-more="loadingGifts"
        @refresh="onRefresh"
        @load-more="loadMoreGifts"
        @cate-change="handleShopCateChange"
        @exchange="btnExchangeClk"
        @add-wish="btnAddWishClk"
        @delete="btnDeleteGiftClk" />
      <HistoryTab
        :user-list="userList"
        :selected-user="selectedUser"
        :score-history-list="scoreHistoryList"
        :user-score="globalVar.user.score"
        :selected-action="selectedAction"
        :has-more="scoreHistoryHasMore"
        @refresh="onRefresh"
        @user-change="handleUserChange"
        @action-change="handleActionChange"
        @load-more="loadMoreScoreHistory" />
    </ion-segment-view>
    <LotterySetting :is-open="lotterySetting.open" @willDismiss="onSettingDismiss" @saved="handleFullRefresh" />
    <LotteryPool :is-open="lotteryPool.open" @willDismiss="onPoolDismiss" @refresh="handleFullRefresh" />
  </ion-page>
</template>

<script setup lang="ts">
import ServerRemoteBadge from "@/components/ServerRemoteBadge.vue";
import { Icon } from "@iconify/vue";
import EventBus, { C_EVENT } from "@/types/event-bus";
import { getList } from "@/api/data";
import { doExchange, doLottery, getGiftData, getLotteryData, getGiftList, delGiftData, getGiftCategoryList, getGiftPoolList } from "@/api/api-lottery";
import { clearUserListCache, getUserList, setUserData } from "@/api/api-user";
import { getNetworkErrorMessage } from "@/utils/net-util";
import { getCachedPicByName, PicDisplaySize } from "@/utils/img-mgr";
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
import { computed, inject, nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import LotteryTab from "./TabLottery.vue";
import TabPrize from "./TabPrize.vue";
import HistoryTab from "./TabHistory.vue";
import LotterySetting from "./dialogs/LotterySetting.vue";
import LotteryPool from "./dialogs/LotteryPool.vue";

const PAGE_SIZE = 20;
const lotterySetting = ref({ open: false });
const lotteryPool = ref({ open: false });
const globalVar: any = inject("globalVar");
const isAdmin = computed(() => globalVar?.user?.admin === 1);
const lotteryDate = ref<any>({});
const segmentValue = ref("lotterySpecial");  // Default to lottery special
const selectedPool = ref<any>(null);

const wishList = ref<any>({
  progress: 30.2,  // 这个是个数
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
const loadingGifts = ref(false);
const giftListHasMore = computed(() => {
  const { pageNum, totalPage, data, totalCount } = giftList.value;
  // 如果正在加载中，返回 false 防止重复触发
  if (loadingGifts.value) return false;
  if (totalCount > 0 && data.length < totalCount) return true;
  return pageNum < totalPage;
});
const scoreHistoryHasMore = computed(() => {
  const { pageNum, totalPage, data, totalCount } = scoreHistoryList.value;
  if (totalCount > 0 && data.length < totalCount) return true;
  return pageNum < totalPage;
});
const scoreHistoryList = ref<any>({
  data: [],
  pageNum: 1,
  pageSize: PAGE_SIZE,
  totalCount: 0,
  totalPage: 0,
});
const lotteryCatList = ref<any>([]);
const poolList = ref<any[]>([]);
const userList = ref<any>([]);
const selectedCate = ref<any>(null);
const selectedUser = ref<any>({ id: 0, name: "全部", score: 0 });
const selectedAction = ref<string>("");
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
  handleRefresh({ target: { complete: () => { } } });

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

const onNavToCate = (cateId: number) => {
  const target = lotteryCatList.value.find((c: any) => c.id === cateId);
  if (target) {
    selectedCate.value = target;
  } else {
    selectedCate.value = {
      id: cateId,
      name: "",
      cost: lotteryDate.value.fee || 10,
    };
  }
  segmentValue.value = "shop";
  if (selectedCate.value) {
    refreshGiftList(selectedCate.value.id);
  }
};

EventBus.$on(C_EVENT.LOTTERY_NAV_TO_CATE, onNavToCate);
onBeforeUnmount(() => {
  window.removeEventListener("resize", updateTabsHeight);
  if (observer) {
    observer.disconnect();
    observer = null;
  }
  EventBus.$off(C_EVENT.LOTTERY_NAV_TO_CATE, onNavToCate);
});

function onRefresh(event: any) {
  handleRefresh(event);
}

// 用于奖池管理弹窗关闭后的完整刷新（不需要 event.target.complete）
function handleFullRefresh() {
  const cateId = selectedCate.value?.id === 0 ? undefined : selectedCate.value?.id;
  refreshGiftList(cateId, 1);
  refreshCateList();
  refreshPoolList();
  refreshScoreHistoryList(selectedUser.value?.id, 1);
  getLotteryData()
    .then((data: any) => {
      lotteryDate.value = JSON.parse(data);
      if (selectedCate.value && selectedCate.value.id == 0) {
        selectedCate.value.cost = lotteryDate.value.fee;
      }
    })
    .catch((err) => {
      EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
    });
}

function handleRefresh(event: any) {
  const cateId = selectedCate.value?.id === 0 ? undefined : selectedCate.value?.id;
  refreshGiftList(cateId, 1);
  refreshCateList();
  refreshPoolList();
  refreshScoreHistoryList(selectedUser.value?.id, 1);
  getLotteryData()
    .then((data: any) => {
      lotteryDate.value = JSON.parse(data);
      if (selectedCate.value && selectedCate.value.id == 0) {
        selectedCate.value.cost = lotteryDate.value.fee;
      }
    })
    .catch((err) => {
      EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
    })
    .finally(() => event.target.complete());
}

function handleSegmentChange(event: any) {
  segmentValue.value = event.detail.value;
  if (segmentValue.value === "shop" && selectedCate.value) {
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

function btnPoolClk() {
  lotteryPool.value.open = true;
}
function onPoolDismiss(event: any) {
  lotteryPool.value.open = false;
  if (event.detail.role === "cancel") {
    return;
  }
}

async function refreshScoreHistoryList(userId: number | undefined, pageNum: number, append: boolean = false) {
  let filter = undefined;

  // 构建筛选条件
  const filterConditions: Record<string, any> = {};
  if (userId && userId !== 0) {
    filterConditions.user_id = userId;
  }

  // action 筛选
  if (selectedAction.value) {
    filterConditions.action = selectedAction.value;
  }

  // 如果 filterConditions 不为空才使用
  if (Object.keys(filterConditions).length > 0) {
    filter = filterConditions;
  }

  try {
    const data = await getList("t_score_history", filter, pageNum, PAGE_SIZE);
    if (!append) {
      scoreHistoryList.value = data;
    } else {
      // 追加数据
      scoreHistoryList.value.data.push(...data.data);
      scoreHistoryList.value.pageNum = data.pageNum;
      scoreHistoryList.value.totalCount = data.totalCount;
      scoreHistoryList.value.totalPage = data.totalPage;
    }
  } catch (err) {
    EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
  }
}
function refreshCateList() {
  getGiftCategoryList()
    .then((data) => {
      const d = data.data;
      lotteryCatList.value = [...d];
      lotteryCatList.value.unshift({ id: 0, name: "全部", cost: lotteryDate.value.fee || 100 });
      // 注意：不再在这里设置 selectedCate，交给子组件的 watch 处理
    })
    .catch((err) => {
      EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
    });
}
function refreshPoolList() {
  getGiftPoolList()
    .then((data) => {
      const pools = data?.data ?? [];
      poolList.value = [...pools];

      // 在奖池列表前添加"全部"选项
      if (poolList.value.length > 0) {
        // 检查是否已存在 ID 为 0 的"全部"奖池
        const hasAllPool = poolList.value.some((pool: any) => pool.id === 0);
        if (!hasAllPool) {
          poolList.value.unshift({
            id: 0,
            name: "全部",
            cost: lotteryDate.value.fee || 10,
            count: 1,
          });
        }
      } else {
        // 如果没有奖池数据，创建默认的"全部"奖池
        poolList.value = [{
          id: 0,
          name: "全部",
          cost: lotteryDate.value.fee || 10,
          count: 1,
        }];
      }

      // 注意：不再在这里设置 selectedCate，交给子组件的 watch 处理
    })
    .catch((err) => {
      EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
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
        globalVar.user.score = sUser.score ?? globalVar.user.score;
        wishList.value.progress = sUser.wish_progress ?? 0;
        if (sUser.wish_list) {
          wishList.value.ids = sUser.wish_list;
          wishList.value.data = [];
          _.forEach(wishList.value.ids, async (gId) => {
            const item = await getGiftData(gId);
            wishList.value.data.push({
              id: item.id,
              name: item.name,
              image: item.image,
            });
          });
        }
      }
    })
    .catch((err) => {
      EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
    });
}

async function refreshGiftList(
  cateId?: number | undefined,
  pageNum: number = 1,
  append: boolean = false
): Promise<void> {
  const filter: Record<string, unknown> = {
    enable: 1,
    show: 1,
    stock: ['>', 0],  // stock > 0
  };
  if (cateId) {
    filter["cate_id"] = cateId;
  }
  if (append) {
    loadingGifts.value = true;
  }
  try {
    try {
      const data = await getGiftList({ conditions: filter, pageNum, pageSize: PAGE_SIZE });
      const d = data.data ?? [];
      if (!append) {
        giftList.value.data = [];
      }
      const totalCount = Number(data.totalCount) ?? 0;
      const pageSizeNum = Number(data.pageSize) || PAGE_SIZE;
      giftList.value.pageNum = Number(data.pageNum) ?? pageNum;
      giftList.value.pageSize = pageSizeNum;
      giftList.value.totalCount = totalCount;
      // 兜底：接口未返回 totalPage 或为 0 时，用 totalCount 推算，避免翻页一直为 false
      const rawTotalPage = Number(data.totalPage);
      giftList.value.totalPage =
        rawTotalPage > 0
          ? rawTotalPage
          : totalCount > 0
            ? Math.max(1, Math.ceil(totalCount / pageSizeNum))
            : 0;

      _.forEach(d, (item) => {
        const row = {
          ...item,
          edited: false,
          cachedImgUrl: "" as string,
        };
        giftList.value.data.push(row);
        const name = item.image;
        if (name) {
          getCachedPicByName(name, PicDisplaySize.LIST, PicDisplaySize.LIST).then(
            (url) => {
              row.cachedImgUrl = url;
            }
          );
        }
      });
    } catch (err) {
      EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
    }
  } finally {
    loadingGifts.value = false;
  }
}

function loadMoreGifts(event: any) {
  const { pageNum, totalPage, data, totalCount } = giftList.value;
  const noMore =
    totalCount > 0 ? data.length >= totalCount : pageNum >= totalPage;
  if (loadingGifts.value || noMore) {
    // 立即完成事件，防止重复触发
    event?.target?.complete();
    return;
  }
  refreshGiftList(
    selectedCate.value?.id === 0 ? undefined : selectedCate.value?.id,
    giftList.value.pageNum + 1,
    true
  ).finally(() => {
    nextTick(() => {
      event?.target?.complete();
    });
  });
}

function handlePoolChange(value: any) {
  selectedPool.value = value;
}

function handleShopCateChange(value: any) {
  selectedCate.value = value;
  refreshGiftList(value?.id);
}
function handleUserChange(value: any) {
  selectedUser.value = value;
  refreshScoreHistoryList(value?.id, 1);
}
function handleActionChange(value: string) {
  selectedAction.value = value;
  refreshScoreHistoryList(selectedUser.value?.id, 1);
}

function loadMoreScoreHistory(event: any) {
  const { pageNum, totalPage, data, totalCount } = scoreHistoryList.value;
  const noMore =
    totalCount > 0 ? data.length >= totalCount : pageNum >= totalPage;
  if (noMore) {
    event?.target?.complete();
    return;
  }
  refreshScoreHistoryList(
    selectedUser.value?.id,
    scoreHistoryList.value.pageNum + 1,
    true
  ).finally(() => {
    nextTick(() => {
      event?.target?.complete();
    });
  });
}

async function btnLotteryClk() {
  const { alertController, loadingController } = await import("@ionic/vue");
  const poolName = selectedPool.value?.name ?? "当前奖池";
  const alert = await alertController.create({
    header: "确认抽奖",
    message: `确定使用积分进行抽奖吗？\n（${poolName}）`,
    buttons: [
      { text: "取消", role: "cancel" },
      {
        text: "确定",
        role: "confirm",
        handler: async () => {
          const loading = await loadingController.create({ message: "抽奖中..." });
          await loading.present();
          try {
            const data = await doLottery(globalVar.user.id, selectedPool.value.id);
            // 优先使用 gifts 数组（支持多个中奖礼物），兼容旧的 gift 字段
            const wonGifts: any[] = data.gifts || (data.gift ? [data.gift] : []);
            if (wonGifts.length > 0) {
              // 构建奖励列表
              const rewardList = wonGifts.map((gift) => ({
                value: gift.name || "-",
                img: gift.image || "",
                rewardType: "gift" as const,
              }));
              // 只有一个元素时使用 REWARD，多个元素时使用 REWARD_LIST
              if (rewardList.length === 1) {
                EventBus.$emit(C_EVENT.REWARD, rewardList[0]);
              } else {
                EventBus.$emit(C_EVENT.REWARD_LIST, {
                  rewardList,
                });
              }
            }
            EventBus.$emit(C_EVENT.TOAST, "抽奖成功");
            clearUserListCache();
            await refreshUserList();
          } catch (err) {
            EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
          } finally {
            await loading.dismiss();
          }
        },
      },
    ],
  });
  await alert.present();
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
              EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
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
      EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
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
        handler: async () => {
          try {
            const data = await doExchange(globalVar.user.id, item.id);
            // 兑换只返回单个礼物
            EventBus.$emit(C_EVENT.REWARD, {
              value: data.gift.name || "-",
              img: data.gift.image || "",
              rewardType: "gift" as const,
            });
            EventBus.$emit(C_EVENT.TOAST, "兑换成功");
            clearUserListCache();
            await refreshUserList();
            refreshGiftList(selectedCate.value?.id, 1);
          } catch (err) {
            EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
          }
        },
      },
      "Cancel",
    ],
  });
  await alert.present();
}

async function btnDeleteGiftClk(item: any) {
  const { alertController } = await import("@ionic/vue");
  const alert = await alertController.create({
    header: "确认删除",
    message: `确定删除奖品「${item.name}」吗？`,
    buttons: [
      { text: "取消", role: "cancel" },
      {
        text: "确定",
        role: "confirm",
        handler: async () => {
          try {
            await delGiftData(item.id);
            EventBus.$emit(C_EVENT.TOAST, "删除成功");
            refreshGiftList(selectedCate.value?.id, 1);
          } catch (err) {
            EventBus.$emit(C_EVENT.TOAST, getNetworkErrorMessage(err));
          }
        },
      },
    ],
  });
  await alert.present();
}
</script>
