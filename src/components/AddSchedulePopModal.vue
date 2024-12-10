<template>
  <div class="ion-padding" id="main">
    <ion-toolbar class="transparent">
      <ion-title>Add Schedule</ion-title>
    </ion-toolbar>
    <ion-segment value="sType" @ionChange="onTypeChange">
      <ion-segment-button value="sType" content-id="sType">
        <ion-label>Schedule</ion-label>
      </ion-segment-button>
      <ion-segment-button value="tType" content-id="tType">
        <ion-label>Todo</ion-label>
      </ion-segment-button>
    </ion-segment>
    <ion-segment-view class="main_content">
      <ion-segment-content
        id="sType"
        style="height: 100%; background-color: gray !important"
      >
        <ion-content id="main_bg" class="ion-margin-top">
          <ion-list :inset="true">
            <ion-item>
              <ion-input
                placeholder="输入日程标题"
                v-model="curScheduleData.title"
              >
              </ion-input>
            </ion-item>
            <ion-item>
              <ion-select label-placement="floating" label="Group" value="work">
                <ion-icon slot="start" :icon="bookmark" aria-hidden="true">
                </ion-icon>
                <ion-select-option value="none">None</ion-select-option>
                <ion-select-option value="work">Work</ion-select-option>
                <ion-select-option value="other">Other</ion-select-option>
              </ion-select>
              <ion-select label-placement="stacked" label="Priority" value="0">
                <ion-icon slot="start" :icon="airplane" aria-hidden="true">
                </ion-icon>
                <ion-select-option value="0">I</ion-select-option>
                <ion-select-option value="1">II</ion-select-option>
                <ion-select-option value="2">III</ion-select-option>
                <ion-select-option value="3">IV</ion-select-option>
              </ion-select>
              <ion-select label-placement="stacked" label="Color" value="0">
                <ion-icon slot="start" :icon="colorPalette" aria-hidden="true">
                </ion-icon>
                <ion-select-option value="0">Red</ion-select-option>
                <ion-select-option value="1">Yellow</ion-select-option>
                <ion-select-option value="2">Blue</ion-select-option>
                <ion-select-option value="3">White</ion-select-option>
              </ion-select>
            </ion-item>
          </ion-list>
          <ion-list :inset="true">
            <ion-item
              class="ion-text-center"
              :button="true"
              size="large"
              @click="btnScheduleDTClk"
            >
              <ion-icon :icon="calendar" slot="start"></ion-icon>
              <div
                class="flex ion-justify-content-around ion-padding width-100"
              >
                <div class="ion-text-center">
                  <ion-label>Start</ion-label>
                  <ion-label color="tertiary" class="font-size-mini">{{
                    curScheduleData.startTs?.format("YYYY-MM-DD")
                  }}</ion-label>
                </div>
                <div>
                  <ion-label> >></ion-label>
                </div>
                <div class="ion-text-center">
                  <ion-label>End</ion-label>
                  <ion-label color="tertiary" class="font-size-mini">{{
                    curScheduleData.endTs?.format("YYYY-MM-DD")
                  }}</ion-label>
                </div>
              </div>
            </ion-item>
            <ion-item ref="dtItem" class="height-0-block flex">
              <div ref="scheduleDT">
                <ion-buttons mode="ios" class="ion-justify-content-around">
                  <ion-button @click="btnDatetimeClearClk">Clear </ion-button>
                  <ion-segment
                    value="0"
                    mode="ios"
                    style="width: 130px"
                    @ionChange="onDtTabChange"
                  >
                    <ion-segment-button value="0" id="dtStart">
                      Start
                    </ion-segment-button>
                    <ion-segment-button value="1" id="dtEnd">
                      End
                    </ion-segment-button>
                  </ion-segment>
                  <ion-button @click="btnDatetimeOkClk">OK </ion-button>
                </ion-buttons>
                <ion-datetime presentation="date" @ionChange="onDtChange">
                </ion-datetime>
              </div>
            </ion-item>
            <ion-item :button="true" :detail="true">
              <ion-icon :icon="notifications" aria-hidden="true" slot="start">
              </ion-icon>
              <ion-select
                id="selectReminder"
                v-model="curScheduleData.reminder"
                @ionChange="onReminderChange"
              >
                <div slot="label">
                  <ion-label>Reminder</ion-label>
                </div>
                <ion-select-option
                  v-for="(op, idx) in reminderOptions"
                  :key="idx"
                  :value="op.value"
                >
                  {{ op.label }}
                </ion-select-option>
              </ion-select>
            </ion-item>
            <ion-item detail="true">
              <ion-icon :icon="repeat" aria-hidden="true" slot="start">
              </ion-icon>
              <ion-select
                v-model="curScheduleData.repeat"
                @ion-change="onRepeatChange"
              >
                <div slot="label">
                  <ion-label>Repeat</ion-label>
                </div>
                <ion-select-option
                  v-for="(op, idx) in repeatOptions"
                  :key="idx"
                  :value="op.value"
                >
                  {{ op.label }}
                </ion-select-option>
              </ion-select>
            </ion-item>
            <ion-item detail="true" :button="true">
              <ion-icon :icon="power" slot="start"></ion-icon>
              <ion-label>Repeat End</ion-label>
              <ion-datetime-button
                datetime="repeatEndTs"
                :value="curScheduleData.repeatEndTs"
              >
                <div slot="time-target"></div>
              </ion-datetime-button>
              <ion-modal :keep-contents-mounted="true" ref="repeatEndTsModal">
                <ion-datetime
                  id="repeatEndTs"
                  ref="repeatEndTs"
                  presentation="date"
                  @ionChange="onRepeatEndDtChange"
                >
                  <ion-buttons
                    slot="buttons"
                    mode="ios"
                    class="ion-justify-content-around"
                  >
                    <ion-button color="warning" @click="btnRepeatEndClearClk"
                      >Clear
                    </ion-button>
                    <ion-button @click="btnRepeatEndOkClk">OK</ion-button>
                  </ion-buttons>
                </ion-datetime>
              </ion-modal>
            </ion-item>
          </ion-list>
        </ion-content>
      </ion-segment-content>
      <ion-segment-content id="tType">
        <ion-label>Second</ion-label>
        <ion-content color="primary"></ion-content>
      </ion-segment-content>
    </ion-segment-view>
    <ion-footer>
      <ion-button expand="block" mode="ios" color="warning" @click="btnSaveClk">
        Save
      </ion-button>
    </ion-footer>
  </div>
