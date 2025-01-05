import _ from "lodash";
export const WEEK = ["星期天", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];
export interface RemindType {
  id: number;
  label: string;
}
// 日程提醒类型
export const ReminderOptions: RemindType[] = [
  { id: 0, label: "None" },
  { id: 1, label: "On the day 9:00" },
  { id: 2, label: "1 day early 9:00" },
  { id: 3, label: "2 day early 9:00" },
  { id: 4, label: "3 day early 9:00" },
  { id: 5, label: "4 day early 9:00" },
];

export interface RepeatType {
  id: number;
  label: string;
  tag: string;
  icon?: any;
}

// 日程重复类型
import MdiCalendarMonthOutline from "virtual:icons/mdi/calendar-month-outline";
import MdiCalendarWeekBeginOutline from "virtual:icons/mdi/calendar-week-begin-outline";
import MdiCalendarTodayOutline from "virtual:icons/mdi/calendar-today-outline";
import MdiCalendarMultiselectOutline from "virtual:icons/mdi/calendar-multiselect-outline";
import MdiCalendarBlankOutline from "virtual:icons/mdi/calendar-blank-outline";
import MdiCalendarWeekendOutline from "~icons/mdi/calendar-weekend-outline?width=24px&height=24px";
import MdiCalendarWeekOutline from "~icons/mdi/calendar-week-outline?width=24px&height=24px";
export const RepeatOptions: RepeatType[] = [
  { id: 0, label: "无", tag: "", icon: MdiCalendarBlankOutline },
  { id: 1, label: "每天", tag: "day", icon: MdiCalendarMonthOutline },
  { id: 5, label: "工作日", tag: "workday", icon: MdiCalendarWeekOutline },
  { id: 6, label: "每周末", tag: "weekend", icon: MdiCalendarWeekendOutline },
  { id: 2, label: "每星期", tag: "week", icon: MdiCalendarWeekBeginOutline },
  { id: 3, label: "每月", tag: "month", icon: MdiCalendarTodayOutline },
  { id: 4, label: "每年", tag: "year", icon: MdiCalendarMultiselectOutline },
];

export const getRepeatOptions = (id: number | undefined | null): RepeatType => {
  for (const v of RepeatOptions) {
    if (v.id === id) {
      return v;
    }
  }
  return RepeatOptions[0];
};

/**
 * 获取下一次的重复日期
 */
export function getNextRepeatDate(
  date: dayjs.Dayjs | undefined,
  repeatId: number | null | undefined
) {
  if (!date || !repeatId) {
    return undefined;
  }
  const repeat = getRepeatOptions(repeatId);
  if (repeat.id === 0) {
    return undefined;
  }
  let ret = null;
  if (_.includes([1, 2, 3, 4], repeat.id)) {
    ret = date.add(1, repeat.tag as dayjs.ManipulateType);
  } else if (repeat.id === 5) {
    // 工作日
    const week = date.day();
    if (week === 5 || week === 6) {
      ret = date.add(8 - week, "day");
    } else {
      ret = date.add(1, "day");
    }
  } else if (repeat.id === 6) {
    // 周末
    const week = date.day();
    if (week === 5 || week === 6) {
      ret = date.add(1, "day");
    } else {
      ret = date.add(6 - week, "day");
    }
  }
  // console.log("getNextRepeatDate", repeat, ret);
  return ret?.format("YYYY-MM-DD") ?? undefined;
}

export interface PriorityType {
  id: number;
  icon: any;
  color: string;
  label: string;
}
// 优先级类型
import MdiRomanNumeral1 from "virtual:icons/mdi/roman-numeral-1";
import MdiRomanNumeral2 from "virtual:icons/mdi/roman-numeral-2";
import MdiRomanNumeral3 from "virtual:icons/mdi/roman-numeral-3";
import MdiRomanNumeral4 from "virtual:icons/mdi/roman-numeral-4";
export const PriorityOptions: PriorityType[] = [
  { id: 0, icon: MdiRomanNumeral1, color: "#1a65eb", label: "不重要并且不紧急" },
  { id: 1, icon: MdiRomanNumeral2, color: "#2dd55b", label: "不重要但是紧急" },
  { id: 2, icon: MdiRomanNumeral3, color: "#ffc409", label: "重要但是不紧急" },
  { id: 3, icon: MdiRomanNumeral4, color: "#cb1a27", label: "重要并且紧急" },
];
export const getPriorityOptions = (id?: number): PriorityType => {
  for (const v of PriorityOptions) {
    if (v.id === id) {
      return v;
    }
  }
  return PriorityOptions[0];
};

import MdiLearnOutline from "~icons/mdi/learn-outline";
import MdiWorkOutline from "~icons/mdi/work-outline";
import MdiRoundedCorner from "~icons/mdi/rounded-corner";
import dayjs from "dayjs";
// 分组配置
export interface GroupType {
  id: number;
  label: string;
  color: string;
  icon: any;
}
export const GroupOptions: GroupType[] = [
  { id: 0, label: "未分类", color: "white", icon: MdiRoundedCorner },
  { id: 1, label: "工作", color: "red", icon: MdiWorkOutline },
  { id: 2, label: "学习", color: "yellow", icon: MdiLearnOutline },
];

export const getGroupOptions = (id?: number): GroupType => {
  for (const v of GroupOptions) {
    if (v.id === id) {
      return v;
    }
  }
  return GroupOptions[0];
};

export default {
  ReminderOptions,
  RepeatOptions,
  GroupOptions,
};
