"""REST API 路由。"""

from __future__ import annotations

import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict
from sqlmodel import Session

from app.api.deps import get_db_session
from app.config import refresh_settings_cache
from app.config_defaults import DEFAULT_SETTINGS_VALUES, SENSITIVE_SETTING_KEYS
from app.db.config_store import dump_settings_dict, load_settings_dict
from app.core.report import ReportProcessor
from app.db.crud import (
    close_session,
    create_course,
    create_report,
    create_session,
    get_keyword_by_id,
    get_knowledge_point_by_id,
    list_settings,
    get_course_by_id,
    get_question_by_id,
    get_quiz_item_by_id,
    get_relay_log_by_id,
    get_report_by_id,
    get_segment_summary_by_id,
    get_session_by_id,
    get_stats_total_by_id,
    get_transcript_by_id,
    list_courses,
    list_keywords,
    list_keywords_by_session,
    list_knowledge_points,
    list_knowledge_points_by_session,
    list_questions,
    list_questions_by_session,
    list_question_transcript_maps,
    list_quiz_items,
    list_quiz_items_by_session,
    list_quiz_item_transcript_maps,
    list_relay_logs,
    list_reports,
    list_reports_by_session,
    list_segment_summaries,
    list_segment_summaries_by_session,
    list_segment_summary_transcript_maps,
    list_sessions,
    list_stats_dailies,
    list_stats_hourlies,
    list_stats_totals,
    list_transcripts,
    list_transcripts_by_session,
    list_keyword_transcript_maps,
    list_knowledge_point_transcript_maps,
    upsert_settings,
    update_course,
    update_question,
    update_report,
    update_session,
    delete_course,
    delete_session,
)
from app.utils.time import now_ts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["rest"])

_QUESTION_SIMILARITY_THRESHOLD = 0.55


def _question_tokens(text: str) -> set[str]:
    """将问题文本切成用于相似度判断的轻量 token 集合。"""
    import re

    normalized = re.sub(r"\s+", "", text or "").lower()
    words = re.findall(r"[\u4e00-\u9fff]+|[a-z0-9]+", normalized)
    tokens: set[str] = set()
    for word in words:
        if re.fullmatch(r"[\u4e00-\u9fff]+", word):
            if len(word) <= 2:
                tokens.add(word)
            else:
                tokens.update(word)
                tokens.update(word[index : index + 2] for index in range(len(word) - 1))
        else:
            tokens.add(word)
    return tokens


def _question_similarity(left: str, right: str) -> float:
    """基于分词 token 的 Jaccard 相似度。"""
    left_tokens = _question_tokens(left)
    right_tokens = _question_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def _select_diverse_top_questions(questions: list[Any], limit: int = 10) -> list[Any]:
    """按评分优先选择问题，同时跳过语义相近的问题。"""
    sorted_questions = sorted(
        questions,
        key=lambda x: (
            x.score is None,
            -(x.score or 0),
            x.created_at,
        ),
    )
    selected = []
    for question in sorted_questions:
        if any(
            _question_similarity(question.text, picked.text)
            >= _QUESTION_SIMILARITY_THRESHOLD
            for picked in selected
        ):
            continue
        selected.append(question)
        if len(selected) >= limit:
            break
    return selected


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


class KeywordRead(BaseModel):
    """关键词输出结构。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    keyword_sets: str
    source: str = "llm"
    created_at: int


class QuizItemRead(BaseModel):
    """小测题目输出结构。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    type: str | None = None
    question: str
    answer: str | None = None
    explanation: str | None = None
    created_at: int


class KnowledgePointRead(BaseModel):
    """知识点输出结构。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    name: str
    description: str | None = None
    difficulty: str | None = None
    created_at: int


class ReportRead(BaseModel):
    """课后报告输出结构。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    content: str | None = None
    file_path: str | None = None
    created_at: int


