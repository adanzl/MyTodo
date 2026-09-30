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
}
