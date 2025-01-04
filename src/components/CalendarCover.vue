<template>
  <ion-modal mode="ios" ref="selfRef">
    <ion-content class="main_content">
      <ion-item class="transparent">
        <h2 class="text-xl font-bold text-white">
          {{ currentDate.format("YYYY-MM-DD") + " " + weekHead[currentDate.day()] }}
        </h2>
        <ion-button
          slot="end"
          fill="clear"
          @click="btnTodayClk"
          size="small"
          class="ion-padding-horizontal"
          v-if="!currentDate.isToday()">
          <div class="bg-orange-600 w-16 h-8 flex items-center text-white rounded-md p-2">
            <icon-mdi-calendar-today-outline :height="'16'" slot="start" />
            今天
          </div>
        </ion-button>
      </ion-item>
      <swiper
        @transitionEnd="onTransitionEnd"
        @swiper="setSwiperInstance"
        :centered-slides="true"
        :modules="[IonicSlides, Keyboard, EffectCoverflow]"
        :effect="'coverflow'"
        :slidesPerView="'auto'"
        :freeMode="false"
        :coverflowEffect="{
          rotate: 20,
          stretch: -10,
          depth: 10,
          modifier: 1,
          slideShadows: false, // 是否开启slide阴影
        }"
        :keyboard="true"
        class="h-[90%]">
        <swiper-slide
          v-for="(day, idx) in dayArr"
          :key="idx"
          class="data-content h-full w-4/5 flex-col">
          <ion-item color="light" lines="none" class="w-full rounded-t">
            <icon-mdi-list-status class="text-blue-500" :height="'30'" :width="'30'" slot="start">
            </icon-mdi-list-status>
            <div class="h-12"></div>
          </ion-item>
          <ion-content>
            <ion-item v-for="(schedule, idx) in day.events" :key="idx">
              <ion-checkbox
                style="--size: 26px"
                :checked="day.save && day.save[schedule.id]?.state === 1"
                @ionChange="onScheduleCheckboxChange($event, day, schedule.id)">
              </ion-checkbox>
              <div @click="btnScheduleClk($event, schedule, day)" class="flex items-center w-full">
                <ion-label
                  :class="{
                    'text-line-through': day.save && day.save[schedule.id]?.state === 1,
                  }"
                  class="p-2.5 flex-1">
                  <h2 class="truncate">{{ schedule.title }}</h2>
                  <div class="flex text-gray-400">
                    <p class="w-14 mr-2">
                      <ion-icon :icon="listOutline" class="relative top-0.5"></ion-icon>
                      {{ countFinishedSubtask(day, schedule) }}
                      /
                      {{ schedule?.subtasks?.length }}
                    </p>
                    <span class="mr-1 pt-[1px]">
                      <component
                        :is="getGroupOptions(schedule.groupId).icon"
                        height="16px"
                        width="16px" />
                    </span>
                    <p class="schedule-lb-group w-14">
                      {{ getGroupOptions(schedule.groupId).label }}
                    </p>
                    <p>{{ schedule.allDay ? "全天" : schedule.startTs?.format("HH:mm") }}</p>
                  </div>
                </ion-label>
                <span
                  class="v-dot ml-2.5"
                  :style="{
                    'background-color': getColorOptions(schedule.color).tag,
                  }" />
                <component
                  :is="getPriorityOptions(schedule.priority).icon"
                  :height="'36px'"
                  width="36px"
                  :color="getPriorityOptions(schedule.priority).color" />
                <!-- <div class="w-14">11x</div> -->
              </div>
            </ion-item>
          </ion-content>
        </swiper-slide>
      </swiper>
      <ion-fab slot="fixed" vertical="bottom" horizontal="end">
        <ion-fab-button @click="btnAddScheduleClk">
          <ion-icon :icon="add" size="large"></ion-icon>
        </ion-fab-button>
      </ion-fab>
    </ion-content>
    <div class="w-full h-[10%]" @click="selfRef.$el.dismiss()"></div>
    <SchedulePop
      id="pop-modal"
      aria-hidden="false"
      ref="scheduleModal"
      :is-open="isScheduleModalOpen"
      :modal="scheduleModal"
      :schedule="scheduleModalData"
      :save="scheduleSave"
      @willDismiss="onScheduleModalDismiss">
    </SchedulePop>
  </ion-modal>
</template>
<script setup lang="ts">
import SchedulePop from "@/components/SchedulePopModal.vue";
import { getGroupOptions, getPriorityOptions } from "@/modal/ScheduleType";
import { getColorOptions } from "@/modal/ColorType";
import { DayData, S_TS, ScheduleData, ScheduleSave, UData, UserData } from "@/modal/UserData";
import { setSave } from "@/utils/NetUtil";
// import midCalendarTodayOutline from "@iconify-icons/mdi/calendar-today-outline";
// import mdiListStatus from "@iconify-icons/mdi/list-status";
import { IonCheckbox, IonFab, IonFabButton, IonicSlides } from "@ionic/vue";
import "@ionic/vue/css/ionic-swiper.css";
import dayjs from "dayjs";
import { add, listOutline } from "ionicons/icons";
import "swiper/css";
import "swiper/css/effect-fade";
import { EffectCoverflow, Keyboard } from "swiper/modules";
import { Swiper, SwiperSlide } from "swiper/vue";
import { nextTick, ref, watch } from "vue";
const weekHead = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];
const props = defineProps({
  dt: {
    type: Object,
    default: dayjs(),
  },
  userData: {
    type: Object,
    required: true,
  },
});
const emits = defineEmits(["update:data"]);
const dayArr = ref<any[]>([{}, {}, {}]); // 滑动数据
const swiperRef = ref(); // 滑动对象
const currentDate = ref(dayjs(props.dt as dayjs.Dayjs)); // 当前日期
const selfRef = ref();
// === 弹窗对象
const scheduleModal = ref();
const scheduleModalData = ref<ScheduleData>();
const scheduleSave = ref<ScheduleSave>();
const isScheduleModalOpen = ref(false);
// === 弹窗对象结束

