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
}

// 日程重复类型
export const RepeatOptions: RepeatType[] = [
  { id: 0, label: "无", tag: "" },
  { id: 1, label: "每天", tag: "day" },
  { id: 2, label: "每星期", tag: "week" },
  { id: 3, label: "每月", tag: "month" },
  { id: 4, label: "每年", tag: "year" },
];

export interface ColorType {
  id: number;
  label: string;
  tag: string;
}
// 颜色类型
export const ColorOptions: ColorType[] = [
  { id: 0, label: "None", tag: "white" },
  { id: 1, label: "Red", tag: "red" },
  { id: 2, label: "Yellow", tag: "yellow" },
  { id: 3, label: "Blue", tag: "#7970ff" },
  { id: 4, label: "Green", tag: "#3fef28" },
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
  { id: 0, icon: MdiRomanNumeral1, color: "#1a65eb", label: "较低" },
  { id: 1, icon: MdiRomanNumeral2, color: "#2dd55b", label: "中等" },
  { id: 2, icon: MdiRomanNumeral3, color: "#ffc409", label: "较高" },
  { id: 3, icon: MdiRomanNumeral4, color: "#cb1a27", label: "核心" },
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
  getColorOptions,
  getGroupOptions,
};
