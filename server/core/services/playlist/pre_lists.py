"""pre_lists 相关纯函数。

提取自 `core/services/playlist_mgr.py`，作为 P0 阶段的零风险拆分起点。

`get_pre_list_at` 是 weekday-无关的纯函数（便于单测），
`get_pre_list_for_today` 在其基础上结合 weekday 提供完整能力。
"""

from typing import List

from core.utils import get_weekday_index


def get_pre_list_at(pre_lists: List[List], weekday_index: int) -> List:
    """根据给定 weekday_index 取对应的前置文件列表。

    Args:
        pre_lists: 长度为 7 的二维数组，分别代表周一到周日。
        weekday_index: 0-6 的星期索引。

    Returns:
        对应的列表；输入不合法时返回空列表。
    """
    if not pre_lists or len(pre_lists) != 7:
        return []
    if not 0 <= weekday_index < 7:
        return []
    return pre_lists[weekday_index] if isinstance(pre_lists[weekday_index], list) else []


def get_pre_list_for_today(pre_lists: List[List]) -> List:
    """获取今天对应的前置文件列表。

    Args:
        pre_lists: pre_lists 数组，固定 7 个元素，分别代表周一到周日。

    Returns:
        今天对应的前置文件列表。
    """
    return get_pre_list_at(pre_lists, get_weekday_index())
