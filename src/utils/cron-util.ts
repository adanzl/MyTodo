/**
 * Cron 表达式工具函数
 */

/**
 * 计算下次执行时间
 * @param cronExpr cron表达式 (秒 分 时 日 月 周)
 * @returns 格式化的下次执行时间字符串，格式: MM-DD HH:mm 周X
 */
export function getNextCronTime(cronExpr: string): string | null {
  if (!cronExpr) return null;
  
  try {
    const trimmed = cronExpr.trim();
    if (!trimmed) return null;
    
    // 解析cron表达式 (秒 分 时 日 月 周)
    const parts = trimmed.split(/\s+/);
    if (parts.length !== 6) return null;
    
    const [second, minute, hour] = parts;
    const now = new Date();
    const nextTime = new Date(now);
    nextTime.setMilliseconds(0);
    
    // 设置秒、分钟和小时
    const targetHour = hour === '*' ? now.getHours() : parseInt(hour);
    const targetMinute = minute === '*' ? now.getMinutes() : parseInt(minute);
    const targetSecond = second === '*' ? now.getSeconds() : parseInt(second);
    
    nextTime.setHours(targetHour, targetMinute, targetSecond);
    
    // 如果时间已过，推到下一分钟
    if (nextTime <= now) {
      nextTime.setMinutes(nextTime.getMinutes() + 1);
      nextTime.setSeconds(targetSecond);
    }
    
    // 格式化输出
    const monthStr = String(nextTime.getMonth() + 1).padStart(2, '0');
    const dayStr = String(nextTime.getDate()).padStart(2, '0');
    const hourStr = String(nextTime.getHours()).padStart(2, '0');
    const minuteStr = String(nextTime.getMinutes()).padStart(2, '0');
    
    const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    const weekdayStr = weekdays[nextTime.getDay()];
    
    return `${monthStr}-${dayStr} ${hourStr}:${minuteStr} ${weekdayStr}`;
  } catch (error) {
    console.error('解析cron表达式失败:', error);
    return null;
  }
}
