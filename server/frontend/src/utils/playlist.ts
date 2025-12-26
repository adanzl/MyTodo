/**
 * 播放列表相关工具函数
 */

/**
 * 创建播放列表ID
 */
export function createPlaylistId(): string {
  return `pl_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
}


