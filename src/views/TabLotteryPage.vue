<template>
  <ion-page id="main-content">
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
    <ion-content>
      <ion-refresher slot="fixed" @ionRefresh="handleRefresh($event)">
        <ion-refresher-content></ion-refresher-content>
      </ion-refresher>
      <ion-segment value="shop" @ionChange="handleSegmentChange">
        <ion-segment-button value="lottery" content-id="lottery" layout="icon-start">
          <ion-icon :icon="squareOutline"></ion-icon>
          <ion-label>混合抽取</ion-label>
        </ion-segment-button>
        <ion-segment-button value="lotterySpecial" content-id="lotterySpecial" layout="icon-start">
          <ion-label>定向抽取</ion-label>
          <ion-icon :icon="heartOutline"></ion-icon>
        </ion-segment-button>
        <ion-segment-button value="shop" content-id="shop" layout="icon-start">
          <ion-icon :icon="giftOutline"></ion-icon>
          <ion-label>积分兑换</ion-label>
        </ion-segment-button>
      </ion-segment>
      <ion-segment-view>
        <ion-segment-content id="lottery">First</ion-segment-content>
        <ion-segment-content id="lotterySpecial">Second</ion-segment-content>
        <ion-segment-content id="shop">
          <ion-item>
            <ion-select label="类别" placeholder="选择类别" v-model="selectedCate.id">
              <ion-select-option :value="cate.id" v-for="cate in lotteryCatList" :key="cate.id">
                {{ cate.name }}
              </ion-select-option>
            </ion-select>
            <div class="flex w-1/3 items-center justify-center">
              <MdiStar class="text-red-500" />
              <div class="text-left pl-1 font-bold w-8">100</div>
            </div>
          </ion-item>
          <ion-list>
            <ion-item v-for="item in giftList.data" :key="item.id">
              <ion-thumbnail slot="start">
                <img :src="item.img" />
              </ion-thumbnail>
              <div class="w-full">
                <ion-label>
                  <h2>{{ item.name }}</h2>
                </ion-label>
                <div class="flex items-center">
                  <MdiStar class="text-red-500" />
                  <div class="text-left pl-1 font-bold w-8">{{ item.cost }}</div>
                </div>
              </div>
              <ion-button @click="btnExchangeClk(item)">兑</ion-button>
            </ion-item>
          </ion-list>
        </ion-segment-content>
      </ion-segment-view>
      <!-- <ion-card class="ion-padding">
        <ion-card-header>
          <ion-card-title>抽奖</ion-card-title>
        </ion-card-header>
        <ion-card-content>
          <ion-grid>
            <ion-row v-for="(row, rowIdx) in lotteryMatrix" :key="rowIdx">
              <ion-col v-for="(item, colIdx) in row" :key="colIdx" class="text-center">
                <div
                  :class="{
                    highlight: item.highlight,
                  }"
                  class="text-lg">
                  <img :src="item.img || avatar" class="max-w-16 max-h-16 m-auto" />
                  {{ item.name }}
                </div>
              </ion-col>
            </ion-row>
          </ion-grid>
        </ion-card-content>
        <ion-card-content>
          <ion-button expand="full" @click="btnStartClk" :disabled="animation > 0">
            开始抽奖
          </ion-button>
        </ion-card-content>

        <ion-card-content>
          <p v-if="winner.bWin">恭喜你，抽中了：{{ winner.prize }}</p>
          <p v-else>快来抽奖吧</p>
        </ion-card-content>
      </ion-card> -->
    </ion-content>
    <ion-toast
      :is-open="toastData.isOpen"
      :message="toastData.text"
      :duration="toastData.duration"
      @didDismiss="
        () => {
          toastData.isOpen = false;
        }
      ">
    </ion-toast>
    <LotterySetting :is-open="lotterySetting.open" @willDismiss="onSettingDismiss" />
  </ion-page>
</template>

