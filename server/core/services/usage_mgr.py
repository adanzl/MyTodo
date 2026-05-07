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

            if result.get('code') != 0:
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

    def query_sum_usage(
        self,
        user_id: Optional[int] = None,
        type: Optional[str] = None,
        time_start: Optional[str] = None,
        time_end: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        查询特定条件下的使用时间总长。

        Args:
            user_id: 用户ID（可选）
            type: 使用类型（可选）
            time_start: 开始时间范围起始（可选）
            time_end: 开始时间范围结束（可选）

        Returns:
            总时长（秒）
        """
        try:
            # 构建 SQL 查询
            sql_parts = ["SELECT COALESCE(SUM(duration), 0) as total_duration FROM t_usage WHERE 1=1"]
            params = []

            if user_id is not None:
                sql_parts.append("AND user_id = ?")
                params.append(user_id)

            if type:
                sql_parts.append("AND type = ?")
                params.append(type)

            if time_start:
                sql_parts.append("AND start_time >= ?")
                params.append(time_start)

            if time_end:
                sql_parts.append("AND start_time <= ?")
                params.append(time_end)

            sql = " ".join(sql_parts)
            log.debug(f"[UsageMgr] 查询总时长 SQL: {sql}, params: {params}")

            # 执行查询
            result = db_mgr.query(sql)

            if result.get('code') == 0 and result.get('data'):
                total_duration = result['data'][0]['total_duration'] if result['data'] else 0
                return {"code": 0, "msg": "ok", "data": {"total_duration": total_duration}}
            else:
                log.error(f"[UsageMgr] 查询总时长失败: {result.get('msg')}")
                return result

        except Exception as e:
            log.error(f"[UsageMgr] 查询总时长异常: {e}", exc_info=True)
            return {"code": -1, "msg": f'error: {str(e)}'}


usage_mgr = UsageMgr()
