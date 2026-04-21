/**
 * 文件相关工具函数
 */
import { getApiUrl } from "@/api/api-client";

/**
 * 获取媒体文件的播放URL
 * @param filePath - 文件路径
 * @returns 完整的媒体文件 URL
 */
export function getMediaFileUrl(filePath: string): string {
  if (!filePath || typeof filePath !== "string" || filePath.trim() === "") {
    console.warn("getMediaFileUrl: 文件路径无效", filePath);
    return "";
  }

  try {
    const baseURL = getApiUrl();
    if (!baseURL || typeof baseURL !== "string") {
      console.warn("getMediaFileUrl: API baseURL无效", baseURL);
      return "";
    }

    const path = filePath.startsWith("/") ? filePath.slice(1) : filePath;
    if (!path || path.trim() === "") {
      console.warn("getMediaFileUrl: 处理后的路径为空", filePath);
      return "";
    }

    const encodedPath = path
      .split("/")
      .map(part => encodeURIComponent(part))
      .join("/");
    const mediaUrl = `${baseURL}/media/files/${encodedPath}`;

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
