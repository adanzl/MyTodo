/**
 * 日程相关工具函数
 */
import * as _ from "lodash-es";
import type { Dayjs } from "dayjs";
import {
  RepeatOptions,
  WEEK,
  PriorityOptions,
  GroupOptions,
  ColorOptions,
  type RepeatOption,
  type PriorityOption,
  type GroupOption,
  type ColorOption,
} from "@/constants/schedule";

interface RepeatData {
  week?: number[];
  weekdays?: number[];
  monthDays?: number[];
  interval?: number;
}

/**
 * 获取重复选项
 */
export function getRepeatOptions(id: number | string): RepeatOption {
  for (const v of RepeatOptions) {
    if (v.id === id) {
      return v;
    }
  }
  return RepeatOptions[0];
}

/**
 * 构建自定义重复标签
 */
export function buildCustomRepeatLabel(repeatData: RepeatData): string {
  let ret = "每周: ";
  _.forEach(repeatData.week, (v: number) => {
    ret += WEEK[v] + ",";
  });
  ret = ret.slice(0, -1);
  return ret;
}

/**
 * 获取下一次的重复日期
 */
export function getNextRepeatDate(
  date: Dayjs,
  repeatId: number | string,
  repeatData?: RepeatData
): string | undefined {
  if (!date || !repeatId) {
    return undefined;
  }
  const repeat = getRepeatOptions(repeatId);
  if (repeat.id === 0) {
    return undefined;
  }
  let ret: Dayjs | null = null;
  if (_.includes([1, 2, 3, 4], repeat.id)) {
    // repeat.tag 是 "day" | "week" | "month" | "year"，符合 dayjs.ManipulateType
    ret = date.add(1, repeat.tag as "day" | "week" | "month" | "year");
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
  } else if (repeat.id === 999) {
    if (repeatData?.week?.length) {
      const ln = repeatData.week.length ?? 0;
      const sortedWeek = [...repeatData.week].sort();
      const day = date.day();
      const idx = _.sortedIndex(sortedWeek, day);
      if (idx === ln) {
        const d = 7 - day + sortedWeek[0];
        ret = date.add(d, "day");
      } else {
        if (sortedWeek[idx] == day) {
          const d = (sortedWeek[(idx + 1) % ln] + 7 - day) % 7;
          ret = date.add(d, "day");
        } else {
          const d = sortedWeek[idx] - day;
          ret = date.add(d, "day");
        }
      }
    }
  }
  return ret?.format("YYYY-MM-DD") ?? undefined;
}

/**
 * 获取优先级选项
 */
export function getPriorityOptions(id: number): PriorityOption {
  for (const v of PriorityOptions) {
    if (v.id === id) {
      return v;
    }
  }
  return PriorityOptions[0];
}

/**
 * 获取分组选项
 */
export function getGroupOptions(id: number): GroupOption {
  for (const v of GroupOptions) {
    if (v.id === id) {
      return v;
    }
  }
  return GroupOptions[0];
}

/**
 * 获取颜色选项
 */
export function getColorOptions(id?: number): ColorOption {
  for (const v of ColorOptions) {
    if (v.id === id) {
      return v;
    }
  }
  return ColorOptions[0];
}

/**
 * 获取重复规则展示文本
 */
export function getRepeatRuleText(repeat: number | string, repeatData?: RepeatData | string): string {
  const repeatId = Number(repeat);
  const repeatMap: Record<number, string> = {
    0: "无",
    1: "每天",
    2: "每星期",
    3: "每月",
    4: "每年",
    5: "工作日",
    6: "每周末",
    999: "自定义",
  };
  const base = repeatMap[repeatId] ?? String(repeat);
  if (repeatId !== 999 || !repeatData) {
    return base;
  }
  try {
    const data =
      typeof repeatData === "string" ? (JSON.parse(repeatData) as RepeatData) : repeatData;
    if (data.week?.length) {
      return buildCustomRepeatLabel(data);
    }
    const parts: string[] = [];
    if (data.interval) parts.push(`每${data.interval}次`);
    if (data.weekdays?.length) {
      const dayNames = ["日", "一", "二", "三", "四", "五", "六"];
      parts.push(data.weekdays.map((d) => `周${dayNames[d]}`).join("、"));
    }
    if (data.monthDays?.length) {
      parts.push(`每月${data.monthDays.join("、")}日`);
    }
    return parts.length ? `${base}（${parts.join("，")}）` : base;
  } catch {
    return base;
  }
}


