"""外部服务调用日志与统计。"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Literal

from sqlmodel import Session

from app.db import get_engine
from app.db.crud import (
    create_relay_log,
    get_stats_total_by_service_type,
    get_stats_daily_by_date,
    get_stats_hourly_by_hour,
    upsert_stats_daily,
    upsert_stats_hourly,
    upsert_stats_total,
)

logger = logging.getLogger(__name__)

ServiceType = Literal["llm", "tts", "asr"]


def _serialize_payload(payload: Any | None) -> str | None:
    """将请求/响应体统一序列化为可存储字符串。"""
    if payload is None:
        return None
    if isinstance(payload, str):
        return payload

    payload_type = type(payload)

    model_dump_json_fn = getattr(payload_type, "model_dump_json", None)
    if callable(model_dump_json_fn):
        try:
            return model_dump_json_fn(payload)  # type: ignore[misc]
        except Exception:
            pass

    model_dump_fn = getattr(payload_type, "model_dump", None)
    if callable(model_dump_fn):
        try:
            return json.dumps(model_dump_fn(payload), ensure_ascii=False, default=str)  # type: ignore[misc]
        except Exception:
            pass

    to_dict_fn = getattr(payload_type, "to_dict", None)
    if callable(to_dict_fn):
        try:
            return json.dumps(to_dict_fn(payload), ensure_ascii=False, default=str)  # type: ignore[misc]
        except Exception:
            pass

    try:
        return json.dumps(payload, ensure_ascii=False, default=str)
    except Exception:
        return str(payload)


def record_service_usage(
    *,
    service_type: ServiceType,
    request_model_name: str | None = None,
    input_value: float = 0,
    output_value: float = 0,
    start_time: int | None = None,
    latency: int | None = None,
    first_response_time: int | None = None,
    status: str = "success",
    error: str | None = None,
    request_content: Any | None = None,
    response_content: Any | None = None,
    attempts: str | None = None,
    total_attempts: int | None = None,
) -> None:
    """记录一次外部服务调用及聚合统计。

    Args:
        request_content: 请求体内容（通常为字符串化后的请求 payload）。
        response_content: 响应体内容（通常为字符串化后的响应 payload）。
        start_time: 请求开始时间（Unix 秒级时间戳）。
    """
    try:
        serialized_request_content = _serialize_payload(request_content)
        serialized_response_content = _serialize_payload(response_content)
        with Session(get_engine()) as db:
            create_relay_log(
                db,
                time=start_time,
                service_type=service_type,
                request_model_name=request_model_name,
                input_value=input_value,
                output_value=output_value,
                latency=latency,
                first_response_time=first_response_time,
                status=status,
                error=error,
                request_content=serialized_request_content,
                response_content=serialized_response_content,
                attempts=attempts,
                total_attempts=total_attempts,
            )
            _update_stats(
                db,
                service_type=service_type,
                input_value=input_value,
                output_value=output_value,
                wait_time=latency or 0,
                success=(status == "success"),
            )
    except Exception:
        logger.exception("记录服务调用统计失败: service_type=%s", service_type)


def _update_stats(
    db: Session,
    *,
    service_type: ServiceType,
    input_value: float,
    output_value: float,
    wait_time: int,
    success: bool,
) -> None:
    """更新累计、按日、按小时统计。"""
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_hour = now.hour

    total_stats = get_stats_total_by_service_type(db, service_type)
    daily_stats = get_stats_daily_by_date(db, current_date, service_type)
    hourly_stats = get_stats_hourly_by_hour(
        db, current_date, current_hour, service_type
    )

    upsert_stats_total(
        db,
        service_type,
        input_value=int((total_stats.input_value if total_stats else 0) + input_value),
        output_value=int(
            (total_stats.output_value if total_stats else 0) + output_value
        ),
        wait_time=int((total_stats.wait_time if total_stats else 0) + wait_time),
        request_success=(total_stats.request_success if total_stats else 0)
        + (1 if success else 0),
        request_failed=(total_stats.request_failed if total_stats else 0)
        + (0 if success else 1),
    )
    upsert_stats_daily(
        db,
        current_date,
        service_type,
        input_value=int((daily_stats.input_value if daily_stats else 0) + input_value),
        output_value=int(
            (daily_stats.output_value if daily_stats else 0) + output_value
        ),
        wait_time=int((daily_stats.wait_time if daily_stats else 0) + wait_time),
        request_success=(daily_stats.request_success if daily_stats else 0)
        + (1 if success else 0),
        request_failed=(daily_stats.request_failed if daily_stats else 0)
        + (0 if success else 1),
    )
    upsert_stats_hourly(
        db,
        current_date,
        current_hour,
        service_type,
        input_value=int(
            (hourly_stats.input_value if hourly_stats else 0) + input_value
        ),
        output_value=int(
            (hourly_stats.output_value if hourly_stats else 0) + output_value
        ),
        wait_time=int((hourly_stats.wait_time if hourly_stats else 0) + wait_time),
        request_success=(hourly_stats.request_success if hourly_stats else 0)
        + (1 if success else 0),
        request_failed=(hourly_stats.request_failed if hourly_stats else 0)
        + (0 if success else 1),
    )