class WithTranscriptSegments(BaseModel):
    """包含关联转写分段信息的输出结构。"""

    transcript_ids: list[int] = []
    transcript_segments: list[TranscriptRead] = []
    transcript_joined_text: str = ""


class QuestionDetailRead(QuestionRead, WithTranscriptSegments):
    """问题详情输出结构。"""


class SegmentSummaryDetailRead(SegmentSummaryRead, WithTranscriptSegments):
    """分段小结详情输出结构。"""


class KeywordDetailRead(KeywordRead, WithTranscriptSegments):
    """关键词详情输出结构。"""


class QuizItemDetailRead(QuizItemRead, WithTranscriptSegments):
    """小测题目详情输出结构。"""


class KnowledgePointDetailRead(KnowledgePointRead, WithTranscriptSegments):
    """知识点详情输出结构。"""


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


def _serialize_with_related_transcripts(
    db: Session,
    model: Any,
    schema: type[BaseModel],
    mapping_loader,
    entity_key: str,
) -> dict[str, Any]:
    """序列化模型并附带关联转写分段。"""
    serialized = _serialize_model(model, schema)

    mapping_query = {entity_key: getattr(model, "id", None)}
    mappings = mapping_loader(db, **mapping_query)

    transcript_id_set: set[int] = {
        int(item.transcript_id)
        for item in mappings
        if getattr(item, "transcript_id", None) is not None
    }
    transcript_ids = sorted(transcript_id_set)

    transcript_objects = [
        transcript
        for transcript_id in transcript_ids
        for transcript in [get_transcript_by_id(db, transcript_id)]
        if transcript is not None
    ]

    transcript_objects.sort(
        key=lambda transcript: (
            (
                transcript.start_time
                if transcript.start_time is not None
                else transcript.created_at
            ),
            transcript.created_at,
            transcript.seq if transcript.seq is not None else 0,
            transcript.id,
        )
    )

    transcript_segments = [
        _serialize_model(transcript, TranscriptRead)
        for transcript in transcript_objects
    ]

    transcript_joined_text = "\n".join(
        transcript.text.strip()
        for transcript in transcript_objects
        if isinstance(transcript.text, str) and transcript.text.strip()
    )

    return {
        **serialized,
        "transcript_ids": transcript_ids,
        "transcript_segments": transcript_segments,
        "transcript_joined_text": transcript_joined_text,
    }


def _serialize_models_with_related_transcripts(
    db: Session,
    models: list[Any],
    schema: type[BaseModel],
    mapping_loader,
    entity_key: str,
) -> list[dict[str, Any]]:
    """批量序列化模型并附带关联转写分段。"""
    return [
        _serialize_with_related_transcripts(
            db,
            model,
            schema,
            mapping_loader,
            entity_key,
        )
        for model in models
    ]


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


def _require_keyword(db: Session, keyword_id: int):
    keyword = get_keyword_by_id(db, keyword_id)
    if keyword is None:
        raise _not_found("关键词")
    return keyword


def _require_quiz_item(db: Session, quiz_item_id: int):
    quiz_item = get_quiz_item_by_id(db, quiz_item_id)
    if quiz_item is None:
        raise _not_found("小测题目")
    return quiz_item


def _require_knowledge_point(db: Session, knowledge_point_id: int):
    knowledge_point = get_knowledge_point_by_id(db, knowledge_point_id)
    if knowledge_point is None:
        raise _not_found("知识点")
    return knowledge_point


def _require_report(db: Session, report_id: int):
    report = get_report_by_id(db, report_id)
    if report is None:
        raise _not_found("课后报告")
    return report


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
    session_record = _require_session(db, session_id)
    start_time = (
        now_ts()
        if payload is None or payload.start_time is None
        else payload.start_time
    )

    # 已有开始时间时，不允许用更晚的时间覆盖。
    if (
        session_record.start_time is not None
        and start_time > session_record.start_time
    ):
        return _success({}, "课堂已开始")

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
    session_record = _require_session(db, session_id)
    end_time = (
        now_ts() if payload is None or payload.end_time is None else payload.end_time
    )

    # 已有结束时间时，不允许用更早的时间覆盖。
    if (
        session_record.end_time is not None
        and end_time < session_record.end_time
    ):
        return _success({}, "课堂已结束")

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
    return _success(
        _serialize_models_with_related_transcripts(
            db,
            list_questions(db),
            QuestionRead,
            list_question_transcript_maps,
            "question_id",
        )
    )


