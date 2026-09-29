import type { ChatMsg, ChatMsgStatus } from "@/views/page-chat/ai-chat-types";

let bubbleSeq = 0;

export function newBubbleKey(prefix = "b"): string {
  bubbleSeq += 1;
  return `${prefix}-${Date.now()}-${bubbleSeq}`;
}

export function historyBubbleKey(id: string | number, role: string): string {
  return `hist-${id}-${role}`;
}

const TERMINAL: ChatMsgStatus[] = ["done", "error", "stopped"];

function isTerminal(status: ChatMsgStatus | undefined): boolean {
  return status !== undefined && TERMINAL.includes(status);
}

export function findServerByClientRequestId(
  messages: ChatMsg[],
  clientRequestId: string
): ChatMsg | undefined {
  return messages.find(
    (m) => m.role === "server" && m.clientRequestId === clientRequestId
  );
}

export function findUserByClientRequestId(
  messages: ChatMsg[],
  clientRequestId: string
): ChatMsg | undefined {
  return messages.find(
    (m) => m.role === "me" && m.clientRequestId === clientRequestId
  );
}

export function applyChatChunkToMessages(
  messages: ChatMsg[],
  data: { clientRequestId?: string; id?: string | number; content?: string }
): boolean {
  const chunk = data.content ?? "";
  if (!chunk || !data.clientRequestId) return false;
  const target = findServerByClientRequestId(messages, data.clientRequestId);
  if (!target || isTerminal(target.status)) return false;
  if (data.id !== undefined && data.id !== "") target.id = data.id;
  if (target.status === "thinking") {
    target.status = "streaming";
    target.content = chunk;
  } else {
    target.content = (target.content ?? "") + chunk;
  }
  return true;
}

export function failServerReply(
  messages: ChatMsg[],
  clientRequestId: string,
  errorMessage: string,
  retryText?: string
): void {
  const target = findServerByClientRequestId(messages, clientRequestId);
  if (target) {
    const wasThinking =
      target.status === "thinking" &&
      (target.content === "正在思考…" || target.content === "");
    target.status = "error";
    target.errorMessage = errorMessage;
    if (retryText) target.retryText = retryText;
    if (wasThinking) target.content = "";
    return;
  }
  messages.push({
    bubbleKey: newBubbleKey("err"),
    role: "server",
    content: "",
    errorMessage,
    status: "error",
    clientRequestId,
    retryText,
  });
}

export function finishServerReply(
  messages: ChatMsg[],
  clientRequestId: string,
  opts?: { stopped?: boolean }
): void {
  if (opts?.stopped) stopVoiceRecognizing(messages, clientRequestId);
  const target = findServerByClientRequestId(messages, clientRequestId);
  if (!target) return;
  if (opts?.stopped) {
    if (target.status === "thinking") {
      target.status = "stopped";
      target.content = "已停止";
    } else if (target.status === "streaming") {
      target.status = "stopped";
    } else if (!isTerminal(target.status)) {
      target.status = "stopped";
    }
    return;
  }
  if (target.status === "thinking") {
    target.status = "done";
    if (target.content === "正在思考…") target.content = "";
  } else if (!isTerminal(target.status)) {
    target.status = "done";
  }
}

export function stopVoiceRecognizing(
  messages: ChatMsg[],
  clientRequestId: string
): void {
  const user = findUserByClientRequestId(messages, clientRequestId);
  if (user?.status === "recognizing") {
    user.status = "stopped";
    user.content = "已取消识别";
  }
}

export function failVoiceRecognizing(
  messages: ChatMsg[],
  clientRequestId: string,
  errorMessage: string,
  opts?: { retryVoice?: boolean }
): void {
  const user = findUserByClientRequestId(messages, clientRequestId);
  if (user?.status === "recognizing" || user?.status === "error") {
    if (user.content === "正在识别…") user.content = "";
    user.status = "error";
    user.errorMessage = errorMessage;
    if (opts?.retryVoice) user.retryKind = "voice";
  }
}

export function completeVoiceRecognizing(
  messages: ChatMsg[],
  clientRequestId: string,
  text: string,
  audioSrc?: string
): void {
  const user = findUserByClientRequestId(messages, clientRequestId);
  if (user) {
    user.content = text;
    user.status = "done";
    if (audioSrc) user.audioSrc = audioSrc;
  } else {
    messages.push({
      bubbleKey: newBubbleKey("me"),
      role: "me",
      content: text,
      status: "done",
      clientRequestId,
      audioSrc,
    });
  }
}
