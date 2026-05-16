"""
JSON 序列化工具函数
"""
import json
from typing import Any, List, Optional


def serialize_object_list(obj_list: Optional[List[Any]]) -> Optional[str]:
    """将对象列表序列化为 JSON 字符串。
    
    Args:
        obj_list: 对象列表，每个对象需要有 __dict__ 属性
        
    Returns:
        JSON 字符串，如果列表为空或 None 则返回 None
    """
    if not obj_list:
        return None
    return json.dumps([obj.__dict__ for obj in obj_list], ensure_ascii=False)


def serialize_data(data: Any) -> Optional[str]:
    """将数据序列化为 JSON 字符串。
    
    Args:
        data: 任意可序列化的数据
        
    Returns:
        JSON 字符串，如果数据为 None 则返回 None
    """
    if data is None:
        return None
    return json.dumps(data, ensure_ascii=False)