@router.get("/questions/{question_id}")
def get_question_endpoint(question_id: int, db: Session = Depends(get_db_session)):
    question = _require_question(db, question_id)
    return _success(
        _serialize_with_related_transcripts(
            db,
            question,
            QuestionDetailRead,
            list_question_transcript_maps,
            "question_id",
        )
    )


@router.get("/sessions/{session_id}/questions")
def list_session_questions_endpoint(
    session_id: int, db: Session = Depends(get_db_session)
):
    _require_session(db, session_id)
    return _success(
        _serialize_models_with_related_transcripts(
            db,
            list_questions_by_session(db, session_id),
            QuestionRead,
            list_question_transcript_maps,
            "question_id",
        )
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
    return _success(
        _serialize_models_with_related_transcripts(
            db,
            list_segment_summaries(db),
            SegmentSummaryRead,
            list_segment_summary_transcript_maps,
            "segment_summary_id",
        )
    )


@router.get("/segment-summaries/{summary_id}")
def get_segment_summary_endpoint(
    summary_id: int, db: Session = Depends(get_db_session)
):
    summary = get_segment_summary_by_id(db, summary_id)
    if summary is None:
        raise _not_found("分段小结")
    return _success(
        _serialize_with_related_transcripts(
            db,
            summary,
            SegmentSummaryDetailRead,
            list_segment_summary_transcript_maps,
            "segment_summary_id",
        )
    )


@router.get("/sessions/{session_id}/segment-summaries")
def list_session_segment_summaries_endpoint(
    session_id: int, db: Session = Depends(get_db_session)
):
    _require_session(db, session_id)
    return _success(
        _serialize_models_with_related_transcripts(
            db,
            list_segment_summaries_by_session(db, session_id),
            SegmentSummaryRead,
            list_segment_summary_transcript_maps,
            "segment_summary_id",
        )
    )


@router.get("/keywords")
def list_keywords_endpoint(db: Session = Depends(get_db_session)):
    return _success(
        _serialize_models_with_related_transcripts(
            db,
            list_keywords(db),
            KeywordRead,
            list_keyword_transcript_maps,
            "keyword_id",
        )
    )


@router.get("/keywords/{keyword_id}")
def get_keyword_endpoint(keyword_id: int, db: Session = Depends(get_db_session)):
    keyword = _require_keyword(db, keyword_id)
    return _success(
        _serialize_with_related_transcripts(
            db,
            keyword,
            KeywordDetailRead,
            list_keyword_transcript_maps,
            "keyword_id",
        )
    )


@router.get("/sessions/{session_id}/keywords")
def list_session_keywords_endpoint(
    session_id: int, db: Session = Depends(get_db_session)
):
    _require_session(db, session_id)
    return _success(
        _serialize_models_with_related_transcripts(
            db,
            list_keywords_by_session(db, session_id),
            KeywordRead,
            list_keyword_transcript_maps,
            "keyword_id",
        )
    )


@router.get("/quiz-items")
def list_quiz_items_endpoint(db: Session = Depends(get_db_session)):
    return _success(
        _serialize_models_with_related_transcripts(
            db,
            list_quiz_items(db),
            QuizItemRead,
            list_quiz_item_transcript_maps,
            "quiz_item_id",
        )
    )


@router.get("/quiz-items/{quiz_item_id}")
def get_quiz_item_endpoint(quiz_item_id: int, db: Session = Depends(get_db_session)):
    quiz_item = _require_quiz_item(db, quiz_item_id)
    return _success(
        _serialize_with_related_transcripts(
            db,
            quiz_item,
            QuizItemDetailRead,
            list_quiz_item_transcript_maps,
            "quiz_item_id",
        )
    )


@router.get("/sessions/{session_id}/quiz-items")
def list_session_quiz_items_endpoint(
    session_id: int, db: Session = Depends(get_db_session)
):
    _require_session(db, session_id)
    return _success(
        _serialize_models_with_related_transcripts(
            db,
            list_quiz_items_by_session(db, session_id),
            QuizItemRead,
            list_quiz_item_transcript_maps,
            "quiz_item_id",
        )
    )


@router.get("/knowledge-points")
def list_knowledge_points_endpoint(db: Session = Depends(get_db_session)):
    return _success(
        _serialize_models_with_related_transcripts(
            db,
            list_knowledge_points(db),
            KnowledgePointRead,
            list_knowledge_point_transcript_maps,
            "knowledge_point_id",
        )
    )


@router.get("/knowledge-points/{knowledge_point_id}")
def get_knowledge_point_endpoint(
    knowledge_point_id: int, db: Session = Depends(get_db_session)
):
    knowledge_point = _require_knowledge_point(db, knowledge_point_id)
    return _success(
        _serialize_with_related_transcripts(
            db,
            knowledge_point,
            KnowledgePointDetailRead,
            list_knowledge_point_transcript_maps,
            "knowledge_point_id",
        )
    )


@router.get("/sessions/{session_id}/knowledge-points")
def list_session_knowledge_points_endpoint(
    session_id: int, db: Session = Depends(get_db_session)
):
    _require_session(db, session_id)
    return _success(
        _serialize_models_with_related_transcripts(
            db,
            list_knowledge_points_by_session(db, session_id),
            KnowledgePointRead,
            list_knowledge_point_transcript_maps,
            "knowledge_point_id",
        )
    )


@router.get("/reports")
def list_reports_endpoint(db: Session = Depends(get_db_session)):
    return _success(_serialize_models(list_reports(db), ReportRead))


@router.get("/reports/{report_id}")
def get_report_endpoint(report_id: int, db: Session = Depends(get_db_session)):
    report = _require_report(db, report_id)
    return _success(_serialize_model(report, ReportRead))


@router.get("/sessions/{session_id}/reports")
def list_session_reports_endpoint(
    session_id: int, db: Session = Depends(get_db_session)
):
    _require_session(db, session_id)
    return _success(
        _serialize_models(list_reports_by_session(db, session_id), ReportRead)
    )


def _run_report_generation(report_id: int, session_id: int, material: str) -> None:
    """在线程中生成报告，PDF 导出失败时保留 HTML 报告。"""
    try:
        logger.info("开始生成课后报告 (report_id=%d)", report_id)
        processor = ReportProcessor()
        html_content = processor.generate_report(material=material)

        pdf_file_path = _try_save_report_as_pdf(report_id, session_id, html_content)

        # 更新数据库中的报告内容和文件路径
        from app.db import get_engine

        with Session(get_engine()) as db:
            update_report(
                db,
                report_id,
                content=html_content,
                file_path=pdf_file_path,
            )

        if pdf_file_path:
            logger.info("课后报告生成完成 (report_id=%d, pdf=%s)", report_id, pdf_file_path)
        else:
            logger.info("课后报告生成完成 (report_id=%d, pdf=未生成)", report_id)
    except Exception as e:
        logger.error("课后报告生成失败 (report_id=%d): %s", report_id, e)
        # 记录错误信息到报告内容中
        from app.db import get_engine

        with Session(get_engine()) as db:
            update_report(db, report_id, content=f"<p>报告生成失败: {str(e)}</p>")


def _start_report_generation(report_id: int, session_id: int, material: str) -> None:
    """启动独立线程，避免课后报告任务阻塞请求生命周期。"""
    thread = threading.Thread(
        target=_run_report_generation,
        args=(report_id, session_id, material),
        name=f"report-generator-{report_id}",
        daemon=True,
    )
    thread.start()


def _try_save_report_as_pdf(
    report_id: int, session_id: int, html_content: str
) -> str | None:
    """尝试导出 PDF；失败时保存 HTML 文件作为降级产物。"""
    try:
        return _save_report_as_pdf(report_id, session_id, html_content)
    except Exception as e:
        logger.warning("PDF 导出失败，改为保存 HTML 报告 (report_id=%d): %s", report_id, e)
        return _save_report_as_html(report_id, session_id, html_content)


def _save_report_as_pdf(report_id: int, session_id: int, html_content: str) -> str:
    """将 HTML 报告转换为 PDF 并保存。返回相对文件路径。"""
    # 创建 data/reports 文件夹
    reports_dir = Path("data") / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # 生成文件名（使用报告 ID 和时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"report_session{session_id}_id{report_id}_{timestamp}.pdf"
    pdf_path = reports_dir / pdf_filename

    try:
        # 使用 Playwright/Chromium 转换 HTML 为 PDF
        _render_html_to_pdf(html_content, pdf_path)

        # 返回相对路径
        relative_path = str(pdf_path).replace("\\", "/")
        logger.info("PDF 已保存: %s", relative_path)
        return relative_path
    except Exception as e:
        logger.error("PDF 生成失败: %s", e)
        raise


def _save_report_as_html(report_id: int, session_id: int, html_content: str) -> str:
    """将 HTML 报告保存为文件。返回相对文件路径。"""
    reports_dir = Path("data") / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_filename = f"report_session{session_id}_id{report_id}_{timestamp}.html"
    html_path = reports_dir / html_filename
    html_path.write_text(html_content, encoding="utf-8")

    relative_path = str(html_path).replace("\\", "/")
    logger.info("HTML 报告已保存: %s", relative_path)
    return relative_path


def _render_html_to_pdf(html_content: str, pdf_path: Path) -> None:
    """使用 Playwright Chromium 渲染 HTML 并打印为 PDF。"""
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        logger.error("playwright 不可用，无法生成 PDF: %s", e)
        raise RuntimeError(
            "PDF 生成库不可用，请安装 playwright 并执行 python -m playwright install chromium"
        ) from e

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html_content, wait_until="load")
            page.pdf(
                path=str(pdf_path),
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                margin={
                    "top": "18mm",
                    "right": "16mm",
                    "bottom": "18mm",
                    "left": "16mm",
                },
            )
        finally:
            browser.close()


