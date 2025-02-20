<template>
  <ion-modal mode="ios" ref="selfRef" @willDismiss="onModalDismiss">
    <ion-content class="main_content" fixed-slot-placement="before">
      <ion-item class="transparent ion-padding-start">
        <h2 class="text-xl font-bold text-white">
          {{ currentDate.format("YYYY-MM-DD") + " " + weekHead[currentDate.day()] }}
        </h2>
        <ion-button
          slot="end"
          fill="clear"
          @click="btnTodayClk"
          size="small"
          shape="round"
          class="ion-no-padding mr-3"
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
        :modules="[Keyboard, EffectCoverflow, IonicSlides]"
        :effect="'coverflow'"
        :slidesPerView="'auto'"
        :freeMode="false"
        :coverflowEffect="{
          rotate: 0,
          stretch: -10,
          depth: 0, // 这玩意在Safari上有问题
          modifier: 1,
          slideShadows: false, // 是否开启slide阴影
        }"
        :keyboard="true"
        class="h-[90%]">
        <swiper-slide
          v-for="(day, idx) in dayArr"
          :key="idx"
          class="data-content h-full w-[85%] flex-col">
          <ion-item color="light" lines="none" class="w-full rounded-t">
            <icon-mdi-list-status class="text-blue-500" :height="'30'" :width="'30'" slot="start">
            </icon-mdi-list-status>
            <div class="h-12"></div>
            <ion-button id="btnSort" @click="btnSortClk" fill="clear" slot="end">
              <ion-icon :icon="swapVertical" class="button-native"></ion-icon>
            </ion-button>
          </ion-item>
          <ion-content class="">
            <ion-reorder-group
              :disabled="bReorderDisabled"
              @ionItemReorder="onReorder($event, day)">
              <div v-for="(schedule, idx) in day.events" :key="idx" class="bg-white">
                <ion-item lines="none">
                  <ion-checkbox
                    style="--size: 22px; padding-right: 10px"
                    :checked="day.save && day.save[schedule.id]?.state === 1"
                    @ionChange="onScheduleCheckboxChange($event, day, schedule)" />
                  <div
                    @click="btnScheduleClk($event, schedule, day)"
                    class="flex items-center w-full">
                    <ion-label
                      :class="{
                        'line-through': day.save && day.save[schedule.id]?.state === 1,
                      }"
                      class="pt-2.5 flex-1">
                      <h2 class="truncate">{{ schedule.title }}</h2>
                      <div class="flex text-gray-400">
                        <span class="mr-1 flex items-center text-xs">
                          <component
                            :is="getGroupOptions(schedule.groupId).icon"
                            height="18px"
                            width="18px" />
                        </span>
                        <span class="w-11 mr-1 flex items-center text-xs">
                          {{ getGroupOptions(schedule.groupId).label }}
                        </span>
                        <span class="mr-3 flex items-center text-xs">
                          {{ schedule.allDay ? "全天" : schedule.startTs?.format("HH:mm") }}
                        </span>
                        <span class="mr-1 flex items-center">
                          <MdiStar class="mr-1 text-sm" />
                          <p class="w-5 text-sm">
                            {{ countAllReward(schedule) }}
                          </p>
                        </span>
                      </div>
                    </ion-label>
                    <span
                      class="v-dot ml-2.5"
                      :style="{
                        'background-color': getColorOptions(schedule.color).tag,
                      }" />
                    <component
                      v-if="bReorderDisabled"
                      :is="getPriorityOptions(schedule.priority).icon"
                      :height="'36px'"
                      width="36px"
                      :color="getPriorityOptions(schedule.priority).color" />
                    <ion-reorder slot="end"></ion-reorder>
                  </div>
                </ion-item>
                <div
                  class="pl-[45px] flex items-center text-gray-400"
                  v-for="(sub, idx) in schedule.subtasks"
                  :key="idx"
                  @click="btnScheduleClk($event, schedule, day)">
                  <ion-checkbox
                    disabled
                    class="sub-checkbox"
                    :checked="day.save && day.save[schedule.id]?.subtasks[sub.id] === 1" />
                  <span class="pl-2 text-base flex-1 text-left">{{ sub.name }}</span>
                  <MdiStar class="w-[1em] h-[1em]" />
                  <span class="w-5 text-right mr-6">{{ sub.score ?? 0 }}</span>
                </div>
                <div style="border-bottom-width: 1px" class="mt-2"></div>
              </div>
            </ion-reorder-group>
          </ion-content>
        </swiper-slide>
      </swiper>
    </ion-content>
    <div class="w-full h-[10%] absolute bottom-0" @click="selfRef.$el.dismiss()"></div>
    <FabButton
      @click="btnAddScheduleClk"
      class="right-[9%] bottom-[10%]"
      bottom="10%"
      right="9%"
      :hasBar="false">
      <ion-icon :icon="add" size="large"></ion-icon>
    </FabButton>
    <SchedulePop
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
import FabButton from "@/components/FabButton.vue";
import SchedulePop from "@/components/SchedulePopModal.vue";
import { getColorOptions } from "@/modal/ColorType";
import { getGroupOptions, getPriorityOptions } from "@/modal/ScheduleType";
import { DayData, S_TS, ScheduleData, ScheduleSave, UData, UserData } from "@/modal/UserData";
import { setSave } from "@/utils/NetUtil";
import { IonCheckbox, IonicSlides, IonReorder, IonReorderGroup } from "@ionic/vue";
import "@ionic/vue/css/ionic-swiper.css";
import dayjs from "dayjs";
import { add, swapVertical } from "ionicons/icons";
import _ from "lodash";
import "swiper/css";
import "swiper/css/effect-fade";
import { EffectCoverflow, Keyboard } from "swiper/modules";
import { Swiper, SwiperSlide } from "swiper/vue";
import { inject, nextTick, onMounted, ref, watch } from "vue";
import MdiStar from "~icons/mdi/star";
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
const globalVar: any = inject("globalVar");
const emits = defineEmits(["update:data"]);
const dayArr = ref<any[]>([{}, {}, {}]); // 滑动数据
const swiperRef = ref(); // 滑动对象
const currentDate = ref(dayjs(props.dt as dayjs.Dayjs)); // 当前日期
const selfRef = ref();
const bReorderDisabled = ref(true);
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
onMounted(() => {});
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