<script setup lang="ts">
import { LotteryData } from "@/modal/UserData";
import { getImage } from "@/utils/ImgMgr";
import { getList, getLotteryData } from "@/utils/NetUtil";
import {
  IonSelect,
  IonSelectOption,
  IonRefresher,
  IonRefresherContent,
  IonSegment,
  IonSegmentButton,
  IonSegmentContent,
  IonSegmentView,
  IonThumbnail,
} from "@ionic/vue";
import { giftOutline, heartOutline, squareOutline } from "ionicons/icons";
import _ from "lodash";
import { onBeforeUnmount, onMounted, ref } from "vue";
import MdiStar from "~icons/mdi/star";
import WeuiSettingOutlined from "~icons/weui/setting-outlined";

const lotteryData = ref<LotteryData[] | []>([]);
const COL_SIZE = 3; // 列数
const ROW_SIZE_MIN = 4; // 行数最小值
const LIGHT_RATE = 0.5; // 高亮比例
const ANIMATION_TIME = 1000; // 动画时间
const lotteryMatrix = ref<LotteryData[][]>([]);
const toastData = ref({
  isOpen: false,
  duration: 3000,
  text: "",
});
const lotterySetting = ref({ open: false });
const animation = ref(-1);
const winner = ref({ bWin: false, prize: "" });

const giftList = ref<any>({
  data: [],
  pageNum: 1,
  pageSize: 10,
  totalCount: 0,
  totalPage: 0,
});
const lotteryCatList = ref<any>([]);
const selectedCate = ref<any>({ id: 0, name: "全部" });

onMounted(() => {
  // 获取数据
  refreshGiftList();
  refreshCateList();
});
onBeforeUnmount(() => {
  clearTimeout(animation.value);
});
function handleRefresh(event: any) {
  getLotteryData()
    .then((data: any) => {
      buildLotteryMatrix(JSON.parse(data));
    })
    .catch((err) => {
      toastData.value.isOpen = true;
      toastData.value.text = JSON.stringify(err);
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

function btnStartClk() {
  if (animation.value > 0) {
    console.log("animation is running");
    return;
  }
  const buildHighlight = () => {
    const total = lotteryMatrix.value.length * COL_SIZE;
    const cnt = Math.floor(total * LIGHT_RATE);
    const ids: any[] = [];
    for (let i = 0; i < cnt; i++) {
      const idx = Math.floor(Math.random() * total);
      const r = Math.floor(idx / COL_SIZE);
      const c = idx % COL_SIZE;
      lotteryMatrix.value[r][c].highlight = true;
      ids.push(idx);
    }
    animation.value = setTimeout(() => {
      for (const ii of ids) {
        const r = Math.floor(ii / COL_SIZE);
        const c = ii % COL_SIZE;
        lotteryMatrix.value[r][c].highlight = false;
      }
      buildHighlight();
    }, 150);
  };
  buildHighlight();
  setTimeout(() => {
    clearTimeout(animation.value);
    animation.value = -1;
    for (let i = 0; i < lotteryMatrix.value.length; i++) {
      for (let j = 0; j < lotteryMatrix.value[i].length; j++) {
        lotteryMatrix.value[i][j].highlight = false;
      }
    }
    winner.value.bWin = true;
    winner.value.prize =
      lotteryData.value[Math.floor(Math.random() * lotteryData.value.length)].name;
  }, ANIMATION_TIME);
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
function refreshGiftList(cateId?: number | undefined) {
  let filter = undefined;
  if (cateId) {
    filter = { cate_id: cateId };
  }
  getList("t_gift", filter)
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
      toastData.value.isOpen = true;
      toastData.value.text = JSON.stringify(err);
    });
}
function refreshCateList() {
  getList("t_gift_category")
    .then((data) => {
      const d = data.data;
      // console.log(d);
      lotteryCatList.value = [...d];
      lotteryCatList.value.unshift({ id: 0, name: "全部" });
      if (selectedCate.value == null) {
        selectedCate.value = lotteryCatList.value[0];
      }
    })
    .catch((err) => {
      toastData.value.isOpen = true;
      toastData.value.text = JSON.stringify(err);
    });
}
async function handleSegmentChange(event: any) {
  console.log("segment change", event);
  if (event.detail.value === "shop") {
    refreshGiftList(undefined);
  }
}
function btnExchangeClk(item: any) {
  console.log(item);
}
</script>
<style scoped>
.highlight {
  background-color: #ffeb3b; /* 亮起时的背景色 */
  transition: background-color 0.3s ease;
}
</style>
