/**
 * 聊天室消息里图片文件名的解析。
 *
 * 与 AI 对话不同，聊天室不经过 Dify：图片由前端调 `/api/pic/upload` 存到本服务，
 * 消息里只带**文件名**，收发双方都用 `/pic/view?name=<filename>` 渲染。
 * 文件名由上传时的 `chat-<userId>-<时间戳>.<ext>` 保证唯一。
 *
 * 抽成独立模块有两个原因：组件用的是 `<script setup>`（不能包含 ES 导出），
 * 以及这里的分支需要能单独测试。
 */

/**
 * 从消息体的 `files` 字段取出图片文件名。
 *
 * 兼容两种形态：字符串数组（前端可能只传名字）与对象数组
 * （`{type, filename}`，与 AI 侧保持一致）。非法输入一律返回空数组，
 * 不抛异常——一条格式异常的历史消息不该让整个房间加载失败。
 */
export function roomImageFilenames(files: unknown): string[] {
  if (!Array.isArray(files)) return [];
  const names: string[] = [];
  for (const item of files) {
    const name =
      typeof item === "string"
        ? item
        : (item as { filename?: unknown })?.filename;
    if (typeof name === "string" && name.trim()) names.push(name.trim());
  }
  return names;
}
