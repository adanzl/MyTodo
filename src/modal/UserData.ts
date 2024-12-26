import dayjs from "dayjs";

export class Subtask {
  id: number = -1;
  name?: string = "";
  imgIds: number[] = []; // 图片id列表
  static Copy(o: Subtask): Subtask {
    return {
      id: o.id,
      name: o.name,
      imgIds: o.imgIds?.concat(),
    };
  }
}

// 日程计划数据
export class ScheduleData {
  // ===== 日程数据 =====
  id: number = -1; // 任务id
  startTs?: dayjs.Dayjs; // 开始时间
  endTs?: dayjs.Dayjs; // 结束时间
  allDay?: boolean = true; // 是否全天
  reminder?: number = 0; // 提醒类型
  repeat?: number = 0; // 重复类型
  repeatEndTs?: dayjs.Dayjs; // 重复结束类型
  // 以下字段为覆盖字段，用于覆盖默认值
  title?: string; // 任务标题
  color? = 0; // 颜色id
  priority? = -1; // 优先级
  groupId? = -1; // 分组id
  subtasks: Subtask[] = []; // 子任务列表
  static Copy(o: ScheduleData): ScheduleData {
    const ret = JSON.parse(JSON.stringify(o));
    ret.startTs = o.startTs?.clone();
    ret.endTs = o.endTs?.clone();
    ret.repeatEndTs = o.repeatEndTs?.clone();
    ret.subtasks = [];
    if (o.subtasks) {
      for (const subtask of o.subtasks) {
        ret.subtasks.push(Subtask.Copy(subtask));
      }
    }
    return ret;
  }
  constructor() {
    this.startTs = dayjs().startOf("day");
    this.endTs = dayjs().startOf("day");
  }
}

// 日程存档【每天】
export class ScheduleSave {
  state: number = -1;
  subtasks: Record<number, number> = {}; // <number, number>;
  // 覆盖字段
  scheduleOverride?: ScheduleData;
  static Copy(o: ScheduleSave): ScheduleSave {
    const ret = new ScheduleSave();
    ret.state = o.state;
    ret.subtasks = JSON.parse(JSON.stringify(o.subtasks));
    return ret;
  }
}

// 用户数据
export class UserData {
  id: number = -1; // 用户id
  name: string = ""; // 用户名称
  schedules: ScheduleData[] = []; // 日程计划列表
  // 计划完成情况  日期->对应日期完成情况(任务id->完成情况)
  save: Record<string, Record<number, ScheduleSave>> = {};
  static Copy(o: UserData): UserData {
    const ret = new UserData();
    ret.id = o.id;
    ret.name = o.name;
    ret.schedules = [];
    for (const schedule of o.schedules) {
      ret.schedules.push(ScheduleData.Copy(schedule));
    }
    ret.save = JSON.parse(JSON.stringify(o.save));
    return ret;
  }
}

// 一天的数据
export class DayData {
  dt: dayjs.Dayjs = dayjs().startOf("day");
  events: ScheduleData[] = []; // 当天可见日程
  save: Record<number, ScheduleSave> = {}; // 日程id->日程保存情况
  constructor(_dt?: dayjs.Dayjs) {
    if (_dt) this.dt = _dt;
  }
}

// 一个月的数据
export class MonthData {
  vid: number = 0;
  month: number = 0;
  year: number = 0;
  firstDayOfMonth: dayjs.Dayjs = dayjs().startOf("day");
  weekArr: DayData[][] = [];
}

export class UData {
  /**
   * 创建一个月的日历数据
   * @param datetime 当前月份的某一天
   * @param userData 用户数据
   * @param selectedDate 选中的日期
   * @returns 月份数据
   */
  static createMonthData(datetime: dayjs.Dayjs, userData: UserData, selectedDate?: any): MonthData {
    const firstDayOfMonth = datetime.startOf("month");
    let _dt = firstDayOfMonth.startOf("week");
    // console.log("firstDayOfWeek", _dt);
    const wArr: DayData[][] = [];
    do {
      const week: DayData[] = [];
      for (let i = 0; i < 7; i++) {
        const dayData = UData.createDayData(_dt, userData);
        if (selectedDate && selectedDate.value?.dt.unix() == _dt.unix()) {
          selectedDate.value = dayData;
        }
        week.push(dayData);
        _dt = _dt.add(1, "days");
      }
      wArr.push(week);
    } while (_dt.month() == datetime.month());
    // console.log("wArr", wArr);
    return {
      vid: datetime.year(),
      month: datetime.month(),
      year: datetime.year(),
      firstDayOfMonth: firstDayOfMonth,
      weekArr: wArr,
    } as MonthData;
  }
  /**
   * 创建一星期的日历数据
   * @param datetime 当前周的某一天
   * @param userData 用户数据
   * @param selectedDate 选中的日期
   * @returns 月份数据
   */
  static createWeekData(datetime: dayjs.Dayjs, userData: UserData, selectedDate?: any): MonthData {
    const firstDayOfMonth = datetime.startOf("month");
    let _dt = datetime.startOf("week");
    // console.log("firstDayOfWeek", _dt);
    const wArr: DayData[][] = [];
    const week: DayData[] = [];
    for (let i = 0; i < 7; i++) {
      const dayData = UData.createDayData(_dt, userData);
      if (selectedDate && selectedDate.value?.dt.unix() == _dt.unix()) {
        selectedDate.value = dayData;
      }
      week.push(dayData);
      _dt = _dt.add(1, "days");
    }
    wArr.push(week);
    return {
      vid: datetime.year(),
      month: datetime.month(),
      year: datetime.year(),
      firstDayOfMonth: firstDayOfMonth,
      weekArr: wArr,
    } as MonthData;
  }

