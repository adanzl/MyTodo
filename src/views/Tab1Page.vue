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
          <div v-else>日历</div>
        </ion-title>
        <ion-buttons slot="end" class="ion-padding">
          <ion-icon
            :icon="ellipseOutline"
            @click="btnTodayClk"
            style="margin-right: 16px"
          ></ion-icon>
          <ion-icon :icon="swapVertical" @click="btnSortClk"></ion-icon>
        </ion-buttons>
      </ion-toolbar>
    </ion-header>
    <ion-content :scroll-y="false">
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
      <!-- 日程列表 -->
      <ion-content
        color="light"
        @touchmove="onTouchMove"
        @touchstart="onTouchStart"
      >
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
                <!-- 日程条目 -->
                <ion-item-sliding
                  v-for="(schedule, idx) in selectedDate?.events"
                  :key="idx"
                >
                  <ion-item :detail="true" :button="true">
                    <ion-checkbox
                      slot="start"
                      :checked="
                        selectedDate?.save.get(schedule.id)?.state === 1
                      "
                      @ionChange="
                        onScheduleCheckboxChange(
                          $event,
                          selectedDate,
                          schedule.id
                        )
                      "
                    >
                    </ion-checkbox>
                    <ion-label
                      :class="{
                        'text-line-through':
                          selectedDate?.save.get(schedule.id)?.state === 1,
                      }"
                      @click="btnScheduleClk($event, schedule)"
                    >
                      <h2>{{ schedule.title }}</h2>
                      <p>
                        {{ selectedDate?.dt.format("ddd") }}
                        <ion-icon
                          :icon="listOutline"
                          style="position: relative; top: 3px"
                        ></ion-icon>
                        {{
                          schedule?.subTasks?.filter(
                            (t) =>
                              (selectedDate?.save
                                .get(schedule.id)
                                ?.subTasks.get(t.id) || 0) === 1
                          ).length
                        }}/{{ schedule?.subTasks?.length }}
                      </p>
                    </ion-label>
                  </ion-item>
                  <ion-item-options side="end">
                    <ion-item-option @click="btnScheduleAlarmClk">
                      <ion-icon :icon="alarmOutline"></ion-icon>
                    </ion-item-option>
                    <ion-item-option
                      color="danger"
                      @click="btnScheduleRemoveClk($event, schedule)"
                    >
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
        ref="scheduleModal"
        :is-open="isScheduleModalOpen"
        class="ion-padding"
        @willDismiss="onScheduleModalDismiss"
      >
        <SchedulePop
          :modal="scheduleModal"
          :schedule="scheduleModalData"
          :save="scheduleSave"
          @update:save="onUpdateScheduleSave"
          @update:schedule="onUpdateScheduleData"
        ></SchedulePop>
      </ion-modal>
      <ion-alert
        :is-open="scheduleDelConfirm.isOpen"
        header="Confirm!"
        :buttons="alertButtons"
        :sub-header="scheduleDelConfirm.text"
        @didDismiss="onDelSchedulerConfirm($event)"
      ></ion-alert>
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
      <ion-fab-button @click="btnAddScheduleClk">
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
import CalenderTab from "@/components/CalendarTab.vue";
import SchedulePop from "@/components/SchedulePopModal.vue";
import { LocalNotifications } from "@capacitor/local-notifications";

import {
  IonAccordion,
  IonAccordionGroup,
  IonCheckbox,
  IonFab,
  IonFabButton,
  IonicSlides,
  IonItemOption,
  IonItemOptions,
  IonItemSliding,
  IonModal,
  IonRefresher,
  IonRefresherContent,
} from "@ionic/vue";
import dayjs from "dayjs";
import {
  addCircleOutline,
  alarmOutline,
  chevronDown,
  chevronUp,
  ellipseOutline,
  list,
  listOutline,
  swapVertical,
  trashOutline,
} from "ionicons/icons";
import { Keyboard } from "swiper/modules";
import { Swiper, SwiperSlide } from "swiper/vue";
import { onMounted, ref } from "vue";

