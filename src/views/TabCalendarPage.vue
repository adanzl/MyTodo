<template>
  <ion-page id="main-content" main>
    <ion-header>
      <ion-toolbar>
        <ion-buttons slot="start">
          <ion-menu-button></ion-menu-button>
        </ion-buttons>
        <ion-title>
          <div v-if="currentDate">{{ currentDate.format("YY年MM月") }}</div>
          <div v-else>日历</div>
        </ion-title>
        <ion-buttons slot="end">
          <ion-button
            style="position: absolute; right: 50px"
            @click="btnTodayClk"
            v-if="!isThisMonth()">
            今
          </ion-button>
        </ion-buttons>
      </ion-toolbar>
    </ion-header>
    <ion-row class="text-blue-500" style="background-color: antiquewhite">
      <ion-col class="ion-text-center font-bold text-red-600">日</ion-col>
      <ion-col class="ion-text-center font-bold">一</ion-col>
      <ion-col class="ion-text-center font-bold">二</ion-col>
      <ion-col class="ion-text-center font-bold">三</ion-col>
      <ion-col class="ion-text-center font-bold">四</ion-col>
      <ion-col class="ion-text-center font-bold">五</ion-col>
      <ion-col class="ion-text-center font-bold text-red-600">六</ion-col>
    </ion-row>
    <ion-content>
      <swiper
        @slideNextTransitionEnd="onSlideChangeNext"
        @slidePrevTransitionEnd="onSlideChangePre"
        @swiper="setSwiperInstance"
        :centered-slides="true"
        :autoHeight="true"
        :modules="[IonicSlides, Keyboard]">
        <swiper-slide v-for="(month, idx) in monthArr" :key="idx">
          <ion-grid class="w-full">
            <ion-row v-for="week in month.weekArr" :key="week" class="flex-nowrap">
              <ion-col
                class="p-[1px] min-h-32 border-[0.5px] border-gray-300 border-solid w-[14.28%] h-auto"
                @click="onDaySelected(month, day)"
                v-for="day in week"
                :key="day">
                <span class="bg-slate-200 text-left text-xs/[12px] block">
                  <ion-chip
                    :class="{
                      transparent: day.dt.unix() !== dayjs().startOf('day').unix(),
                      today: day.dt.unix() === dayjs().startOf('day').unix(),
                      gray: day.dt.month() !== month.month,
                    }"
                    class="py-[1px] px-1 min-h-0">
                    {{ day.dt.date() }}
                  </ion-chip>
                </span>
                <div
                  v-for="(event, idx) of day.events.filter(bShowScheduleItem)"
                  :key="idx"
                  :class="{
                    'text-line-through': day.save && day.save[event.id]?.state === 1,
                    gray: day.save && day.save[event.id]?.state === 1,
                  }"
                  class="text-left truncate mt-[1px] rounded-sm py-[1px] px-1"
                  :style="{
                    'background-color': getColorOptions(event.color).tag,
                    'font-size': 'clamp(9px, 2.7vw, 16px)',
                  }">
                  {{ event.title }}
                </div>
              </ion-col>
            </ion-row>
          </ion-grid>
        </swiper-slide>
      </swiper>
    </ion-content>
    <ion-toast
      :is-open="toastData.isOpen"
      :message="toastData.text"
      :duration="toastData.duration"
      @didDismiss="() => (toastData.isOpen = false)">
    </ion-toast>
    <CalendarCover
      ref="scheduleModal"
      :is-open="isScheduleModalOpen"
      :dt="selectedDate?.dt"
      :userData="userData"
      @update:data="onDataUpdate"
      @willDismiss="onScheduleModalDismiss">
    </CalendarCover>
  </ion-page>
