/** 跟踪当前 AI 请求，丢弃已取消/ superseded 请求的 Socket 事件。 */
export function createAiRequestTracker() {
  let activeId: string | null = null;
  const dismissed = new Set<string>();

  function activate(id: string) {
    if (activeId) dismissed.add(activeId);
    activeId = id;
  }

  function dismiss(id: string) {
    dismissed.add(id);
    if (activeId === id) activeId = null;
  }

  function getActive(): string | null {
    return activeId;
  }

  /** 无 clientRequestId 的旧服务端事件在存在活跃请求时一律忽略。 */
  function accepts(clientRequestId: string | undefined): boolean {
    if (!clientRequestId) return activeId === null;
    if (dismissed.has(clientRequestId)) return false;
    return clientRequestId === activeId;
  }

  return { activate, dismiss, accepts, getActive };
}

export type AiRequestTracker = ReturnType<typeof createAiRequestTracker>;
