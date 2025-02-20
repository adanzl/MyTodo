import CalenderTab from "@/components/CalendarTab.vue";
import FabButton from "@/components/FabButton.vue";
import SchedulePop from "@/components/SchedulePopModal.vue";
import { getColorOptions } from "@/modal/ColorType";
import { C_EVENT } from "@/modal/EventBus";
import IonIcons from "@/modal/IonIcons";
import { getGroupOptions, getPriorityOptions } from "@/modal/ScheduleType";
import {
  DayData,
  MonthData,
  S_TS,
  ScheduleData,
  ScheduleSave,
  UData,
  User,
  UserData,
} from "@/modal/UserData";
import { getSave, setSave } from "@/utils/NetUtil";
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
  IonMenuButton,
  IonRefresher,
  IonRefresherContent,
  IonReorder,
  IonReorderGroup,
  loadingController,
  onIonViewDidEnter,
} from "@ionic/vue";
import "@ionic/vue/css/ionic-swiper.css";
import dayjs from "dayjs";
import _ from "lodash";
import "swiper/css";
import "swiper/css/effect-fade";
import { Keyboard } from "swiper/modules";
import { Swiper, SwiperSlide } from "swiper/vue";
import { defineComponent, inject, nextTick, onMounted, ref } from "vue";
import MdiStar from "~icons/mdi/star";