  /**
   * 创建一天的数据
   * @param _dt 当前日期
   * @param userData 用户数据
   * @returns 当前日期的数据
   */
  static createDayData(_dt: dayjs.Dayjs, userData: UserData): DayData {
    const dayData = new DayData(_dt);
    const ts = _dt.unix();
    if (userData.save[S_TS(_dt)] == undefined) {
      userData.save[S_TS(_dt)] = {};
    }
    const save = userData.save[S_TS(_dt)];
    for (const s of userData.schedules) {
      const schedule = ScheduleData.Copy(s);
      if (schedule.startTs && schedule.startTs.startOf("day").unix() <= ts) {
        if (schedule.startTs.startOf("day").unix() === ts) {
          dayData.events.push(schedule);
          continue;
        }
        // 处理repeat
        if (schedule.repeatEndTs && schedule.repeatEndTs.unix() < ts) {
          continue;
        }
        if (schedule.repeat == 1) {
          // daily
          dayData.events.push(schedule);
        } else if (schedule.repeat == 2) {
          // weekly
          if (_dt.day() == schedule.startTs.day()) {
            dayData.events.push(schedule);
          }
        } else if (schedule.repeat == 3) {
          // monthly
          if (_dt.date() == schedule.startTs.date()) {
            dayData.events.push(schedule);
          }
        } else if (schedule.repeat == 4) {
          // yearly
          if (_dt.date() == schedule.startTs.date() && _dt.month() == schedule.startTs.month()) {
            dayData.events.push(schedule);
          }
        }
      }
      // schedule;
      const scheduleSave = save?.[schedule.id];
      if (scheduleSave && scheduleSave.scheduleOverride) {
        const os = scheduleSave.scheduleOverride;
        // 处理覆盖问题
        // 任务标题
        os.title && (schedule.title = os.title);
        // 颜色id
        os.color && (schedule.color = os.color);
        // 优先级
        os.priority && (schedule.priority = os.priority);
        // 分组id
        os.groupId && (schedule.groupId = os.groupId);
        // 子任务列表
        os.subtasks && (schedule.subtasks = os.subtasks);
      }
    }
    // 排序日程
    dayData.save = save;
    dayData.events.sort((a: ScheduleData, b: ScheduleData) => {
      const sa: number = save[a.id]?.state || 0;
      const sb: number = save[b.id]?.state || 0;
      if (sa === sb) {
        return (a.id ?? 0) - (b.id ?? 0);
      }
      return sa - sb;
    });
    return dayData;
  }

  /**
   * 更新日程数据
   * @param userData 用户数据
   * @param _scheduleData 日程数据
   * @param _scheduleSave 日程存档数据
   * @param dt 当前日期
   * @param type 更新类型 all:更新日程和存档 cur:更新存档
   * @returns 是否更新成功
   */
  static updateSchedularData(
    userData: UserData,
    _scheduleData: ScheduleData,
    _scheduleSave: ScheduleSave,
    dt: dayjs.Dayjs,
    type: string
  ): boolean {
    const dKey = S_TS(dt);
    if (type === "all") {
      // 日程变化
      if (_scheduleData.id === -1) {
        // add id userData.value.schedules id的最大值=1
        const id = userData.schedules.reduce((max, s) => (s.id! > max ? s.id! : max), 0);
        _scheduleData.id = id;
        userData.schedules.push(_scheduleData);
      } else {
        const idx = userData.schedules.findIndex((s) => s.id === _scheduleData.id);
        if (idx !== -1) {
          userData.schedules[idx] = _scheduleData;
        }
      }
      // 存档变化
      if (!(dKey in userData.save)) {
        userData.save[dKey] = {};
      }
      const map = userData.save[dKey];
      map![_scheduleData.id!] = _scheduleSave;
    } else if (type === "cur") {
      // 只管当天日程 存档变化
      if (!(dKey in userData.save)) {
        userData.save[dKey] = {};
      }
      const map = userData.save[dKey];
      const s: ScheduleSave = (map![_scheduleData.id!] = _scheduleSave);
      s.scheduleOverride = _scheduleData;
    } else {
      return false;
    }
    return true;
  }

  static parseScheduleData(jsonStr: string): ScheduleData {
    const ret = JSON.parse(jsonStr) as ScheduleData;
    ret.startTs = dayjs(ret.startTs);
    ret.endTs = dayjs(ret.endTs);
    ret.repeatEndTs = ret.repeatEndTs && dayjs(ret.repeatEndTs);
    return ret;
  }

  static parseUserData(jsonStr: string): UserData {
    const ret = JSON.parse(jsonStr) as UserData;
    if (ret.schedules === undefined) {
      ret.schedules = [];
    }
    for (let i = 0; i < ret.schedules.length; i++) {
      const schedule = ret.schedules[i];
      schedule.startTs = dayjs(schedule.startTs);
      schedule.endTs = dayjs(schedule.endTs);
      schedule.repeatEndTs = schedule.repeatEndTs && dayjs(schedule.repeatEndTs);
      if (schedule.subtasks === undefined) {
        schedule.subtasks = [];
      }
    }

    return ret;
  }
}
export const S_TS = (dt?: dayjs.Dayjs): string => {
  if (dt === undefined) return "";
  return dt.format("YYYY-MM-DD");
};

export default {
  ScheduleData,
  ScheduleSave,
  UserData,
  DayData,
  MonthData,
  S_TS,
  UData,
};
