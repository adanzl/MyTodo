from typing import Any
from pydantic import BaseModel


class AgentHeartbeatData(BaseModel):
    address: str  # 设备的访问地址，通常是 IP:PORT 格式
    name: str | None = None  # 设备名称
    actions: list[str] | None = None  # 设备支持的操作列表
    config: dict[str, Any] | None = None  # 设备配置


class AgentConfigBody(BaseModel):
    agent_id: str  # 设备 ID
    config: dict[str, Any]  # 配置内容


class AgentEventBody(BaseModel):
    key: str
    action: str
    value: Any | None = None


class AgentMockBody(BaseModel):
    agent_id: str
    action: str
    key: str | None = None
    value: Any | None = None


class OCRBody(BaseModel):
    """OCR 请求体（使用文件路径）"""
    image_paths: str | list[str]
