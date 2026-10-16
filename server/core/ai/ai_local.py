"""Dify AI（本地/私有化）客户端封装。

`AILocal` 提供：
- 流式对话请求（SSE 形式的 `data:` 行）；
- 取消流式任务；
- 拉取历史消息。

该类被 `core/chat/chat_mgr.py` 用作对话与语音链路的一环。
"""

import json

import requests

from core.chat import chat_request_store
from core.config import app_logger, config

log = app_logger
API_URL = config.AI_DIFY_API_URL
LEO_USER = "leo"
CANCAN_USER = "灿灿"

# 建连超时（秒）：DNS + TCP + TLS 正常在 1s 内完成，5s 足够覆盖抖动，超了就是不可达。
CONNECT_TIMEOUT = 5
# 流式（SSE）读超时（秒）。stream=True 时 read timeout 限制的是「两次 socket 读之间」的
# 等待时间，而不是整段回答的总时长，所以它相当于「上游多久没吐一个 chunk 就算失联」。
# - 原值 30s 偏短：Dify 侧做工具调用/长文本生成时，两次 chunk 之间隔几十秒是可能的，
#   30s 会直接掐断一个本来正常的回答（用户看到回答说到一半就报错）；
# - 但也不能不封顶：上游一直不吐数据（半开连接/服务端卡住）时，这个调用会永久挂着，
#   该请求对应的 greenlet 和用户界面就一直停在「生成中」。
# 故给 180s：比旧值放宽 6 倍，足够长回答与工具调用间隙，又能兜住真正的失联。
STREAM_READ_TIMEOUT = 180


def dify_api_key(user: str | None) -> str:
    """按用户名选择 Dify 应用的 API Key。

    - `leo`  -> `AI_DIFY_API_KEY`
    - `灿灿` -> `AI_DIFY_CANCAN_API_KEY`
    - 其他（含 `昭昭`）-> `AI_DIFY_ZHAOZHAO_API_KEY`

    注意：该分流同时作用于移动端对话（`stream_msg`），不只是查询接口，
    换 key 等于换机器人。
    """
    name = (user or "").strip()
    if name.lower() == LEO_USER:
        return config.AI_DIFY_API_KEY
    if name == CANCAN_USER:
        return config.AI_DIFY_CANCAN_API_KEY
    return config.AI_DIFY_ZHAOZHAO_API_KEY


def dify_headers(user: str | None) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {dify_api_key(user)}",
    }


