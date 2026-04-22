/**
 * 日期工具函数
 */
import dayjs from 'dayjs';

/**
 * 获取今天的日期字符串（YYYY-MM-DD）
 */
export function getTodayStr(): string {
  return dayjs().format('YYYY-MM-DD');
}

/**
 * 格式化日期为 YYYY-MM-DD
 * @param date - 日期对象或字符串
 */
export function formatDate(date: dayjs.ConfigType): string {
  return dayjs(date).format('YYYY-MM-DD');
}

/**
 * 增加天数
 * @param date - 日期对象或字符串
 * @param days - 增加的天数
 */
export function addDays(date: dayjs.ConfigType, days: number): Date {
  return dayjs(date).add(days, 'day').toDate();
}

/**
 * 减少天数
 * @param date - 日期对象或字符串
 * @param days - 减少的天数
 */
export function subtractDays(date: dayjs.ConfigType, days: number): Date {
  return dayjs(date).subtract(days, 'day').toDate();
}

/**
 * 计算两个日期之间的天数差
 * @param date1 - 日期1
 * @param date2 - 日期2
 */
export function diffDays(date1: dayjs.ConfigType, date2: dayjs.ConfigType): number {
  return dayjs(date1).diff(dayjs(date2), 'day');
}

/**
 * 判断日期是否在范围内
 * @param date - 要判断的日期
 * @param startDate - 开始日期
 * @param endDate - 结束日期
 */
export function isDateInRange(
  date: dayjs.ConfigType,
  startDate: dayjs.ConfigType,
  endDate: dayjs.ConfigType
): boolean {
  const d = dayjs(date);
  const start = dayjs(startDate);
  const end = dayjs(endDate);
  return d.isAfter(start.subtract(1, 'day')) && d.isBefore(end.add(1, 'day'));
}