// 日程状态改变
const onScheduleCheckboxChange = (
  _event: any,
  day: DayData | undefined,
  schedule: ScheduleData
) => {
  if (day) {
    const dKey = S_TS(day.dt);
    if (day.save === undefined) {
      day.save = {};
      const uSave = props.userData.save;
      uSave[dKey] = day.save;
    }
    const preSave = day.save[schedule.id] || new ScheduleSave();
    preSave.state = _event.detail.checked ? 1 : 0;
    // day.save[scheduleId] = preSave;
    UData.setScheduleSave(dKey, props.userData as UserData, schedule, preSave);
    nextTick(() => {
      // schedule 排序 这玩意必须延后一帧，否则会导致checkbox状态错乱
      day.events.sort((a: ScheduleData, b: ScheduleData) => {
        return UData.CmpScheduleData(a, b, day.save);
      });
    });
    doSaveUserData();
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
  }
};

// 保存存档
function doSaveUserData() {
  // console.log("doSaveUserData", props.userData);
  setSave(globalVar.scheduleListId, props.userData)
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

// 排序按钮
const btnSortClk = () => {
  bReorderDisabled.value = !bReorderDisabled.value;
};
function onReorder(event: any, day: DayData) {
  let eList = day.events;
  // console.log(_.map(eList, 'title'));
  eList = event.detail.complete(eList);
  const userData = props.userData;
  if (eList) {
    let ii = eList[0].order ?? 0;
    _.forEach(eList, (e: any) => {
      userData.schedules[e.id].order = ii;
      e.order = ii++;
    });
  }
  // console.log(_.map(eList, "title"));
  eList.sort((a: ScheduleData, b: ScheduleData) => {
    return UData.CmpScheduleData(a, b, day.save);
  });
  doSaveUserData();
  // console.log(eList);
}
function onModalDismiss() {
  // console.log("onModalDismiss");
  bReorderDisabled.value = true;
  emits("update:data", currentDate.value);
}

// 总奖励
function countAllReward(schedule: ScheduleData) {
  return UData.CountScheduleReward(schedule);
}
</script>
<style scoped>
.main_content::part(scroll) {
  height: 90%;
  margin-top: 5vh;
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
  padding: 6px;
  border-bottom-right-radius: 10px;
  border-bottom-left-radius: 10px;
}
.data-content ion-content::part(background) {
  border-bottom-right-radius: 10px;
  border-bottom-left-radius: 10px;
}
.sub-checkbox {
  --size: 18px;
  --border-radius: 4px;
}
</style>
