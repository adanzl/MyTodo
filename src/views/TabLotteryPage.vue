<template>
  <ion-page id="main-content" class="main-bg">
    <ion-header>
      <ion-toolbar>
        <ion-title>Secret Room</ion-title>
        <ion-buttons slot="end">
          <ion-button @click="btnSettingClk">
            <WeuiSettingOutlined class="button-native" width="30" height="30" />
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
        <ion-label>抽取奖励</ion-label>
        <ion-icon :icon="heartOutline"></ion-icon>
      </ion-segment-button>
      <ion-segment-button value="shop" content-id="shop" layout="icon-start" class="text-blue-500">
        <ion-icon :icon="giftOutline"></ion-icon>
        <ion-label>积分兑换</ion-label>
      </ion-segment-button>
      <ion-segment-button
        value="history"
        content-id="history"
        layout="icon-start"
        class="text-blue-500">
        <MaterialSymbolsHistory width="25" height="25" />
        <ion-label>积分历史</ion-label>
      </ion-segment-button>
    </ion-segment>
    <ion-segment-view :style="{ height: `calc(100% - ${tabsHeight}px)` }">
      <!-- 抽奖页签 -->
      <ion-segment-content id="lotterySpecial">
        <ion-content>
          <ion-item>
            <div class="flex items-center justify-center">
              <span>当前积分：</span>
              <MdiStar class="text-red-500" />
              <div class="text-left pl-1 font-bold w-12">{{ globalVar.user.score }}</div>
            </div>
          </ion-item>
          <ion-radio-group
            :value="selectedCate"
            class="radio-grid p-5"
            @ionChange="handleShopCateChange">
            <ion-radio
              v-for="item in lotteryCatList"
              :key="item.id"
              :value="item"
              label-placement="end"
              justify="start">
              <span class="text-black">{{ item.name }}</span>
            </ion-radio>
          </ion-radio-group>
          <div class="flex items-center justify-center bg-slate-400 h-[calc(100%-300px)]">
            <ion-button @click="btnLotteryClk" size="default">
              <div class="w-20 h-20 flex flex-col items-center justify-center">
                <span>立即抽奖</span>
                <div class="flex items-center justify-center mt-2">
                  <MdiStar class="text-red-500" />{{ selectedCate.cost }}
                </div>
              </div>
            </ion-button>
          </div>
          <!-- 心愿单 -->
          <div class="px-4">
            <h2 class="text-lg text-blue-500 font-bold">心愿单</h2>
            <swiper
              class="py-4"
              :freeMode="{ enabled: true, momentumRatio: 0.5 }"
              :modules="[FreeMode]"
              :slidesPerView="'auto'"
              :resistance="true"
              :resistanceRatio="0.5"
              @swiper="setSwiperInstance">
              <swiper-slide v-for="item in lotteryHistory" :key="item.id" class="!w-auto px-2">
                <div class="w-24 h-24 relative">
                  <img :src="item.img" class="w-full h-full object-cover rounded-lg" />
                  <div
                    class="absolute bottom-0 left-0 right-0 bg-black bg-opacity-50 text-white text-xs p-1 rounded-b-lg truncate">
                    {{ item.name }}
                  </div>
                </div>
              </swiper-slide>
            </swiper>
          </div>
        </ion-content>
      </ion-segment-content>
      <!-- 积分兑换页签 -->
      <ion-segment-content id="shop">
        <ion-item>
          <ion-select
            label="类别"
            placeholder="选择类别"
            v-model="selectedCate"
            @ionChange="handleShopCateChange">
            <ion-select-option :value="cate" v-for="cate in lotteryCatList" :key="cate.id">
              {{ cate.name }}
            </ion-select-option>
          </ion-select>
          <div class="flex w-1/3 items-center justify-center">
            <MdiStar class="text-red-500" />
            <div class="text-left pl-1 font-bold w-12">{{ globalVar.user.score }}</div>
          </div>
        </ion-item>
        <ion-content :scrollY="true" :style="{ height: 'calc(100% - 56px)' }">
          <ion-refresher slot="fixed" @ionRefresh="handleRefresh($event)">
            <ion-refresher-content></ion-refresher-content>
          </ion-refresher>
          <ion-item v-for="item in giftList.data" :key="item.id">
            <ion-thumbnail slot="start">
              <img :src="item.img" />
            </ion-thumbnail>
            <div class="w-full">
              <ion-label>
                <h2 class="flex">
                  <div class="w-8">[{{ item.id }}]</div>
                  {{ item.name }}
                </h2>
              </ion-label>
              <div class="flex items-center">
                <MdiStar class="text-red-500" />
                <div class="text-left pl-1 font-bold w-12">{{ item.cost }}</div>
                <p class="text-sm ml-2">{{ getCateName(item.cate_id) }}</p>
              </div>
            </div>
            <ion-button @click="btnExchangeClk(item)" size="default"> 兑 </ion-button>
          </ion-item>
        </ion-content>
      </ion-segment-content>
      <!-- 积分历史 -->
      <ion-segment-content id="history">
        <ion-item>
          <!-- 用户筛选 -->
          <ion-select label="用户" v-model="selectedUser" @ionChange="handleUserChange">
            <ion-select-option :value="item" v-for="item in userList" :key="item.id">
              {{ item.name }}
            </ion-select-option>
          </ion-select>
          <div class="flex w-1/3 items-center justify-center">
            <MdiStar class="text-red-500" />
            <div class="text-left pl-1 font-bold w-12">{{ globalVar.user.score }}</div>
          </div>
        </ion-item>
        <ion-content :scrollY="true" :style="{ height: 'calc(100% - 56px)' }">
          <ion-refresher slot="fixed" @ionRefresh="handleRefresh($event)">
            <ion-refresher-content></ion-refresher-content>
          </ion-refresher>
          <ion-item v-for="item in scoreHistoryList.data" :key="item.id">
            <div class="flex flex-col w-full">
              <div class="flex">
                <div class="w-1/5">ID: {{ item.id }}</div>
                <div class="ml-2 flex items-center w-1/4">
                  {{ item.action }}
                </div>
                <div class="ml-2 flex items-center text-sm">
                  <ion-icon class="mr-1" :icon="timeOutline"></ion-icon>
                  {{ formatDate(item.dt) }}
                </div>
              </div>
              <div class="flex mb-2">
                <div class="flex item-center w-1/5">
                  V:
                  {{ item.value }}
                </div>
                <div class="ml-2 flex items-center w-1/4">
                  <MdiStar class="text-red-500" />
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
    </ion-segment-view>
    <LotterySetting :is-open="lotterySetting.open" @willDismiss="onSettingDismiss" />
  </ion-page>
