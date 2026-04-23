/**
 * 日期时间工具函数
 */
import dayjs, { type Dayjs } from "dayjs";

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
  const start = dayjs(startDate);
  const target = dayjs(targetDate);
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
