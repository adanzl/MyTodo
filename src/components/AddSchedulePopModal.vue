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
              <ion-checkbox slot="start" @ionChange="onTaskCheckboxChange">
              </ion-checkbox>
              <ion-input
                placeholder="输入日程标题"
                v-model="curScheduleData.title"
                :required="true"
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
                  <ion-label color="tertiary" class="font-size-mini">
                    {{ curScheduleData.startTs?.format("YYYY-MM-DD") }}
                  </ion-label>
                </div>
                <div>
                  <ion-label> >></ion-label>
                </div>
                <div class="ion-text-center">
                  <ion-label>End</ion-label>
                  <ion-label color="tertiary" class="font-size-mini">
                    {{ curScheduleData.endTs?.format("YYYY-MM-DD") }}
                  </ion-label>
                </div>
              </div>
            </ion-item>
            <ion-item ref="dtItem" class="height-0-block flex">
              <div ref="scheduleDT">
                <ion-buttons mode="ios" class="ion-justify-content-around">
                  <ion-button @click="btnScheduleDatetimeClearClk"
                    >Clear
                  </ion-button>
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
          <ion-list :inset="true">
            <ion-item lines="none">
              <ion-icon :icon="listOutline" slot="start"></ion-icon>
              <ion-label>Sub-task</ion-label>
              <span
                >{{
                  curScheduleData?.subTasks?.filter((t) => t.state === 1)
                    .length
                }}/{{ curScheduleData?.subTasks?.length }}</span
              >
            </ion-item>
            <ion-item lines="none">
              <ion-icon :icon="add" slot="start" style="width: 22px"></ion-icon>
              <ion-input
                v-model="addSubtaskInput"
                placeholder="Add a subtask"
                @ionChange="onSubtaskInputChange($event, undefined)"
              >
              </ion-input>
            </ion-item>
            <ion-item v-for="task in curScheduleData?.subTasks" :key="task">
              <ion-checkbox
                slot="start"
                @ionChange="onSubtaskCheckboxChange($event, task)"
              >
              </ion-checkbox>
              <ion-input
                :value="task.name"
                @ionChange="onSubtaskInputChange($event, task)"
                :class="{ 'text-line-through': task.state === 1 }"
              >
              </ion-input>
              <ion-icon
                :icon="removeCircleOutline"
                slot="end"
                @click="btnSubtaskRemoveClk($event, task)"
              >
              </ion-icon>
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
</template>
<script setup lang="ts">
import { ScheduleData, SubTask } from "@/type/UserData.vue";
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
  IonCheckbox,
} from "@ionic/vue";
import dayjs from "dayjs";
import {
  add,
  airplane,
  bookmark,
  calendar,
  colorPalette,
  listOutline,
  notifications,
  removeCircleOutline,
  power,
  repeat,
} from "ionicons/icons";
import { ref } from "vue";
const props = defineProps({
  modal: Object,
});
// 任务状态改变
const onTaskCheckboxChange = (event: any) => {
  curScheduleData.value.state = event.detail.checked ? 1 : 0;
};
// 日程类型切换
const onTypeChange = (event: any) => {
  console.log(event.detail.value);
};
// 日期类型切换，开始日期和结束日期
const onDtTabChange = (event: any) => {
  scheduleType.value = event.detail.value;
};
// 日期选择
const onDtChange = (event: any) => {
  const dt = dayjs(event.detail.value);
  if (scheduleType.value == 0) {
    curScheduleData.value.startTs = dt.startOf("day");
    curScheduleData.value.endTs = dt.startOf("day");
  } else if (scheduleType.value == 1) {
    curScheduleData.value.endTs = dt.startOf("day");
  }
};
// 提醒类型切换
const onReminderChange = (event: any) => {
  console.log("onReminderChange", event.detail);
};
// 重复类型切换
const onRepeatChange = (event: any) => {
  console.log("onRepeatChange", event.detail);
};
// 重复结束日期改变
const onRepeatEndDtChange = (event: any) => {
  curScheduleData.value.repeatEndTs = dayjs(event.detail.value);
};
// 子任务状态改变
const onSubtaskCheckboxChange = (event: any, task?: SubTask) => {
  if (task) {
    task.state = event.detail.checked ? 1 : 0;
  }
};
// 子任务名称改变
const onSubtaskInputChange = (event: any, task?: SubTask) => {
  // console.log("onSubtaskInputChange", event.detail.value, task);
  if (task) {
    if (event.detail.value) {
      task.name = event.detail.value;
    } else {
      // todo 移除
    }
  } else {
    if (event.detail.value) {
      curScheduleData.value.subTasks?.unshift({
        id: curScheduleData.value.subTasks.length,
        name: event.detail.value,
        state: 0,
      });
    }
    addSubtaskInput.value = "";
  }
};
// 开始结束日期按钮点击
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
// 开始结束日期按钮点击
const btnDatetimeOkClk = () => {
  btnScheduleDTClk();
};
// 重复结束日期选择确认点击
const btnRepeatEndOkClk = () => {
  repeatEndTs.value.$el.confirm();
  repeatEndTsModal.value.$el.dismiss();
};
// 重复结束日期点击清除
const btnRepeatEndClearClk = () => {
  repeatEndTs.value.$el.cancel();
  curScheduleData.value.repeatEndTs = undefined;
  repeatEndTsModal.value.$el.dismiss();
};
// 日程开始结束日期点击清除
const btnScheduleDatetimeClearClk = () => {
  curScheduleData.value.startTs = undefined;
  curScheduleData.value.endTs = undefined;
  btnScheduleDTClk();
};
// 子任务移除点击
const btnSubtaskRemoveClk = (event: any, task: SubTask) => {
  for (let i = 0; i < curScheduleData.value.subTasks?.length; i++) {
    if (curScheduleData.value.subTasks[i].id === task.id) {
      curScheduleData.value.subTasks.splice(i, 1);
      break;
    }
  }
};
// 保存按钮点击
const btnSaveClk = () => {
  console.log("btnSaveClk", curScheduleData.value);
  if (!curScheduleData.value.title) {
    toastData.value.text = "Title is empty";
    toastData.value.isOpen = true;
    return;
  }
  props.modal?.$el.dismiss(curScheduleData.value, "confirm");
};

const scheduleDT = ref();
const bShowScheduleDT = ref(false);
const repeatEndTs = ref();
const repeatEndTsModal = ref();
const dtItem = ref();
const scheduleType = ref(0); // 0:start 1:end
const addSubtaskInput = ref();
const toastData = ref({
  isOpen: false,
  duration: 3000,
  text: "",
});
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
  state: 0, // 任务状态
  startTs: dayjs().startOf("day"), // 开始时间
  endTs: dayjs().startOf("day"), // 结束时间
  reminder: 0, // 提醒类型
  repeat: 0, // 重复类型
  repeatEndTs: undefined, // 重复结束类型
  subTasks: [], // 子任务
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