</template>

<script setup lang="ts">
import EventBus, { C_EVENT } from "@/modal/EventBus";
import { LotteryData } from "@/modal/UserData";
import { getImage } from "@/utils/ImgMgr";
import { getList, getLotteryData, getUserList } from "@/utils/NetUtil";
import {
  IonButton,
  IonContent,
  IonHeader,
  IonIcon,
  IonItem,
  IonLabel,
  IonPage,
  IonRadio,
  IonRadioGroup,
  IonRefresher,
  IonRefresherContent,
  IonSegment,
  IonSegmentButton,
  IonSegmentContent,
  IonSegmentView,
  IonSelect,
  IonSelectOption,
  IonThumbnail,
  alertController,
} from "@ionic/vue";
import "@ionic/vue/css/ionic-swiper.css";
import dayjs from "dayjs";
import { chatbubbleEllipsesOutline, giftOutline, heartOutline, timeOutline } from "ionicons/icons";
import _ from "lodash";
import "swiper/css";
import "swiper/css/free-mode";
import { FreeMode } from "swiper/modules";
import { Swiper, SwiperSlide } from "swiper/vue";
import { inject, onBeforeUnmount, onMounted, ref } from "vue";
import MaterialSymbolsHistory from "~icons/material-symbols/history";
import MdiStar from "~icons/mdi/star";
import WeuiSettingOutlined from "~icons/weui/setting-outlined";

const lotteryData = ref<LotteryData[] | []>([]);
const COL_SIZE = 3; // 列数
const ROW_SIZE_MIN = 4; // 行数最小值
const PAGE_SIZE = 20; // 每页显示的数量
const lotteryMatrix = ref<LotteryData[][]>([]);
const lotterySetting = ref({ open: false });
const globalVar: any = inject("globalVar");
// const winner = ref({ bWin: false, prize: "" });

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
const selectedCate = ref<any>({ id: 0, name: "全部", cost: 100 });
const selectedUser = ref<any>({ id: 0, name: "全部", score: 0 });
const tabsHeight = ref(0);
const swiperRef = ref(); // 滑动对象
let observer: MutationObserver | null = null;

const lotteryHistory = ref([
  { id: 1, name: "奖品1", img: "https://picsum.photos/200" },
  { id: 2, name: "奖品2", img: "https://picsum.photos/201" },
  { id: 3, name: "奖品3", img: "https://picsum.photos/202" },
  { id: 4, name: "奖品4", img: "https://picsum.photos/203" },
  { id: 5, name: "奖品5", img: "https://picsum.photos/204" },
]);

function setSwiperInstance(swiper: any) {
  swiperRef.value = swiper;
  swiper.update();
}
const updateTabsHeight = () => {
  const tabs = document.querySelector("ion-tab-bar");
  if (tabs) {
    tabsHeight.value = tabs.clientHeight;
  }
};

