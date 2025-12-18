/**
 * 通用工具函数
 */

/**
 * 创建播放列表ID
 * @returns {string} 播放列表ID
 */
export function createPlaylistId() {
  return `pl_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
}

/**
 * 格式化日期时间为字符串
 * @returns {string} 格式化的日期时间字符串，格式：YYYY-MM-DD HH:MM:SS
 */
export function formatDateTime() {
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
 * 格式化时长（秒）为可读格式
 * @param {number} seconds - 秒数
 * @returns {string} 格式化的时长字符串，如 "3:45" 或 "1:23:45"
 */
export function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return "";
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }
  return `${minutes}:${String(secs).padStart(2, "0")}`;
}

/**
 * 格式化时长（分钟）为可读格式
 * @param {number} minutes - 分钟数
 * @returns {string} 格式化的时长字符串，如 "1小时 30分钟" 或 "不停止"
 */
export function formatDurationMinutes(minutes) {
  if (!minutes || minutes === 0) return "不停止";
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;

  const parts = [];
  if (hours > 0) {
    parts.push(`${hours}小时`);
  }
  if (mins > 0) {
    parts.push(`${mins}分钟`);
  }

  return parts.length > 0 ? parts.join(" ") : "0分钟";
}

/**
 * 格式化文件大小
 * @param {number} bytes - 字节数
 * @returns {string} 格式化的文件大小字符串，如 "1.5 MB"
 */
export function formatSize(bytes) {
  if (!bytes) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}

/**
 * 解析 Cron 字段表达式
 * @param {string} expr - Cron 字段表达式
 * @param {number} min - 最小值
 * @param {number} max - 最大值
 * @returns {Array<number>|null} 解析后的值数组，或 null 表示匹配所有值
 */
export function parseCronField(expr, min, max) {
  if (expr === "*") {
    return null; // null 表示匹配所有值
  }
  if (!expr || typeof expr !== 'string') {
    return null;
  }

  const values = new Set();
  const parts = String(expr).split(",");

  for (const part of parts) {
    const trimmed = part.trim();
    if (trimmed.includes("/")) {
      // 步长：*/30 或 0-59/10
      const [range, step] = trimmed.split("/");
      const stepNum = parseInt(step, 10);
      if (range === "*") {
        for (let i = min; i <= max; i += stepNum) {
          values.add(i);
        }
      } else if (range.includes("-")) {
        const [start, end] = range.split("-").map((x) => parseInt(x, 10));
        for (let i = start; i <= end; i += stepNum) {
          values.add(i);
        }
      }
    } else if (trimmed.includes("-")) {
      // 范围：1-5
      const [start, end] = trimmed.split("-").map((x) => parseInt(x, 10));
      for (let i = start; i <= end; i++) {
        values.add(i);
      }
    } else {
      // 单个值
      const val = parseInt(trimmed, 10);
      if (!isNaN(val) && val >= min && val <= max) {
        values.add(val);
      }
    }
  }

  return values.size > 0 ? Array.from(values).sort((a, b) => a - b) : null;
}

/**
 * 计算 Cron 表达式的下 N 次执行时间
 * @param {string} cronExpr - Cron 表达式（6个字段：秒 分 时 日 月 周）
 * @param {number} count - 需要计算的次数，默认 3
 * @returns {Array<string>} 执行时间数组，格式：["YYYY-MM-DD HH:MM:SS", ...]
 */
export function calculateNextCronTimes(cronExpr, count = 3) {
  try {
    if (!cronExpr || typeof cronExpr !== 'string') {
      throw new Error("Cron 表达式必须是字符串类型");
    }
    const parts = String(cronExpr).trim().split(/\s+/);
    if (parts.length !== 6) {
      throw new Error("Cron 表达式必须包含6个字段：秒 分 时 日 月 周");
    }

    const [secExpr, minExpr, hourExpr, dayExpr, monthExpr, weekdayExpr] = parts;

    // 解析各个字段
    const seconds = parseCronField(secExpr, 0, 59);
    const minutes = parseCronField(minExpr, 0, 59);
    const hours = parseCronField(hourExpr, 0, 23);
    const days = parseCronField(dayExpr, 1, 31);
    const months = parseCronField(monthExpr, 1, 12);
    let weekdays = parseCronField(weekdayExpr, 0, 7);

    // 处理周字段：7 和 0 都表示周日
    if (weekdays && weekdays.includes(7)) {
      weekdays = weekdays.filter((d) => d !== 7);
      if (!weekdays.includes(0)) {
        weekdays.push(0);
      }
      weekdays.sort((a, b) => a - b);
    }

    const times = [];
    const current = new Date();
    current.setMilliseconds(0);

    // 如果当前秒不在范围内，跳到下一分钟
    if (seconds && !seconds.includes(current.getSeconds())) {
      current.setSeconds(0);
      current.setMinutes(current.getMinutes() + 1);
    }

    let iterations = 0;
    const maxIterations = 10000;

    while (times.length < count && iterations < maxIterations) {
      iterations++;

      // 检查月份
      const currentMonth = current.getMonth() + 1; // getMonth() 返回 0-11
      if (months && !months.includes(currentMonth)) {
        // 跳到下一个有效月份的第一天
        let nextMonth = null;
        for (const m of months) {
          if (m > currentMonth) {
            nextMonth = m;
            break;
          }
        }
        if (nextMonth === null) {
          // 跳到下一年的第一个有效月份
          nextMonth = months[0];
          current.setFullYear(current.getFullYear() + 1, nextMonth - 1, 1);
          current.setHours(0, 0, seconds ? seconds[0] : 0);
        } else {
          current.setMonth(nextMonth - 1, 1);
          current.setHours(0, 0, seconds ? seconds[0] : 0);
        }
        continue;
      }

      // 检查日期和星期
      const currentDay = current.getDate();
      const currentWeekday = current.getDay(); // 0=周日, 1=周一, ..., 6=周六

      let validDay = true;
      if (dayExpr !== "*" && weekdayExpr !== "*") {
        // 两个都指定，满足任意一个即可（OR逻辑）
        validDay =
          (days && days.includes(currentDay)) ||
          (weekdays && weekdays.includes(currentWeekday));
      } else if (dayExpr !== "*") {
        // 只检查日期
        validDay = days && days.includes(currentDay);
      } else if (weekdayExpr !== "*") {
        // 只检查星期
        validDay = weekdays && weekdays.includes(currentWeekday);
      }

      if (!validDay) {
        current.setDate(current.getDate() + 1);
        current.setHours(0, 0, seconds ? seconds[0] : 0);
        continue;
      }

      // 检查小时
      const currentHour = current.getHours();
      if (hours && !hours.includes(currentHour)) {
        // 跳到下一个有效小时
        let nextHour = null;
        for (const h of hours) {
          if (h > currentHour) {
            nextHour = h;
            break;
          }
        }
        if (nextHour === null) {
          // 跳到下一天的第一个有效小时
          current.setDate(current.getDate() + 1);
          current.setHours(hours[0], 0, seconds ? seconds[0] : 0);
        } else {
          current.setHours(nextHour, 0, seconds ? seconds[0] : 0);
        }
        continue;
      }

      // 检查分钟
      const currentMinute = current.getMinutes();
      if (minutes && !minutes.includes(currentMinute)) {
        // 跳到下一个有效分钟
        let nextMinute = null;
        for (const m of minutes) {
          if (m > currentMinute) {
            nextMinute = m;
            break;
          }
        }
        if (nextMinute === null) {
          // 跳到下一个有效小时的第一分钟
          let nextHour = null;
          for (const h of hours || [currentHour]) {
            if (h > currentHour) {
              nextHour = h;
              break;
            }
          }
          if (nextHour === null) {
            current.setDate(current.getDate() + 1);
            current.setHours(hours ? hours[0] : 0, minutes[0], seconds ? seconds[0] : 0);
          } else {
            current.setHours(nextHour, minutes[0], seconds ? seconds[0] : 0);
          }
        } else {
          current.setMinutes(nextMinute, seconds ? seconds[0] : 0);
        }
        continue;
      }

      // 检查秒
      const currentSecond = current.getSeconds();
      if (seconds && !seconds.includes(currentSecond)) {
        // 跳到下一个有效秒
        let nextSecond = null;
        for (const s of seconds) {
          if (s > currentSecond) {
            nextSecond = s;
            break;
          }
        }
        if (nextSecond === null) {
          // 跳到下一分钟的第一个有效秒
          current.setMinutes(current.getMinutes() + 1);
          current.setSeconds(seconds[0]);
        } else {
          current.setSeconds(nextSecond);
        }
        continue;
      }

      // 检查是否在未来
      if (current > new Date()) {
        const timeStr =
          current.getFullYear() +
          "-" +
          String(current.getMonth() + 1).padStart(2, "0") +
          "-" +
          String(current.getDate()).padStart(2, "0") +
          " " +
          String(current.getHours()).padStart(2, "0") +
          ":" +
          String(current.getMinutes()).padStart(2, "0") +
          ":" +
          String(current.getSeconds()).padStart(2, "0");
        times.push(timeStr);
      }

      // 移动到下一个可能的执行时间
      if (seconds && seconds.length > 0) {
        current.setSeconds(seconds[0]);
      }
      current.setMinutes(current.getMinutes() + 1);
    }

    return times.slice(0, count);
  } catch (error) {
    console.error("计算 Cron 执行时间失败:", error);
    throw error;
  }
}

/**
 * 生成 Cron 表达式
 * @param {Object} builder - Cron 构建器对象
 * @returns {string} 生成的 Cron 表达式
 */
export function generateCronExpression(builder) {
  const second =
    builder.second === "custom" ? builder.secondCustom || "*" : builder.second || "*";
  const minute =
    builder.minute === "custom" ? builder.minuteCustom || "*" : builder.minute || "*";
  const hour = builder.hour === "custom" ? builder.hourCustom || "*" : builder.hour || "*";
  const day = builder.day === "custom" ? builder.dayCustom || "*" : builder.day || "*";
  const month =
    builder.month === "custom" ? builder.monthCustom || "*" : builder.month || "*";
  const weekday =
    builder.weekday === "custom" ? builder.weekdayCustom || "*" : builder.weekday || "*";

  return `${second} ${minute} ${hour} ${day} ${month} ${weekday}`;
}
