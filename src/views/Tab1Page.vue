<template>
  <ion-page>
    <ion-header>
      <ion-toolbar>
        <ion-buttons slot="start" class="ion-padding">
          <ion-icon :icon="list"></ion-icon>
        </ion-buttons>
        <ion-title>
          <span v-if="selectedDate">{{
            selectedDate.dt.format("YY年MM月")
          }}</span>
        </ion-title>
        <ion-buttons slot="end" class="ion-padding">
          <ion-icon :icon="swapVertical"></ion-icon>
        </ion-buttons>
      </ion-toolbar>
    </ion-header>
    <ion-content :fullscreen="true">
      <!-- https://blog.csdn.net/weixin_41863239/article/details/82490886 -->
      <swiper
        @slideNextTransitionEnd="onSlideChangeNext"
        @slidePrevTransitionEnd="onSlideChangePre"
        @slidesUpdated="onSlideUpdate"
        @swiper="setSwiperInstance"
        :centered-slides="true"
        :autoHeight="true"
        :modules="[IonicSlides, Keyboard]"
        :keyboard="true"
      >
        <swiper-slide>
          <!-- <swiper-slide v-for="(slide, idx) in slideArr" :key="idx"> -->
          <CalenderTab
            :slide="slideArr[0]"
            :daySelectCallback="daySelect"
            :selectedDate="selectedDate"
          ></CalenderTab>
        </swiper-slide>
        <swiper-slide>
          <CalenderTab
            :slide="slideArr[1]"
            :daySelectCallback="daySelect"
            :selectedDate="selectedDate"
          ></CalenderTab>
        </swiper-slide>
        <swiper-slide>
          <CalenderTab
            :slide="slideArr[2]"
            :daySelectCallback="daySelect"
            :selectedDate="selectedDate"
          ></CalenderTab>
        </swiper-slide>
      </swiper>
      <ion-button
        color="light"
        expand="full"
        fill="clear"
        size="small"
        @click="calendarFold()"
      >
        <ion-icon
          :icon="bFold ? chevronDown : chevronUp"
          size="medium"
          color="primary"
        >
        </ion-icon>
      </ion-button>
      <ion-content color="light">
        <ion-refresher slot="fixed" @ionRefresh="handleRefresh($event)">
          <ion-refresher-content></ion-refresher-content>
        </ion-refresher>
        <ion-list :inset="true" lines="full" mode="ios">
          <ion-item>
            <ion-label>
              Multi-line text that should wrap when it is too long to fit on one
              line.
            </ion-label>
          </ion-item>

          <ion-item>
            <ion-label class="ion-text-nowrap">
              Multi-line text that should ellipsis when it is too long to fit on
              one line.
            </ion-label>
          </ion-item>

          <ion-item>
            <ion-label>
              <h1>H1 Heading</h1>
              <p>Paragraph</p>
            </ion-label>
          </ion-item>
        </ion-list>
      </ion-content>
      <ion-modal
        id="pop-modal"
        ref="modal"
        trigger="open-dialog"
        class="ion-padding"
      >
        <div class="wrapper ion-padding">
          <h1>Dialog header</h1>
          <ion-list lines="none">
            <ion-item :button="true" :detail="false" aria-label="button">
              <ion-label>Item 1</ion-label>
            </ion-item>
            <ion-item :button="true" :detail="false" aria-label="button">
              <ion-label>Item 2</ion-label>
            </ion-item>
            <ion-item :button="true" :detail="false" aria-label="button">
              <ion-label>Item 3</ion-label>
            </ion-item>
          </ion-list>
        </div>
      </ion-modal>
    </ion-content>
    <ion-fab slot="fixed" vertical="bottom" horizontal="end">
      <ion-fab-button id="open-dialog">
        <ion-icon :icon="addCircleOutline" size="large"></ion-icon>
      </ion-fab-button>
    </ion-fab>
  </ion-page>
</template>

<script setup lang="ts">
import {
  IonFab,
  IonFabButton,
  IonicSlides,
  IonRefresher,
  IonRefresherContent,
  IonModal,
} from "@ionic/vue";
import dayjs from "dayjs";
import {
  addCircleOutline,
  chevronUp,
  chevronDown,
  list,
  swapVertical,
} from "ionicons/icons";
import { Keyboard } from "swiper/modules";
import { Swiper, SwiperSlide } from "swiper/vue";
import CalenderTab from "@/components/CalendarTab.vue";
import { ref } from "vue";
import axios from "axios";

import "@ionic/vue/css/ionic-swiper.css";
import "swiper/css";
import "swiper/css/effect-fade";
const slideArr = ref<any[]>([{}, {}, {}]); // 滑动数据
const swiperRef = ref(); // 滑动对象
const bFold = ref(false); // 日历折叠状态
const selectedDate: any = ref(null); // 选中日期