onMounted(() => {
  // 获取数据
  refreshGiftList(undefined, 1);
  refreshCateList();
  refreshScoreHistoryList(undefined, 1);
  refreshUserList();

  // 创建 MutationObserver 监听 tabs 元素
  observer = new MutationObserver(() => {
    updateTabsHeight();
  });

  // 开始监听 body 的变化，因为 tabs 可能还没有渲染
  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });

  // 立即尝试获取一次高度
  updateTabsHeight();

  // 监听窗口大小变化
  window.addEventListener("resize", updateTabsHeight);
});

onBeforeUnmount(() => {
  // 移除事件监听
  window.removeEventListener("resize", updateTabsHeight);
  // 断开 observer
  if (observer) {
    observer.disconnect();
    observer = null;
  }
});

function handleRefresh(event: any) {
  getLotteryData()
    .then((data: any) => {
      buildLotteryMatrix(JSON.parse(data));
    })
    .catch((err) => {
      EventBus.$emit(C_EVENT.TOAST, JSON.stringify(err));
    })
    .finally(() => event.target.complete());
}

async function buildLotteryMatrix(data: LotteryData[]) {
  lotteryData.value = data;
  const matrix: any = [];
  const length = Math.max(ROW_SIZE_MIN, Math.ceil(data.length / COL_SIZE));
  let ii = 0;
  for (let i = 0; i < length; i++) {
    const row: LotteryData[] = [];
    for (let j = 0; j < COL_SIZE; j++) {
      const d = data[ii++ % data.length];
      d.img = await getImage(d.imgId);
      row.push(_.clone(d));
    }
    matrix.push(row);
  }
  lotteryMatrix.value = matrix;
}
function btnSettingClk() {
  lotterySetting.value.open = true;
}
function onSettingDismiss(event: any) {
  // console.log(event);
  lotterySetting.value.open = false;
  if (event.detail.role === "cancel") {
    return;
  }
  buildLotteryMatrix(event.detail.data);
}

function refreshScoreHistoryList(userId: number | undefined, pageNum: number) {
  let filter = undefined;
  if (userId) {
    filter = { user_id: userId };
  }
  getList("t_score_history", filter, pageNum, PAGE_SIZE)
    .then((data) => {
      scoreHistoryList.value = data;
      // console.log(scoreHistoryList.value);
    })
    .catch((err) => {
      EventBus.$emit(C_EVENT.TOAST, JSON.stringify(err));
    });
}
function refreshCateList() {
  getList("t_gift_category")
    .then((data) => {
      const d = data.data;
      // console.log(d);
      lotteryCatList.value = [...d];
      lotteryCatList.value.unshift({ id: 0, name: "全部", cost: 100 });
      if (selectedCate.value.id == 0) {
        selectedCate.value = lotteryCatList.value[0];
      }
    })
    .catch((err) => {
      EventBus.$emit(C_EVENT.TOAST, JSON.stringify(err));
    });
}
function refreshUserList() {
  getUserList()
    .then((uList) => {
      userList.value = [...uList.data];
      userList.value.unshift({ id: 0, name: "全部", score: 0 });
      if (selectedUser.value.id == 0) {
        selectedUser.value = userList.value[0];
      }
    })
    .catch((err) => {
      EventBus.$emit(C_EVENT.TOAST, JSON.stringify(err));
    });
}

function getCateName(cateId: number) {
  const cate = _.find(lotteryCatList.value, { id: cateId });
  return cate ? cate.name : "";
}
async function handleSegmentChange(event: any) {
  // console.log("segment change", event);
  if (event.detail.value === "shop") {
    refreshGiftList(selectedCate.value.id);
  }
}
// 抽奖页签
function btnLotteryClk() {}
// 积分兑换页签
function refreshGiftList(cateId?: number | undefined, pageNum?: number) {
  let filter = undefined;
  if (cateId) {
    filter = { cate_id: cateId };
  }
  getList("t_gift", filter, pageNum, PAGE_SIZE)
    .then((data) => {
      const d = data.data;
      // console.log(data);
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
function handleShopCateChange(event: any) {
  selectedCate.value = event.detail.value;
  refreshGiftList(selectedCate.value.id);
}
function handleUserChange(event: any) {
  selectedUser.value = event.detail.value;
  refreshScoreHistoryList(selectedUser.value.id, 1);
}
function formatDate(dateStr: string) {
  if (!dateStr) return dateStr;
  return dayjs(dateStr).format("YYYY-MM-DD HH:mm:ss");
}
async function btnExchangeClk(item: any) {
  console.log(item);
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
<style scoped>
.highlight {
  background-color: #ffeb3b; /* 亮起时的背景色 */
  transition: background-color 0.3s ease;
}

.radio-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding: 8px;
}

.radio-grid ion-radio {
  margin: 0;
  --padding-start: 0;
}

/* ion-content {
  --padding-bottom: 56px;
} */
</style>
