import CalenderTab from "@/components/CalendarTab.vue";
import SchedulePop from "@/components/SchedulePopModal.vue";
import icons from "@/modal/Icons";
import { LocalNotifications } from "@capacitor/local-notifications";
import "@ionic/vue/css/ionic-swiper.css";
import "swiper/css";
import "swiper/css/effect-fade";

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
  IonRefresher,
  IonRefresherContent,
  loadingController,
  onIonViewDidEnter,
} from "@ionic/vue";
import dayjs from "dayjs";
import {
  addCircleOutline,
  alarmOutline,
  chevronDown,
  chevronUp,
  ellipseOutline,
  list,
  listOutline,
  swapVertical,
  trashOutline,
} from "ionicons/icons";
import { Keyboard } from "swiper/modules";
import { Swiper, SwiperSlide } from "swiper/vue";
import { defineComponent, nextTick, onMounted, ref } from "vue";

import {
  ColorOptions,
  getColorOptions,
  getGroupOptions,
  getPriorityOptions,
} from "@/modal/ScheduleType";
import { DayData, MonthData, ScheduleData, ScheduleSave, UData, UserData } from "@/modal/UserData";
import { getSave, setSave } from "@/utils/NetUtil";
import { Icon } from "@iconify/vue";
import "@ionic/vue/css/ionic-swiper.css";
import "swiper/css";
import "swiper/css/effect-fade";