import { getSave, setSave } from "@/components/NetUtil.vue";
import { ScheduleData, ScheduleSave, UserData } from "@/type/UserData.vue";
import "@ionic/vue/css/ionic-swiper.css";
import "swiper/css";
import "swiper/css/effect-fade";

export type SlideData = {
  vid: number;
  month: number;
  year: number;
  firstDayOfMonth: dayjs.Dayjs;
  weekArr: DayData[][];
};
const userData = ref<UserData>({
  id: 1,
  name: "leo",
  schedules: [],
  save: new Map(),
});
const slideArr = ref<any[]>([{}, {}, {}]); // 滑动数据
const curScheduleList = ref();
const swiperRef = ref(); // 滑动对象
const bFold = ref(false); // 日历折叠状态
const selectedDate = ref<DayData>(); // 选中日期
const scheduleModal = ref(); // 弹窗对象
const scheduleModalData = ref<ScheduleData>();
const scheduleSave = ref<ScheduleSave>();
const isScheduleModalOpen = ref(false);
const toastData = ref({
  isOpen: false,
  duration: 3000,
  text: "",
});
//  一天的日程数据
type DayData = {
  dt: dayjs.Dayjs;
  events: ScheduleData[]; // 当天可见日程
  save: Map<number, ScheduleSave>; // 日程id->日程保存情况
};
let currentDate = dayjs().startOf("day");
const createSlideData = (datetime: dayjs.Dayjs): SlideData => {
  const firstDayOfMonth = datetime.startOf("month");
  let _dt = firstDayOfMonth.startOf("week");
  const wArr: DayData[][] = [];
  do {
    const week: DayData[] = [];
    for (let i = 0; i < 7; i++) {
      const dayData: DayData = {
        dt: _dt,
        events: [],
        save: new Map(),
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
        const save = userData.value.save?.get(_dt.format("YYYY-MM-DD"));
        if (save) {
          dayData.save = save;
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

let pTouch: any;
let lstTs = 0;
const onTouchStart = (event: any) => {
  // console.log("onTouchStart", bMoving, event);
  pTouch = event.touches[0];
};
const onTouchMove = (event: any) => {
  // console.log("onTouchMove", bMoving, event);
  const ds = dayjs().valueOf() - lstTs;
  if (ds < 300) {
    // console.log("too fast", ds);
    return;
  }
  const d = event.touches[0].clientY - pTouch.clientY;
  if (Math.abs(d) > 20) {
    lstTs = dayjs().valueOf();
    if (d > 0 === bFold.value) {
      btnCalendarFoldClk();
    }
  }
};
// 添加日程页面关闭回调
const onScheduleModalDismiss = (event: any) => {
  const scheduleData = event.detail.data;
  // console.log("onScheduleModalDismiss", event, scheduleSave.value);
  if (scheduleData && event.detail.role === "confirm") {
    // 处理数据
    // 日程变化
    if (scheduleData.id === undefined) {
      // add id userData.value.schedules id的最大值=1
      const id = userData.value.schedules.reduce(
        (max, s) => (s.id! > max ? s.id! : max),
        0
      );
      scheduleData.id = id;
      userData.value.schedules.push(scheduleData);
    } else {
      const idx = userData.value.schedules.findIndex(
        (s) => s.id === scheduleData.id
      );
      if (idx !== -1) {
        userData.value.schedules[idx] = scheduleData;
      }
    }
    // 存档变化 TODO
    
    updateScheduleData();
    setSave(
      userData.value.id,
      userData.value.name,
      JSON.stringify(userData.value)
    )
      .then((res) => {
        console.log("setSave", res);
      })
      .catch((err) => {
        console.error("setSave", err);
      });
  }
  isScheduleModalOpen.value = false;
};
// 删除日程确认框
const scheduleDelConfirm = ref<{ isOpen: boolean; data: any; text: string }>({
  isOpen: false,
  data: undefined,
  text: "",
});
const alertButtons = [
  {
    text: "Cancel",
    role: "cancel",
  },
  {
    text: "OK",
    role: "confirm",
  },
];
const onDelSchedulerConfirm = (event: any) => {
  // 处理数据
  scheduleDelConfirm.value.isOpen = false;
  if (event.detail.role === "confirm") {
    const idx = userData.value.schedules.findIndex(
      (s) => s.id === scheduleDelConfirm.value.data.id
    );
    if (idx !== -1) {
      userData.value.schedules.splice(idx, 1);
    }
    updateScheduleData();
  }
};
// 日程删除
const btnScheduleRemoveClk = (event: any, schedule: ScheduleData) => {
  scheduleDelConfirm.value.isOpen = true;
  scheduleDelConfirm.value.data = schedule;
  scheduleDelConfirm.value.text = "del " + schedule.title + "?";
};
// 日程状态改变
const onScheduleCheckboxChange = (
  _event: any,
  day: DayData | undefined,
  scheduleId: number
) => {
  if (day) {
    const preSave = day.save.get(scheduleId) || {
      state: 0,
      subTasks: new Map(),
    };
    preSave.state = _event.detail.checked ? 1 : 0;
    day.save.set(scheduleId, preSave);
  }
  // task 排序
  // selectedDate.value?.events.sort((a: ScheduleData, b: ScheduleData) => {
  //   if (a.state === b.state) {
  //     return (a.id??0) - (b.id??0);
  //   }
  //   return a.state - b.state;
  // });
};

const onUpdateScheduleSave = (d: any) => (scheduleSave.value = d);
const onUpdateScheduleData = (d: any) => (scheduleModalData.value = d);

// 日程按钮点击
const btnScheduleClk = (event: any, schedule: ScheduleData) => {
  scheduleModalData.value = schedule;
  scheduleSave.value = selectedDate.value?.save.get(schedule.id);
  isScheduleModalOpen.value = true;
  console.log("btnScheduleClk", schedule, scheduleSave.value);
};
// 添加日程按钮
const btnAddScheduleClk = () => {
  isScheduleModalOpen.value = true;
  scheduleModalData.value = undefined;
  scheduleSave.value = undefined;
};
// 排序按钮
const btnSortClk = () => {
  swiperRef?.value?.update();
};
// 返回今天按钮
const btnTodayClk = () => {
  currentDate = dayjs().startOf("day");
  selectedDate.value = undefined;
  updateScheduleData();
  chooseSelectedDate();
};
// 左下测试按钮
const btnTestClk = () => {
  console.log(JSON.stringify(userData.value));
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
  // setSave(
  //   userData.value.id,
  //   userData.value.name,
  //   JSON.stringify(userData.value)
  // )
  //   .then((res) => {
  //     console.log("setSave", res);
  //   })
  //   .catch((err) => {
  //     console.log("setSave", err);
  //   });
};
// 获取swiper对象
const setSwiperInstance = (swiper: any) => {
  swiperRef.value = swiper;
  swiper.slideTo(1, 0, false);
};
// 刷新页面事件
const handleRefresh = (event: any) => {
  // console.log("handleRefresh", event);
  getSave(1)
    .then((res) => {
      console.log("handleRefresh", res);
      toastData.value.isOpen = true;
      toastData.value.text = "更新成功";
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
const updateScheduleData = () => {
  slideArr.value = [
    createSlideData(currentDate.subtract(1, "months")),
    createSlideData(currentDate),
    createSlideData(currentDate.add(1, "months")),
  ];
};

onMounted(() => {
  // 获取数据
  getSave(1)
    .then((res: any) => {
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
    })
    .catch((err) => {
      toastData.value.isOpen = true;
      toastData.value.text = JSON.stringify(err);
    });
});

// 日历折叠按钮
const btnCalendarFoldClk = () => {
  bFold.value = !bFold.value;
  setTimeout(() => {
    swiperRef.value.update();
  }, 100);
};

// 日程专注按钮
const btnScheduleAlarmClk = () => {
  console.log("btnScheduleAlarmClk");
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

#eventMask {
  width: 100%;
  height: 100%;
  display: block;
  position: absolute;
  top: 0;
  left: 0;
  z-index: 9999;
  /* background-color: rgba(0, 0, 0, 0.5); */
}
</style>
