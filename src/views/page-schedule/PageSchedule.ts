import CalenderTab from "@/views/page-calendar/CalendarTab.vue";
import FabButton from "@/components/FabButton.vue";
import SchedulePop from "@/views/page-schedule/dialogs/SchedulePopModal.vue";
import ServerRemoteBadge from "@/components/ServerRemoteBadge.vue";
import { getColorOptions } from "@/types/color-type";
import EventBus, { C_EVENT } from "@/types/event-bus";
import IonIcons from "@/types/ion-icons";
import { getGroupOptions, getPriorityOptions } from "@/types/schedule-type";
import {
  DayData,
  MonthData,
  ScheduleData,
  ScheduleSave,
  UData,
  User,
  UserData,
} from "@/types/user-data";
import { getTodoCalendar, createTodo, updateTodo, deleteTodo, saveTodo } from "@/api/api-todo";
import { getUserInfo } from "@/api/api-user";
import { LocalNotifications } from "@capacitor/local-notifications";
import {
  IonAccordion,
  IonAccordionGroup,
  IonCheckbox,
  IonFab,
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
import "swiper/css";
import "swiper/css/effect-fade";
import { Keyboard } from "swiper/modules";
import { Swiper, SwiperSlide } from "swiper/vue";
import { defineComponent, inject, onMounted, ref } from "vue";

export default defineComponent({
  components: {
    FabButton,
    ServerRemoteBadge,
    IonAccordion,
    IonAccordionGroup,
    IonCheckbox,
    IonFab,
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
      userData: ref<UserData>(new UserData()), // 旧数据结构（兜底）
      calendarData: ref<Record<string, any[]>>({}), // 新接口返回的日历数据 {date: ScheduleData[]}
      user: ref<User>(globalVar.user),
      slideArr: ref<any[]>([{}, {}, {}]), // 滑动数据
      bReorderDisabled: ref(true),
      curScheduleList: ref(),
      swiperRef: ref(), // 滑动对象
      bFold: ref(true), // 日历折叠状态
      selectedDate: ref<DayData>(), // 选中日期
      scheduleModal: ref(), // 弹窗对象
      scheduleModalData: ref<ScheduleData>(),
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

    // 初始化数据 - 使用新数据结构
    // 排序日程列表：状态 -> order -> id
    const sortEvents = (events: ScheduleData[]) => {
      return events.sort((a: ScheduleData, b: ScheduleData) => {
        const sa = a.state ?? 0;
        const sb = b.state ?? 0;
        if (sa !== sb) return sa - sb;
        const oa = a.order ?? 99999;
        const ob = b.order ?? 99999;
        if (oa !== ob) return oa - ob;
        return (a.id ?? 0) - (b.id ?? 0);
      });
    };

    const updateScheduleData = () => {
      const calendarData = refData.calendarData.value;
      if (!calendarData || Object.keys(calendarData).length === 0) {
        console.warn('[PageSchedule] calendarData is empty');
        return;
      }

      if (refData.bFold.value) {
        // 周视图：生成3页
        const currentWeekStart = currentDate.startOf('week');
        const prevWeekStart = currentWeekStart.subtract(1, 'week');
        const nextWeekStart = currentWeekStart.add(1, 'week');
        refData.slideArr.value = [
          createWeekDataFromCalendar(prevWeekStart, {}), // 前一页
          createWeekDataFromCalendar(currentWeekStart, calendarData), // 中间页（有数据）
          createWeekDataFromCalendar(nextWeekStart, {}) // 后一页
        ];
      } else {
        // 月视图：生成3页
        const prevMonth = currentDate.subtract(1, 'month');
        const nextMonth = currentDate.add(1, 'month');
        refData.slideArr.value = [
          createMonthDataFromCalendar(prevMonth, {}), // 前一页
          createMonthDataFromCalendar(currentDate, calendarData), // 中间页（有数据）
          createMonthDataFromCalendar(nextMonth, {}) // 后一页
        ];
      }

    };

    // 从 calendarData 创建周视图数据
    const createWeekDataFromCalendar = (weekStart: dayjs.Dayjs, calendarData: Record<string, any[]>): any => {
      const weekData: any = {
        vid: 0,
        weekStart: weekStart,
        month: weekStart.month(), // 添加 month 字段，与 dayjs.month() 一致
        weekArr: []
      };

      const week: any[] = [];
      for (let i = 0; i < 7; i++) {
        const currentDay = weekStart.add(i, 'day');
        const dateStr = currentDay.format('YYYY-MM-DD');
        const events = calendarData[dateStr] || [];
        
        // 排序：状态 -> order -> id
        const sortedEvents = sortEvents([...events]);
        
        week.push({
          dt: currentDay,
          events: sortedEvents,
          save: {}
        });
      }
      weekData.weekArr = [week]; // 包装成二维数组

      return weekData;
    };

    // 从 calendarData 创建月视图数据
    const createMonthDataFromCalendar = (monthDate: dayjs.Dayjs, calendarData: Record<string, any[]>): any => {
      const monthData: any = {
        vid: 0,
        month: monthDate.month(), // 使用 0-11，与 dayjs.month() 一致
        year: monthDate.year(),
        firstDayOfMonth: monthDate.startOf('month'),
        weekArr: []
      };

      const startOfMonth = monthDate.startOf('month');
      const endOfMonth = monthDate.endOf('month');
      const startDate = startOfMonth.startOf('week');
      const endDate = endOfMonth.endOf('week');

      let currentWeek: any[] = [];
      let current = startDate;

      while (current <= endDate) {
        const dateStr = current.format('YYYY-MM-DD');
        const events = calendarData[dateStr] || [];
        
        // 排序：状态 -> order -> id
        const sortedEvents = sortEvents([...events]);
        
        currentWeek.push({
          dt: current,
          events: sortedEvents,
          save: {}
        });

        if (currentWeek.length === 7) {
          monthData.weekArr.push(currentWeek);
          currentWeek = [];
        }

        current = current.add(1, 'day');
      }

      // 处理最后一周不足7天的情况
      if (currentWeek.length > 0) {
        monthData.weekArr.push(currentWeek);
      }

      return monthData;
    };

    // 初始化日历
    // 处理选中日期
    const chooseSelectedDate = () => {
      const mm = refData.slideArr.value[1];
      if (!mm.weekArr) {
        console.warn("no weekArr");
        return;
      }
      
      // 如果已有选中日期，检查是否在新视图范围内
      if (refData.selectedDate.value) {
        // 检查月份是否匹配（处理跨周边界问题）
        if (refData.selectedDate.value.dt.month() !== mm.month) {
          // 月份不匹配，清空后重新选择
          refData.selectedDate.value = undefined;
        } else {
          // 月份匹配，再检查日期是否在视图中
          for (const week of mm.weekArr) {
            for (const day of week) {
              if (day.dt.unix() === refData.selectedDate.value.dt.unix()) {
                // 在范围内，更新为新的对象引用以获取最新数据
                refData.selectedDate.value = day;
                return;
              }
            }
          }
          // 日期不在视图中，清空后重新选择
          refData.selectedDate.value = undefined;
        }
      }
      
      // selectedDate 没有值，按规则选择
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

    const refreshAllData = async (id: number = 3, showLoading: boolean = true) => {
      let loading: any;
      if (showLoading) {
        loading = await loadingController.create({
          message: "Loading...",
        });
        loading.present();
      }
      
      try {
        // 根据视图类型确定查询范围
        let startTime: string;
        let endTime: string;
        
        // console.log('[PageSchedule] currentDate:', currentDate.format('YYYY-MM-DD'), 'bFold:', refData.bFold.value);
        
        if (refData.bFold.value) {
          // 周视图：只查询当前周
          startTime = currentDate.startOf('week').format('YYYY-MM-DD');
          endTime = currentDate.endOf('week').format('YYYY-MM-DD');
        } else {
          // 月视图：前后各扩展一个月
          startTime = currentDate.startOf('month').subtract(1, 'month').format('YYYY-MM-DD');
          endTime = currentDate.endOf('month').add(1, 'month').format('YYYY-MM-DD');
        }
        
        // console.log('[PageSchedule] query range:', startTime, 'to', endTime);
        
        const calendarData = await getTodoCalendar(startTime, endTime, id);
        // console.log('[PageSchedule] calendarData:', calendarData);
        
        // 存储新数据
        refData.calendarData.value = calendarData;
        
        // 更新显示
        updateScheduleData();
        chooseSelectedDate();
        setTimeout(() => {
          refData.swiperRef?.value?.update();
        }, 100);
      } catch (err) {
        console.error('[PageSchedule] refreshAllData error:', err);
        refData.toastData.value.isOpen = true;
        refData.toastData.value.text = JSON.stringify(err);
      } finally {
        if (loading) {
          loading.dismiss();
        }
      }
    };
    eventBus.$on(C_EVENT.UPDATE_SCHEDULE_GROUP, () => {
      // console.log("UPDATE_SCHEDULE_GROUP", params);
      refreshAllData(globalVar.scheduleListId);
    });
    eventBus.$on(C_EVENT.UPDATE_USER_INFO, async () => {
      getUserInfo(refData.user.value.id).then((userInfo: any) => {
        refData.user.value = userInfo;
      });
    });
    onMounted(() => {
      // console.log("onMounted page");
      eventBus.$on(C_EVENT.MENU_CLOSE, (params: any) => {
        refData.filter.value = params;
      });
    });
    
    onIonViewDidEnter(() => {
      refreshAllData(globalVar.scheduleListId);
    });

    // 保存存档
    // ============ 工具栏 ============
    const toolbarMethod = {
      // 返回今天按钮
      btnTodayClk: async () => {
        currentDate = dayjs().startOf("day");
        await refreshAllData(globalVar.scheduleListId);
        setTimeout(() => {
          refData.swiperRef?.value?.update();
        }, 100);
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
      slideChange: async (obj: any) => {
        // 重新获取数据（基于新的 currentDate）
        await refreshAllData(globalVar.scheduleListId);
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
      btnCalendarFoldClk: async (value?: boolean) => {
        const v = value ?? !refData.bFold.value;
        if (v === refData.bFold.value) return;
        
        const savedDate = refData.selectedDate.value?.dt;
        refData.bFold.value = v;
        await refreshAllData(globalVar.scheduleListId);
        
        // 在新视图中恢复选中日期
        if (savedDate) {
          const mm = refData.slideArr.value[1];
          if (mm.weekArr) {
            for (const week of mm.weekArr) {
              for (const day of week) {
                if (day.dt.unix() === savedDate.unix()) {
                  refData.selectedDate.value = day;
                  break;
                }
              }
            }
          }
        }
        
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
        // 从 events 中查找日程的 state
        const schedule = refData.selectedDate.value?.events?.find((s: any) => s.id === scheduleId);
        return schedule?.state === 1;
      },
      // 判断是否可以修改完成状态（查看日期在今天及过去1天内可以修改）
      canModifyScheduleState: () => {
        // 检查是否为管理员
        if (refData.user.value?.admin === 1) {
          return true;
        }
        
        // 使用选中的日期来判断
        const selectedDate = refData.selectedDate.value?.dt;
        if (!selectedDate) {
          return true; // 如果没有选中日期，允许修改
        }
        
        const now = dayjs().startOf('day');
        const viewDate = selectedDate.startOf('day');
        
        // 计算天数差：viewDate - now，负数表示过去，正数表示未来
        const diffDays = viewDate.diff(now, 'day');
        // diffDays <= 0 表示今天或过去，diffDays >= -1 表示不超过1天
        return diffDays <= 0 && diffDays >= -1;
      },
      // 日程状态改变
      onScheduleCheckboxChange: async (_event: any, day: DayData | undefined, schedule: ScheduleData) => {
        if (day) {
          const newState = _event.detail.checked ? 1 : 0;
          const oldState = schedule.state ?? 0;
          
          // 乐观更新：立即更新本地数据
          schedule.state = newState;
          
          try {
            // 保存日程状态到存档
            const scheduleSave: any = {
              date: day.dt.format('YYYY-MM-DD'),
              schedule_id: schedule.id,
              state: newState,
            };
            await saveTodo(scheduleSave);
            
            // 重新排序当前日期的事件列表
            if (day.events) {
              sortEvents(day.events);
              // 触发响应式更新
              refData.selectedDate.value!.events = [...day.events];
            }
            
            // 如果从未完成变为完成，且有积分，触发奖励事件
            if (oldState === 0 && newState === 1 && schedule.score && schedule.score > 0) {
              EventBus.$emit(C_EVENT.REWARD, {
                rewardType: 'points',
                value: schedule.score,
              });
            }
            // 重新加载用户信息以更新积分显示
            getUserInfo(refData.user.value.id).then((userInfo: any) => {
              refData.user.value = userInfo;
            });
          } catch (err) {
            console.error('[PageSchedule] 更新日程状态失败:', err);
            // 失败则回滚
            schedule.state = oldState;
            refData.toastData.value.isOpen = true;
            refData.toastData.value.text = '更新状态失败';
          }
        }
      },

      // 日程按钮点击
      btnScheduleClk: (event: any, schedule: ScheduleData) => {
        refData.isScheduleModalOpen.value = true;
        refData.scheduleModalData.value = schedule;
      },
      // 日程专注按钮
      btnScheduleAlarmClk: () => {
        console.log("btnScheduleAlarmClk");
      },
      // 日程删除
      btnScheduleRemoveClk: (_event: any, schedule: ScheduleData) => {
        refData.scheduleDelConfirm.value.isOpen = true;
        refData.scheduleDelConfirm.value.data = schedule;
        refData.scheduleDelConfirm.value.text =
          "确定要删除日程「" + (schedule.title || "未命名") + "」吗？删除后不可恢复。";
      },
      onDelSchedulerConfirm: async (event: any) => {
        refData.scheduleDelConfirm.value.isOpen = false;
        if (event.detail.role === "confirm") {
          const schedule = refData.scheduleDelConfirm.value.data;
          try {
            await deleteTodo(schedule.id);
            // 刷新显示
            await refreshAllData(globalVar.scheduleListId);
            EventBus.$emit(C_EVENT.TOAST, "已删除日程");
          } catch (err) {
            console.error('[PageSchedule] 删除日程失败:', err);
            refData.toastData.value.isOpen = true;
            refData.toastData.value.text = '删除失败';
          }
        }
      },
      onReorder: async (event: any) => {
        let eList = refData.selectedDate.value?.events.filter(scheduleListMethod.bShowScheduleItem);
        eList = event.detail.complete(eList);
        if (eList) {
          try {
            // 批量更新日程排序
            const updates = eList.map((e, index) => ({
              id: e.id,
              order: index,
            }));
            
            // 逐个更新
            for (const update of updates) {
              await updateTodo(update.id, { order: update.order });
            }
            
            // 刷新显示
            await refreshAllData(globalVar.scheduleListId);
          } catch (err) {
            console.error('[PageSchedule] 更新日程排序失败:', err);
            refData.toastData.value.isOpen = true;
            refData.toastData.value.text = '更新排序失败';
          }
        }
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
        refData.isScheduleModalOpen.value = true;
      },
      // 添加日程页面关闭回调
      onScheduleModalDismiss: async (event: any) => {
        refData.isScheduleModalOpen.value = false;
        if (event.detail.role === "backdrop") return;
        
        const _scheduleData = event.detail.data;
        const role = event.detail.role; // "all" 或 "cur"
        
        try {
          if (role === "all") {
            // 应用到所有：新增或编辑日程模板
            if (_scheduleData.id === -1) {
              // 新增日程
              const newId = await createTodo(_scheduleData);
              _scheduleData.id = newId; // 更新ID
            } else {
              // 编辑日程
              await updateTodo(_scheduleData.id, _scheduleData);
              
              // 如果有save信息（state或subtasks），则保存到存档
              if (refData.selectedDate.value && (_scheduleData.state !== undefined || _scheduleData.subtasks)) {
                const scheduleSave: any = {
                  date: refData.selectedDate.value.dt.format('YYYY-MM-DD'),
                  schedule_id: _scheduleData.id,
                };
                
                if (_scheduleData.state !== undefined) {
                  scheduleSave.state = _scheduleData.state;
                }
                
                if (_scheduleData.subtasks !== undefined) {
                  const subtaskStates: Record<number, number> = {};
                  _scheduleData.subtasks.forEach((st: any) => {
                    if (st.id !== -1 && st.state !== undefined) {
                      subtaskStates[st.id] = st.state;
                    }
                  });
                  if (Object.keys(subtaskStates).length > 0) {
                    scheduleSave.subtasks = subtaskStates;
                  }
                }
                
                await saveTodo(scheduleSave);
              }
            }
          } else if (role === "cur") {
            // 仅当天：保存特定日期的覆盖数据
            if (refData.selectedDate.value) {
              const scheduleSave: Partial<ScheduleSave> = {
                date: refData.selectedDate.value.dt.format('YYYY-MM-DD'),
                scheduleOverride: _scheduleData,
              };
              await saveTodo(scheduleSave);
            }
          }
          
          // 刷新显示
          await refreshAllData(globalVar.scheduleListId);
        } catch (err) {
          console.error('[PageSchedule] 保存日程失败:', err);
          refData.toastData.value.isOpen = true;
          refData.toastData.value.text = '保存失败';
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
