import ColorSelector from "@/components/ColorSelector.vue";
import PrioritySelector from "@/components/PrioritySelector.vue";
import { getColorOptions, ReminderOptions, getPriorityOptions, RepeatOptions } from "@/modal/ScheduleType";
import { ScheduleData, ScheduleSave, SubTask } from "@/modal/UserData";
import icons from "@/modal/Icons";

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
  chevronBackOutline,
  repeat,
  timeOutline,
} from "ionicons/icons";
import { defineComponent, onMounted, ref, watch } from "vue";

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
    ColorSelector,
    PrioritySelector,
  },
  props: {
    modal: Object,
    schedule: Object,
    save: Object,
  },
  emits: ["update:schedule", "update:save"],
  setup(props: any, ctx) {
    // 当前日程
    const curScheduleData = ref<ScheduleData>(new ScheduleData());
    // 日程存档
    const curSave = ref<ScheduleSave>(new ScheduleSave());
    const dateShowFlag = ref(false); // 开始日期选择器显示标记
    const scheduleTab = ref(); // 日程tab
    const scheduleDTComponent = ref(); // 日期选择器组件
    const dtComponentItem = ref(); // 日期选择器容器
    const datetimeShowFlag = ref(false); // 开始时间选择器显示标记
    const scheduleStartTsComponent = ref(curScheduleData.value.startTs); // 开始时间选择器组件值
    const repeatEndTsComponent = ref(); // 重复结束日期选择器
    const repeatEndTsModal = ref(); // 重复结束日期选择器modal
    const scheduleType = ref("0"); // 日期类型 0:start 1:end
    const addSubtaskInput = ref(); // 新增子任务输入框
    // 提示框数据
    const toastData = ref({
      isOpen: false,
      duration: 3000,
      text: "",
    });
    const reminderOptions = ref(ReminderOptions); //  提醒选项

    const refreshUI = () => {
      // task 排序
      curScheduleData.value?.subTasks.sort((a: SubTask, b: SubTask) => {
        const sa = curSave.value.subTasks[a.id] || 0;
        const sb = curSave.value.subTasks[b.id] || 0;
        if (sa === sb) {
          return a.id - b.id;
        }
        return sa - sb;
      });
    };

    onMounted(() => {});
    watch(
      () => props.schedule,
      () => {
        if (props.schedule) curScheduleData.value = props.schedule! as ScheduleData;
        refreshUI();
      }
    );
    watch(
      () => props.save,
      () => {
        if (props.save) curSave.value = props.save as ScheduleSave;
        refreshUI();
      }
    );

    // 返回cancel
    const btnCancelClk = () => {
      props.modal?.$el.dismiss(curScheduleData.value, "cancel");
    };
    // ============ Tab1 ============
    // 任务状态改变
    const onTaskCheckboxChange = (event: any) => {
      curSave.value!.state = event.detail.checked ? 1 : 0;
    };
    // 日程类型切换
    const onTypeChange = (event: any) => {
      console.log(event.detail.value);
    };
    // 颜色选择
    const onColorChange = (nv: number) => {
      curScheduleData.value!.color = nv;
    };
    // 优先级选择
    const onPriorityChange = (nv: number) => {
      curScheduleData.value!.priority = nv;
    };
    // ============ Tab2 ============
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
        // scheduleType.value = "1";
      } else if (scheduleType.value === "1") {
        curScheduleData.value!.endTs = dt.startOf("day");
      }
    };
    // 开始-结束 日期按钮点击
    const btnScheduleDTClk = async () => {
      const hh = scheduleDTComponent.value.offsetHeight;
      const kf = [
        { offset: 0, height: hh + "px", top: "0" },
        { offset: 0.5, height: hh * 0.5 + "px", top: "0" },
        { offset: 1, height: "0", top: "0" },
      ];

      let animation = createAnimation().addElement(dtComponentItem.value.$el).duration(300).keyframes(kf).beforeStyles({
        "transform-origin": "top",
        overflow: "hidden",
        display: "block",
        position: "relative",
      });
      if (!dateShowFlag.value) {
        animation = animation.direction("reverse");
        scheduleTab.value.$el.scrollToPoint(0, 130, 200);
      }
      await animation.play();
      dateShowFlag.value = !dateShowFlag.value;
    };
    // 开始-结束日期按钮点击
    const btnDatetimeOkClk = () => {
      btnScheduleDTClk();
    };
    // 日程开始结束日期点击清除
    const btnScheduleDateClearClk = () => {
      curScheduleData.value.startTs = dayjs();
      curScheduleData.value.endTs = dayjs();
      btnScheduleDTClk();
    };
    // 日程开始时间选择器确认
    const btnScheduleDatetimeOkClk = () => {
      datetimeShowFlag.value = false;
      curScheduleData.value.startTs = scheduleStartTsComponent.value;
    };
    // 日程开始时间选择器AllDay切换
    const onScheduleDatetimeAllDayChange = (event: any) => {
      curScheduleData.value.allDay = event.detail.checked;
    };
    // ============ 提醒 ============
    // 提醒类型切换
    const onReminderChange = (event: any) => {
      curScheduleData.value!.reminder = event.detail.value;
    };
    // =========== 重复 ============
    // 重复类型切换
    const onRepeatChange = (event: any) => {
      curScheduleData.value!.repeat = event.detail.value;
    };
    // 重复结束日期改变
    const onRepeatEndDtChange = (event: any) => {
      curScheduleData.value!.repeatEndTs = dayjs(event.detail.value);
    };
    // 重复结束日期选择确认点击
    const btnRepeatEndOkClk = () => {
      repeatEndTsComponent.value.$el.confirm();
      repeatEndTsModal.value.$el.dismiss();
    };
    // 重复结束日期点击清除
    const btnRepeatEndClearClk = () => {
      repeatEndTsComponent.value.$el.cancel();
      curScheduleData.value!.repeatEndTs = undefined;
      repeatEndTsModal.value.$el.dismiss();
    };
    // ============ Tab3 ============
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

    // 子任务移除点击
    const btnSubtaskRemoveClk = (event: any, task: SubTask) => {
      for (let i = 0; i < curScheduleData.value.subTasks?.length; i++) {
        if (curScheduleData.value.subTasks[i].id === task.id) {
          curScheduleData.value.subTasks.splice(i, 1);
          break;
        }
      }
    };
    // ============ 保存 ============
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

    return {
      icons,
      curScheduleData,
      scheduleDTComponent,
      scheduleStartTsComponent,
      dateShowFlag,
      repeatEndTsComponent,
      repeatEndTsModal,
      chevronBackOutline,
      dtComponentItem,
      scheduleType,
      addSubtaskInput,
      toastData,
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
      datetimeShowFlag,
      scheduleTab,
      getColorOptions,
      getPriorityOptions,
      onTaskCheckboxChange,
      onTypeChange,
      onDtTabChange,
      onDtChange,
      onReminderChange,
      onPriorityChange,
      onRepeatChange,
      onRepeatEndDtChange,
      onSubtaskCheckboxChange,
      onColorChange,
      subTaskChecked,
      onSubtaskInputChange,
      btnScheduleDTClk,
      btnDatetimeOkClk,
      btnRepeatEndOkClk,
      btnRepeatEndClearClk,
      btnSubtaskRemoveClk,
      btnSaveClk,
      btnScheduleDateClearClk,
      btnScheduleDatetimeOkClk,
      onScheduleDatetimeAllDayChange,
      btnCancelClk,
      RepeatOptions,
    };
  },
});
