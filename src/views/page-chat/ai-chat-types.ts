export type ChatMsgStatus =
  | "sending"
  | "thinking"
  | "streaming"
  | "done"
  | "error"
  | "stopped"
  | "recognizing";

export interface ChatMsg {
  bubbleKey: string;
  id?: string | number;
  content: string;
  role: string;
  audioSrc?: string;
  /** TTS 已请求、尚未收到首包音频 */
  audioLoading?: boolean;
  playing?: boolean;
  ts?: string;
  type?: string;
  status?: ChatMsgStatus;
  clientRequestId?: string;
  retryText?: string;
  retryKind?: "text" | "voice";
  errorMessage?: string;
  /**
   * 用户消息随附的图片文件名（pic 目录里的名字）。
   * 渲染时用 `/api/pic/view?name=<filename>` 拼 URL，不需要额外映射。
   */
  images?: string[];
}
