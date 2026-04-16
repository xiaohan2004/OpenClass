"""REST API 路由。"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session

from app.api.deps import get_db_session
from app.config import refresh_settings_cache
from app.config_defaults import DEFAULT_SETTINGS_VALUES, SENSITIVE_SETTING_KEYS
from app.db.config_store import dump_settings_dict, load_settings_dict
from app.db.crud import (
    close_session,
    create_course,
    create_session,
    list_settings,
    get_course_by_id,
    get_question_by_id,
    get_relay_log_by_id,
    get_segment_summary_by_id,
    get_session_by_id,
    get_stats_total_by_id,
    get_transcript_by_id,
    list_courses,
    list_questions,
    list_questions_by_session,
    list_relay_logs,
    list_segment_summaries,
    list_segment_summaries_by_session,
    list_sessions,
    list_stats_dailies,
    list_stats_hourlies,
    list_stats_totals,
    list_transcripts,
    list_transcripts_by_session,
    upsert_settings,
    update_course,
    update_question,
    update_session,
    delete_course,
    delete_session,
)
from app.utils.time import now_ts

router = APIRouter(prefix="/api", tags=["rest"])


class ApiResponse(BaseModel):
    """统一 REST 响应结构。"""

    code: int = 0
    msg: str = "ok"
    data: Any = {}


class CourseCreatePayload(BaseModel):
    """创建课程请求。"""

    code: str | None = None
    name: str | None = None
    description: str | None = None
    teacher: str | None = None


class CourseUpdatePayload(CourseCreatePayload):
    """更新课程请求。"""


class CoursePatchPayload(BaseModel):
    """部分更新课程请求。"""

    code: str | None = None
    name: str | None = None
    description: str | None = None
    teacher: str | None = None


class SessionCreatePayload(BaseModel):
    """创建课堂请求。"""

    course_id: int
    title: str | None = None


class SessionUpdatePayload(BaseModel):
    """更新课堂请求。"""

    title: str | None = None


class SessionPatchPayload(BaseModel):
    """部分更新课堂请求。"""

    title: str | None = None


class SessionStartPayload(BaseModel):
    """开始课堂请求。"""

    start_time: int | None = None


class SessionEndPayload(BaseModel):
    """结束课堂请求。"""

    end_time: int | None = None


class QuestionPatchPayload(BaseModel):
    """更新问题请求。"""

    status: str | None = None
    asked_at: int | None = None
    score: float | None = None


class CourseRead(BaseModel):
    """课程输出结构。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str | None = None
    name: str | None = None
    description: str | None = None
    teacher: str | None = None
    created_at: int


class SessionRead(BaseModel):
    """课堂输出结构。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    seq: int | None = None
    title: str | None = None
    start_time: int | None = None
    end_time: int | None = None
    created_at: int


class TranscriptRead(BaseModel):
    """转写输出结构。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    seq: int | None = None
    text: str
    start_time: int | None = None
    end_time: int | None = None
    created_at: int


class QuestionRead(BaseModel):
    """问题输出结构。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    text: str
    status: str | None = None
    score: float | None = None
    created_at: int
    asked_at: int | None = None


class SegmentSummaryRead(BaseModel):
    """分段小结输出结构。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    text: str
    start_time: int | None = None
    end_time: int | None = None
    score: float | None = None
    created_at: int


class RelayLogRead(BaseModel):
    """请求日志输出结构。

    说明：
    - request_content: 请求体
    - response_content: 响应体
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    time: int
    service_type: str
    request_model_name: str | None = None
    input_value: float | None = None
    output_value: float | None = None
    latency: int | None = None
    first_response_time: int | None = None
    status: str | None = None
    request_content: str | None = None
    response_content: str | None = None
    error: str | None = None
    attempts: str | None = None
    total_attempts: int | None = None


class StatsTotalRead(BaseModel):
    """累计统计输出结构。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    service_type: str
    input_value: int | None = None
    output_value: int | None = None
    wait_time: int | None = None
    request_success: int | None = None
    request_failed: int | None = None


class StatsDailyRead(BaseModel):
    """按日统计输出结构。"""

    model_config = ConfigDict(from_attributes=True)

    date: str
    service_type: str
    input_value: int | None = None
    output_value: int | None = None
    wait_time: int | None = None
    request_success: int | None = None
    request_failed: int | None = None