watch(
  () => props.dt,
  (nv) => {
    currentDate.value = nv as dayjs.Dayjs;
    updateScheduleData();
  },
  { deep: true }
);
// 初始化数据
const updateScheduleData = () => {
  dayArr.value = [
    UData.createDayData(currentDate.value.subtract(1, "day"), props.userData as UserData),
    UData.createDayData(currentDate.value as dayjs.Dayjs, props.userData as UserData),
    UData.createDayData(currentDate.value.add(1, "day"), props.userData as UserData),
  ];
  // console.log("updateScheduleData", currentDate.value, dayArr.value);
};
// 翻页事件
function onTransitionEnd(obj: any) {
  if (1 === obj.activeIndex) return;
  const currentIndex = obj.activeIndex;
  const previousIndex = obj.previousIndex;
  if (currentIndex < previousIndex) {
    currentDate.value = currentDate.value.subtract(1, "day");
    updateScheduleData();
    // console.log("transitionEnd <-", currentIndex, previousIndex, obj.slides, dayArr.value);
    obj.slideTo(1, 0, false);
  } else if (currentIndex > previousIndex) {
    currentDate.value = currentDate.value.add(1, "day");
    updateScheduleData();
    obj.slideTo(1, 0, false);
    // console.log("transitionEnd ->", currentIndex, previousIndex, obj.slides, dayArr.value);
  }
}
// 获取swiper对象
const setSwiperInstance = (swiper: any) => {
  swiperRef.value = swiper;
  swiper.slideTo(1, 0, false);
};
// 计算完成任务数量
const countFinishedSubtask = (day: DayData, schedule: ScheduleData) => {
  try {
    return schedule?.subtasks?.filter(
      (t: any) =>
        ((day.save && day.save[schedule.id]?.subtasks && day.save[schedule.id]?.subtasks[t.id]) ||
          0) === 1
    ).length;
  } catch (error) {
    console.log("countFinishedSubtask", error);
    return 0;
  }
};
// 日程状态改变
const onScheduleCheckboxChange = (_event: any, day: DayData | undefined, scheduleId: number) => {
  if (day) {
    if (day.save === undefined) {
      day.save = {};
      const uSave = props.userData.save;
      uSave[S_TS(day.dt)] = day.save;
    }
    const preSave = day.save[scheduleId] || new ScheduleSave();
    preSave.state = _event.detail.checked ? 1 : 0;
    day.save[scheduleId] = preSave;
    nextTick(() => {
      // schedule 排序 这玩意必须延后一帧，否则会导致checkbox状态错乱
      day.events.sort((a: ScheduleData, b: ScheduleData) => {
        return UData.CmpScheduleData(a, b, day.save);
      });
    });
    doSaveUserData();
    emits("update:data", currentDate.value);
  }
};
// 日程按钮点击
const btnScheduleClk = (_event: any, schedule: ScheduleData, day: DayData) => {
  isScheduleModalOpen.value = true;
  scheduleModalData.value = schedule;
  scheduleSave.value = day.save ? day.save[schedule.id] : undefined;
};
// 添加日程页面关闭回调
const onScheduleModalDismiss = (event: any) => {
  // console.log("onScheduleModalDismiss", event, event.detail.data);
  isScheduleModalOpen.value = false;
  if (event.detail.role === "backdrop") return;
  const [_scheduleData, _scheduleSave] = event.detail.data;
  const dt = currentDate.value;
  const r = UData.updateSchedularData(
    props.userData as UserData,
    _scheduleData,
    _scheduleSave,
    dt,
    event.detail.role
  );
  if (r) {
    updateScheduleData();
    doSaveUserData();
    emits("update:data", currentDate.value);
  }
};

// 保存存档
function doSaveUserData() {
  setSave(props.userData.id, props.userData.name, JSON.stringify(props.userData))
    .then((res) => {
      console.log("doSaveUserData", res);
    })
    .catch((err) => {
      console.log("doSaveUserData", err);
    });
}
// 今天按钮点击
function btnTodayClk() {
  currentDate.value = dayjs();
  updateScheduleData();
  swiperRef?.value?.slideTo(1, 0, false);
}

// 添加日程按钮
const btnAddScheduleClk = () => {
  // 清空数据
  scheduleModalData.value = undefined;
  scheduleSave.value = undefined;
  isScheduleModalOpen.value = true;
};
</script>
<style scoped>
.main_content::part(scroll) {
  height: 90%;
  margin-top: 20%;
}
.main_content::part(background) {
  display: none;
}
ion-modal::part(backdrop) {
  background-color: var(--ion-color-dark) !important;
  opacity: 0.3 !important;
}

ion-modal::part(content) {
  /* background-color: #ffffff4b !important; */
  background-color: transparent !important;
  align-items: center;
}
ion-modal {
  --height: 100%;
  --width: 100%;
  align-items: center;
}
.data-content ion-content::part(scroll) {
  height: 100%;
  /* border: 1px solid #e2d0d0; */
  /* border-radius: 10px; */
  border-bottom-right-radius: 10px;
  border-bottom-left-radius: 10px;
}
.data-content ion-content::part(background) {
  border-bottom-right-radius: 10px;
  border-bottom-left-radius: 10px;
}
</style>
