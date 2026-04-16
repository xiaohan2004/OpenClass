"""数据库配置存储与初始化。"""

from __future__ import annotations

from typing import Any

from sqlmodel import Session

from app.config_defaults import (
    BOOTSTRAP_SETTING_KEYS,
    DEFAULT_SETTINGS_VALUES,
    SENSITIVE_SETTING_KEYS,
)
from app.db.crud import list_settings, upsert_setting


def _coerce_value(key: str, value: Any) -> str:
    """将配置值序列化为数据库字符串。"""
    if value is None:
        return ""

    if isinstance(value, bool):
        return "true" if value else "false"

    return str(value)


def _parse_bool(value: str, default: bool) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _parse_value(key: str, value: str) -> Any:
    """根据默认值类型解析数据库字符串。"""
    default_value = DEFAULT_SETTINGS_VALUES[key]

    if default_value is None:
        return value or None

    if isinstance(default_value, bool):
        return _parse_bool(value, default_value)

    if isinstance(default_value, int) and not isinstance(default_value, bool):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default_value

    if isinstance(default_value, float):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default_value

    return value if value else default_value


def _should_seed_default(key: str, raw_value: str | None) -> bool:
    """判断配置是否需要写入默认值。"""
    if raw_value is None:
        return True

    if key in SENSITIVE_SETTING_KEYS:
        return False

    return raw_value.strip() == ""


def ensure_default_settings(db: Session) -> bool:
    """确保系统配置表包含完整默认值。"""
    existing_settings = {setting.key: setting.value for setting in list_settings(db)}
    expected_keys = set(DEFAULT_SETTINGS_VALUES.keys())

    if not existing_settings:
        for key, value in DEFAULT_SETTINGS_VALUES.items():
            upsert_setting(db, key, _coerce_value(key, value))
        return True

    has_changed = False
    for key in expected_keys:
        current_value = existing_settings.get(key)
        if _should_seed_default(key, current_value):
            upsert_setting(db, key, _coerce_value(key, DEFAULT_SETTINGS_VALUES[key]))
            has_changed = True

    return has_changed


def load_settings_dict(db: Session) -> dict[str, Any]:
    """从数据库加载并解析全部配置。"""
    ensure_default_settings(db)
    settings_map = {setting.key: setting.value for setting in list_settings(db)}

    resolved_settings: dict[str, Any] = {}
    for key, default_value in DEFAULT_SETTINGS_VALUES.items():
        raw_value = settings_map.get(key)
        if raw_value is None:
            raw_value = _coerce_value(key, default_value)
        resolved_settings[key] = _parse_value(key, raw_value)

    return resolved_settings


def dump_settings_dict(settings: dict[str, Any]) -> dict[str, str]:
    """将配置字典转换为数据库可存储字符串。"""
    return {key: _coerce_value(key, value) for key, value in settings.items()}


def is_bootstrap_setting_key(key: str) -> bool:
    """判断是否属于数据库引导配置。"""
    return key in BOOTSTRAP_SETTING_KEYS