class StatsHourlyRead(BaseModel):
    """按小时统计输出结构。"""

    model_config = ConfigDict(from_attributes=True)

    hour: int
    date: str
    service_type: str
    input_value: int | None = None
    output_value: int | None = None
    wait_time: int | None = None
    request_success: int | None = None
    request_failed: int | None = None


class SettingRead(BaseModel):
    """设置输出结构。"""

    key: str
    value: Any | None = None
    sensitive: bool = False
    has_value: bool = False


class SettingsRead(BaseModel):
    """设置列表输出结构。"""

    items: list[SettingRead]


class SettingUpdateItem(BaseModel):
    """设置更新项。"""

    key: str
    value: Any | None = None


class SettingsUpdatePayload(BaseModel):
    """设置更新请求。"""

    items: list[SettingUpdateItem]


def _success(data: Any, msg: str = "ok") -> dict[str, Any]:
    """构造统一成功响应。"""
    return ApiResponse(msg=msg, data=data).model_dump()


def _not_found(name: str) -> HTTPException:
    """构造统一不存在异常。"""
    return HTTPException(status_code=404, detail=f"{name}不存在")


def _serialize_model(model: Any, schema: type[BaseModel]) -> dict[str, Any]:
    """序列化单个模型。"""
    raw_data = jsonable_encoder(model)
    data = schema.model_validate(raw_data).model_dump()
    return jsonable_encoder(data)


def _serialize_models(
    models: list[Any], schema: type[BaseModel]
) -> list[dict[str, Any]]:
    """序列化模型列表。"""
    return [_serialize_model(model, schema) for model in models]


def _serialize_settings(db: Session) -> dict[str, Any]:
    """序列化设置项，敏感键不回传明文。"""
    settings_dict = load_settings_dict(db)
    raw_settings_map = {setting.key: setting.value for setting in list_settings(db)}

    items: list[dict[str, Any]] = []
    for key in DEFAULT_SETTINGS_VALUES.keys():
        is_sensitive = key in SENSITIVE_SETTING_KEYS
        raw_value = raw_settings_map.get(key)
        has_value = isinstance(raw_value, str) and bool(raw_value.strip())

        value = None if is_sensitive else settings_dict.get(key)
        items.append(
            SettingRead(
                key=key,
                value=value,
                sensitive=is_sensitive,
                has_value=has_value,
            ).model_dump()
        )

    return SettingsRead(items=items).model_dump()


def _require_course(db: Session, course_id: int):
    course = get_course_by_id(db, course_id)
    if course is None:
        raise _not_found("课程")
    return course


def _require_session(db: Session, session_id: int):
    session_record = get_session_by_id(db, session_id)
    if session_record is None:
        raise _not_found("课堂")
    return session_record


def _require_question(db: Session, question_id: int):
    question = get_question_by_id(db, question_id)
    if question is None:
        raise _not_found("问题")
    return question


@router.post("/courses")
def create_course_endpoint(
    payload: CourseCreatePayload, db: Session = Depends(get_db_session)
):
    course = create_course(db, **payload.model_dump())
    return _success(_serialize_model(course, CourseRead), "创建成功")


@router.get("/courses")
def list_courses_endpoint(db: Session = Depends(get_db_session)):
    return _success(_serialize_models(list_courses(db), CourseRead))


@router.get("/courses/{course_id}")
def get_course_endpoint(course_id: int, db: Session = Depends(get_db_session)):
    course = _require_course(db, course_id)
    return _success(_serialize_model(course, CourseRead))


@router.put("/courses/{course_id}")
def update_course_endpoint(
    course_id: int, payload: CourseUpdatePayload, db: Session = Depends(get_db_session)
):
    _require_course(db, course_id)
    course = update_course(db, course_id, **payload.model_dump())
    return _success(_serialize_model(course, CourseRead), "更新成功")


@router.patch("/courses/{course_id}")
def patch_course_endpoint(
    course_id: int, payload: CoursePatchPayload, db: Session = Depends(get_db_session)
):
    _require_course(db, course_id)
    course = update_course(
        db, course_id, **payload.model_dump(exclude_unset=True, exclude_none=True)
    )
    return _success(_serialize_model(course, CourseRead), "更新成功")


