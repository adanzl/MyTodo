"""
阿里相关模块公用：在能导入 core.config 时使用应用 logger 与 ALI_KEY，否则使用 dotenv + 默认 logger。
供独立运行脚本或测试时使用。
"""
import dashscope
import platform
from typing import Dict

from dashscope.common import utils as dashscope_utils

# 统一设置 dashscope 的基础 URL
dashscope.base_http_api_url = "https://dashscope.aliyuncs.com/api/v1"

# ---- 全局补丁：修复 gevent 环境下 platform 平台信息导致的 child watcher 报错 ----
# 有些调用链会直接使用 platform.platform() / platform.processor()，例如
# dashscope.common.utils.default_headers 以及 Python 标准库中的平台探测。
# 在 gevent 下这些调用可能通过 subprocess 触发 child watcher 错误。

_original_platform_platform = platform.platform
_original_platform_processor = platform.processor


def _safe_platform(*_args, **_kwargs) -> str:
    """全局替换 platform.platform，避免其内部再去启动子进程。"""
    try:
        return f"{platform.system()}-{platform.release()}-{platform.machine()}"
    except Exception:
        return "unknown"


def _safe_processor(*_args, **_kwargs) -> str:
    """全局替换 platform.processor，避免其内部再去启动子进程。"""
    try:
        value = _original_platform_processor()
        return value or ""
    except Exception:
        return ""


# 全局覆盖，确保所有第三方库（包括 dashscope）调用到的是安全版本
platform.platform = _safe_platform  # type: ignore[assignment]
platform.processor = _safe_processor  # type: ignore[assignment]


class BaseAli:
    """
    Base Ali API
    """

    def __init__(self, name: str):
        self.name = name

    def validate_response(self, response: dict) -> tuple[str, str]:
        """验证 API 响应"""

        if not response:
            log.error(f"[{self.name}] API 响应为空")
            return "error", "API 响应为空"

        if "output" not in response or not response["output"]:
            log.error(f"[{self.name}] API 响应中缺少 output 字段，响应: {response}")
            return "error", "API 响应格式错误：缺少 output 字段"

        if "choices" not in response["output"] or not response["output"]["choices"]:
            log.error(f"[{self.name}] API 响应中缺少 choices 字段，响应: {response}")
            return "error", "API 响应格式错误：缺少 choices 字段"

        if len(response["output"]["choices"]) == 0:
            log.error(f"[{self.name}] API 响应中 choices 列表为空")
            return "error", "API 响应格式错误：choices 列表为空"

        choice = response["output"]["choices"][0]
        if "message" not in choice or not choice["message"]:
            log.error(f"[{self.name}] API 响应中缺少 message 字段，choice: {choice}")
            return "error", "API 响应格式错误：缺少 message 字段"
        message = choice["message"]

        # message.content 可能是属性或字典键，需要兼容处理
        content = None
        if hasattr(message, "content"):
            content = message.content
        elif isinstance(message, dict) and "content" in message:
            content = message["content"]
        else:
            log.error(f"[{self.name}] API 响应中缺少 content 字段，message: {message}")
            return "error", "API 响应格式错误：缺少 content 字段"

        if not content:
            log.error(f"[{self.name}] API 响应中 content 为空")
            return "error", "API 响应格式错误：content 为空"
        return "ok", content


def get_log_and_key():
    """获取 logger 和 ALI_KEY，优先使用 core.config，失败时使用 dotenv + 默认 logging。"""
    try:
        from core.config import app_logger, config
        return app_logger, config.ALI_KEY
    except ImportError:
        from dotenv import load_dotenv
        import os
        import logging

        load_dotenv()
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        log = logging.getLogger()
        ali_key = os.getenv('ALI_KEY', '')
        print(f"use default log and ALI_KEY: {ali_key}")
        return log, ali_key


log, ALI_KEY = get_log_and_key()
