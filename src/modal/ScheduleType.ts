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
  { id: 0, label: "None", tag: "" },
  { id: 1, label: "Daily", tag: "day" },
  { id: 2, label: "Weekly", tag: "week" },
  { id: 3, label: "Monthly", tag: "month" },
  { id: 4, label: "Yearly", tag: "year" },
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
  { id: 3, label: "Blue", tag: "blue" },
  { id: 4, label: "Green", tag: "green" },
];

export const getColorOptions = (id: number): ColorType => {
  for (const v of ColorOptions) {
    if (v.id === id) {
      return v;
    }
  }
  return ColorOptions[0];
};

export interface PriorityType {
  id: number;
  icon: string;
  color: string;
  label: string;
}
// 优先级类型
export const PriorityOptions: PriorityType[] = [
  { id: 0, icon: "mdi:roman-numeral-1", color: "#1a65eb !important", label: "Low" },
  { id: 1, icon: "mdi:roman-numeral-2", color: "#2dd55b !important", label: "Medium" },
  { id: 2, icon: "mdi:roman-numeral-3", color: "#ffc409 !important", label: "High" },
  { id: 3, icon: "mdi:roman-numeral-4", color: "#cb1a27 !important", label: "Critical" },
];
export const getPriorityOptions = (id: number): PriorityType => {
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
  { id: 0, label: "All", color: "white" },
  { id: 1, label: "Work", color: "red" },
  { id: 2, label: "Home", color: "yellow" },
];

export const getGroupOptions = (id: number): GroupType => {
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
