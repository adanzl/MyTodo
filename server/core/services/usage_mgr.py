"""Usage 管理服务模块。
提供使用记录的增删改查功能。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from core.config import app_logger
from core.db.db_mgr import db_mgr

log = app_logger


class UsageMgr:
    """Usage 管理类，封装使用记录的操作"""

    def add_usage(
        self,
        type: str,
        start_time: str,
        duration: int,
        user_id: int,
        out_key: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        添加使用记录到 t_usage 表。

        Args:
            type: 使用类型
            start_time: 开始时间（字符串格式）
            duration: 持续时间（秒）
            user_id: 用户ID
            out_key: 外部关联键（可选）

        Returns:
            操作结果字典
        """
        try:
            # 准备数据
            data = {
                'type': type,
                'start_time': start_time,
                'duration': duration,
                'user_id': user_id,
            }

            if out_key is not None:
                data['out_key'] = out_key

            # 插入数据
            result = db_mgr.set_data('t_usage', data)

            if result.get('code') == 0:
                log.info(f"[UsageMgr] 添加使用记录成功: type={type}, user_id={user_id}, duration={duration}")
            else:
                log.error(f"[UsageMgr] 添加使用记录失败: {result.get('msg')}")

            return result

        except Exception as e:
            log.error(f"[UsageMgr] 添加使用记录异常: {e}", exc_info=True)
            return {"code": -1, "msg": f'error: {str(e)}'}

    def get_usage_list(
        self,
        page_num: int = 1,
        page_size: int = 20,
        user_id: Optional[int] = None,
        type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        获取使用记录列表。

        Args:
            page_num: 页码
            page_size: 每页数量
            user_id: 用户ID过滤（可选）
            type: 类型过滤（可选）

        Returns:
            分页数据
        """
        try:
            conditions = {}

            if user_id is not None:
                conditions['user_id'] = user_id

            if type:
                conditions['type'] = type

            result = db_mgr.get_list(
                't_usage',
                page_num=page_num,
                page_size=page_size,
                fields='*',
                conditions=conditions if conditions else None,
            )

            return result

        except Exception as e:
            log.error(f"[UsageMgr] 获取使用记录列表异常: {e}", exc_info=True)
            return {"code": -1, "msg": f'error: {str(e)}', "data": None}

    def delete_usage(self, id: int) -> Dict[str, Any]:
        """
        删除使用记录。

        Args:
            id: 记录ID

        Returns:
            操作结果
        """
        try:
            result = db_mgr.del_data('t_usage', id)

            if result.get('code') == 0:
                log.info(f"[UsageMgr] 删除使用记录成功: id={id}")
            else:
                log.error(f"[UsageMgr] 删除使用记录失败: {result.get('msg')}")

            return result

        except Exception as e:
            log.error(f"[UsageMgr] 删除使用记录异常: {e}", exc_info=True)
            return {"code": -1, "msg": f'error: {str(e)}'}


usage_mgr = UsageMgr()
