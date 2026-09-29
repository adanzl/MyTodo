/** AI 单次请求的显式阶段（待确认 → 处理中 → 终态）。 */
export type AiRequestPhase =
  | "outbound"
  | "asr"
  | "ai"
  | "done"
  | "failed"
  | "cancelled";

export type AiRequestKind = "text" | "voice";

export interface AiRequestRecord {
  id: string;
  kind: AiRequestKind;
  phase: AiRequestPhase;
  retryText?: string;
  /** 与后端 chat:req 记录对齐，用于丢弃同 ID 上一轮的迟到事件 */
  attempt?: number;
  /** 明确重新生成时，必须等服务端确认一个更大的 attempt。 */
  awaitingNextAttempt?: boolean;
}

/**
 * 跟踪当前 AI 请求生命周期，并丢弃已 supersede / dismiss 的 Socket 事件。
 * 替代仅用全局 isWaitingServer 的粗粒度判断。
 */
export function createAiRequestController() {
  let activeId: string | null = null;
  const dismissed = new Set<string>();
  const records = new Map<string, AiRequestRecord>();
  /** 同 clientRequestId 已见过的最大 attempt（purge 后仍保留，用于恢复与过滤旧轮次） */
  const maxAttemptById = new Map<string, number>();

  function normalizeAttempt(n?: number): number {
    return typeof n === "number" && Number.isFinite(n) && n >= 0 ? n : 0;
  }

  function rememberAttempt(id: string, attempt: number) {
    const a = normalizeAttempt(attempt);
    const prev = maxAttemptById.get(id) ?? -1;
    if (a > prev) maxAttemptById.set(id, a);
  }

  function knownAttemptForRegister(id: string): number {
    return maxAttemptById.get(id) ?? 0;
  }

  /**
   * 登记客户端即将发送的请求。attempt 由服务端拥有：
   * - 新请求从 0 开始；
   * - 明确重新生成只标记“等待更大 attempt”，不在客户端预增。
   */
  function register(
    id: string,
    kind: AiRequestKind,
    retryText?: string,
    opts?: { requireNewAttempt?: boolean }
  ) {
    if (activeId && activeId !== id) dismissed.add(activeId);
    dismissed.delete(id);
    activeId = id;
    const hasKnownAttempt = maxAttemptById.has(id);
    records.set(id, {
      id,
      kind,
      phase: "outbound",
      retryText,
      attempt: knownAttemptForRegister(id),
      awaitingNextAttempt: Boolean(opts?.requireNewAttempt && hasKnownAttempt),
    });
  }

  /** 用服务端 queryChatRequest 快照恢复原轮次，不创建新 attempt。 */
  function restore(
    id: string,
    kind: AiRequestKind,
    retryText: string | undefined,
    attempt?: number
  ) {
    if (activeId && activeId !== id) dismissed.add(activeId);
    dismissed.delete(id);
    activeId = id;
    const incoming = normalizeAttempt(attempt);
    rememberAttempt(id, incoming);
    records.set(id, {
      id,
      kind,
      phase: "outbound",
      retryText,
      attempt: incoming,
      awaitingNextAttempt: false,
    });
  }

  function get(id: string): AiRequestRecord | undefined {
    return records.get(id);
  }

  function setAttempt(id: string, attempt: number) {
    const rec = records.get(id);
    if (!rec || dismissed.has(id)) return;
    const incoming = normalizeAttempt(attempt);
    const floor = normalizeAttempt(rec.attempt);
    if (rec.awaitingNextAttempt ? incoming <= floor : incoming < floor) return;
    rec.attempt = incoming;
    rec.awaitingNextAttempt = false;
    rememberAttempt(id, incoming);
  }

  /**
   * 服务器 msgAccepted；attempt 只增不减，迟到旧确认会被拒绝。
   */
  function markAccepted(id: string, attempt?: number): boolean {
    const rec = records.get(id);
    if (!rec || dismissed.has(id)) return false;
    if (attempt !== undefined) {
      const incoming = normalizeAttempt(attempt);
      const floor = normalizeAttempt(rec.attempt);
      if (rec.awaitingNextAttempt ? incoming <= floor : incoming < floor) return false;
      rec.attempt = incoming;
      rec.awaitingNextAttempt = false;
      rememberAttempt(id, incoming);
    } else if (rec.awaitingNextAttempt) {
      return false;
    }
    if (rec.phase !== "outbound") return true;
    rec.phase = rec.kind === "voice" ? "asr" : "ai";
    return true;
  }

  function markAiPhase(id: string) {
    const rec = records.get(id);
    if (rec && !dismissed.has(id)) rec.phase = "ai";
  }

  function markTerminal(id: string, phase: "done" | "failed" | "cancelled") {
    const rec = records.get(id);
    if (rec) rec.phase = phase;
  }

  function dismiss(id: string, terminal: "failed" | "cancelled" = "cancelled") {
    dismissed.add(id);
    markTerminal(id, terminal);
    if (activeId === id) activeId = null;
  }

  function getActive(): string | null {
    return activeId;
  }

  function accepts(clientRequestId: string | undefined): boolean {
    if (!clientRequestId) return activeId === null;
    if (dismissed.has(clientRequestId)) return false;
    return clientRequestId === activeId;
  }

  /** 流式 chunk / 完成 / 错误：须已确认，且 attempt 与当前轮次一致 */
  function acceptsEvent(
    clientRequestId: string | undefined,
    attempt?: number
  ): boolean {
    if (!accepts(clientRequestId)) return false;
    if (!clientRequestId) return true;
    const rec = records.get(clientRequestId);
    if (!rec) return false;
    if (rec.phase === "outbound") return false;
    return normalizeAttempt(attempt) === normalizeAttempt(rec.attempt);
  }

  /**
   * queryChatRequest 快照：终态须与当前跟踪轮次完全一致；处理中须不低于本地轮次。
   */
  function acceptsQueryResult(
    clientRequestId: string,
    attempt: number | undefined,
    phase: string
  ): boolean {
    const incoming = normalizeAttempt(attempt);
    const terminal =
      phase === "done" || phase === "failed" || phase === "cancelled";
    const rec = records.get(clientRequestId);

    if (rec && activeId === clientRequestId && !dismissed.has(clientRequestId)) {
      const bound = normalizeAttempt(rec.attempt);
      if (rec.awaitingNextAttempt) return incoming > bound;
      if (terminal) return incoming === bound;
      return incoming >= bound;
    }

    const last = maxAttemptById.get(clientRequestId);
    // 冷恢复/重连允许服务端返回历史同一轮；只有比历史更旧的轮次才拒绝。
    return last === undefined || incoming >= last;
  }

  function isInFlight(): boolean {
    if (!activeId || dismissed.has(activeId)) return false;
    const rec = records.get(activeId);
    if (!rec) return false;
    return rec.phase === "outbound" || rec.phase === "asr" || rec.phase === "ai";
  }

  function isAwaitingServerAck(): boolean {
    if (!activeId || dismissed.has(activeId)) return false;
    return records.get(activeId)?.phase === "outbound";
  }

  function release(id: string) {
    markTerminal(id, "done");
    dismissed.add(id);
    if (activeId === id) activeId = null;
  }

  function purge(id: string) {
    const rec = records.get(id);
    if (rec?.attempt !== undefined) rememberAttempt(id, rec.attempt);
    records.delete(id);
    dismissed.delete(id);
  }

  return {
    register,
    restore,
    get,
    markAccepted,
    setAttempt,
    markAiPhase,
    markTerminal,
    dismiss,
    release,
    getActive,
    accepts,
    acceptsEvent,
    acceptsQueryResult,
    isInFlight,
    isAwaitingServerAck,
    purge,
  };
}

export type AiRequestController = ReturnType<typeof createAiRequestController>;
