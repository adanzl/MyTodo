/**
 * 通用工具函数
 */

/**
 * 处理 API 错误
 * @param {Error} error - 错误对象
 * @param {string} defaultMessage - 默认错误消息
 * @param {Object} options - 可选参数
 * @param {string} options.context - 额外的上下文信息（用于 console.error）
 */
export function logAndNoticeError(error, defaultMessage, options = {}) {
  const { context } = options;
  const errorContext = context ? `${defaultMessage} (${context})` : defaultMessage;
  console.error(errorContext, error);

  const { ElMessage } = window.ElementPlus;
  const errorMessage = error?.response?.data?.msg || error?.message || "未知错误";
  ElMessage.error(`${defaultMessage}: ${errorMessage}`);
}

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
 * 格式化日期时间，包含星期
 * @param {string} dateStr - 日期时间字符串，格式：YYYY-MM-DD HH:mm:ss
 * @returns {string|null} 格式化的日期时间字符串，包含星期，如 "2024-01-01 周一 12:00:00"
 */
export function formatDateTimeWithWeekday(dateStr) {
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
 * 格式化时长（秒）为可读格式
 * @param {number} seconds - 秒数
 * @returns {string} 格式化的时长字符串，如 "3:45" 或 "1:23:45"
 */
export function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return "";
  // 确保秒数是整数，避免显示小数
  const totalSeconds = Math.floor(seconds);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const secs = totalSeconds % 60;
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

/**
 * 获取当前星期对应的索引（0=周一，6=周日）
 * @returns {number} 星期索引，0表示周一，6表示周日
 */
export function getWeekdayIndex() {
  const weekday = new Date().getDay(); // 0=周日，1=周一，...，6=周六
  return weekday === 0 ? 6 : weekday - 1; // 转换为 0=周一，6=周日
}

/**
 * 从文件项中提取文件名
 * @param {Object} fileItem - 文件项对象，可能包含 uri、path 或 file 属性
 * @returns {string} 文件名
 */
export function getFileName(fileItem) {
  const filePath = fileItem?.uri || fileItem?.path || fileItem?.file || '';
  return filePath ? String(filePath).split("/").pop() || filePath : '';
}

/**
 * 规范化文件列表格式（对象格式）
 * @param {Array} files - 文件列表
 * @param {boolean} includeDuration - 是否包含时长信息，默认 true
 * @returns {Array} 规范化后的文件列表
 */
export function normalizeFiles(files, includeDuration = true) {
  if (!Array.isArray(files)) return [];
  return files.map((fileItem) => {
    if (!fileItem || typeof fileItem !== "object") return null;
    const normalized = {
      uri: fileItem.uri,
    };
    if (includeDuration) {
      normalized.duration = fileItem.duration || null;
    }
    return normalized;
  }).filter((item) => item !== null);
}

/**
 * 计算文件列表总时长（秒）
 * @param {Array} files - 文件列表
 * @returns {number} 总时长（秒）
 */
export function calculateFilesTotalDuration(files) {
  if (!Array.isArray(files) || files.length === 0) {
    return 0;
  }
  return files.reduce((total, file) => {
    const duration = file?.duration;
    return total + (typeof duration === 'number' && duration > 0 ? duration : 0);
  }, 0);
}

/**
 * 获取媒体文件的播放URL
 * @param {string} filePath - 本地文件路径
 * @param {Function} getApiUrl - 获取API基础URL的函数
 * @returns {string} HTTP URL
 */
export function getMediaFileUrl(filePath, getApiUrl) {
  if (!filePath || typeof filePath !== 'string' || filePath.trim() === '') {
    console.warn('getMediaFileUrl: 文件路径无效', filePath);
    return '';
  }
  if (!getApiUrl || typeof getApiUrl !== 'function') {
    console.warn('getMediaFileUrl: getApiUrl 函数未提供');
    return '';
  }

  try {
    const apiUrl = getApiUrl();
    if (!apiUrl || typeof apiUrl !== 'string') {
      console.warn('getMediaFileUrl: API URL无效', apiUrl);
      return '';
    }

    const path = filePath.startsWith('/') ? filePath.slice(1) : filePath;
    if (!path || path.trim() === '') {
      console.warn('getMediaFileUrl: 处理后的路径为空', filePath);
      return '';
    }

    const encodedPath = path.split('/').map(part => encodeURIComponent(part)).join('/');
    const mediaUrl = `${apiUrl}/media/files/${encodedPath}`;

    // 验证生成的 URL
    if (mediaUrl.includes('index.html') || mediaUrl.endsWith('.html')) {
      console.error('getMediaFileUrl: 生成的URL包含HTML页面', { filePath, mediaUrl });
      return '';
    }

    return mediaUrl;
  } catch (error) {
    console.error('getMediaFileUrl: 生成URL时出错', error, { filePath });
    return '';
  }
}
