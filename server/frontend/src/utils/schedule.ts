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
  type RepeatOption,
  type PriorityOption,
  type GroupOption,
} from "@/constants/schedule";

interface RepeatData {
  week?: number[];
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
    ret = date.add(1, repeat.tag as any);
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
      repeatData.week.sort();
      const day = date.day();
      const idx = _.sortedIndex(repeatData.week, day);
      if (idx === ln) {
        const d = 7 - day + repeatData.week[0];
        ret = date.add(d, "day");
      } else {
        if (repeatData.week[idx] == day) {
          const d = (repeatData.week[(idx + 1) % ln] + 7 - day) % 7;
          ret = date.add(d, "day");
        } else {
          const d = repeatData.week[idx] - day;
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


