<template>
  <ion-page>
    <ion-header>
      <ion-toolbar>
        <ion-title>日历视图</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-row style="background-color: antiquewhite; color: blue">
      <ion-col class="ion-text-center" v-for="head in weekHead" :key="head">
        {{ head }}
      </ion-col>
    </ion-row>
    <ion-content>
      <swiper
        @slideNextTransitionEnd="onSlideChangeNext"
        @slidePrevTransitionEnd="onSlideChangePre"
        @swiper="setSwiperInstance"
        :centered-slides="true"
        :autoHeight="true"
        :modules="[IonicSlides, Keyboard]"
        :keyboard="true">
        <swiper-slide v-for="(slide, idx) in slideArr" :key="idx">
          <!-- <CalenderTab
            :slide="slide"
            :daySelectCallback="onDaySelected"
            :selectedDate="selectedDate"
            :minimal="bFold"
            :swiperRef="swiperRef">
          </CalenderTab> -->
          <ion-grid style="height: auto" fixed>
            <ion-row v-for="week in slide.weekArr" :key="week">
              <ion-col
                class="day-item"
                @click="onDaySelected(slide, day)"
                v-for="day in week"
                :key="day">
                <span>
                  <ion-chip
                    :class="{
                      transparent: day.dt.unix() !== dayjs().startOf('day').unix(),
                      today: day.dt.unix() === dayjs().startOf('day').unix(),
                      gray: day.dt.month() !== slide.month,
                    }">
                    {{ day.dt.date() }}
                  </ion-chip>
                </span>
                <div
                  v-for="(event, idx) of day.events"
                  :key="idx"
                  :class="{
                    'text-line-through': day.save[event.id]?.state === 1,
                    'gray': day.save[event.id]?.state === 1,
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
  </ion-page>
</template>
<script setup lang="ts">
import { DayData, MonthData, UData, UserData } from "@/modal/UserData";
import { getSave } from "@/utils/NetUtil";
import { IonCol, IonGrid, IonRow, IonicSlides } from "@ionic/vue";
import "@ionic/vue/css/ionic-swiper.css";
import dayjs from "dayjs";
import "swiper/css";
import "swiper/css/effect-fade";
import { Keyboard } from "swiper/modules";
import { Swiper, SwiperSlide } from "swiper/vue";
import { onMounted, ref } from "vue";
const weekHead = ["日", "一", "二", "三", "四", "五", "六"];
const toastData = ref({
  isOpen: false,
  duration: 3000,
  text: "",
});
const slideArr = ref<any[]>([{}, {}, {}]); // 滑动数据
const userData = ref<UserData>(new UserData());
const swiperRef = ref(); // 滑动对象
const selectedDate = ref<DayData>(); // 选中日期
let currentDate = dayjs().startOf("day"); // 当前日期
onMounted(() => {
  // 获取数据
  getSave(1)
    .then((res: any) => {
      userData.value = UData.parseUserData(res);
      console.log("getSave", userData.value);
      updateScheduleData();
      setTimeout(() => {
        swiperRef?.value?.update();
      }, 100);
    })
    .catch((err) => {
      console.log("getSave", err);
      toastData.value.isOpen = true;
      toastData.value.text = JSON.stringify(err);
    });
});
// 初始化数据
const updateScheduleData = () => {
  slideArr.value = [
    UData.createMonthData(currentDate.subtract(1, "months"), userData.value, selectedDate),
    UData.createMonthData(currentDate, userData.value, selectedDate),
    UData.createMonthData(currentDate.add(1, "months"), userData.value, selectedDate),
  ];
};
const slideChange = (obj: any) => {
  slideArr.value = [
    UData.createMonthData(currentDate.subtract(1, "months"), userData.value),
    UData.createMonthData(currentDate, userData.value),
    UData.createMonthData(currentDate.add(1, "months"), userData.value),
  ];
  obj.slideTo(1, 0, false);
  obj.update();
  if (selectedDate.value && selectedDate.value.dt.month() !== currentDate.month()) {
    selectedDate.value = undefined; // 清空选中日期
  }
};
// 向右滑
const onSlideChangeNext = (obj: any) => {
  currentDate = currentDate.add(1, "months").startOf("month");
  slideChange(obj);
};
// 向左滑
const onSlideChangePre = (obj: any) => {
  currentDate = currentDate.subtract(1, "months").startOf("month");
  slideChange(obj);
};
// 获取swiper对象
const setSwiperInstance = (swiper: any) => {
  swiperRef.value = swiper;
  swiper.slideTo(1, 0, false);
};
const onDaySelected = (slide: MonthData, day: DayData) => {
  selectedDate.value = day;
};
</script>
<style lang="css" scoped>
.day-item {
  min-height: 120px;
  width: 13vw;
  border: 1px solid #f1eded;
  padding: 0;
}
.day-item span {
  display: block;
  font-size: 14px;
  text-align: left;
  background-color: #f1eded;
}
.day-item div {
  font-size: 12px;
  text-align: left;
  height: auto;
  align-items: top;
  white-space: nowrap; /* 防止文本换行 */
  overflow: hidden; /* 隐藏溢出的文本 */
  text-overflow: space; /* 显示省略号 */
  padding: 1px 1px 1px 1px;
  margin-top: 1px;
  background-color: #e9bcbcb6;
}
.day-item ion-chip {
  padding: 1px 3px 1px 3px;
  height: auto;
  min-height: auto;
}
</style>
