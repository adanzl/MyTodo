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
    <ion-content >
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
        <ion-accordion-group :multiple="true" :value="['schedule', 'goals']">
          <ion-accordion value="schedule">
            <ion-item slot="header" color="light">
              <ion-label>{{ selectedDate?.dt.format("MM-DD") }}</ion-label>
            </ion-item>
            <div class="" slot="content">
              <ion-list
                :inset="true"
                lines="full"
                mode="ios"
                ref="curScheduleList"
              >
                <ion-item-sliding
                  v-for="(schedule, idx) in selectedDate?.events"
                  :key="idx"
                >
                  <ion-item :detail="true">
                    <ion-checkbox
                      slot="start"
                      @ionChange="onScheduleCheckboxChange($event, schedule)"
                    >
                    </ion-checkbox>
                    <ion-label
                      :class="{ 'text-line-through': schedule.state === 1 }"
                    >
                      <h2>{{ schedule.title }}</h2>
                      <p>
                        {{ selectedDate?.dt.format("ddd") }}
                        <ion-icon
                          :icon="listOutline"
                          style="position: relative; top: 3px"
                        ></ion-icon>
                        {{
                          schedule?.subTasks?.filter((t) => t.state === 1)
                            .length
                        }}/{{ schedule?.subTasks?.length }}
                      </p>
                    </ion-label>
                  </ion-item>
                  <ion-item-options side="end">
                    <ion-item-option>
                      <ion-icon :icon="alarmOutline"></ion-icon>
                    </ion-item-option>
                    <ion-item-option color="danger">
                      <ion-icon :icon="trashOutline"></ion-icon>
                    </ion-item-option>
                  </ion-item-options>
                </ion-item-sliding>
              </ion-list>
            </div>
          </ion-accordion>
          <ion-accordion value="goals">
            <ion-item slot="header" color="light">
              <ion-label>Goals</ion-label>
            </ion-item>
            <div class="ion-padding" slot="content">Content</div>
          </ion-accordion>
        </ion-accordion-group>
      </ion-content>
      <ion-modal
        id="pop-modal"
        ref="modal"
        trigger="open-dialog"
        class="ion-padding"
        aria-hidden="true"
        @ionModalWillDismiss="onAddModalDismiss"
      >
        <SchedulePop :modal="modal"></SchedulePop>
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
      >
      </ion-toast>
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
import SchedulePop from "@/components/SchedulePopModal.vue";
import CalenderTab from "@/components/CalendarTab.vue";
import { LocalNotifications } from "@capacitor/local-notifications";

import {
  IonFab,
  IonFabButton,
  IonicSlides,
  IonModal,
  IonRefresher,
  IonRefresherContent,
  IonCheckbox,
  IonAccordion,
  IonAccordionGroup,
  IonItemSliding,
  IonItemOption,
  IonItemOptions,
} from "@ionic/vue";
import dayjs from "dayjs";
import {
  addCircleOutline,
  chevronDown,
  chevronUp,
  list,
  swapVertical,
  trashOutline,
  alarmOutline,
  listOutline,
} from "ionicons/icons";
import { Keyboard } from "swiper/modules";
import { Swiper, SwiperSlide } from "swiper/vue";
import { ref, onMounted } from "vue";

import "@ionic/vue/css/ionic-swiper.css";
import "swiper/css";
import "swiper/css/effect-fade";
import { UserData, ScheduleData } from "@/type/UserData.vue";
import { getSave, setSave } from "@/components/NetUtil.vue";

export type SlideData = {
  vid: number;
  month: number;
  year: number;
  firstDayOfMonth: dayjs.Dayjs;
  weekArr: any[];
};
const userData = ref<UserData>({ id: 0, name: "leo", schedules: [] });
const slideArr = ref<any[]>([{}, {}, {}]); // 滑动数据
const curScheduleList = ref();
const swiperRef = ref(); // 滑动对象
const bFold = ref(false); // 日历折叠状态
const selectedDate = ref<DayData>(); // 选中日期
const modal = ref(); // 弹窗对象
const toastData = ref({
  isOpen: false,
  duration: 3000,
  text: "",
});
type DayData = {
  dt: dayjs.Dayjs;
  events: ScheduleData[];
};
let currentDate = dayjs().startOf("day");
const createSlideData = (datetime: dayjs.Dayjs): SlideData => {
  const firstDayOfMonth = datetime.startOf("month");
  let _dt = firstDayOfMonth.startOf("week");
  const wArr = [];
  do {
    const week = [];
    for (let i = 0; i < 7; i++) {
      const dayData: DayData = {
        dt: _dt,
        events: [],
      };
      for (const schedule of userData.value.schedules) {
        if (
          schedule.startTs &&
          schedule.startTs.unix() <= _dt.unix() &&
          schedule.endTs &&
          schedule.endTs.unix() >= _dt.unix()
        ) {
          dayData.events.push(schedule);
        }
      }
      if (selectedDate.value?.dt.unix() == _dt.unix()) {
        selectedDate.value = dayData;
      }
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
const btnDaySelectClk = (slide: SlideData, day: DayData) => {
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
  if (!mm.weekArr) {
    console.warn("no weekArr");
    return;
  }
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
    selectedDate.value = undefined; // 清空选中日期
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
  const scheduleData = event.detail.data;
  if (scheduleData && event.detail.role === "confirm") {
    // 处理数据
    userData.value.schedules.push(scheduleData);
    updateScheduleData();
    console.log(selectedDate.value);
  }
};
// 日程状态改变
const onScheduleCheckboxChange = (event: any, schedule: any) => {
  if (schedule) {
    schedule.state = event.detail.checked ? 1 : 0;
  }
};

// 排序按钮
const btnSortClk = () => {
  swiperRef?.value?.update();
};
// 左下测试按钮
const btnTestClk = () => {
  console.log(JSON.stringify(userData.value));
  // 测试通知
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
  //
  setSave(
    1,
    "leo",
    JSON.stringify(userData.value),
    (res) => {
      console.log("setSave", res);
    },
    (err) => {
      console.log("setSave", err);
    }
  );
};
// 获取swiper对象
const setSwiperInstance = (swiper: any) => {
  console.log("setSwiperInstance", swiper);
  swiperRef.value = swiper;
  swiper.slideTo(1, 0, false);
  // chooseSelectedDate();
};
// 刷新页面事件
const handleRefresh = (event: any) => {
  // console.log("handleRefresh", event);
  getSave(
    1,
    (res) => {
      console.log("handleRefresh", res);
      toastData.value.isOpen = true;
      toastData.value.text = "更新成功";
      event.target.complete();
    },
    (err) => {
      console.log("handleRefresh", err);
      toastData.value.isOpen = true;
      toastData.value.text = JSON.stringify(err);
      event.target.complete();
    }
  );
};

// 初始化数据
const updateScheduleData = () => {
  slideArr.value = [
    createSlideData(currentDate.subtract(1, "months")),
    createSlideData(currentDate),
    createSlideData(currentDate.add(1, "months")),
  ];
};

onMounted(() => {
  // 获取数据
  getSave(
    1,
    (res) => {
      console.log("getSave", res.data);
      userData.value = JSON.parse(res.data);
      for (let i = 0; i < userData.value.schedules.length; i++) {
        const schedule = userData.value.schedules[i];
        schedule.startTs = dayjs(schedule.startTs);
        schedule.endTs = dayjs(schedule.endTs);
      }
      updateScheduleData();
      chooseSelectedDate();
      setTimeout(() => {
        swiperRef?.value?.update();
      }, 100);
    },
    (err) => {
      console.log("getSave", err);
    }
  );
});
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
