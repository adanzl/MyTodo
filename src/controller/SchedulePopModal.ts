import ColorSelector from "@/components/ColorSelector.vue";
import PrioritySelector from "@/components/PrioritySelector.vue";
import GroupSelector from "@/components/GroupSelector.vue";
import SubtaskPopModal from "@/components/SubtaskPopModal.vue";
import {
  getColorOptions,
  ReminderOptions,
  getPriorityOptions,
  RepeatOptions,
  getGroupOptions,
} from "@/modal/ScheduleType";
import { ScheduleData, ScheduleSave, Subtask } from "@/modal/UserData";
import { Icon } from "@iconify/vue";

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
import localizedFormat from "dayjs/plugin/localizedFormat";
import "dayjs/locale/zh-cn";
dayjs.extend(localizedFormat);
dayjs.locale("zh-cn");

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
    GroupSelector,
    SubtaskPopModal,
    Icon,
  },
  props: {
    modal: Object,
    schedule: {
      type: Object,
      default: new ScheduleData(),
    },
    save: {
      type: Object,
      default: new ScheduleSave(),
    },
  },
  emits: ["update:schedule", "update:save"],
  setup(props: any) {
    // 当前日程
    const curScheduleData = ref<ScheduleData>(ScheduleData.Copy(props.schedule));
    // 日程存档
    const curSave = ref<ScheduleSave>(ScheduleSave.Copy(props.save));
    const dateShowFlag = ref(false); // 开始日期选择器显示标记
    const scheduleTab = ref(); // 日程tab
    const scheduleDTComponent = ref(); // 日期选择器组件
    const dtComponentItem = ref(); // 日期选择器容器
    const datetimeShowFlag = ref(false); // 开始时间选择器显示标记
    const scheduleStartTsComponent = ref(curScheduleData.value.startTs); // 开始时间选择器组件值
    const repeatEndTsComponent = ref(); // 重复结束日期选择器
    const repeatEndTsModal = ref(); // 重复结束日期选择器modal
    const scheduleType = ref("0"); // 日期类型 0:start 1:end
    const openSubtaskModal = ref(false);
    const curSubtask = ref<any>();
    // 提示框数据
    const toastData = ref({
      isOpen: false,
      duration: 3000,
      text: "",
    });
    const reminderOptions = ref(ReminderOptions); //  提醒选项

    const refreshUI = () => {
      // console.log("refreshUI", curScheduleData.value, curSave.value, props);
      // task 排序
      curScheduleData.value?.subtasks.sort((a: Subtask, b: Subtask) => {
        const sa = curSave.value.subtasks[a.id] || 0;
        const sb = curSave.value.subtasks[b.id] || 0;
        if (sa === sb) {
          return a.id - b.id;
        }
        return sa - sb;
      });
    };

    onMounted(() => {
      watch(
        () => props.schedule,
        () => {
          if (props.schedule) {
            curScheduleData.value = ScheduleData.Copy(props.schedule);
          }
          refreshUI();
        }
      );
      watch(
        () => props.save,
        () => {
          if (props.save) curSave.value = ScheduleSave.Copy(props.save);
          refreshUI();
        }
      );
    });

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
    // 分组选择
    const onGroupChange = (nv: number) => {
      curScheduleData.value!.groupId = nv;
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

      let animation = createAnimation()
        .addElement(dtComponentItem.value.$el)
        .duration(300)
        .keyframes(kf)
        .beforeStyles({
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
    const onSubtaskCheckboxChange = (event: any, task?: Subtask) => {
      if (task) {
        curSave.value!.subtasks[task.id] = event.detail.checked ? 1 : 0;
      }
      // task 排序
      curScheduleData.value!.subtasks.sort((a: Subtask, b: Subtask) => {
        const sa = curSave.value!.subtasks[a.id] || 0;
        const sb = curSave.value!.subtasks[b.id] || 0;
        if (sa === sb) {
          return a.id - b.id;
        }
        return sa - sb;
      });
      // 如果所有子任务都完成了，整个任务变成完成状态
      const cnt = curScheduleData.value.subtasks?.filter((t: any) => subTaskChecked(t)).length;
      if (cnt === curScheduleData.value.subtasks?.length) {
        curSave.value!.state = 1;
        // onTaskCheckboxChange
      }
    };
    const subTaskChecked = (task: Subtask) => {
      return (curSave.value!.subtasks[task.id] || 0) === 1;
    };
    // 子任务更新
    const onSubtaskChange = (task: Subtask) => {
      console.log("onSubtaskChange", task);
      if (task.id === -1) {
        // 新建
        task.id = curScheduleData.value.subtasks.length;
        curScheduleData.value.subtasks?.unshift(task);
      } else {
        // 更新
        for (const subtask of curScheduleData.value.subtasks) {
          if (subtask.id === task.id) {
            subtask.name = task.name;
            subtask.imgIds = task.imgIds;
            break;
          }
        }
      }
    };

    // 子任务点击
    const onSubtaskClk = (_event: any, task: Subtask) => {
      curSubtask.value = task as Subtask;
      openSubtaskModal.value = true;
    };
    // 子任务添加点击
    const btnSubtaskAddClk = () => {
      curSubtask.value = null;
      openSubtaskModal.value = true;
    };
    // 子任务移除点击
    const btnSubtaskRemoveClk = (_event: any, task: Subtask) => {
      for (let i = 0; i < curScheduleData.value.subtasks?.length; i++) {
        if (curScheduleData.value.subtasks[i].id === task.id) {
          curScheduleData.value.subtasks.splice(i, 1);
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
      // ctx.emit("update:schedule", curScheduleData.value);
      // ctx.emit("update:save", curSave.value);
      props.modal?.$el.dismiss([curScheduleData.value, curSave.value], "confirm");
    };
    // 返回cancel
    const btnCancelClk = () => {
      // console.log("cancel", props.save, props.schedule);
      curScheduleData.value = ScheduleData.Copy(props.schedule);
      curSave.value = ScheduleSave.Copy(props.save);
      refreshUI();
      props.modal?.$el.dismiss([], "cancel");
    };

    return {
      openSubtaskModal,
      curSubtask,
      curScheduleData,
      scheduleDTComponent,
      scheduleStartTsComponent,
      dateShowFlag,
      repeatEndTsComponent,
      repeatEndTsModal,
      chevronBackOutline,
      dtComponentItem,
      scheduleType,
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
      getGroupOptions,
      getPriorityOptions,
      onTaskCheckboxChange,
      onTypeChange,
      onDtTabChange,
      onDtChange,
      onReminderChange,
      onPriorityChange,
      onGroupChange,
      onRepeatChange,
      onRepeatEndDtChange,
      onSubtaskCheckboxChange,
      onColorChange,
      subTaskChecked,
      onSubtaskChange,
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
      onSubtaskClk,
      btnSubtaskAddClk,
      RepeatOptions,
    };
  },
});
