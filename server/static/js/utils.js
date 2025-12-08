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