</template>
<script setup lang="ts">
import { ScheduleData } from "@/type/UserData.vue";
import {
  IonDatetime,
  IonDatetimeButton,
  IonModal,
  IonSegment,
  IonSegmentButton,
  IonSegmentContent,
  IonSegmentView,
  IonSelect,
  IonSelectOption,
  createAnimation,
} from "@ionic/vue";
import dayjs from "dayjs";
import {
  airplane,
  bookmark,
  calendar,
  colorPalette,
  notifications,
  power,
  repeat,
} from "ionicons/icons";
import { ref } from "vue";
defineProps({
  modal: Object,
});
const onTypeChange = (event: any) => {
  // 日程类型
  console.log(event.detail.value);
};

const onDtTabChange = (event: any) => {
  scheduleType.value = event.detail.value;
};
const onDtChange = (event: any) => {
  const dt = dayjs(event.detail.value);
  if (scheduleType.value == 0) {
    curScheduleData.value.startTs = dt;
    curScheduleData.value.endTs = dt;
  } else if (scheduleType.value == 1) {
    curScheduleData.value.endTs = dt;
  }
};

const onReminderChange = (event: any) => {
  console.log("onReminderChange", event.detail);
};
const onRepeatChange = (event: any) => {
  console.log("onRepeatChange", event.detail);
};

const onRepeatEndDtChange = (event: any) => {
  curScheduleData.value.repeatEndTs = dayjs(event.detail.value);
};

const btnScheduleDTClk = async () => {
  const hh = scheduleDT.value.offsetHeight;
  const kf = [
    { offset: 0, height: hh + "px", top: "0" },
    { offset: 0.5, height: hh * 0.5 + "px", top: "0" },
    { offset: 1, height: "0", top: "0" },
  ];

  let animation = createAnimation()
    .addElement(dtItem.value.$el)
    .duration(300)
    .keyframes(kf)
    .beforeStyles({
      "transform-origin": "top",
      overflow: "hidden",
      display: "block",
      position: "relative",
    });
  if (!bShowScheduleDT.value) {
    animation = animation.direction("reverse");
  }
  await animation.play();
  bShowScheduleDT.value = !bShowScheduleDT.value;
};

const btnDatetimeOkClk = () => {
  btnScheduleDTClk();
};

const btnRepeatEndOkClk = () => {
  repeatEndTs.value.$el.confirm();
  repeatEndTsModal.value.$el.dismiss();
};
const btnRepeatEndClearClk = () => {
  repeatEndTs.value.$el.cancel();
  curScheduleData.value.repeatEndTs = undefined;
  repeatEndTsModal.value.$el.dismiss();
};

const btnDatetimeClearClk = () => {
  curScheduleData.value.startTs = undefined;
  curScheduleData.value.endTs = undefined;
  btnScheduleDTClk();
};
const btnSaveClk = () => {
  console.log(curScheduleData.value);
};

const scheduleDT = ref();
const bShowScheduleDT = ref(false);
const repeatEndTs = ref();
const repeatEndTsModal = ref();
const dtItem = ref();
const scheduleType = ref(0); // 0:start 1:end
const repeatOptions = ref([
  { value: 0, label: "None" },
  { value: 1, label: "Workday" },
  { value: 2, label: "Every day" },
  { value: 3, label: "Every week" },
  { value: 4, label: "Every month" },
  { value: 5, label: "Every year" },
]);
const reminderOptions = ref([
  { value: 0, label: "None" },
  { value: 1, label: "On the day 9:00" },
  { value: 2, label: "1 day early 9:00" },
  { value: 3, label: "2 day early 9:00" },
  { value: 4, label: "3 day early 9:00" },
  { value: 5, label: "4 day early 9:00" },
]);

const curScheduleData = ref<ScheduleData>({
  id: undefined, // 任务id
  title: "", // 任务标题
  startTs: undefined, // 开始时间
  endTs: undefined, // 结束时间
  reminder: 0, // 提醒类型
  repeat: 0, // 重复类型
  repeatEndTs: undefined, // 重复结束类型
});
</script>

<style scoped>
.main_content {
  /* background-color: gray; */
  height: 75%;
}

#main {
  background: rgb(244, 245, 231);
  /* background: transparent; */
  height: 100%;
}
ion-footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: fit-content;
  padding: 16px;
}
ion-list {
  background-color: transparent !important;
}
ion-segment-content {
  height: 70%;
}

#dtStart,
#dtEnd {
  font-size: min(0.8125rem, 39px);
  height: 32px;
  width: 64px;
  min-height: 10px;
  min-width: 10px;
  --margin-top: 0px;
}

.font-size-mini {
  font-size: 0.8rem;
}
ion-select::part(icon) {
  opacity: 0;
}
</style>
