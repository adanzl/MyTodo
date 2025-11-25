"""
Device Agent 客户端配置
"""
import os

# Device Agent 服务地址（内网IP）
# 可以通过环境变量 DEVICE_AGENT_HOST 和 DEVICE_AGENT_PORT 进行配置
DEVICE_AGENT_HOST = os.getenv('DEVICE_AGENT_HOST', '192.168.50.184')
DEVICE_AGENT_PORT = os.getenv('DEVICE_AGENT_PORT', '8000')

# 完整的服务URL
DEVICE_AGENT_BASE_URL = f"http://{DEVICE_AGENT_HOST}:{DEVICE_AGENT_PORT}"

# 请求超时时间（秒）
DEVICE_AGENT_TIMEOUT = 30