class AILocal:
    """Dify AI 客户端（支持流式响应）。"""

    def __init__(self, on_msg=None, on_err=None):
        """创建客户端实例。

        Args:
            on_msg: 回调 `on_msg(payload, message_id, type, client_request_id)`。
                - type=0: 流式 message chunk
                - type=1: message_end（metadata）
            on_err: 错误回调 `on_err(err, client_request_id, attempt=0)`。
        """
        self.aiConversationId = ""
        self.user = "user"
        self.on_msg = on_msg or (lambda a, b, c, d="", attempt=0: None)
        self.on_err = on_err or (lambda x, d="", attempt=0: None)
        self.last_task_id = -1
        self._active_stream_request_id = ""
        self._task_id_by_request: dict[str, object] = {}
        self._pending_cancel: set[str] = set()
        self._abort_requests: set[str] = set()

    def _invoke_on_msg(
        self,
        text,
        msg_id,
        msg_type,
        req_id: str,
        attempt: int,
    ) -> None:
        try:
            self.on_msg(text, msg_id, msg_type, req_id, attempt=attempt)
        except TypeError:
            self.on_msg(text, msg_id, msg_type, req_id)

    def _invoke_on_err(self, err: Exception, req_id: str, attempt: int) -> None:
        try:
            self.on_err(err, req_id, attempt=attempt)
        except TypeError:
            self.on_err(err, req_id)

    def stream_msg(
        self,
        query: str,
        inputs: dict | None = None,
        timeout: int = STREAM_READ_TIMEOUT,
        try_times: int = 0,
        client_request_id: str = "",
        bound_attempt: int | None = None,
        files: list[dict] | None = None,
    ) -> None:
        """发起流式对话请求。

        Args:
            query (str): 用户输入文本。
            inputs (dict | None): 透传给 Dify 的 inputs。
            timeout (int): **读**超时（秒）。SSE 场景下它是「两个 chunk 之间的最大间隔」，
                不是整段回答的总时长，所以默认给 `STREAM_READ_TIMEOUT`(180s) 而不是更小的值，
                否则长回答会被误杀。建连超时固定为 `CONNECT_TIMEOUT`(5s)。
            try_times (int): 内部递归重试计数（仅做一次轻量重试）。
            files (list[dict] | None): Dify `files` 参数（图片等附件），由
                `core.ai.ai_file.resolve_chat_files` 生成。
        """
        payload = {
            "inputs": inputs or {},
            "query": query,
            "conversation_id": self.aiConversationId,
            "response_mode": "streaming",
            "user": self.user,
            "files": files or [],
        }
        req_id = client_request_id or ""
        stream_attempt = (
            bound_attempt
            if bound_attempt is not None
            else (chat_request_store.get_attempt(self.user, req_id) if req_id else 0)
        )
        self._active_stream_request_id = req_id
        if req_id:
            self._abort_requests.discard(req_id)
        log.info(
            f"==== [AI] Query: {self.user} - {query} [{req_id}] attempt={stream_attempt}"
        )

        had_output = False
        last_line = b""
        try:
            with requests.post(
                    f"{API_URL}/chat-messages",
                    headers=dify_headers(self.user),
                    json=payload,
                    stream=True,
                    # 流式请求用「短建连 + 长读」的组合：建连失败要快速失败，
                    # 读超时则按 SSE 的 chunk 间隔来算（见 STREAM_READ_TIMEOUT 注释）。
                    timeout=(CONNECT_TIMEOUT, timeout),
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    last_line = line or last_line
                    if req_id and req_id in self._abort_requests:
                        break
                    if line and line.startswith(b"data:"):
                        chunk = json.loads(line.decode("utf-8")[6:])
                        self.aiConversationId = chunk["conversation_id"]
                        if "task_id" in chunk:
                            self.last_task_id = chunk["task_id"]
                            if req_id:
                                self._task_id_by_request[req_id] = chunk["task_id"]
                                if req_id in self._pending_cancel:
                                    self._pending_cancel.discard(req_id)
                                    self._abort_requests.add(req_id)
                                    self._post_stop_task(
                                        req_id, chunk["task_id"], stream_attempt
                                    )
                                    break
                        if "message" == chunk["event"]:
                            had_output = True
                            self._invoke_on_msg(
                                chunk["answer"],
                                chunk["message_id"],
                                0,
                                req_id,
                                stream_attempt,
                            )
                        elif chunk["event"] == "error":
                            raise RuntimeError(f"{chunk['code']} : {chunk['message']}")
                        elif chunk["event"] == "message_end":
                            log.info(chunk["metadata"])
                            had_output = True
                            self._invoke_on_msg(
                                chunk["metadata"],
                                chunk["message_id"],
                                1,
                                req_id,
                                stream_attempt,
                            )

        except requests.exceptions.RequestException as e:
            log.error(f">>[AI] 请求失败: {str(e)}")
            if req_id and req_id in self._abort_requests:
                return
            if had_output or try_times >= 1:
                self._invoke_on_err(e, req_id, stream_attempt)
            else:
                self.stream_msg(
                    query,
                    inputs,
                    timeout,
                    try_times + 1,
                    client_request_id=req_id,
                    bound_attempt=stream_attempt,
                )
        except Exception as ee:
            if last_line:
                log.error(">>[AI] 响应数据解析错误 " + last_line.decode("utf-8", errors="replace"))
            else:
                log.error(">>[AI] 响应数据解析错误")
            self._invoke_on_err(ee, req_id, stream_attempt)

    def _post_stop_task(
        self,
        req_id: str,
        task_id: object,
        attempt: int = 0,
    ) -> None:
        if task_id is None or task_id == -1:
            log.info(f">>[AI] skip cancel [{req_id}]: missing task_id")
            return
        payload = {"user": self.user}
        log.info(f">>[AI] cancel streaming [{req_id}] task={task_id}")
        try:
            # 必须带超时：此前缺省为「无限等待」，上游不响应时该调用会一直悬挂，
            # 而取消操作是在用户等结果时触发的，悬挂会直接卡住交互。
            with requests.post(
                    f"{API_URL}/chat-messages/{task_id}/stop",
                    headers=dify_headers(self.user),
                    json=payload,
                    timeout=(5, 15),
            ) as response:
                response.raise_for_status()
        except Exception as ee:
            log.error(f">>[AI] cancel error {ee}")
            self._invoke_on_err(ee, req_id, attempt)

    def streaming_cancel(self, client_request_id: str = "") -> None:
        """取消流式任务；尚无 task_id 时登记待取消，拿到 ID 后再 stop。"""
        req_id = (client_request_id or self._active_stream_request_id or "").strip()
        if not req_id:
            return
        task_id = self._task_id_by_request.get(req_id)
        if task_id is not None:
            self._pending_cancel.discard(req_id)
            self._abort_requests.add(req_id)
            attempt = chat_request_store.get_attempt(self.user, req_id)
            self._post_stop_task(req_id, task_id, attempt)
            return
        self._pending_cancel.add(req_id)
        log.info(f">>[AI] defer cancel [{req_id}] until task_id arrives")

    @staticmethod
    def get_chat_messages(conversation_id, limit, user, first_id=None):
        """从 Dify 获取历史消息列表。"""
        try:
            payload = {
                "conversation_id": conversation_id,
                "user": user,
                "limit": limit,
            }
            if first_id:
                payload["first_id"] = first_id
            with requests.get(
                    f"{API_URL}/messages",
                    headers=dify_headers(user),
                    params=payload,
                    timeout=(5, 30),
            ) as r:
                r.raise_for_status()
                return r.json()
        except Exception as e:
            log.error(f"请求失败: {str(e)}")
            return None

    @staticmethod
    def get_conversations(user, limit=20, last_id=None):
        """从 Dify 获取会话列表（按 updated_at 倒序，`last_id` 往更早翻页）。

        与 `get_chat_messages` 不同：这里不吞异常，交给路由层返回 `code:-1`，
        避免「上游报错」被前端当成「没有数据」。
        """
        payload = {"user": user, "limit": limit}
        if last_id:
            payload["last_id"] = last_id
        with requests.get(
                f"{API_URL}/conversations",
                headers=dify_headers(user),
                params=payload,
                timeout=(5, 30),
        ) as r:
            r.raise_for_status()
            return r.json()


if __name__ == "__main__":

    def f(msg):
        print(msg, end="")

    ai = AILocal(f)
    ai.user = "leo"
    while True:
        log.info("ready")
        msg = input(">?")
        ai.stream_msg(msg)
