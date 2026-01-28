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
_original_default_headers = dashscope_utils.default_headers


def _safe_default_headers(api_key: str | None = None) -> Dict[str, str]:
    """
  替换 dashscope 默认的 default_headers，避免在 gevent 环境下调用
  platform.platform() / platform.processor() 触发 child watchers 错误。
  """
    try:
        safe_platform = f"{platform.system()}-{platform.release()}-{platform.machine()}"
    except Exception:
        safe_platform = "unknown"

    try:
        safe_processor = platform.processor() or ""
    except Exception:
        safe_processor = ""

    ua = "dashscope/%s; python/%s; platform/%s; processor/%s" % (
        dashscope_utils.__version__,
        platform.python_version(),
        safe_platform,
        safe_processor,
    )

    headers: Dict[str, str] = {"user-agent": ua}
    if api_key is None:
        api_key = dashscope_utils.get_default_api_key()
    headers["Authorization"] = "Bearer %s" % api_key
    headers["Accept"] = "application/json"
    return headers


# 覆盖 dashscope 内部使用的 default_headers，避免其内部直接调用 platform.platform()
dashscope_utils.default_headers = _safe_default_headers  # type: ignore[assignment]


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