export default defineComponent({
  components: {
    IonAccordion,
    IonAccordionGroup,
    IonCheckbox,
    IonFab,
    IonFabButton,
    IonicSlides,
    IonItemOption,
    IonItemOptions,
    IonItemSliding,
    IonRefresher,
    IonRefresherContent,
    CalenderTab,
    SchedulePop,
    Swiper,
    SwiperSlide,
    Icon,
  },
  emits: ["view:didEnter"],
  setup() {
    // https://iconify.design/docs/icon-components/vue/
    // https://yesicon.app/search/roman?coll=mdi
    const userData = ref<UserData>(new UserData());
    let currentDate = dayjs().startOf("day");
    let pTouch: any;
    let lstTs = 0;
    const slideArr = ref<any[]>([{}, {}, {}]); // 滑动数据
    const curScheduleList = ref();
    const swiperRef = ref(); // 滑动对象
    const bFold = ref(true); // 日历折叠状态
    const selectedDate = ref<DayData>(); // 选中日期
    const scheduleModal = ref(); // 弹窗对象
    const scheduleModalData = ref<ScheduleData>();
    const scheduleSave = ref<ScheduleSave>();
    const isScheduleModalOpen = ref(false);
    const toastData = ref({
      isOpen: false,
      duration: 3000,
      text: "",
    });
    //  删除日程确认框
    const scheduleDelConfirm = ref<{
      isOpen: boolean;
      data: any;
      text: string;
    }>({
      isOpen: false,
      data: undefined,
      text: "",
    });
    const alertButtons = [
      {
        text: "Cancel",
        role: "cancel",
      },
      {
        text: "OK",
        role: "confirm",
      },
    ];

    // 初始化数据
    const updateScheduleData = () => {
      if (bFold.value) {
        slideArr.value = [
          UData.createWeekData(currentDate.subtract(1, "weeks"), userData.value, selectedDate),
          UData.createWeekData(currentDate, userData.value, selectedDate),
          UData.createWeekData(currentDate.add(1, "weeks"), userData.value, selectedDate),
        ];
      } else {
        slideArr.value = [
          UData.createMonthData(currentDate.subtract(1, "months"), userData.value, selectedDate),
          UData.createMonthData(currentDate, userData.value, selectedDate),
          UData.createMonthData(currentDate.add(1, "months"), userData.value, selectedDate),
        ];
      }
      // console.log("updateScheduleData", currentDate, slideArr.value);
    };
    //  初始化日历
    // 处理选中日期
    const chooseSelectedDate = () => {
      const mm = slideArr.value[1];
      if (!mm.weekArr) {
        console.warn("no weekArr");
        return;
      }
      selectedDate.value = undefined; // 清空选中日期
      const now = dayjs().startOf("day");
      if (!selectedDate.value) {
        // 选今天
        outer: for (const week of mm.weekArr) {
          for (const _dt of week) {
            if (_dt.dt.unix() == now.unix()) {
              selectedDate.value = _dt;
              break outer;
            }
          }
        }
      }
      if (!selectedDate.value) {
        // 选当前月的第一天
        outer: for (const week of mm.weekArr) {
          for (const _dt of week) {
            if (_dt.dt.unix() == currentDate.unix()) {
              selectedDate.value = _dt;
              break outer;
            }
          }
        }
      }
      if (!selectedDate.value) {
        // 选当周的第一天
        selectedDate.value = mm.weekArr[0][0];
      }
    };

    const refreshAllData = async () => {
      const loading = await loadingController.create({
        message: "Loading...",
      });
      loading.present();
      // 获取数据
      getSave(1)
        .then((res: any) => {
          userData.value = UData.parseUserData(res);
          // console.log("getSave", userData.value);
          updateScheduleData();
          chooseSelectedDate();
          setTimeout(() => {
            swiperRef?.value?.update();
          }, 100);
        })
        .catch((err) => {
          console.log("getSave", err);
          toastData.value.isOpen = true;
          toastData.value.text = JSON.stringify(err);
        })
        .finally(() => {
          loading.dismiss();
        });
    };

    onMounted(() => {
      refreshAllData();
      onIonViewDidEnter(() => {
        refreshAllData();
      });
    });
    // 保存存档
    const doSaveUserData = () => {
      setSave(userData.value.id, userData.value.name, JSON.stringify(userData.value))
        .then((res) => {
          console.log("doSaveUserData", res);
        })
        .catch((err) => {
          console.log("doSaveUserData", err);
        });
    };
    // 返回今天按钮
    const btnTodayClk = () => {
      currentDate = dayjs().startOf("day");
      selectedDate.value = new DayData(dayjs().startOf("day"));
      updateScheduleData();
    };
    // 排序按钮
    const btnSortClk = () => {
      swiperRef?.value?.update();
    };
    // 左下测试按钮
    const btnTestClk = () => {
      console.log(JSON.stringify(userData.value));
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
    };

    // ============ 日历开始 ============
    const slideChange = (obj: any) => {
      updateScheduleData();
      obj.slideTo(1, 0, false);
      obj.update();
      chooseSelectedDate();
    };
    // 向右滑
    const onSlideChangeNext = (obj: any) => {
      if (bFold.value) {
        currentDate = currentDate.add(1, "weeks").startOf("week");
      } else {
        currentDate = currentDate.add(1, "months").startOf("month");
      }
      slideChange(obj);
    };
    // 向左滑
    const onSlideChangePre = (obj: any) => {
      if (bFold.value) {
        currentDate = currentDate.subtract(1, "weeks").startOf("week");
      } else {
        currentDate = currentDate.subtract(1, "months").startOf("month");
      }
      slideChange(obj);
    };
    // 获取swiper对象
    const setSwiperInstance = (swiper: any) => {
      swiperRef.value = swiper;
      swiper.slideTo(1, 0, false);
    };
    // 点击日历某个日期
    const onDaySelected = (slide: MonthData, day: DayData) => {
      if (slide.month != day.dt.month()) {
        if (slide.year * 100 + slide.month < day.dt.year() * 100 + day.dt.month()) {
          swiperRef.value.slideNext();
        } else {
          swiperRef.value.slidePrev();
        }
      }
      selectedDate.value = day;
    };
    // 日历折叠按钮
    const btnCalendarFoldClk = () => {
      bFold.value = !bFold.value;
      updateScheduleData();
      setTimeout(() => {
        swiperRef.value.update();
      }, 100);
    };
    // ============ 日历结束 ============
    // ========== 日程列表开始 ===========
    const onScheduleListTouchStart = (event: any) => {
      // console.log("onTouchStart", bMoving, event);
      pTouch = event.touches[0];
    };
    const onScheduleListTouchMove = (event: any) => {
      // console.log("onTouchMove", bMoving, event);
      const ds = dayjs().valueOf() - lstTs;
      if (ds < 300) {
        return;
      }
      const d = event.touches[0].clientY - pTouch.clientY;
      if (Math.abs(d) > 20) {
        lstTs = dayjs().valueOf();
        if (d > 0 === bFold.value) {
          btnCalendarFoldClk();
        }
      }
    };
    // 刷新页面事件
    const handleRefresh = async (event: any) => {
      // console.log("handleRefresh", event);
      await refreshAllData();
      event.target.complete();
    };
    // 计算完成任务数量
    const countFinishedSubtask = (schedule: ScheduleData) => {
      try {
        return schedule?.subtasks?.filter(
          (t) =>
            ((selectedDate.value?.save[schedule.id]?.subtasks &&
              selectedDate.value?.save[schedule.id]?.subtasks[t.id]) ||
              0) === 1
        ).length;
      } catch (error) {
        console.log("countFinishedSubtask", error);
        return 0;
      }
    };
    // 日程完成状态
    const scheduleChecked = (scheduleId: number) => {
      return selectedDate.value!.save[scheduleId]?.state === 1;
    };
    // 日程状态改变
    const onScheduleCheckboxChange = (
      _event: any,
      day: DayData | undefined,
      scheduleId: number
    ) => {
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
      }
    };

    // 日程按钮点击
    const btnScheduleClk = (event: any, schedule: ScheduleData) => {
      isScheduleModalOpen.value = true;
      scheduleModalData.value = schedule;
      scheduleSave.value = selectedDate.value?.save[schedule.id];
      event.stopPropagation();
      // console.log("btnScheduleClk", schedule, scheduleSave.value);
    };
    // 日程专注按钮
    const btnScheduleAlarmClk = () => {
      console.log("btnScheduleAlarmClk");
    };
    // 日程删除
    const btnScheduleRemoveClk = (event: any, schedule: ScheduleData) => {
      scheduleDelConfirm.value.isOpen = true;
      scheduleDelConfirm.value.data = schedule;
      scheduleDelConfirm.value.text = "del " + schedule.title + "?";
    };
    const onDelSchedulerConfirm = (event: any) => {
      // 处理数据
      scheduleDelConfirm.value.isOpen = false;
      if (event.detail.role === "confirm") {
        const idx = userData.value.schedules.findIndex(
          (s) => s.id === scheduleDelConfirm.value.data.id
        );
        if (idx !== -1) {
          userData.value.schedules.splice(idx, 1);
        }
        updateScheduleData();
        doSaveUserData();
      }
    };
    // ========== 日程列表结束 ===========
    // ========== 日程弹窗开始 ===========
    // 添加日程按钮
    const btnAddScheduleClk = () => {
      // 清空数据
      scheduleModalData.value = undefined;
      scheduleSave.value = undefined;
      isScheduleModalOpen.value = true;
    };
    // 添加日程页面关闭回调
    const onScheduleModalDismiss = (event: any) => {
      isScheduleModalOpen.value = false;
      if (event.detail.role === "backdrop") return;
      const [_scheduleData, _scheduleSave] = event.detail.data;
      const dt = selectedDate.value!.dt!;
      const r = UData.updateSchedularData(
        userData.value,
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

    // ========== 日程弹窗结束 ===========
    return {
      icons,
      ColorOptions,
      getColorOptions,
      getPriorityOptions,
      getGroupOptions,
      addCircleOutline,
      alarmOutline,
      chevronDown,
      chevronUp,
      ellipseOutline,
      list,
      listOutline,
      swapVertical,
      trashOutline,
      slideArr,
      curScheduleList,
      swiperRef,
      bFold,
      selectedDate,
      scheduleModal,
      scheduleModalData,
      scheduleSave,
      isScheduleModalOpen,
      toastData,
      userData,
      currentDate,
      pTouch,
      lstTs,
      alertButtons,
      scheduleDelConfirm,
      countFinishedSubtask,
      IonicSlides,
      updateScheduleData,
      Keyboard,
      btnTodayClk,
      btnSortClk,
      onSlideChangeNext,
      onSlideChangePre,
      setSwiperInstance,
      onDaySelected,
      btnCalendarFoldClk,
      onScheduleListTouchStart,
      onScheduleListTouchMove,
      handleRefresh,
      scheduleChecked,
      onScheduleCheckboxChange,
      btnScheduleClk,
      btnScheduleAlarmClk,
      btnScheduleRemoveClk,
      onScheduleModalDismiss,
      onDelSchedulerConfirm,
      btnAddScheduleClk,
      btnTestClk,
    };
  },
  methods: {},
});
