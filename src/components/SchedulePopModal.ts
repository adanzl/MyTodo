import ColorSelector from "@/components/ColorSelector.vue";
import GroupSelector from "@/components/GroupSelector.vue";
import PrioritySelector from "@/components/PrioritySelector.vue";
import RepeatSelector from "@/components/RepeatSelector.vue";
import SubtaskPopModal from "@/components/SubtaskPopModal.vue";
import { getColorOptions } from "@/modal/ColorType";
import IonIcons from "@/modal/IonIcons";
import {
  buildCustomRepeatLabel,
  CUSTOM_REPEAT_ID,
  getGroupOptions,
  getNextRepeatDate,
  getPriorityOptions,
  getRepeatOptions,
  ReminderOptions,
  WEEK,
} from "@/modal/ScheduleType";
import { ScheduleData, ScheduleSave, Subtask, UData } from "@/modal/UserData";
import { getImage } from "@/utils/ImgMgr";
import {
  alertController,
  createAnimation,
  IonActionSheet,
  IonCheckbox,
  IonDatetime,
  IonReorder,
  IonReorderGroup,
  IonSegment,
  IonSegmentButton,
  IonSegmentContent,
  IonSegmentView,
  IonSelect,
  IonSelectOption,
} from "@ionic/vue";
import dayjs from "dayjs";
import _ from "lodash";
import { defineComponent, inject, nextTick, onMounted, ref, watch } from "vue";
import MdiChevronDoubleRight from "~icons/mdi/chevron-double-right";
import MdiGiftOutline from "~icons/mdi/gift-outline";
import MdiStar from "~icons/mdi/star";

