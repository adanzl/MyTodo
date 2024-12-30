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
export const RepeatOptions: RepeatType[] = [
  { id: 0, label: "无", tag: "", icon: MdiCalendarBlankOutline },
  { id: 1, label: "每天", tag: "day", icon: MdiCalendarMonthOutline },
  { id: 2, label: "每星期", tag: "week", icon: MdiCalendarWeekBeginOutline },
  { id: 3, label: "每月", tag: "month", icon: MdiCalendarTodayOutline },
  { id: 4, label: "每年", tag: "year", icon: MdiCalendarMultiselectOutline },
];
export const getRepeatOptions = (id?: number): RepeatType => {
  for (const v of RepeatOptions) {
    if (v.id === id) {
      return v;
    }
  }
  return RepeatOptions[0];
};

export interface ColorType {
  id: number;
  label: string;
  tag: string;
}
// 颜色类型
export const ColorOptions: ColorType[] = [
  { id: 0, label: "None", tag: "#f8fafc" },
  { id: 1, label: "Red", tag: "#fca5a5" },
  { id: 2, label: "Yellow", tag: "#fde047" },
  { id: 3, label: "Blue", tag: "#93c5fd" },
  { id: 4, label: "Green", tag: "#4ade80" },
];

export const getColorOptions = (id?: number): ColorType => {
  for (const v of ColorOptions) {
    if (v.id === id) {
      return v;
    }
  }
  return ColorOptions[0];
};

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

// 分组配置
export interface GroupType {
  id: number;
  label: string;
  color: string;
}
export const GroupOptions: GroupType[] = [
  { id: 0, label: "未分类", color: "white" },
  { id: 1, label: "工作", color: "red" },
  { id: 2, label: "学习", color: "yellow" },
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
  ColorOptions,
  GroupOptions,
};
