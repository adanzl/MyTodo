"""
工具函数模块
包含各种通用工具函数和辅助函数
"""

from core.tools.async_util import run_async
from core.tools.useragent_fix import patch_fake_useragent, SafeUserAgent

__all__ = ['run_async', 'patch_fake_useragent', 'SafeUserAgent']

