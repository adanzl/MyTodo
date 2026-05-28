/**
 * 日期时间工具函数
 */
import dayjs, { type Dayjs } from "dayjs";

export type RestDaysRule = {
  weekdays?: number[]; // 0=周日..6=周六
  dates?: string[]; // YYYY-MM-DD，强制休息
  work_dates?: string[]; // YYYY-MM-DD，强制工作（覆盖 weekdays/dates）
};

const DAY_FMT = "YYYY-MM-DD";

function toDayKey(dt: Dayjs | Date | string): string {
  return dayjs(dt).startOf("day").format(DAY_FMT);
}

function normalizeWeekdays(raw?: unknown): number[] {
  if (!Array.isArray(raw)) return [];
  const set = new Set<number>();
  for (const v of raw) {
    const n = typeof v === "number" ? v : Number(v);
    if (!Number.isFinite(n)) continue;
    const i = Math.trunc(n);
    if (i >= 0 && i <= 6) set.add(i);
  }
  return Array.from(set).sort((a, b) => a - b);
}

function normalizeDateList(raw?: unknown): string[] {
  if (!Array.isArray(raw)) return [];
  const set = new Set<string>();
  for (const v of raw) {
    if (typeof v !== "string") continue;
    const d = dayjs(v, DAY_FMT, true);
    if (!d.isValid()) continue;
    set.add(d.format(DAY_FMT));
  }
  return Array.from(set).sort();
}

export function parseRestDays(restDays: unknown): Required<RestDaysRule> {
  let obj: any = restDays;
  if (!obj) return { weekdays: [], dates: [], work_dates: [] };
  if (typeof obj === "string") {
    try {
      obj = JSON.parse(obj);
    } catch {
      return { weekdays: [], dates: [], work_dates: [] };
    }
  }
  if (!obj || typeof obj !== "object") return { weekdays: [], dates: [], work_dates: [] };
  return {
    weekdays: normalizeWeekdays(obj.weekdays),
    dates: normalizeDateList(obj.dates),
    work_dates: normalizeDateList(obj.work_dates),
  };
}

export function isRestDay(restDays: unknown, date: Dayjs | Date | string): boolean {
  const rule = parseRestDays(restDays);
  const dayKey = toDayKey(date);
  // work_dates 覆盖一切
  if (rule.work_dates.includes(dayKey)) return false;
  if (rule.dates.includes(dayKey)) return true;
  if (rule.weekdays.length === 0) return false;
  const weekday = dayjs(dayKey, DAY_FMT, true).day(); // 0=周日..6=周六
  return rule.weekdays.includes(weekday);
}

/**
 * 计算 date 对应的“工作日序号”(0-based)，休息日不计入序号。
 * - date < startDate: 返回 -1
 * - 休息日当天：返回与前一个工作日相同的序号（单调不减）
 */
export function getWorkdayIndex(startDate: string, date: Dayjs | Date | string, restDays?: unknown): number {
  const start = dayjs(startDate).startOf("day");
  const target = dayjs(date).startOf("day");
  if (!start.isValid() || !target.isValid()) return -1;
  if (target.isBefore(start)) return -1;

  let idx = -1;
  const dayDiff = target.diff(start, "day");
  for (let i = 0; i <= dayDiff; i++) {
    const cur = start.add(i, "day");
    if (isRestDay(restDays, cur)) continue;
    idx++;
  }
  return idx;
}

/**
 * 给定工作日序号 idx(0-based)，反推出实际日期（会跳过休息日）。
 * idx < 0 时返回 startDate 当天（用于容错）
 */
export function getDateByWorkdayIndex(startDate: string, idx: number, restDays?: unknown): Dayjs {
  const start = dayjs(startDate).startOf("day");
  if (!start.isValid()) return dayjs().startOf("day");
  if (idx <= 0) {
    // idx=0 代表第1个工作日；可能 start 本身是休息日，需要向后找
    let d = start;
    while (isRestDay(restDays, d)) d = d.add(1, "day");
    return d;
  }

  let d = start;
  let seen = -1;
  while (true) {
    if (!isRestDay(restDays, d)) {
      seen++;
      if (seen === idx) return d;
    }
    d = d.add(1, "day");
  }
}

/** 任务结束日期（最后一个工作日），返回 YYYY-MM-DD */
export function getTaskEndDate(startDate: string, duration: number, restDays?: unknown): string {
  if (!duration || duration <= 0) return "";
  const end = getDateByWorkdayIndex(startDate, duration - 1, restDays);
  return end.format(DAY_FMT);
}

const WEEKDAY_LABELS_ZH: Record<number, string> = {
  0: "周日",
  1: "周一",
  2: "周二",
  3: "周三",
  4: "周四",
  5: "周五",
  6: "周六",
};

