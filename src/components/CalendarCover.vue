<template>
  <ion-modal mode="ios" aria-hidden="false" ref="selfRef">
    <ion-content class="main_content">
      <ion-item class="transparent">
        <h2 style="font-size: 20px; color: white">
          {{ currentDate.format("YYYY-MM-DD") + weekHead[currentDate.day()] }}
        </h2>
        <ion-button slot="end" color="dark" @click="btnTodayClk">Today</ion-button>
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
          rotate: 10,
          stretch: 0,
          depth: 100,
          modifier: 1,
          slideShadows: false,
        }"
        :keyboard="true"
        style="height: 90%">
        <swiper-slide v-for="(day, idx) in dayArr" :key="idx" class="data-content">
          <ion-content>
            <ion-item>日程 {{ day?.dt.format("MM-DD") }}</ion-item>
            <ion-item v-for="(schedule, idx) in day.events" :key="idx">
              <ion-checkbox
                style="--size: 26px; padding-right: 5px"
                slot="start"
                :checked="day.save[schedule.id]?.state === 1"
                @ionChange="onScheduleCheckboxChange($event, day, schedule.id)">
              </ion-checkbox>
              <div @click="btnScheduleClk($event, schedule, day)" class="scheduleItem">
                <ion-label
                  :class="{
                    'text-line-through': day.save[schedule.id]?.state === 1,
                  }">
                  <h2>{{ schedule.title }}</h2>
                  <div class="flex">
                    <p class="schedule-lb-sub">
                      <ion-icon :icon="listOutline" style="position: relative; top: 3px"></ion-icon>
                      {{ countFinishedSubtask(day, schedule) }}
                      /
                      {{ schedule?.subtasks?.length }}
                    </p>
                    <p class="schedule-lb-group">
                      {{ getGroupOptions(schedule.groupId).label }}
                    </p>
                  </div>
                </ion-label>
                <span
                  class="v-dot"
                  :style="{
                    'background-color': getColorOptions(schedule.color).tag,
                    'margin-left': '10px',
                  }">
                </span>
                <Icon
                  :icon="getPriorityOptions(schedule.priority).icon"
                  :height="'36'"
                  :color="getPriorityOptions(schedule.priority).color">
                </Icon>
              </div>
            </ion-item>
          </ion-content>
        </swiper-slide>
      </swiper>
    </ion-content>
    <div style="width: 100%; height: 20%" @click="selfRef.$el.dismiss()"></div>
    <SchedulePop
      id="pop-modal"
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
import { getColorOptions, getGroupOptions, getPriorityOptions } from "@/modal/ScheduleType";
import { DayData, ScheduleData, ScheduleSave, UData, UserData } from "@/modal/UserData";
import { setSave } from "@/utils/NetUtil";
import { Icon } from "@iconify/vue";
import { IonCheckbox, IonicSlides } from "@ionic/vue";
import "@ionic/vue/css/ionic-swiper.css";
import dayjs from "dayjs";
import { listOutline } from "ionicons/icons";
import "swiper/css";
import "swiper/css/effect-fade";
import { EffectCoverflow, Keyboard } from "swiper/modules";
import { Swiper, SwiperSlide } from "swiper/vue";
import { nextTick, ref, watch } from "vue";
1;
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
const curIdx = 1;
function onTransitionEnd(obj: any) {
  if (curIdx === obj.activeIndex) return;
  const currentIndex = obj.activeIndex; // 获取当前活动幻灯片的索引
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
        ((day.save[schedule.id]?.subtasks && day.save[schedule.id]?.subtasks[t.id]) || 0) === 1
    ).length;
  } catch (error) {
    console.log("countFinishedSubtask", error);
    return 0;
  }
};
// 日程状态改变
const onScheduleCheckboxChange = (_event: any, day: DayData | undefined, scheduleId: number) => {
  if (day) {
    const preSave = day.save[scheduleId] || new ScheduleSave();
    preSave.state = _event.detail.checked ? 1 : 0;
    day.save[scheduleId] = preSave;
    nextTick(() => {
      // schedule 排序 这玩意必须延后一帧，否则会导致checkbox状态错乱
      day.events.sort((a: ScheduleData, b: ScheduleData) => {
        const sa: number = day.save[a.id]?.state || 0;
        const sb: number = day.save[b.id]?.state || 0;
        if (sa === sb) {
          return (a.id ?? 0) - (b.id ?? 0);
        }
        return sa - sb;
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
  scheduleSave.value = day.save[schedule.id];
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
  // currentDate.value = dayjs();
  // updateScheduleData();
  // swiperRef?.value?.slideTo(1, 0, false);
}
</script>
<style scoped>
.main_content::part(scroll) {
  height: 100%;
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
.data-content {
  height: 100%;
  width: 80vw;
}
.data-content ion-content::part(scroll) {
  height: 100%;
  border: 1px solid #e2d0d0;
  border-radius: 10px;
}
.data-content ion-content::part(background) {
  border-radius: 10px;
}
.scheduleItem {
  position: relative;
  display: flex;
  box-sizing: border-box;
  align-items: center;
  width: 100%;
  justify-content: space-between;
}
.scheduleItem ion-label {
  margin: 0px;
  padding: 10px;
  flex: 1;
}
.scheduleItem h2 {
  white-space: nowrap; /* 防止文本换行 */
}
</style>
