/**
 * 日程相关常量
 */

export const WEEK = [
  "星期天",
  "星期一",
  "星期二",
  "星期三",
  "星期四",
  "星期五",
  "星期六",
];

export interface ReminderOption {
  id: number;
  label: string;
}

export const ReminderOptions: ReminderOption[] = [
  { id: 0, label: "None" },
  { id: 1, label: "On the day 9:00" },
  { id: 2, label: "1 day early 9:00" },
  { id: 3, label: "2 day early 9:00" },
  { id: 4, label: "3 day early 9:00" },
  { id: 5, label: "4 day early 9:00" },
];

export interface RepeatOption {
  id: number | string;
  label: string;
  tag: string;
  icon: string;
}

export const RepeatOptions: RepeatOption[] = [
  { id: 0, label: "无", tag: "", icon: "MdiCalendarBlankOutline" },
  { id: 1, label: "每天", tag: "day", icon: "MdiCalendarMonthOutline" },
  { id: 5, label: "工作日", tag: "workday", icon: "MdiCalendarWeekOutline" },
  { id: 6, label: "每周末", tag: "weekend", icon: "MdiCalendarWeekendOutline" },
  { id: 2, label: "每星期", tag: "week", icon: "MdiCalendarWeekBeginOutline" },
  { id: 3, label: "每月", tag: "month", icon: "MdiCalendarTodayOutline" },
  { id: 4, label: "每年", tag: "year", icon: "MdiCalendarMultiselectOutline" },
  {
    id: "CUSTOM_REPEAT_ID",
    label: "自定义",
    tag: "custom",
    icon: "MdiHammerWrench",
  },
];

export interface PriorityOption {
  id: number;
  icon: string;
  color: string;
  label: string;
}

export const PriorityOptions: PriorityOption[] = [
  {
    id: 0,
    icon: "MdiRomanNumeral1",
    color: "#1a65eb",
    label: "不重要并且不紧急",
  },
  {
    id: 1,
    icon: "MdiRomanNumeral2",
    color: "#2dd55b",
    label: "不重要但是紧急",
  },
  {
    id: 2,
    icon: "MdiRomanNumeral3",
    color: "#ffc409",
    label: "重要但是不紧急",
  },
  {
    id: 3,
    icon: "MdiRomanNumeral4",
    color: "#cb1a27",
    label: "重要并且紧急",
  },
];

export interface GroupOption {
  id: number;
  label: string;
  color: string;
  icon: string;
}

export const GroupOptions: GroupOption[] = [
  { id: 0, label: "未分类", color: "white", icon: "MdiBorderRoundCorners" },
  { id: 1, label: "工作", color: "red", icon: "MdiWorkOutline" },
  { id: 2, label: "学习", color: "yellow", icon: "MdiLearnOutline" },
];