@router.delete("/courses/{course_id}")
def delete_course_endpoint(course_id: int, db: Session = Depends(get_db_session)):
    _require_course(db, course_id)
    delete_course(db, course_id)
    return _success({}, "删除成功")


@router.post("/sessions")
def create_session_endpoint(
    payload: SessionCreatePayload, db: Session = Depends(get_db_session)
):
    _require_course(db, payload.course_id)
    session_record = create_session(
        db,
        course_id=payload.course_id,
        title=payload.title,
    )
    return _success(_serialize_model(session_record, SessionRead), "创建成功")


@router.get("/sessions")
def list_sessions_endpoint(db: Session = Depends(get_db_session)):
    return _success(_serialize_models(list_sessions(db), SessionRead))


@router.get("/sessions/{session_id}")
def get_session_endpoint(session_id: int, db: Session = Depends(get_db_session)):
    session_record = _require_session(db, session_id)
    return _success(_serialize_model(session_record, SessionRead))


@router.get("/courses/{course_id}/sessions")
def list_course_sessions_endpoint(
    course_id: int, db: Session = Depends(get_db_session)
):
    _require_course(db, course_id)
    return _success(
        _serialize_models(list_sessions(db, course_id=course_id), SessionRead)
    )


@router.put("/sessions/{session_id}")
def update_session_endpoint(
    session_id: int,
    payload: SessionUpdatePayload,
    db: Session = Depends(get_db_session),
):
    _require_session(db, session_id)
    session_record = update_session(
        db,
        session_id,
        title=payload.title,
    )
    return _success(_serialize_model(session_record, SessionRead), "更新成功")


@router.patch("/sessions/{session_id}")
def patch_session_endpoint(
    session_id: int, payload: SessionPatchPayload, db: Session = Depends(get_db_session)
):
    _require_session(db, session_id)
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    session_record = update_session(db, session_id, **updates)
    return _success(_serialize_model(session_record, SessionRead), "更新成功")


@router.delete("/sessions/{session_id}")
def delete_session_endpoint(session_id: int, db: Session = Depends(get_db_session)):
    _require_session(db, session_id)
    delete_session(db, session_id)
    return _success({}, "删除成功")


@router.post("/sessions/{session_id}/start")
def start_session_endpoint(
    session_id: int,
    payload: SessionStartPayload | None = None,
    db: Session = Depends(get_db_session),
):
    _require_session(db, session_id)
    start_time = (
        now_ts()
        if payload is None or payload.start_time is None
        else payload.start_time
    )
    update_session(db, session_id, start_time=start_time)
    return _success({}, "课堂已开始")


@router.post("/sessions/{session_id}/pause")
def pause_session_endpoint(session_id: int, db: Session = Depends(get_db_session)):
    _require_session(db, session_id)
    return _success({}, "课堂已暂停")


@router.post("/sessions/{session_id}/end")
def end_session_endpoint(
    session_id: int,
    payload: SessionEndPayload | None = None,
    db: Session = Depends(get_db_session),
):
    _require_session(db, session_id)
    end_time = (
        now_ts() if payload is None or payload.end_time is None else payload.end_time
    )
    close_session(db, session_id, end_time=end_time)
    return _success({}, "课堂已结束")


@router.get("/transcripts")
def list_transcripts_endpoint(db: Session = Depends(get_db_session)):
    return _success(_serialize_models(list_transcripts(db), TranscriptRead))


@router.get("/transcripts/{transcript_id}")
def get_transcript_endpoint(transcript_id: int, db: Session = Depends(get_db_session)):
    transcript = get_transcript_by_id(db, transcript_id)
    if transcript is None:
        raise _not_found("转写")
    return _success(_serialize_model(transcript, TranscriptRead))


@router.get("/sessions/{session_id}/transcripts")
def list_session_transcripts_endpoint(
    session_id: int, db: Session = Depends(get_db_session)
):
    _require_session(db, session_id)
    return _success(
        _serialize_models(list_transcripts_by_session(db, session_id), TranscriptRead)
    )


@router.get("/questions")
def list_questions_endpoint(db: Session = Depends(get_db_session)):
    return _success(_serialize_models(list_questions(db), QuestionRead))


