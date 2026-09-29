"""Dify AI（本地/私有化）客户端封装。

`AILocal` 提供：
- 流式对话请求（SSE 形式的 `data:` 行）；
- 取消流式任务；
- 拉取历史消息。

该类被 `core/chat/chat_mgr.py` 用作对话与语音链路的一环。
"""

import json

import requests

from core.config import app_logger, config

log = app_logger
API_URL = config.AI_DIFY_API_URL
LEO_USER = "leo"


def dify_api_key(user: str | None) -> str:
    """leo 使用 AI_DIFY_API_KEY，其他用户使用 AI_DIFY_DOUDOU_API_KEY。"""
    if (user or "").strip().lower() == LEO_USER:
        return config.AI_DIFY_API_KEY
    return config.AI_DIFY_DOUDOU_API_KEY


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
            on_err: 错误回调 `on_err(err, client_request_id)`。
        """
        self.aiConversationId = ""
        self.user = "user"
        self.on_msg = on_msg or (lambda a, b, c, d="": None)
        self.on_err = on_err or (lambda x, d="": None)
        self.last_task_id = -1
        self._active_stream_request_id = ""

    def stream_msg(
        self,
        query: str,
        inputs: dict | None = None,
        timeout: int = 30,
        try_times: int = 0,
        client_request_id: str = "",
    ) -> None:
        """发起流式对话请求。

        Args:
            query (str): 用户输入文本。
            inputs (dict | None): 透传给 Dify 的 inputs。
            timeout (int): HTTP 超时时间（秒）。
            try_times (int): 内部递归重试计数（仅做一次轻量重试）。
        """
        payload = {
            "inputs": inputs or {},
            "query": query,
            "conversation_id": self.aiConversationId,
            "response_mode": "streaming",
            "user": self.user,
        }
        req_id = client_request_id or ""
        self._active_stream_request_id = req_id
        log.info(f"==== [AI] Query: {self.user} - {query} [{req_id}]")

        try:
            with requests.post(
                    f"{API_URL}/chat-messages",
                    headers=dify_headers(self.user),
                    json=payload,
                    stream=True,
                    timeout=timeout,
            ) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if line and line.startswith(b"data:"):
                        chunk = json.loads(line.decode("utf-8")[6:])
                        self.aiConversationId = chunk["conversation_id"]
                        if "task_id" in chunk:
                            self.last_task_id = chunk["task_id"]
                        if "message" == chunk["event"]:
                            self.on_msg(chunk["answer"], chunk["message_id"], 0, req_id)
                        elif chunk["event"] == "error":
                            raise RuntimeError(f"{chunk['code']} : {chunk['message']}")
                        elif chunk["event"] == "message_end":
                            log.info(chunk["metadata"])
                            self.on_msg(chunk["metadata"], chunk["message_id"], 1, req_id)

        except requests.exceptions.RequestException as e:
            log.error(f">>[AI] 请求失败: {str(e)}")
            if try_times < 1:
                self.aiConversationId = ""
                self.stream_msg(
                    query, inputs, timeout, try_times + 1, client_request_id=req_id
                )
            else:
                self.on_err(e, req_id)
        except Exception as ee:
            log.error(">>[AI] 响应数据解析错误 " + line.decode("utf-8"))
            self.on_err(ee, req_id)

    def streaming_cancel(self, client_request_id: str = "") -> None:
        """取消当前流式任务（如果服务端支持 stop）。"""
        req_id = client_request_id or self._active_stream_request_id
        task_id = self.last_task_id
        payload = {"user": self.user}
        log.info(f">>[AI] cancel streaming [{req_id}] task={task_id}")
        try:
            with requests.post(
                    f"{API_URL}/chat-messages/:{task_id}/stop",
                    headers=dify_headers(self.user),
                    json=payload,
            ) as response:
                response.raise_for_status()

        except Exception as ee:
            log.error(f">>[AI] cancel error {ee}")
            self.on_err(ee, req_id)

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
            ) as r:
                r.raise_for_status()
                return r.json()
        except Exception as e:
            log.error(f"请求失败: {str(e)}")
            return None


if __name__ == "__main__":

    def f(msg):
        print(msg, end="")

    ai = AILocal(f)
    ai.user = "leo"
    while True:
        log.info("ready")
        msg = input(">?")
        ai.stream_msg(msg)