</template>
<script setup lang="ts">
import CalendarCover from "@/components/CalendarCover.vue";
import { getColorOptions } from "@/modal/ColorType";
import { DayData, MonthData, ScheduleData, UData, UserData } from "@/modal/UserData";
import { LiveUpdateMgr } from "@/utils/AppUpdate";
import { getSave } from "@/utils/NetUtil";
import {
  IonCol,
  IonGrid,
  IonicSlides,
  IonMenuButton,
  IonRow,
  loadingController,
  onIonViewDidEnter,
} from "@ionic/vue";
import "@ionic/vue/css/ionic-swiper.css";
import dayjs from "dayjs";
import "swiper/css";
import "swiper/css/effect-fade";
import { Keyboard } from "swiper/modules";
import { Swiper, SwiperSlide } from "swiper/vue";
import { inject, onMounted, ref } from "vue";
const toastData = ref({
  isOpen: false,
  duration: 3000,
  text: "",
});
const monthArr = ref<any[]>([{}, {}, {}]); // 滑动数据
const userData = ref<UserData>(new UserData());
const swiperRef = ref(); // 滑动对象
const selectedDate = ref<DayData>(); // 选中日期
const currentDate = ref<dayjs.Dayjs>(dayjs().startOf("day")); // 当前日期(月)
const isScheduleModalOpen = ref(false);
const filter = ref<any>({});

const eventBus: any = inject("eventBus");

const refreshAllData = async () => {
  const loading = await loadingController.create({
    message: "Loading...",
  });
  loading.present();
  // 获取数据
  getSave(1)
    .then((res: any) => {
      userData.value = UData.parseUserData(res);
      // console.log("getSave", userData.value);
      updateScheduleData();
      setTimeout(() => {
        swiperRef?.value?.update();
      }, 100);
    })
    .catch((err) => {
      console.log("getSave", err);
      toastData.value.isOpen = true;
      toastData.value.text = JSON.stringify(err);
    })
    .finally(() => {
      loading.dismiss();
    });
};
onMounted(async () => {
  try {
    await LiveUpdateMgr.getDeviceId();
  } catch (err) {
    console.log("getDeviceId err");
  }

  refreshAllData();

  eventBus.$on("menuClose", (params: any) => {
    // console.log("menuClose", params);
    filter.value = params;
  });
});
onIonViewDidEnter(() => {
  refreshAllData();
});

function bShowScheduleItem(schedule: ScheduleData) {
  const [fGroup, fColor, fPriority] = [
    filter.value.group,
    filter.value.color,
    filter.value.priority,
  ];
  if (fGroup && fGroup.get(schedule.groupId) === false) return false;
  if (fColor && fColor.get(schedule.color) === false) return false;
  if (fPriority && fPriority.get(schedule.priority) === false) return false;
  return true;
}

// 初始化数据
const updateScheduleData = () => {
  // console.log("updateScheduleData", currentDate.value);
  monthArr.value = [
    UData.createMonthData(currentDate.value.subtract(1, "months"), userData.value),
    UData.createMonthData(currentDate.value, userData.value),
    UData.createMonthData(currentDate.value.add(1, "months"), userData.value),
  ];
};
const slideChange = (obj: any) => {
  updateScheduleData();
  obj.slideTo(1, 0, false);
  obj.update();
  if (selectedDate.value && selectedDate.value.dt.month() !== currentDate.value.month()) {
    selectedDate.value = undefined; // 清空选中日期
  }
};
// 向右滑
const onSlideChangeNext = (obj: any) => {
  currentDate.value = currentDate.value.add(1, "months").startOf("month");
  slideChange(obj);
};
// 向左滑
const onSlideChangePre = (obj: any) => {
  currentDate.value = currentDate.value.subtract(1, "months").startOf("month");
  slideChange(obj);
};
// 获取swiper对象
const setSwiperInstance = (swiper: any) => {
  swiperRef.value = swiper;
  swiper.slideTo(1, 0, false);
};
const onDaySelected = (slide: MonthData, day: DayData) => {
  selectedDate.value = day;
  isScheduleModalOpen.value = true;
};
//
function onScheduleModalDismiss() {
  isScheduleModalOpen.value = false;
  swiperRef?.value?.update();
}

// 今天
function btnTodayClk() {
  currentDate.value = dayjs().startOf("day");
  updateScheduleData();
}
function isThisMonth() {
  const today = dayjs().startOf("day");
  return today.month() === currentDate.value.month() && today.year() === currentDate.value.year();
}
// 数据更新
function onDataUpdate() {
  updateScheduleData();
  slideChange(swiperRef.value);
}
</script>
<style lang="css" scoped>
ion-chip.today {
  --background: rgb(255, 98, 0) !important;
}
</style>
