import { ReminderOptions, RepeatOptions } from "@/type/ScheduleType.vue";
import { ScheduleData, ScheduleSave, SubTask } from "@/type/UserData.vue";
import {
  createAnimation,
  IonCheckbox,
  IonDatetime,
  IonDatetimeButton,
  IonSegment,
  IonSegmentButton,
  IonSegmentContent,
  IonSegmentView,
  IonSelect,
  IonSelectOption,
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
  power,
  removeCircleOutline,
  repeat,
  timeOutline,
} from "ionicons/icons";
import { defineComponent, onMounted, ref } from "vue";

export default defineComponent({
  components: {
    createAnimation,
    IonCheckbox,
    IonDatetime,
    IonDatetimeButton,
    IonSegment,
    IonSegmentButton,
    IonSegmentContent,
    IonSegmentView,
    IonSelect,
    IonSelectOption,
  },
  props: {
    modal: Object,
    schedule: Object,
    save: Object,
  },
  emits: ["update:schedule", "update:save"],
  setup(props: any, ctx) {

    const curScheduleData = ref<ScheduleData>(new ScheduleData());
    const curSave = ref<ScheduleSave>(new ScheduleSave());
    const dtsShow = ref(false); // 开始时间选择器标记
    const scheduleTab = ref();

    onMounted(() => {
      if (props.schedule) {
        curScheduleData.value = props.schedule! as ScheduleData;
      }
      if (props.save) {
        curSave.value = props.save as ScheduleSave;
      }
      // task 排序
      curScheduleData.value?.subTasks.sort((a: SubTask, b: SubTask) => {
        const sa = curSave.value.subTasks[a.id] || 0;
        const sb = curSave.value.subTasks[b.id] || 0;
        if (sa === sb) {
          return a.id - b.id;
        }
        return sa - sb;
      });
    });

    // 任务状态改变
    const onTaskCheckboxChange = (event: any) => {
      curSave.value!.state = event.detail.checked ? 1 : 0;
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
      if (scheduleType.value === "0") {
        curScheduleData.value!.startTs = dt.startOf("day");
        curScheduleData.value!.endTs = dt.startOf("day");
        scheduleType.value = "1";
      } else if (scheduleType.value === "1") {
        curScheduleData.value!.endTs = dt.startOf("day");
      }
    };
    // 提醒类型切换
    const onReminderChange = (event: any) => {
      curScheduleData.value!.reminder = event.detail.value;
    };
    // 重复类型切换
    const onRepeatChange = (event: any) => {
      // console.log("onRepeatChange", event.detail);
      curScheduleData.value!.repeat = event.detail.value;
    };
    // 重复结束日期改变
    const onRepeatEndDtChange = (event: any) => {
      curScheduleData.value!.repeatEndTs = dayjs(event.detail.value);
    };
    // 子任务状态改变
    const onSubtaskCheckboxChange = (event: any, task?: SubTask) => {
      if (task) {
        curSave.value!.subTasks[task.id] = event.detail.checked ? 1 : 0;
      }
      // task 排序
      curScheduleData.value!.subTasks.sort((a: SubTask, b: SubTask) => {
        const sa = curSave.value!.subTasks[a.id] || 0;
        const sb = curSave.value!.subTasks[b.id] || 0;
        if (sa === sb) {
          return a.id - b.id;
        }
        return sa - sb;
      });
    };

    const subTaskChecked = (task: SubTask) => {
      return (curSave.value!.subTasks[task.id] || 0) === 1;
    };
    // 子任务名称改变
    const onSubtaskInputChange = (event: any, task?: SubTask) => {
      // console.log("onSubtaskInputChange", event.detail.value, task);
      if (task) {
        if (event.detail.value) {
          task.name = event.detail.value;
        } else {
          // 移除
          btnSubtaskRemoveClk(null, task);
        }
      } else {
        if (event.detail.value) {
          curScheduleData.value.subTasks?.unshift({
            id: curScheduleData.value.subTasks.length,
            name: event.detail.value,
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
        scheduleTab.value.$el.scrollToPoint(0, 130, 200);
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
      curScheduleData.value!.repeatEndTs = undefined;
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
      if (!curScheduleData.value.title) {
        toastData.value.text = "Title is empty";
        toastData.value.isOpen = true;
        return;
      }
      ctx.emit("update:schedule", curScheduleData.value);
      ctx.emit("update:save", curSave.value);
      props.modal?.$el.dismiss(curScheduleData.value, "confirm");
    };

    const scheduleDT = ref();
    const bShowScheduleDT = ref(false);
    const repeatEndTs = ref();
    const repeatEndTsModal = ref();
    const dtItem = ref();
    const scheduleType = ref("0"); // 0:start 1:end
    const addSubtaskInput = ref();
    const toastData = ref({
      isOpen: false,
      duration: 3000,
      text: "",
    });
    const repeatOptions = ref(RepeatOptions);
    const reminderOptions = ref(ReminderOptions);
    return {
      curScheduleData,
      scheduleDT,
      bShowScheduleDT,
      repeatEndTs,
      repeatEndTsModal,
      dtItem,
      scheduleType,
      addSubtaskInput,
      toastData,
      repeatOptions,
      reminderOptions,
      dayjs,
      add,
      airplane,
      bookmark,
      calendar,
      colorPalette,
      listOutline,
      notifications,
      power,
      removeCircleOutline,
      repeat,
      timeOutline,
      curSave,
      dtsShow,
      scheduleTab,
      onTaskCheckboxChange,
      onTypeChange,
      onDtTabChange,
      onDtChange,
      onReminderChange,
      onRepeatChange,
      onRepeatEndDtChange,
      onSubtaskCheckboxChange,
      subTaskChecked,
      onSubtaskInputChange,
      btnScheduleDTClk,
      btnDatetimeOkClk,
      btnRepeatEndOkClk,
      btnRepeatEndClearClk,
      btnScheduleDatetimeClearClk,
      btnSubtaskRemoveClk,
      btnSaveClk,
    };
  },
});