let currentDate = dayjs().startOf("day");
const createSlideData = (datetime: dayjs.Dayjs) => {
  // console.log("createSlideData", datetime.format("YYYY-MM-DD"));
  const firstDayOfMonth = datetime.startOf("month");
  let _dt = firstDayOfMonth.startOf("week");
  const wArr = [];
  do {
    const week = [];
    for (let i = 0; i < 7; i++) {
      const dd = {
        dt: _dt,
        events: [1],
      };
      week.push(dd);
      _dt = _dt.add(1, "days");
    }
    wArr.push(week);
  } while (_dt.month() == datetime.month());
  return {
    vid: datetime.year(),
    month: datetime.month(),
    year: datetime.year(),
    weekArr: wArr,
  };
};

const daySelect = (slide: any, day: any) => {
  if (slide.month != day.dt.month()) {
    if (slide.year * 100 + slide.month < day.dt.year() * 100 + day.dt.month()) {
      swiperRef.value.slideNext();
    } else {
      swiperRef.value.slidePrev();
    }
  }
  console.log("daySelect", day);
  selectedDate.value = day;
};
const chooseSelectedDate = () => {
  // 处理选中日期
  const mm = slideArr.value[1];
  const now = dayjs().startOf("day");
  if (!selectedDate.value) {
    outer: for (const week of mm.weekArr) {
      for (const _dt of week) {
        if (_dt.dt.unix() == now.unix()) {
          selectedDate.value = _dt;
          break outer;
        }
      }
    }
  }
  if (!selectedDate.value) {
    outer: for (const week of mm.weekArr) {
      for (const _dt of week) {
        if (_dt.dt.unix() == currentDate.unix()) {
          selectedDate.value = _dt;
          break outer;
        }
      }
    }
  }
  if (selectedDate.value) {
    console.log("ST ", selectedDate.value.dt.format("YYYY-MM-DD"));
  }
};

const onSlideChangeNext = (obj: any) => {
  console.log("onSlideChangeNext", currentDate.format("YYYY-MM-DD"));
  currentDate = currentDate.add(1, "months").startOf("month");
  slideArr.value = [
    createSlideData(currentDate.subtract(1, "months")),
    createSlideData(currentDate),
    createSlideData(currentDate.add(1, "months")),
  ];
  obj.slideTo(1, 0, false);
  obj.update();
  if (
    selectedDate.value &&
    selectedDate.value.dt.month() !== currentDate.month()
  ) {
    selectedDate.value = null; // 清空选中日期
  }
  chooseSelectedDate();
};
const onSlideChangePre = (obj: any) => {
  console.log("onSlideChangePre", currentDate.format("YYYY-MM-DD"));
  currentDate = currentDate.subtract(1, "months").startOf("month");

  slideArr.value = [
    createSlideData(currentDate.subtract(1, "months")),
    createSlideData(currentDate),
    createSlideData(currentDate.add(1, "months")),
  ];
  obj.slideTo(1, 0, false);
  obj.update();
  if (
    selectedDate.value &&
    selectedDate.value.dt.month() !== currentDate.month()
  ) {
    selectedDate.value = null; // 清空选中日期
  }
  chooseSelectedDate();
};

const onSlideUpdate = () => {};

const setSwiperInstance = (swiper: any) => {
  swiperRef.value = swiper;
  swiper.slideTo(1, 0, false);
  chooseSelectedDate();
};

const handleRefresh = (event: any) => {
  console.log("handleRefresh", event);
  axios
    .get("https://3ft23fh89533.vicp.fun/api/getSave", { params: { id: 1 } })
    .then((res) => {
      console.log("handleRefresh", res);
      event.target.complete();
    })
    .catch((err) => {
      console.log("handleRefresh", err);
      event.target.complete();
    });
};

// 初始化数据
slideArr.value = [
  createSlideData(currentDate.subtract(1, "months")),
  createSlideData(currentDate),
  createSlideData(currentDate.add(1, "months")),
];

// 日历折叠
const calendarFold = () => {
  console.log("calendarFold ", bFold.value);
  bFold.value = !bFold.value;
};
</script>
<style>
.vertical {
  display: flex;
  flex-direction: column;
}
.dot {
  display: inline-block;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background-color: #007bff;
  margin-top: 5px;
}
.transparent {
  --background: transparent !important;
}
ion-chip.selected {
  --color: #fff !important;
  --background: #ff3609 !important;
}
.gray {
  --color: #b5b1b1 !important;
}
ion-modal#pop-modal {
  --width: 100%;
  --min-width: fit-content;
  --height: fit-content;
  --border-radius: 6px;
  --box-shadow: 0 28px 48px rgba(0, 0, 0, 0.4);
}
</style>
