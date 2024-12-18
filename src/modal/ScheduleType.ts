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

// 优先级类型
export const PriorityOptions = [
  { id: 0, icon: 0 },
  { id: 1, icon: 1 },
  { id: 2, icon: 2 },
  { id: 3, icon: 3 },
];
export const getPriorityOptions = (id: number): { id: number; icon: number } => {
  for (const v of PriorityOptions) {
    if (v.id === id) {
      return v;
    }
  }
  return PriorityOptions[0];
};

export default {
  ReminderOptions,
  RepeatOptions,
  ColorOptions,
  getColorOptions,
};
