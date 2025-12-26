/**
 * 文件相关工具函数
 */
import { getApiUrl } from "@/api/config";

interface FileItem {
  uri?: string;
  path?: string;
  file?: string;
  duration?: number | null;
}

interface NormalizedFile {
  uri: string;
  duration?: number | null;
}

/**
 * 从文件项中提取文件名
 */
export function getFileName(fileItem: FileItem | null | undefined): string {
  const filePath = fileItem?.uri || fileItem?.path || fileItem?.file || "";
  return filePath ? String(filePath).split("/").pop() || filePath : "";
}

/**
 * 规范化文件列表格式（对象格式）
 */
export function normalizeFiles(
  files: FileItem[],
  includeDuration = true
): NormalizedFile[] {
  if (!Array.isArray(files)) return [];
  return files
    .map((fileItem) => {
      if (!fileItem || typeof fileItem !== "object") return null;
      const normalized: NormalizedFile = {
        uri: fileItem.uri || "",
      };
      if (includeDuration) {
        normalized.duration = fileItem.duration || null;
      }
      return normalized;
    })
    .filter((item): item is NormalizedFile => item !== null);
}

/**
 * 计算文件列表总时长（秒）
 */
export function calculateFilesTotalDuration(files: FileItem[]): number {
  if (!Array.isArray(files) || files.length === 0) {
    return 0;
  }
  return files.reduce((total, file) => {
    const duration = file?.duration;
    return total + (typeof duration === "number" && duration > 0 ? duration : 0);
  }, 0);
}

/**
 * 获取媒体文件的播放URL
 */
export function getMediaFileUrl(filePath: string): string {
  if (!filePath || typeof filePath !== "string" || filePath.trim() === "") {
    console.warn("getMediaFileUrl: 文件路径无效", filePath);
    return "";
  }

  try {
    const apiUrl = getApiUrl();
    if (!apiUrl || typeof apiUrl !== "string") {
      console.warn("getMediaFileUrl: API URL无效", apiUrl);
      return "";
    }

    const path = filePath.startsWith("/") ? filePath.slice(1) : filePath;
    if (!path || path.trim() === "") {
      console.warn("getMediaFileUrl: 处理后的路径为空", filePath);
      return "";
    }

    const encodedPath = path.split("/").map((part) => encodeURIComponent(part)).join("/");
    const mediaUrl = `${apiUrl}/media/files/${encodedPath}`;

    // 验证生成的 URL
    if (mediaUrl.includes("index.html") || mediaUrl.endsWith(".html")) {
      console.error("getMediaFileUrl: 生成的URL包含HTML页面", { filePath, mediaUrl });
      return "";
    }

    return mediaUrl;
  } catch (error) {
    console.error("getMediaFileUrl: 生成URL时出错", error, { filePath });
    return "";
  }
}