@router.get("/questions/{question_id}")
def get_question_endpoint(question_id: int, db: Session = Depends(get_db_session)):
    question = _require_question(db, question_id)
    return _success(_serialize_model(question, QuestionRead))


@router.get("/sessions/{session_id}/questions")
def list_session_questions_endpoint(
    session_id: int, db: Session = Depends(get_db_session)
):
    _require_session(db, session_id)
    return _success(
        _serialize_models(list_questions_by_session(db, session_id), QuestionRead)
    )


@router.patch("/questions/{question_id}")
def patch_question_endpoint(
    question_id: int,
    payload: QuestionPatchPayload,
    db: Session = Depends(get_db_session),
):
    _require_question(db, question_id)
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    if updates.get("status") == "asked" and "asked_at" not in updates:
        updates["asked_at"] = now_ts()
    question = update_question(db, question_id, **updates)
    return _success(_serialize_model(question, QuestionRead), "更新成功")


@router.get("/segment-summaries")
def list_segment_summaries_endpoint(db: Session = Depends(get_db_session)):
    return _success(_serialize_models(list_segment_summaries(db), SegmentSummaryRead))


@router.get("/segment-summaries/{summary_id}")
def get_segment_summary_endpoint(
    summary_id: int, db: Session = Depends(get_db_session)
):
    summary = get_segment_summary_by_id(db, summary_id)
    if summary is None:
        raise _not_found("分段小结")
    return _success(_serialize_model(summary, SegmentSummaryRead))


@router.get("/sessions/{session_id}/segment-summaries")
def list_session_segment_summaries_endpoint(
    session_id: int, db: Session = Depends(get_db_session)
):
    _require_session(db, session_id)
    return _success(
        _serialize_models(
            list_segment_summaries_by_session(db, session_id), SegmentSummaryRead
        )
    )


@router.get("/relay-logs")
def list_relay_logs_endpoint(
    db: Session = Depends(get_db_session),
    service_type: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    return _success(
        _serialize_models(
            list_relay_logs(
                db,
                service_type=service_type,
                limit=limit,
                offset=offset,
            ),
            RelayLogRead,
        )
    )


@router.get("/relay-logs/{relay_log_id}")
def get_relay_log_endpoint(relay_log_id: int, db: Session = Depends(get_db_session)):
    relay_log = get_relay_log_by_id(db, relay_log_id)
    if relay_log is None:
        raise _not_found("请求日志")
    return _success(_serialize_model(relay_log, RelayLogRead))


@router.get("/stats/totals")
def list_stats_totals_endpoint(db: Session = Depends(get_db_session)):
    return _success(_serialize_models(list_stats_totals(db), StatsTotalRead))


@router.get("/stats/totals/{stats_total_id}")
def get_stats_total_endpoint(
    stats_total_id: int, db: Session = Depends(get_db_session)
):
    stats_total = get_stats_total_by_id(db, stats_total_id)
    if stats_total is None:
        raise _not_found("累计统计")
    return _success(_serialize_model(stats_total, StatsTotalRead))


@router.get("/stats/dailies")
def list_stats_dailies_endpoint(db: Session = Depends(get_db_session)):
    return _success(_serialize_models(list_stats_dailies(db), StatsDailyRead))


@router.get("/stats/hourlies")
def list_stats_hourlies_endpoint(db: Session = Depends(get_db_session)):
    return _success(_serialize_models(list_stats_hourlies(db), StatsHourlyRead))


@router.get("/settings")
def list_settings_endpoint(db: Session = Depends(get_db_session)):
    return _success(_serialize_settings(db))


@router.patch("/settings")
def patch_settings_endpoint(
    payload: SettingsUpdatePayload,
    db: Session = Depends(get_db_session),
):
    if not payload.items:
        raise HTTPException(status_code=400, detail="更新项不能为空")

    updates: dict[str, Any] = {}
    valid_keys = set(DEFAULT_SETTINGS_VALUES.keys())
    for item in payload.items:
        if item.key not in valid_keys:
            raise HTTPException(status_code=400, detail=f"不支持的配置项: {item.key}")
        updates[item.key] = item.value

    upsert_settings(db, dump_settings_dict(updates))
    refresh_settings_cache()
    return _success(_serialize_settings(db), "更新成功")
