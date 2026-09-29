export type ChatMsgStatus =
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
  playing?: boolean;
  ts?: string;
  type?: string;
  status?: ChatMsgStatus;
  clientRequestId?: string;
  retryText?: string;
  retryKind?: "text" | "voice";
  errorMessage?: string;
}
