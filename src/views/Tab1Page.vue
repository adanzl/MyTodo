<template>
  <ion-page>
    <ion-header>
      <ion-toolbar>
        <ion-buttons slot="start" class="ion-padding">
          <ion-icon :icon="list"></ion-icon>
        </ion-buttons>
        <ion-title class="ion-text-center">
          <span v-if="selectedDate">{{
            selectedDate.dt.format("YY年MM月")
          }}</span>
        </ion-title>
        <ion-buttons slot="end" class="ion-padding">
          <ion-icon :icon="swapVertical" @click="btnSortClk"></ion-icon>
        </ion-buttons>
      </ion-toolbar>
    </ion-header>
    <ion-content :fullscreen="true">
      <!-- https://blog.csdn.net/weixin_41863239/article/details/82490886 -->
      <swiper
        @slideNextTransitionEnd="onSlideChangeNext"
        @slidePrevTransitionEnd="onSlideChangePre"
        @swiper="setSwiperInstance"
        :centered-slides="true"
        :autoHeight="true"
        :modules="[IonicSlides, Keyboard]"
        :keyboard="true"
      >
        <swiper-slide v-for="(slide, idx) in slideArr" :key="idx">
          <CalenderTab
            :slide="slide"
            :daySelectCallback="btnDaySelectClk"
            :selectedDate="selectedDate"
            :minimal="bFold"
            :swiperRef="swiperRef"
          >
          </CalenderTab>
        </swiper-slide>
      </swiper>
      <ion-button
        color="light"
        expand="full"
        fill="clear"
        size="small"
        @click="btnCalendarFoldClk()"
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
        aria-hidden="true"
        @ionModalWillDismiss="onAddModalDismiss"
      >
        <AddSchedulePop :modal="modal"></AddSchedulePop>
      </ion-modal>
      <ion-toast
        :is-open="toastData.isOpen"
        :message="toastData.text"
        :duration="toastData.duration"
        @didDismiss="
          () => {
            toastData.isOpen = false;
          }
        "
      ></ion-toast>
    </ion-content>
    <ion-fab slot="fixed" vertical="bottom" horizontal="end">
      <ion-fab-button id="open-dialog">
        <ion-icon :icon="addCircleOutline" size="large"></ion-icon>
      </ion-fab-button>
    </ion-fab>
    <ion-fab slot="fixed" vertical="bottom" horizontal="start">
      <ion-fab-button>
        <ion-button @click="btnTestClk">xx</ion-button>
      </ion-fab-button>
    </ion-fab>
  </ion-page>
</template>

<script setup lang="ts">
import AddSchedulePop from "@/components/AddSchedulePopModal.vue";
import CalenderTab from "@/components/CalendarTab.vue";
import { LocalNotifications } from "@capacitor/local-notifications";

import {
  IonFab,
  IonFabButton,
  IonicSlides,
  IonModal,
  IonRefresher,
  IonRefresherContent,
} from "@ionic/vue";
import axios from "axios";
import dayjs from "dayjs";
import {
  addCircleOutline,
  chevronDown,
  chevronUp,
  list,
  swapVertical,
} from "ionicons/icons";
import { Keyboard } from "swiper/modules";
import { Swiper, SwiperSlide } from "swiper/vue";
import { ref } from "vue";

import "@ionic/vue/css/ionic-swiper.css";
import "swiper/css";
import "swiper/css/effect-fade";
import { UserData } from "@/type/UserData.vue";
const userData = ref<UserData>({ id: 0, name: "leo", schedules: [] });
const slideArr = ref<any[]>([{}, {}, {}]); // 滑动数据
const swiperRef = ref(); // 滑动对象
const bFold = ref(false); // 日历折叠状态
const selectedDate: any = ref(null); // 选中日期
const modal = ref(); // 弹窗对象
const toastData = ref({
  isOpen: false,
  duration: 3000,
  text: "",
});

let currentDate = dayjs().startOf("day");
const createSlideData = (datetime: dayjs.Dayjs) => {
  // console.log("createSlideData", datetime.format("YYYY-MM-DD"));
  const firstDayOfMonth = datetime.startOf("month");
  let _dt = firstDayOfMonth.startOf("week");
  const wArr = [];
  do {
    const week = [];
    for (let i = 0; i < 7; i++) {
      const dayData = {
        dt: _dt,
        events: [1],
      };
      week.push(dayData);
      _dt = _dt.add(1, "days");
    }
    wArr.push(week);
  } while (_dt.month() == datetime.month());
  return {
    vid: datetime.year(),
    month: datetime.month(),
    year: datetime.year(),
    firstDayOfMonth: firstDayOfMonth,
    weekArr: wArr,
  }; // SlideData
};
// 点击日历某个日期
const btnDaySelectClk = (slide: any, day: any) => {
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

const slideChange = (obj: any) => {
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
// 向右滑
const onSlideChangeNext = (obj: any) => {
  console.log("onSlideChangeNext", currentDate.format("YYYY-MM-DD"));
  currentDate = currentDate.add(1, "months").startOf("month");
  slideChange(obj);
};
// 向左滑
const onSlideChangePre = (obj: any) => {
  console.log("onSlideChangePre", currentDate.format("YYYY-MM-DD"));
  currentDate = currentDate.subtract(1, "months").startOf("month");
  slideChange(obj);
};
// 添加日程页面关闭回调
const onAddModalDismiss = (event: any) => {
  console.log("onAddModalDismiss", event);
  const scheduleData = event.detail.data;
  if (scheduleData && event.detail.role === "confirm") {
    // 处理数据
    userData.value.schedules.push(scheduleData);
  }
};

// 排序按钮
const btnSortClk = () => {
  swiperRef?.value?.update();
};
// 左下测试按钮
const btnTestClk = () => {
  LocalNotifications.schedule({
    notifications: [
      {
        title: "On sale",
        body: "Widgets are 10% off. Act fast!",
        id: 1,
        schedule: { at: new Date(Date.now() + 1000 * 5) },
        sound: undefined,
        attachments: undefined,
        actionTypeId: "",
        extra: null,
      },
    ],
  });
};
// 获取swiper对象
const setSwiperInstance = (swiper: any) => {
  swiperRef.value = swiper;
  swiper.slideTo(1, 0, false);
  chooseSelectedDate();
};
// 刷新页面事件
const handleRefresh = (event: any) => {
  console.log("handleRefresh", event);
  axios
    .get("https://3ft23fh89533.vicp.fun/api/getSave", { params: { id: 1 } })
    .then((res) => {
      console.log("handleRefresh", res);
      toastData.value.isOpen = true;
      toastData.value.text = JSON.stringify(res.data);
      event.target.complete();
    })
    .catch((err) => {
      console.log("handleRefresh", err);
      toastData.value.isOpen = true;
      toastData.value.text = JSON.stringify(err);
      event.target.complete();
    });
};

// 初始化数据
slideArr.value = [
  createSlideData(currentDate.subtract(1, "months")),
  createSlideData(currentDate),
  createSlideData(currentDate.add(1, "months")),
];

// 日历折叠按钮
const btnCalendarFoldClk = () => {
  bFold.value = !bFold.value;
  setTimeout(() => {
    swiperRef.value.update();
  }, 100);
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
  --height: 85%;
  --min-height: 50%;
  --border-radius: 6px;
  --box-shadow: 0 28px 48px rgba(0, 0, 0, 0.4);
}
</style>
