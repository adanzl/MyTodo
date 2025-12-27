"""
修复 fake_useragent 在 gevent 环境中的问题
在导入 miservice 之前 monkey patch UserAgent，避免 ThreadPoolExecutor 导致的 LoopExit
"""
import random

# 预定义的 User-Agent 列表，避免使用 fake_useragent 库的线程池
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]


class SafeUserAgent:
    """
    安全的 User-Agent 生成器，避免在 gevent 环境中使用 ThreadPoolExecutor
    替代 fake_useragent.UserAgent，提供相同的接口
    """
    def __init__(self, *args, **kwargs):
        """忽略所有参数，避免 fake_useragent 的初始化逻辑"""
        self._ua_list = _USER_AGENTS.copy()
    
    @property
    def random(self):
        """返回随机的 User-Agent"""
        return random.choice(self._ua_list)


def patch_fake_useragent():
    """
    Monkey patch fake_useragent.UserAgent，替换为安全的实现
    必须在导入 miservice 之前调用
    """
    import sys
    # 创建一个假的 fake_useragent 模块
    class FakeModule:
        UserAgent = SafeUserAgent
    
    # 在导入之前就注册这个模块
    sys.modules['fake_useragent'] = FakeModule()


# 自动执行 patch（在导入时）
patch_fake_useragent()

