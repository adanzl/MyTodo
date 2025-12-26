/**
 * 格式化工具函数
 */

/**
 * 格式化时长（秒）为可读格式
 */
export function formatDuration(seconds: number): string {
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
 */
export function formatDurationMinutes(minutes: number): string {
  if (!minutes || minutes === 0) return "不停止";
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;

  const parts: string[] = [];
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
 */
export function formatSize(bytes: number): string {
  if (!bytes) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + " " + sizes[i];
}

