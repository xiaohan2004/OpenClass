"""usage 提取工具。"""

from __future__ import annotations

from typing import Any


def extract_usage(response: Any) -> Any:
    """从响应对象中提取 usage，缺失时返回 None。"""
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    return usage


def usage_value(usage: Any, key: str, *, default: float = 0) -> float:
    """从 usage 提取指定字段的数值，失败时返回 default。"""
    if usage is None:
        return default

    value = getattr(usage, key, None)
    if value is None and isinstance(usage, dict):
        value = usage.get(key)

    try:
        return float(value)
    except (TypeError, ValueError):
        return default
