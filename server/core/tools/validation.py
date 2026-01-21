"""输入校验工具（Pydantic）。

该模块提供一套轻量的 Pydantic 校验封装，用于在不重构现有 Flask Blueprint 的前提下，
为 API 入参提供统一的类型/必填/范围校验，并返回统一的错误结构（兼容现有 `{"code": -1, "msg": ...}`）。
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, Type, TypeVar

from pydantic import BaseModel, ValidationError

ModelT = TypeVar("ModelT", bound=BaseModel)


def parse_with_model(
    model: Type[ModelT],
    data: Dict[str, Any],
    *,
    err_factory,
) -> Tuple[Optional[ModelT], Optional[Dict[str, Any]]]:
    """使用 Pydantic 模型校验并解析输入数据。

    Args:
        model (Type[ModelT]): Pydantic 模型类型。
        data (Dict[str, Any]): 原始输入数据（dict）。
        err_factory: 生成错误响应的函数，签名为 `err_factory(msg: str) -> Dict[str, Any]`。

    Returns:
        Tuple[Optional[ModelT], Optional[Dict[str, Any]]]: (obj, err)
        - obj: 校验成功时返回模型实例
        - err: 校验失败时返回标准错误响应（`{"code": -1, "msg": "..."}`）
    """
    try:
        return model.model_validate(data), None
    except ValidationError as e:
        parts: list[str] = []
        for err in e.errors():
            loc = ".".join(str(x) for x in err.get("loc", []))
            msg = err.get("msg", "invalid")
            parts.append(f"{loc}: {msg}" if loc else msg)
        return None, err_factory("invalid request: " + "; ".join(parts))