export function formatRestDaysFullText(restDays: unknown): string {
  const rule = parseRestDays(restDays);
  const parts: string[] = [];
  if (rule.weekdays.length) {
    parts.push(`每周休：${rule.weekdays.map((d) => WEEKDAY_LABELS_ZH[d] ?? String(d)).join("、")}`);
  }
  if (rule.dates.length) {
    parts.push(`指定休：${rule.dates.join("、")}`);
  }
  if (rule.work_dates.length) {
    parts.push(`补班：${rule.work_dates.join("、")}`);
  }
  return parts.join("；");
}

/**
 * 格式化日期时间为字符串
 * @returns 格式化的日期时间字符串，格式：YYYY-MM-DD HH:MM:SS
 */
export function formatDateTime(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  const hours = String(now.getHours()).padStart(2, "0");
  const minutes = String(now.getMinutes()).padStart(2, "0");
  const seconds = String(now.getSeconds()).padStart(2, "0");
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

/**
 * 格式化日期时间，包含星期
 * @param dateStr - 日期时间字符串，格式：YYYY-MM-DD HH:mm:ss
 * @returns 格式化的日期时间字符串，包含星期，如 "2024-01-01 周一 12:00:00"
 */
export function formatDateTimeWithWeekday(dateStr: string): string | null {
  if (!dateStr) return null;
  try {
    // 解析格式: "YYYY-MM-DD HH:mm:ss"
    const parts = dateStr.match(/(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})/);
    if (!parts) return dateStr;

    const year = parseInt(parts[1], 10);
    const month = parseInt(parts[2], 10) - 1; // 月份从0开始
    const day = parseInt(parts[3], 10);
    const hours = parseInt(parts[4], 10);
    const minutes = parseInt(parts[5], 10);
    const seconds = parseInt(parts[6], 10);

    const date = new Date(year, month, day, hours, minutes, seconds);
    const weekdays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
    const weekday = weekdays[date.getDay()];

    return `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(
      2,
      "0"
    )} ${weekday} ${String(hours).padStart(2, "0")}:${String(minutes).padStart(
      2,
      "0"
    )}:${String(seconds).padStart(2, "0")}`;
  } catch (error) {
    console.error("格式化日期时间失败:", error);
    return dateStr;
  }
}

/**
 * 获取当前星期对应的索引（0=周一，6=周日）
 * @returns 星期索引，0表示周一，6表示周日
 */
export function getWeekdayIndex(): number {
  const weekday = new Date().getDay(); // 0=周日，1=周一，...，6=周六
  return weekday === 0 ? 6 : weekday - 1; // 转换为 0=周一，6=周日
}

/**
 * 日期转字符串（YYYY-MM-DD）
 * @param dt - 日期对象（dayjs 对象或 Date 对象）
 * @returns 格式化的日期字符串
 */
export function S_TS(dt: Dayjs | Date | string | undefined): string {
  if (dt === undefined) return "";
  if (typeof dt === "object" && "format" in dt && typeof dt.format === "function") {
    return dt.format("YYYY-MM-DD");
  }
  // 如果不是 dayjs 对象，尝试转换
  return dayjs(dt).format("YYYY-MM-DD");
}

/**
 * 格式化日期（简短）
 * @param date - 日期对象
 * @returns 格式化的日期字符串，如 "4/21"
 */
export function formatDateShort(date: Date): string {
  const month = date.getMonth() + 1;
  const day = date.getDate();
  return `${month}/${day}`;
}

/**
 * 获取星期
 * @param date - 日期对象
 * @returns 星期字符串，如 "周一"
 */
export function getWeekDay(date: Date): string {
  const weekDays = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"];
  return weekDays[date.getDay()];
}

/**
 * 计算两个日期之间的天数差
 * @param startDate - 开始日期（YYYY-MM-DD 格式字符串）
 * @param targetDate - 目标日期（Date 对象）
 * @returns 天数差（从0开始）
 */
export function getDaysDiff(startDate: string, targetDate: Date): number {
  // 确保startDate被正确解析为本地时间的开始（00:00:00）
  const start = dayjs(startDate).startOf('day');
  // 确保targetDate也被转换为同一天的开始（00:00:00）
  const target = dayjs(targetDate).startOf('day');
  return target.diff(start, "day");
}

/**
 * 格式化日期为 YYYY-MM-DD
 * @param date - 日期对象或字符串
 * @returns 格式化的日期字符串
 */
export function formatDate(date: Date | string): string {
  return dayjs(date).format("YYYY-MM-DD");
}

/**
 * 生成连续日期数组
 * @param startDate - 开始日期（Date 对象或字符串）
 * @param count - 天数
 * @returns 日期数组
 */
export function generateDateRange(startDate: Date | string, count: number): Date[] {
  const dates: Date[] = [];
  const start = dayjs(startDate);
  for (let i = 0; i < count; i++) {
    dates.push(start.add(i, "day").toDate());
  }
  return dates;
}

/**
 * 格式化时间为 mm:ss 格式
 * @param seconds - 秒数
 * @returns 格式化的时间字符串，如 "3:05"
 */
export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}
