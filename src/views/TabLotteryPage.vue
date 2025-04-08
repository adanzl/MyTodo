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
      <ion-card class="ion-padding">
        <ion-card-header>
          <ion-card-title>抽奖</ion-card-title>
        </ion-card-header>
        <ion-card-content>
          <ion-grid>
            <ion-row v-for="(row, rowIdx) in lotteryMatrix" :key="rowIdx">
              <ion-col v-for="(col, colIdx) in row" :key="colIdx" class="text-center">
                <div
                  :class="{
                    highlight: col.highlight,
                  }"
                  class="text-lg">
                  {{ col.name }}
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
      </ion-card>
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
import { getLotteryData } from "@/utils/NetUtil";
import {
  IonRefresher,
  IonRefresherContent,
  IonCard,
  IonCardContent,
  IonCardHeader,
  IonCardTitle,
  IonGrid,
  IonCol,
  IonRow,
} from "@ionic/vue";
import { onBeforeUnmount, onMounted, ref } from "vue";
import WeuiSettingOutlined from "~icons/weui/setting-outlined";
import _ from "lodash";

const lotteryData = ref<[{ icon: ""; name: ""; weight: 1; highlight: false }] | []>([]);
const COL_SIZE = 3; // 列数
const ROW_SIZE_MIN = 6; // 行数最小值
const LIGHT_RATE = 0.5; // 高亮比例
const ANIMATION_TIME = 1000; // 动画时间
const lotteryMatrix = ref<any[]>([]);
const toastData = ref({
  isOpen: false,
  duration: 3000,
  text: "",
});
const lotterySetting = ref({ open: false });
const animation = ref(-1);
const winner = ref({ bWin: false, prize: "" });
onMounted(() => {
  // 获取数据
  getLotteryData()
    .then((data: any) => {
      // console.log(data);
      buildLotteryMatrix(JSON.parse(data));
    })
    .catch((err) => {
      console.error(err);
      toastData.value.isOpen = true;
      toastData.value.text = JSON.stringify(err);
    });
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

function buildLotteryMatrix(data: any) {
  lotteryData.value = data;
  const matrix: any = [];
  const length = Math.max(ROW_SIZE_MIN, Math.ceil(data.length / COL_SIZE));
  let ii = 0;
  for (let i = 0; i < length; i++) {
    const row: any[] = [];
    for (let j = 0; j < COL_SIZE; j++) {
      row.push(_.clone(data[ii++ % data.length]));
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
</script>
<style scoped>
.highlight {
  background-color: #ffeb3b; /* 亮起时的背景色 */
  transition: background-color 0.3s ease;
}
</style>