export default defineComponent({
  components: {
    FabButton,
    MdiStar,
    IonAccordion,
    IonAccordionGroup,
    IonCheckbox,
    IonFab,
    IonFabButton,
    IonicSlides,
    IonReorderGroup,
    IonReorder,
    IonMenuButton,
    IonItemOption,
    IonItemOptions,
    IonItemSliding,
    IonRefresher,
    IonRefresherContent,
    CalenderTab,
    SchedulePop,
    Swiper,
    SwiperSlide,
  },
  emits: ["view:didEnter"],
  setup() {
    // https://yesicon.app/search/roman?coll=mdi
    const eventBus: any = inject("eventBus");
    const globalVar: any = inject("globalVar");
    let currentDate = dayjs().startOf("day"); // 当前日期
    let pTouch: any;
    let scheduleListScrollY = 0;
    let lstTs = 0;
    const refData = {
      userData: ref<UserData>(new UserData()),
      user: ref<User>(globalVar.user),
      slideArr: ref<any[]>([{}, {}, {}]), // 滑动数据
      bReorderDisabled: ref(true),
      curScheduleList: ref(),
      swiperRef: ref(), // 滑动对象
      bFold: ref(true), // 日历折叠状态
      selectedDate: ref<DayData>(), // 选中日期
      scheduleModal: ref(), // 弹窗对象
      scheduleModalData: ref<ScheduleData>(),
      scheduleSave: ref<ScheduleSave>(),
      isScheduleModalOpen: ref(false),
      filter: ref<any>({}),
      scheduleList: ref(),
      toastData: ref({
        isOpen: false,
        duration: 3000,
        text: "",
      }),
      //  删除日程确认框
      scheduleDelConfirm: ref<{
        isOpen: boolean;
        data: any;
        text: string;
      }>({
        isOpen: false,
        data: undefined,
        text: "",
      }),
    };

    // 初始化数据
    const updateScheduleData = () => {
      if (refData.bFold.value) {
        refData.slideArr.value = [
          UData.createWeekData(
            currentDate.subtract(1, "weeks"),
            refData.userData.value,
            refData.selectedDate
          ),
          UData.createWeekData(currentDate, refData.userData.value, refData.selectedDate),
          UData.createWeekData(
            currentDate.add(1, "weeks"),
            refData.userData.value,
            refData.selectedDate
          ),
        ];
      } else {
        refData.slideArr.value = [
          UData.createMonthData(
            currentDate.subtract(1, "months"),
            refData.userData.value,
            refData.selectedDate
          ),
          UData.createMonthData(currentDate, refData.userData.value, refData.selectedDate),
          UData.createMonthData(
            currentDate.add(1, "months"),
            refData.userData.value,
            refData.selectedDate
          ),
        ];
      }
      // console.log("updateScheduleData", currentDate, slideArr.value);
    };
    // 初始化日历
    // 处理选中日期
    const chooseSelectedDate = () => {
      const mm = refData.slideArr.value[1];
      if (!mm.weekArr) {
        console.warn("no weekArr");
        return;
      }
      refData.selectedDate.value = undefined; // 清空选中日期
      const now = dayjs().startOf("day");
      if (!refData.selectedDate.value) {
        // 选今天
        outer: for (const week of mm.weekArr) {
          for (const _dt of week) {
            if (_dt.dt.unix() == now.unix()) {
              refData.selectedDate.value = _dt;
              break outer;
            }
          }
        }
      }
      if (!refData.selectedDate.value) {
        // 选当前月的第一天
        outer: for (const week of mm.weekArr) {
          for (const _dt of week) {
            if (_dt.dt.unix() == currentDate.unix()) {
              refData.selectedDate.value = _dt;
              break outer;
            }
          }
        }
      }
      if (!refData.selectedDate.value) {
        // 选当周的第一天
        refData.selectedDate.value = mm.weekArr[0][0];
      }
    };

    const refreshAllData = async (id: number = 1) => {
      const loading = await loadingController.create({
        message: "Loading...",
      });
      loading.present();
      // 获取数据
      getSave(id)
        .then((uData: any) => {
          refData.userData.value = uData;
          // console.log("getSave", userData.value);
          globalVar.userData = uData;
          updateScheduleData();
          chooseSelectedDate();
          setTimeout(() => {
            refData.swiperRef?.value?.update();
          }, 100);
        })
        .catch((err) => {
          console.log("getSave", err);
          refData.toastData.value.isOpen = true;
          refData.toastData.value.text = JSON.stringify(err);
        })
        .finally(() => {
          loading.dismiss();
        });
    };
    eventBus.$on(C_EVENT.UPDATE_SAVE, (params: any) => {
      console.log("updateScheduleData", params);
      // refreshAllData(globalVar.scheduleListId);
      // TODO
    });
    onMounted(() => {
      console.log("onMounted page");
      // refreshAllData();
      onIonViewDidEnter(() => {
        console.log("onIonViewDidEnter");
        refreshAllData();
      });
      eventBus.$on(C_EVENT.MENU_CLOSE, (params: any) => {
        refData.filter.value = params;
      });
    });

    // 保存存档
    const doSaveUserData = () => {
      console.log("doSaveUserData", refData.userData.value);
      setSave(refData.userData.value.id, refData.userData.value.name, refData.userData.value)
        .then((res: any) => {
          console.log("doSaveUserData", res.statusText);
        })
        .catch((err) => {
          console.log("doSaveUserData", err);
        });
    };
    // ============ 工具栏 ============
    const toolbarMethod = {
      // 返回今天按钮
      btnTodayClk: () => {
        currentDate = dayjs().startOf("day");
        refData.selectedDate.value = new DayData(dayjs().startOf("day"));
        updateScheduleData();
      },
      // 排序按钮
      btnSortClk: () => {
        if (!refData.bFold.value) {
          calenderMethod.btnCalendarFoldClk();
        }
        setTimeout(() => {
          refData.bReorderDisabled.value = !refData.bReorderDisabled.value;
        }, 100);
      },
      // 左下测试按钮
      btnTestClk: () => {
        console.log(JSON.stringify(refData.userData.value));
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
      },
    };

    // ============ 日历 ============
    const calenderMethod = {
      // 滑动事件
      slideChange: (obj: any) => {
        updateScheduleData();
        obj.slideTo(1, 0, false);
        obj.update();
        chooseSelectedDate();
      },
      // 向右滑
      onSlideChangeNext: (obj: any) => {
        if (refData.bFold.value) {
          currentDate = currentDate.add(1, "weeks").startOf("week");
        } else {
          currentDate = currentDate.add(1, "months").startOf("month");
        }
        calenderMethod.slideChange(obj);
      },
      // 向左滑
      onSlideChangePre: (obj: any) => {
        if (refData.bFold.value) {
          currentDate = currentDate.subtract(1, "weeks").startOf("week");
        } else {
          currentDate = currentDate.subtract(1, "months").startOf("month");
        }
        calenderMethod.slideChange(obj);
      },
      // 获取swiper对象
      setSwiperInstance: (swiper: any) => {
        refData.swiperRef.value = swiper;
        swiper.slideTo(1, 0, false);
      },
      // 点击日历某个日期
      onDaySelected: (slide: MonthData, day: DayData) => {
        refData.selectedDate.value = day;
        // if (slide.month != day.dt.month()) {
        //   if (slide.year * 100 + slide.month < day.dt.year() * 100 + day.dt.month()) {
        //     refData.swiperRef.value.slideNext();
        //   } else {
        //     refData.swiperRef.value.slidePrev();
        //   }
        // }
        currentDate = day.dt.startOf("day");
        // console.log("onDaySelected", day);
      },
      // 日历折叠按钮
      btnCalendarFoldClk: (value?: boolean) => {
        const v = value ?? !refData.bFold.value;
        if (v === refData.bFold.value) return;
        refData.bFold.value = v;
        // console.log("btnCalendarFoldClk", refData.bFold.value);
        updateScheduleData();
        // refData.selectedDate.value.$forceUpdate();
        setTimeout(() => {
          refData.swiperRef.value.update();
        }, 100);
      },
    };
    // ========== 日程列表 ===========
    const scheduleListMethod = {
      onScheduleListScroll: (event: any) => {
        // console.log("onScheduleListScroll", event.detail.currentY);
        scheduleListScrollY = event.detail.currentY;
        // const ds = dayjs().valueOf() - lstTs;
        // if (ds < 300) {
        //   // 防止抖动
        //   return;
        // }
        // if (pTouch == null) {
        //   pTouch = event.detail.currentY;
        //   return;
        // }
        // const d = pTouch - event.detail.currentY;
        // if (Math.abs(d) > 20) {
        //   lstTs = dayjs().valueOf();
        //   if (d > 0 === refData.bFold.value) {
        //     calenderMethod.btnCalendarFoldClk();
        //   }
        //   pTouch = event.detail.currentY;
        // }
      },
      onScheduleListTouchStart: (event: any) => {
        // console.log("onScheduleListScrollStart", event);
        if (!refData.bReorderDisabled.value) {
          // 日程排序时禁用调整日历折叠状态
          return;
        }
        pTouch = event.touches[0];
      },
      onScheduleListTouchMove: async (event: any) => {
        if (!refData.bReorderDisabled.value) {
          // 日程排序时禁用调整日历折叠状态
          return;
        }
        const ds = dayjs().valueOf() - lstTs;
        if (ds < 300) {
          // 防止抖动
          return;
        }

        const d = event.touches[0].clientY - pTouch.clientY;
        // console.log("onTouchMove", d, event);
        if (Math.abs(d) > 10) {
          lstTs = dayjs().valueOf();
          if (d < 0) {
            calenderMethod.btnCalendarFoldClk(true);
          } else {
            if (scheduleListScrollY < 10) {
              calenderMethod.btnCalendarFoldClk(false);
            }
          }
        }
      },
      // 筛选日程
      bShowScheduleItem: (schedule: ScheduleData) => {
        const [fGroup, fColor, fPriority] = [
          refData.filter.value.group,
          refData.filter.value.color,
          refData.filter.value.priority,
        ];
        if (fGroup && fGroup.get(schedule.groupId) === false) return false;
        if (fColor && fColor.get(schedule.color) === false) return false;
        if (fPriority && fPriority.get(schedule.priority) === false) return false;
        return true;
      },
      // 计算完成任务数量
      countFinishedSubtask: (schedule: ScheduleData) => {
        try {
          return schedule?.subtasks?.filter(
            (t) =>
              ((refData.selectedDate.value?.save &&
                refData.selectedDate.value?.save[schedule.id]?.subtasks &&
                refData.selectedDate.value?.save[schedule.id]?.subtasks[t.id]) ||
                0) === 1
          ).length;
        } catch (error) {
          console.log("countFinishedSubtask", error);
          return 0;
        }
      },
      // 日程完成状态
      scheduleChecked: (scheduleId: number) => {
        return (
          refData.selectedDate.value!.save &&
          refData.selectedDate.value!.save[scheduleId]?.state === 1
        );
      },
      // 日程状态改变
      onScheduleCheckboxChange: (_event: any, day: DayData | undefined, schedule: ScheduleData) => {
        if (day) {
          const dKey = S_TS(day.dt);
          if (!day.save) {
            day.save = {};
          }
          const preSave = day.save[schedule.id] || new ScheduleSave();
          preSave.state = _event.detail.checked ? 1 : 0;
          UData.setScheduleSave(dKey, refData.userData.value as UserData, schedule, preSave);

          nextTick(() => {
            // schedule 排序 这玩意必须延后一帧，否则会导致checkbox状态错乱
            day.events.sort((a: ScheduleData, b: ScheduleData) => {
              return UData.CmpScheduleData(a, b, day.save);
            });
          });
          doSaveUserData();
        }
      },

      // 日程按钮点击
      btnScheduleClk: (event: any, schedule: ScheduleData) => {
        refData.isScheduleModalOpen.value = true;
        refData.scheduleModalData.value = schedule;
        refData.scheduleSave.value = refData.selectedDate.value?.save
          ? refData.selectedDate.value?.save[schedule.id]
          : undefined;
        // console.log("btnScheduleClk", schedule, scheduleSave.value);
      },
      // 日程专注按钮
      btnScheduleAlarmClk: () => {
        console.log("btnScheduleAlarmClk");
      },
      // 日程删除
      btnScheduleRemoveClk: (_event: any, schedule: ScheduleData) => {
        refData.scheduleDelConfirm.value.isOpen = true;
        refData.scheduleDelConfirm.value.data = schedule;
        refData.scheduleDelConfirm.value.text = "del " + schedule.title + "?";
      },
      onDelSchedulerConfirm: (event: any) => {
        // 处理数据
        refData.scheduleDelConfirm.value.isOpen = false;
        if (event.detail.role === "confirm") {
          const idx = refData.userData.value.schedules.findIndex(
            (s) => s.id === refData.scheduleDelConfirm.value.data.id
          );
          if (idx !== -1) {
            refData.userData.value.schedules.splice(idx, 1);
          }
          updateScheduleData();
          doSaveUserData();
        }
      },
      onReorder: (event: any) => {
        let eList = refData.selectedDate.value?.events.filter(scheduleListMethod.bShowScheduleItem);
        // console.log(_.map(eList, 'order'));
        eList = event.detail.complete(eList);
        // console.log(_.map(eList, 'order'));
        if (eList) {
          let ii = eList[0].order ?? 0;
          _.forEach(eList, (e) => {
            refData.userData.value.schedules[e.id].order = ii;
            e.order = ii++;
          });
        }
        // console.log(_.map(refData.selectedDate.value?.events, "order"));
        refData.selectedDate.value?.events.sort((a: ScheduleData, b: ScheduleData) => {
          return UData.CmpScheduleData(a, b, refData.selectedDate.value?.save);
        });
        // console.log(_.map(refData.selectedDate.value?.events, "order"));
        doSaveUserData();
        // console.log(eList);
      },
      // 总奖励
      countAllReward: (schedule: ScheduleData) => {
        return UData.CountScheduleReward(schedule);
      },
    };
    // ========== 日程弹窗 ===========
    const scheduleModalMethods = {
      // 添加日程按钮
      btnAddScheduleClk: async () => {
        // 清空数据
        refData.scheduleModalData.value = undefined;
        refData.scheduleSave.value = undefined;
        refData.isScheduleModalOpen.value = true;
      },
      // 添加日程页面关闭回调
      onScheduleModalDismiss: (event: any) => {
        refData.isScheduleModalOpen.value = false;
        if (event.detail.role === "backdrop") return;
        const [_scheduleData, _scheduleSave] = event.detail.data;
        // console.log("onScheduleModalDismiss", _scheduleData, _scheduleSave, userData.value);
        const dt = refData.selectedDate.value!.dt!;
        const r = UData.updateSchedularData(
          refData.userData.value,
          _scheduleData,
          _scheduleSave,
          dt,
          event.detail.role
        );
        if (r) {
          updateScheduleData();
          doSaveUserData();
        }
      },
    };

    return {
      getColorOptions,
      getPriorityOptions,
      getGroupOptions,
      IonicSlides,
      Keyboard,
      ...IonIcons,
      ...refData,
      ...toolbarMethod,
      ...calenderMethod,
      ...scheduleListMethod,
      ...scheduleModalMethods,
    };
  },
});