export default defineComponent({
  components: {
    MdiStar,
    MdiGiftOutline,
    MdiChevronDoubleRight,
    IonCheckbox,
    IonDatetime,
    IonSegment,
    IonSegmentButton,
    IonSegmentContent,
    IonSegmentView,
    IonSelect,
    IonSelectOption,
    ColorSelector,
    PrioritySelector,
    GroupSelector,
    RepeatSelector,
    SubtaskPopModal,
    IonActionSheet,
    IonReorder,
    IonReorderGroup,
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
    const refData = {
      // 当前日程
      curScheduleData: ref<ScheduleData>(ScheduleData.Copy(props.schedule)),
      // 日程存档
      curSave: ref<ScheduleSave>(ScheduleSave.Copy(props.save)),
      dateShowFlag: ref(false), // 开始日期选择器显示标记
      scheduleTab: ref(), // 日程tab
      scheduleDTComponent: ref(), // 日期选择器组件
      dtComponentItem: ref(), // 日期选择器容器
      datetimeShowFlag: ref(false), // 开始时间选择器显示标记
      scheduleStartTsComponent: ref(props.schedule.startTs), // 开始时间选择器组件值
      repeatEndTsComponent: ref(), // 重复结束日期选择器
      repeatEndTsModal: ref(), // 重复结束日期选择器modal
      scheduleType: ref("0"), // 日期类型 0:start 1:end
      // =========== 子任务 ============
      bReorderDisabled: ref(true),
      openSubtaskModal: ref(false),
      curSubtask: ref<any>(),
      imgs: ref<Record<number, string>>({}),
      // =========== modal ============
      // 保存面板显示标记
      openSaveSheet: ref(false), // 保存面板显示标记
      // 提示框数据
      toastData: ref({
        isOpen: false,
        duration: 3000,
        text: "",
      }),
    };
    const reminderOptions = ref(ReminderOptions); //  提醒选项
    let changeFlag = false; // 改变标记 日程中可覆盖的值被修改的标记

    const refreshUI = () => {
      // console.log("refreshUI", curScheduleData.value, curSave.value, props);
      // task 排序
      refData.curScheduleData.value?.subtasks.sort((a: Subtask, b: Subtask) => {
        return UData.CmpScheduleSubtasks(a, b, refData.curSave.value);
      });
      refData.imgs.value = {};
      refData.curScheduleData.value?.subtasks.forEach((subtask) => {
        subtask.imgIds?.forEach((imgId) => {
          getImage(imgId).then((img) => {
            refData.imgs.value[imgId] = img;
          });
        });
      });
    };

    onMounted(() => {
      watch(
        () => props.schedule,
        () => {
          if (props.schedule) {
            refData.curScheduleData.value = ScheduleData.Copy(props.schedule);
          }
          refreshUI();
        }
      );
      watch(
        () => props.save,
        () => {
          if (props.save) refData.curSave.value = ScheduleSave.Copy(props.save);
          refreshUI();
        }
      );
    });

    // ============ Tab1 ============
    const tab1Method = {
      // 任务标题
      onTitleChange: (event: any) => {
        refData.curScheduleData.value!.title = event.detail.value;
        changeFlag = true;
      },
      // 任务状态改变
      onTaskCheckboxChange: (event: any) => {
        refData.curSave.value!.state = event.detail.checked ? 1 : 0;
        if (event.detail.checked) {
          _.forEach(refData.curScheduleData.value.subtasks, (subtask) => {
            refData.curSave.value!.subtasks[subtask.id] = 1;
          });
        }
      },
      // 颜色选择
      onColorChange: (nv: number) => {
        refData.curScheduleData.value!.color = nv;
        changeFlag = true;
      },
      // 优先级选择
      onPriorityChange: (nv: number) => {
        refData.curScheduleData.value!.priority = nv;
        changeFlag = true;
      },
      // 分组选择
      onGroupChange: (nv: number) => {
        refData.curScheduleData.value!.groupId = nv;
        changeFlag = true;
      },
    };
    // ============ Tab2 ============
    const tab2Method = {
      // 日期类型切换，开始日期和结束日期
      onDtTabChange: (event: any) => {
        refData.scheduleType.value = event.detail.value;
      },
      // 日期选择
      onDtChange: (event: any) => {
        const dt = dayjs(event.detail.value);
        if (refData.scheduleType.value === "0") {
          refData.curScheduleData.value!.startTs = dt.startOf("day");
          refData.curScheduleData.value!.endTs = dt.startOf("day");
          // scheduleType.value = "1";
        } else if (refData.scheduleType.value === "1") {
          refData.curScheduleData.value!.endTs = dt.startOf("day");
        }
      },
      // 开始-结束 日期按钮点击
      btnScheduleDTClk: async () => {
        const hh = refData.scheduleDTComponent.value.offsetHeight;
        const kf = [
          { offset: 0, height: hh + "px", top: "0" },
          { offset: 0.5, height: hh * 0.5 + "px", top: "0" },
          { offset: 1, height: "0", top: "0" },
        ];

        let animation = createAnimation()
          .addElement(refData.dtComponentItem.value.$el)
          .duration(300)
          .keyframes(kf)
          .beforeStyles({
            "transform-origin": "top",
            overflow: "hidden",
            display: "block",
            position: "relative",
          });
        if (!refData.dateShowFlag.value) {
          animation = animation.direction("reverse");
          refData.scheduleTab.value.$el.scrollToPoint(0, 130, 200);
        }
        await animation.play();
        refData.dateShowFlag.value = !refData.dateShowFlag.value;
      },
      // 开始-结束日期按钮点击
      btnDatetimeOkClk: () => {
        tab2Method.btnScheduleDTClk();
      },
      // 日程开始结束日期点击清除
      btnScheduleDateClearClk: () => {
        refData.curScheduleData.value.startTs = dayjs();
        refData.curScheduleData.value.endTs = dayjs();
        tab2Method.btnScheduleDTClk();
      },
      // 日程开始时间选择器确认
      btnScheduleDatetimeOkClk: () => {
        refData.datetimeShowFlag.value = false;
        refData.curScheduleData.value.startTs = refData.scheduleStartTsComponent.value;
      },
      // 日程开始时间选择器AllDay切换
      onScheduleDatetimeAllDayChange: (event: any) => {
        refData.curScheduleData.value.allDay = event.detail.checked;
      },
      // ============ 提醒 ============
      // 提醒类型切换
      onReminderChange: (event: any) => {
        refData.curScheduleData.value!.reminder = event.detail.value;
      },
      // =========== 重复 ============
      // 重复类型切换
      onRepeatChange: (v0: any, v1: any) => {
        refData.curScheduleData.value!.repeat = v0;
        refData.curScheduleData.value!.repeatData = v1;
      },
      // 重复结束日期改变
      onRepeatEndDtChange: (event: any) => {
        refData.curScheduleData.value!.repeatEndTs = dayjs(event.detail.value);
      },
      // 重复结束日期选择确认点击
      btnRepeatEndOkClk: () => {
        refData.repeatEndTsComponent.value.$el.confirm();
        refData.repeatEndTsModal.value.$el.dismiss();
      },
      // 重复结束日期点击清除
      btnRepeatEndClearClk: () => {
        refData.repeatEndTsComponent.value.$el.cancel();
        refData.curScheduleData.value!.repeatEndTs = undefined;
        refData.repeatEndTsModal.value.$el.dismiss();
      },
      // 总奖励
      countAllReward: () => {
        return UData.CountScheduleReward(refData.curScheduleData.value);
      },
    };
    // ============ Tab3 ============
    const tab3Method = {
      btnSortClk: () => {
        refData.bReorderDisabled.value = !refData.bReorderDisabled.value;
      },
      // 子任务排序改变
      onReorder: (event: any, curScheduleData: any) => {
        let eList = curScheduleData.subtasks;
        eList = event.detail.complete(eList);
        if (eList) {
          let ii = eList[0].order ?? 0;
          _.forEach(eList, (v) => {
            v.order = ii;
            ii++;
          });
        }
        eList.sort((a: Subtask, b: Subtask) => {
          return UData.CmpScheduleSubtasks(a, b, refData.curSave.value);
        });
      },
      // 子任务状态改变
      onSubtaskCheckboxChange: (event: any, task?: Subtask) => {
        if (task) {
          refData.curSave.value!.subtasks[task.id] = event.detail.checked ? 1 : 0;
        }
        // console.log("onSubtaskCheckboxChange", curSave.value, task);
        // task 排序
        nextTick(() => {
          refData.curScheduleData.value!.subtasks.sort((a: Subtask, b: Subtask) => {
            return UData.CmpScheduleSubtasks(a, b, refData.curSave.value);
          });
        });
        // 如果所有子任务都完成了，整个任务变成完成状态
        const cnt = refData.curScheduleData.value.subtasks?.filter((t: any) =>
          tab3Method.subTaskChecked(t)
        ).length;
        if (cnt === refData.curScheduleData.value.subtasks?.length) {
          refData.curSave.value!.state = 1;
        }
      },
      subTaskChecked: (task: Subtask) => {
        // console.log("subTaskChecked", task, (curSave.value!.subtasks[task.id] || 0) === 1);
        return (refData.curSave.value!.subtasks[task.id] || 0) === 1;
      },
      // 子任务更新
      onSubtaskChange: (task: Subtask) => {
        console.log("onSubtaskChange", task);
        if (task.id === -1) {
          // 新建
          task.id = refData.curScheduleData.value.subtasks.length;
          refData.curScheduleData.value.subtasks?.unshift(task);
        } else {
          // 更新
          for (const subtask of refData.curScheduleData.value.subtasks) {
            if (subtask.id === task.id) {
              subtask.name = task.name;
              task.imgIds?.forEach(async (imgId) => {
                refData.imgs.value[imgId] = await getImage(imgId);
              });
              subtask.imgIds = task.imgIds;
              break;
            }
          }
        }
        changeFlag = true;
      },
      onSubtaskPopDismiss: () => {
        console.log("subtask pop willDismiss", refData.curSubtask.value);
        refData.curSubtask.value = new Subtask();
        refData.openSubtaskModal.value = false;
      },
      // 子任务点击
      onSubtaskClk: (_event: any, task: Subtask) => {
        refData.curSubtask.value = task as Subtask;
        refData.openSubtaskModal.value = true;
      },
      // 子任务添加点击
      btnSubtaskAddClk: () => {
        refData.curSubtask.value = new Subtask();
        refData.openSubtaskModal.value = true;
      },
      // 子任务移除点击
      btnSubtaskRemoveClk: async (_event: any, task: Subtask) => {
        const alert = await alertController.create({
          header: "确认",
          message: "确认删除 ： " + task.name,
          buttons: [
            "取消",
            {
              text: "确定",
              handler: () => {
                for (let i = 0; i < refData.curScheduleData.value.subtasks?.length; i++) {
                  if (refData.curScheduleData.value.subtasks[i].id === task.id) {
                    refData.curScheduleData.value.subtasks.splice(i, 1);
                    break;
                  }
                }
                changeFlag = true;
              },
            },
          ],
        });
        await alert.present();
      },
    };
    // ============ 保存 ============
    const saveActionButtons = [
      {
        text: "保存当前日程",
        handler: () => {
          props.modal?.$el.dismiss([refData.curScheduleData.value, refData.curSave.value], "cur");
          refData.openSaveSheet.value = false;
        },
      },
      {
        text: "保存所有日程",
        handler: () => {
          props.modal?.$el.dismiss([refData.curScheduleData.value, refData.curSave.value], "all");
          refData.openSaveSheet.value = false;
        },
      },
      {
        text: "取消",
        role: "cancel",
        handler: () => {
          refData.openSaveSheet.value = false;
        },
      },
    ];
    // ============ UI ============
    const uiMethod = {
      // 保存按钮点击
      btnSaveClk: () => {
        if (!refData.curScheduleData.value.title) {
          refData.toastData.value.text = "Title is empty";
          refData.toastData.value.isOpen = true;
          return;
        }
        if (changeFlag && refData.curScheduleData.value.id !== -1) {
          refData.openSaveSheet.value = true;
        } else {
          props.modal?.$el.dismiss([refData.curScheduleData.value, refData.curSave.value], "all");
        }
      },
      // 返回按钮
      btnBackClk: () => {
        // console.log("cancel", props.save, props.schedule);
        refData.curScheduleData.value = ScheduleData.Copy(props.schedule);
        refData.curSave.value = ScheduleSave.Copy(props.save);
        refData.openSaveSheet.value = false;
        changeFlag = false;
        refreshUI();
        props.modal?.$el.dismiss([], "cancel");
      },
      onToastDismiss: () => (refData.toastData.value.isOpen = false),
      onModalDismiss: () => {
        refData.scheduleDTComponent.value.style.height =
          refData.scheduleDTComponent.value.offsetHeight;
        refData.dateShowFlag.value = false;
        refData.bReorderDisabled.value = true;
      },
    };
    return {
      saveActionButtons,
      reminderOptions,
      dayjs,
      getColorOptions,
      getGroupOptions,
      getPriorityOptions,
      getRepeatOptions,
      getNextRepeatDate,
      buildCustomRepeatLabel,
      CUSTOM_REPEAT_ID,
      WEEK,
      ...refData,
      ...IonIcons,
      ...tab1Method,
      ...tab2Method,
      ...tab3Method,
      ...uiMethod,
    };
  },
  data() {
    return {
      globalVar: inject("globalVar") as any,
    };
  },
  methods: {
    // 奖励
    async btnRewardClk() {
      if (this.globalVar!.user?.admin !== 1) return;
      const alert = await alertController.create({
        header: "日程奖励",
        inputs: [{ type: "number", value: this.curScheduleData.score, placeholder: "奖励积分" }],
        buttons: [
          {
            text: "取消",
            role: "cancel",
          },
          {
            text: "确定",
            handler: (e) => {
              this.curScheduleData.score = parseInt(e[0]);
            },
          },
        ],
      });
      await alert.present();
    },
  },
});
