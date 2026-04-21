"""
素材管理服务
提供素材的增删改查功能
"""
from typing import Any, Dict, List, Optional, Tuple

from core.config import app_logger
from core.db.db_mgr import db_mgr

log = app_logger

TABLE_MATERIAL = 't_material'


class TaskMgr:
    """任务管理器 - 素材管理"""

    def __init__(self) -> None:
        """初始化管理器"""
        pass


task_mgr = TaskMgr()
