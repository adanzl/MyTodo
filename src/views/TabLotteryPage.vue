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
    <ion-content>
      <ion-refresher slot="fixed" @ionRefresh="handleRefresh($event)">
        <ion-refresher-content></ion-refresher-content>
      </ion-refresher>
      <ion-segment value="lotterySpecial" @ionChange="handleSegmentChange">
        <ion-segment-button value="lotterySpecial" content-id="lotterySpecial" layout="icon-start">
          <ion-label>抽取奖励</ion-label>
          <ion-icon :icon="heartOutline"></ion-icon>
        </ion-segment-button>
        <ion-segment-button value="shop" content-id="shop" layout="icon-start">
          <ion-icon :icon="giftOutline"></ion-icon>
          <ion-label>积分兑换</ion-label>
        </ion-segment-button>
      </ion-segment>
      <ion-segment-view>
        <!-- 抽奖页签 -->
        <ion-segment-content id="lotterySpecial" class="flex flex-col h-full">
          <ion-item>
            <div class="flex items-center justify-center">
              <span>当前积分：</span>
              <MdiStar class="text-red-500" />
              <div class="text-left pl-1 font-bold w-12">{{ globalVar.user.score }}</div>
            </div>
          </ion-item>
          <ion-radio-group :value="selectedCate" class="radio-grid" @ionChange="handleShopCateChange">
            <ion-radio
              v-for="item in lotteryCatList"
              :key="item.id"
              :value="item"
              label-placement="end"
              justify="start">
              {{ item.name }}
            </ion-radio>
          </ion-radio-group>
          <div class="flex items-center justify-center flex-1">
            <ion-button @click="btnLotteryClk" size="default">
              <div class="w-20 h-20 flex flex-col items-center justify-center">
                <span>立即抽奖</span>
                <div class="flex items-center justify-center">
                  <MdiStar class="text-red-500" />{{ selectedCate.cost }}
                </div>
              </div>
            </ion-button>
          </div>
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
          <ion-list>
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
          </ion-list>
        </ion-segment-content>
      </ion-segment-view>
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
  IonRadio,
  IonRadioGroup,
  IonSelect,
  IonSelectOption,
  IonRefresher,
  IonRefresherContent,
  IonSegment,
  IonSegmentButton,
  IonSegmentContent,
  IonSegmentView,
  IonThumbnail,
  alertController,
} from "@ionic/vue";
import { giftOutline, heartOutline } from "ionicons/icons";
import _ from "lodash";
import { inject, onBeforeUnmount, onMounted, ref } from "vue";
import MdiStar from "~icons/mdi/star";
import WeuiSettingOutlined from "~icons/weui/setting-outlined";

const lotteryData = ref<LotteryData[] | []>([]);
const COL_SIZE = 3; // 列数
const ROW_SIZE_MIN = 4; // 行数最小值
const lotteryMatrix = ref<LotteryData[][]>([]);
const toastData = ref({
  isOpen: false,
  duration: 3000,
  text: "",
});
const lotterySetting = ref({ open: false });
const animation = ref(-1);
const globalVar: any = inject("globalVar");
// const winner = ref({ bWin: false, prize: "" });

const giftList = ref<any>({
  data: [],
  pageNum: 1,
  pageSize: 10,
  totalCount: 0,
  totalPage: 0,
});
const lotteryCatList = ref<any>([]);
const selectedCate = ref<any>({ id: 0, name: "全部", cost: 100 });

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
      toastData.value.isOpen = true;
      toastData.value.text = JSON.stringify(err);
    });
}

function getCateName(cateId: number) {
  const cate = _.find(lotteryCatList.value, { id: cateId });
  return cate ? cate.name : "";
}
async function handleSegmentChange(event: any) {
  console.log("segment change", event);
  if (event.detail.value === "shop") {
    refreshGiftList(selectedCate.value.id);
  }
}
// 抽奖页签
function btnLotteryClk() {}
// 积分兑换页签
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
function handleShopCateChange(event: any) {
  selectedCate.value = event.detail.value;
  refreshGiftList(selectedCate.value.id);
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
</style>