def _build_report_material(
    session_id: int,
    course_id: int,
    db: Session,
) -> str:
    """构建课后报告所需的核心材料。"""
    import json

    parts = []

    # 1. 课程信息
    course = get_course_by_id(db, course_id)
    if course:
        parts.append("# 课程信息\n")
        parts.append(f"课程代码: {course.code or 'N/A'}\n")
        parts.append(f"课程名称: {course.name or 'N/A'}\n")
        parts.append(f"授课教师: {course.teacher or 'N/A'}\n")
        parts.append(f"课程描述: {course.description or 'N/A'}\n\n")

    # 2. 课堂信息
    session = get_session_by_id(db, session_id)
    if session:
        parts.append("# 课堂信息\n")
        parts.append(f"课堂标题: {session.title or 'N/A'}\n")
        parts.append(f"课堂序号: {session.seq or 'N/A'}\n\n")

    # 3. 转写分段（从旧到新）
    transcripts = list_transcripts_by_session(db, session_id)
    if transcripts:
        parts.append("# 老师讲课原文（可能有转译错误）\n\n")
        for transcript in transcripts:
            parts.append(f"{transcript.text}\n")
        parts.append("\n\n")

    # 4. 分段小结（从旧到新）
    summaries = list_segment_summaries_by_session(db, session_id)
    # 需要反序因为默认是新到旧
    summaries_asc = sorted(summaries, key=lambda x: x.created_at)
    if summaries_asc:
        parts.append("# 分段小结\n\n")
        for summary in summaries_asc:
            parts.append(f"{summary.text}\n")
        parts.append("\n\n")

    # 5. 高分模拟学生提问（按评分优先，跳过相似问题）
    questions = list_questions_by_session(db, session_id)
    top_questions = _select_diverse_top_questions(questions, limit=10)
    if top_questions:
        parts.append("# 高分模拟学生提问（最多 10 个，请在报告中生成参考回答）\n\n")
        for index, q in enumerate(top_questions, start=1):
            parts.append(f"{index}. {q.text}\n")
            parts.append(f"状态: {q.status or 'N/A'}\n")
            parts.append(f"分数: {q.score or 'N/A'}\n\n")

    # 6. LLM 关键词（去重）
    keywords = list_keywords_by_session(db, session_id, source="llm")
    keywords_asc = sorted(keywords, key=lambda x: x.created_at)
    deduped_keywords = []
    seen_keywords = set()
    for kw in keywords_asc:
        try:
            raw_keywords = json.loads(kw.keyword_sets)
        except (json.JSONDecodeError, TypeError):
            raw_keywords = kw.keyword_sets
        if isinstance(raw_keywords, str):
            keyword_items = [raw_keywords]
        else:
            keyword_items = raw_keywords if isinstance(raw_keywords, list) else []
        for item in keyword_items:
            keyword = str(item).strip()
            if not keyword or keyword in seen_keywords:
                continue
            seen_keywords.add(keyword)
            deduped_keywords.append(keyword)
    if deduped_keywords:
        parts.append("# LLM关键词（已去重）\n\n")
        parts.append("、".join(deduped_keywords))
        parts.append("\n\n")

    # 7. 知识点（从旧到新）
    knowledge_points = list_knowledge_points_by_session(db, session_id)
    kp_asc = sorted(knowledge_points, key=lambda x: x.created_at)
    if kp_asc:
        parts.append("# 知识点\n\n")
        for index, kp in enumerate(kp_asc, start=1):
            parts.append(f"{index}. {kp.name}\n")
            if kp.description:
                parts.append(f"说明: {kp.description}\n")
            if kp.difficulty:
                parts.append(f"难度: {kp.difficulty}\n")
            parts.append("\n")

    # 8. 小测题目（从旧到新，原样展示）
    quiz_items = list_quiz_items_by_session(db, session_id)
    quiz_asc = sorted(quiz_items, key=lambda x: x.created_at)
    if quiz_asc:
        parts.append("# 小测题目（原样展示）\n\n")
        for index, quiz in enumerate(quiz_asc, start=1):
            parts.append(f"{index}. 题型: {quiz.type or 'N/A'}\n")
            parts.append(f"题目: {quiz.question}\n")
            if quiz.answer:
                parts.append(f"答案: {quiz.answer}\n")
            if quiz.explanation:
                parts.append(f"解释: {quiz.explanation}\n")
            parts.append("\n")

    return "".join(parts)


@router.post("/sessions/{session_id}/reports")
def generate_report_endpoint(
    session_id: int,
    db: Session = Depends(get_db_session),
):
    """触发课后报告生成（异步），立即返回"""
    session = _require_session(db, session_id)

    # 验证有转写数据
    transcripts = list_transcripts_by_session(db, session_id)
    if not transcripts:
        raise HTTPException(status_code=400, detail="该课堂没有转写数据，无法生成报告")

    # 构建完整的报告材料（包含所有课堂数据）
    material = _build_report_material(session_id, session.course_id, db)

    # 创建报告记录（初始状态，内容为空）
    report = create_report(db, session_id=session_id, content=None)

    # 后台异步生成任务（FastAPI BackgroundTasks）
    _start_report_generation(report.id, session_id, material)

    return _success(
        _serialize_model(report, ReportRead),
        "报告生成已启动，请稍候...",
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
