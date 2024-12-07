<template>
  <ion-page>
    <ion-header>
      <ion-toolbar>
        <ion-title>Tab 1</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content :fullscreen="true" color="light">
      <swiper
        ref="swiperRef"
        @slideChangeTransitionEnd="onSlideChange"
        @slidesUpdated="onSlideUpdate"
        :slidesPerView="1"
        :slidesPerGroup="1"
        :centered-slides="true"
        :modules="[EffectFade, IonicSlides, Keyboard]"
        :keyboard="true"
      >
        <swiper-slide v-for="(slide, idx) in slideArr" :key="idx">
          <ion-grid>
            <ion-row justify-content-center>
              <ion-col col-auto class="ion-text-left">
                <ion-icon :icon="list"></ion-icon>
              </ion-col>
              <ion-col col-auto class="ion-text-center">
                <div>{{ slide.year }} 年 {{ slide.month + 1 }} 月</div>
              </ion-col>
              <ion-col col-auto class="ion-text-right">
                <ion-icon :icon="swapVertical"></ion-icon>
              </ion-col>
            </ion-row>

            <ion-row>
              <ion-col
                class="calendar-header-col ion-text-center"
                v-for="head in weekHead"
                :key="head"
              >
                {{ head }}
              </ion-col>
            </ion-row>

            <ion-row
              class="calendar-row"
              v-for="week in slide.weekArr"
              :key="week"
            >
              <ion-col
                class="calendar-col ion-text-center ion-no-padding"
                @click="daySelect(slide, day)"
                v-for="day in week"
                :key="day"
              >
                <ion-chip
                  :class="{
                    vertical: true,
                    transparent:
                      selectedDate && day.dt.unix() !== selectedDate.dt.unix(),
                    selected:
                      selectedDate && day.dt.unix() === selectedDate.dt.unix(),
                    gray: day.dt.month() !== slide.month,
                  }"
                >
                  <span>
                    <strong> {{ day.dt.date() }}</strong>
                  </span>
                  <span class="dot" v-if="day.events.length > 0"></span>
                </ion-chip>
              </ion-col>
            </ion-row>
          </ion-grid>
        </swiper-slide>
      </swiper>
      <ion-button
        color="light"
        expand="full"
        fill="outline"
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
    <ion-fab slot="fixed" vertical="bottom" horizontal="end">
      <ion-fab-button>
        <ion-icon :icon="addCircleOutline" size="large"></ion-icon>
      </ion-fab-button>
    </ion-fab>
  </ion-page>
</template>

<script setup lang="ts">
import {
  IonCol,
  IonFab,
  IonFabButton,
  IonGrid,
  IonRow,
  IonicSlides,
} from "@ionic/vue";
import dayjs from "dayjs";
import {
  addCircleOutline,
  chevronUp,
  chevronDown,
  list,
  swapVertical,
} from "ionicons/icons";
import { EffectFade, Keyboard } from "swiper/modules";
import { Swiper, SwiperSlide } from "swiper/vue";
import { ref } from "vue";

import "@ionic/vue/css/ionic-swiper.css";
import "swiper/css";
import "swiper/css/effect-fade";
const slideArr = ref<any[]>([{}, {}, {}]);
const swiperRef = ref();

let currentDate = dayjs().startOf("day");
const selectedDate: any = ref(null);
const weekHead = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const createSlideData = (datetime: any) => {
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
      if (selectedDate.value == null && _dt.unix() == currentDate.unix()) {
        selectedDate.value = dd;
      }
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
  console.log("daySelect", day);
  selectedDate.value = day;
};
let curIdx = 0;
const onSlideChange = (obj: any) => {
  const currentSlideIndex = obj.activeIndex;
  const previousSlideIndex = obj.previousIndex;

  if (currentSlideIndex < previousSlideIndex) {
    curIdx -= 1;
    if (curIdx < 0) curIdx += 3;
    console.log("<-", curIdx, slideArr.value);
    currentDate = currentDate.subtract(1, "months");
    slideArr.value[(curIdx - 1 + 3) % 3] = createSlideData(
      currentDate.subtract(1, "months")
    );
  } else if (currentSlideIndex > previousSlideIndex) {
    curIdx += 1;
    console.log("->", curIdx, slideArr.value);
    currentDate = currentDate.add(1, "months");
    slideArr.value[(curIdx + 1 + 3) % 3] = createSlideData(
      currentDate.add(1, "months")
    );
  }
  console.log("Cur M:", currentDate.month());
};

const onSlideUpdate = (obj: any) => {
  obj.params.loop = true;
};

slideArr.value = [
  createSlideData(currentDate),
  createSlideData(currentDate.add(1, "months")),
  createSlideData(currentDate.subtract(1, "months")),
];
// swiperRef.value.loop = true;
console.log("M:", currentDate.month());
const bFold = ref(false);
const calendarFold = () => {
  console.log("calendarFold");
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
</style>
