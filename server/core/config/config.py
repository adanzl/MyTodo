"""
统一配置管理模块
集中管理所有配置项，包括环境变量、应用配置、服务配置等
"""
import os
from typing import Optional
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


class Config:
    """应用配置类"""

    # ========== 环境配置 ==========
    ENV: str = os.environ.get('ENV', 'development').lower()
    IS_PRODUCTION: bool = ENV == 'production'

    # ========== 服务器配置 ==========
    HOST: str = os.environ.get('HOST', '127.0.0.1')
    PORT: int = int(os.environ.get('PORT', 8000))

    # ========== Flask 配置 ==========
    MAX_CONTENT_LENGTH: int = int(os.environ.get('MAX_CONTENT_LENGTH', 2000 * 1024 * 1024))  # 默认 2000MB

    # ========== 数据库配置 ==========
    DB_NAME: str = os.environ.get('DB_NAME', 'data.db')

    # 数据库连接池配置
    DB_POOL_SIZE: int = int(os.environ.get('DB_POOL_SIZE', 10))  # 连接池大小
    DB_MAX_OVERFLOW: int = int(os.environ.get('DB_MAX_OVERFLOW', 20))  # 连接池最大溢出连接数
    DB_POOL_RECYCLE: int = int(os.environ.get('DB_POOL_RECYCLE', 3600))  # 连接回收时间（秒）
    DB_POOL_PRE_PING: bool = os.environ.get('DB_POOL_PRE_PING', 'true').lower() == 'true'  # 连接前检查连接是否有效

    # ========== Redis 配置 ==========
    REDIS_HOST: str = os.environ.get('REDIS_HOST', 'localhost')
    REDIS_PORT: int = int(os.environ.get('REDIS_PORT', 6379))
    REDIS_DB: int = int(os.environ.get('REDIS_DB', 0))

    # ========== AI 服务配置 ==========
    # Dify AI 服务
    AI_DIFY_API_URL: str = os.environ.get('AI_DIFY_API_URL', 'http://192.168.50.171:9098/v1')
    AI_DIFY_API_KEY: str = os.environ.get('AI_DIFY_API_KEY', '')

    # 火山引擎豆包
    DOUBAO_API_URL: str = os.environ.get('DOUBAO_API_URL', 'https://ark.cn-beijing.volces.com')
    DOUBAO_AK: str = os.environ.get('DOUBAO_AK', '')
    DOUBAO_MODEL: str = os.environ.get('DOUBAO_MODEL', 'ep-20250205111100-zhcpq')

    # ========== TTS 服务配置 ==========
    # 阿里云 DashScope
    ALI_KEY: str = os.environ.get('ALI_KEY', '')

    # 豆包 TTS
    DOUBAO_TTS_API_URL: str = os.environ.get('DOUBAO_TTS_API_URL', 'https://openspeech.bytedance.com/api/v1/tts')
    DOUBAO_TTS_API_ID: str = os.environ.get('DOUBAO_TTS_API_ID', '')
    DOUBAO_TTS_API_TOKEN: str = os.environ.get('DOUBAO_TTS_API_TOKEN', '')

    # Zero TTS FastAPI 服务
    ZERO_TTS_FASTAPI_URL: str = os.environ.get('ZERO_TTS_FASTAPI_URL', 'http://192.168.50.171:9099/inference_zero_shot')

    # ========== ASR 服务配置 ==========
    ASR_SERVER: str = os.environ.get('ASR_SERVER', 'ws://192.168.50.171:9096')
    ASR_MODE: str = os.environ.get('ASR_MODE', 'offline')

    # ========== 设备配置 ==========
    # 小米设备
    MI_USER: str = os.environ.get('MI_USER', '')
    MI_PASS: str = os.environ.get('MI_PASS', '')

    # Agent 设备
    DEVICE_AGENT_BASE_URL: str = os.environ.get('DEVICE_AGENT_BASE_URL', 'http://192.168.50.184:8000')
    DEVICE_AGENT_TIMEOUT: int = int(os.environ.get('DEVICE_AGENT_TIMEOUT', 30))

    # ========== 文件路径配置 ==========
    # BASE_TMP_DIR: 临时文件目录，用于保存 TTS、PDF、媒体处理等任务产生的临时文件
    BASE_TMP_DIR: str = os.environ.get('BASE_TMP_DIR', '/opt/my_todo/data')
    # DEFAULT_BASE_DIR: 项目文件目录，用于保存用户访问的项目文件
    DEFAULT_BASE_DIR: str = os.environ.get('DEFAULT_BASE_DIR', '/opt/my_todo/data')
    LOG_DIR: str = os.environ.get('LOG_DIR', 'logs')

    # ========== 工具配置 ==========
    FFMPEG_PATH: str = os.environ.get('FFMPEG_PATH', '/usr/bin/ffmpeg')
    FFMPEG_TIMEOUT: int = int(os.environ.get('FFMPEG_TIMEOUT', 300))

    # ========== CORS 配置 ==========
    CORS_ORIGINS: str = os.environ.get('CORS_ORIGINS', '*')

    # ========== JWT / Auth 配置 ==========
    # IMPORTANT: set a strong secret in environment for production.
    JWT_SECRET_KEY: str = os.environ.get('JWT_SECRET_KEY', 'change-me-in-prod')
    JWT_ACCESS_DAYS: int = int(os.environ.get('JWT_ACCESS_DAYS', 1))
    JWT_REFRESH_DAYS: int = int(os.environ.get('JWT_REFRESH_DAYS', 30))

    # Whitelist behavior: start with all /api allowed, then turn off and tighten.
    AUTH_WHITELIST_ALL_API: bool = os.environ.get('AUTH_WHITELIST_ALL_API', '1') == '1'
    AUTH_API_WHITELIST: str = os.environ.get('AUTH_API_WHITELIST', '')
    AUTH_API_WHITELIST_PREFIX: str = os.environ.get('AUTH_API_WHITELIST_PREFIX', '')

    # ========== 限流配置 ==========
    # Flask-Limiter 默认限流规则（可用 "200 per day; 50 per hour" 这种复合写法）
    RATE_LIMIT_DEFAULT: str = os.environ.get('RATE_LIMIT_DEFAULT', '20000 per day; 5000 per hour')
    # 限流状态存储：默认使用内存（单进程/单 worker 生效）。生产建议使用 Redis。
    # 示例：redis://localhost:6379/1
    RATE_LIMIT_STORAGE_URI: str = os.environ.get('RATE_LIMIT_STORAGE_URI', 'memory://')

    @classmethod
    def get_cors_origins(cls) -> list:
        """获取 CORS 允许的来源列表"""
        if cls.CORS_ORIGINS == '*':
            return ['*']
        return [origin.strip() for origin in cls.CORS_ORIGINS.split(',')]

    @classmethod
    def validate(cls) -> tuple[bool, Optional[str]]:
        """
        验证必需的配置项
        :return: (是否有效, 错误消息)
        """
        errors = []

        # 验证必需的配置（根据实际需求调整）
        if cls.IS_PRODUCTION:
            if not cls.AI_DIFY_API_KEY and not cls.DOUBAO_AK:
                errors.append("生产环境需要配置 AI 服务密钥")

        if errors:
            return False, '; '.join(errors)
        return True, None

    @classmethod
    def get_summary(cls) -> dict:
        """获取配置摘要（隐藏敏感信息）"""
        return {
            'env': cls.ENV,
            'host': cls.HOST,
            'port': cls.PORT,
            'max_content_length_mb': cls.MAX_CONTENT_LENGTH // (1024 * 1024),
            'has_ai_dify_key': bool(cls.AI_DIFY_API_KEY),
            'has_doubao_ak': bool(cls.DOUBAO_AK),
            'has_ali_key': bool(cls.ALI_KEY),
            'has_mi_credentials': bool(cls.MI_USER and cls.MI_PASS),
        }


# 创建配置实例
config = Config()
