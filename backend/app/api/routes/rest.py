"""REST API 路由。"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
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
    list_quiz_items,
    list_quiz_items_by_session,
    list_relay_logs,
    list_reports,
    list_reports_by_session,
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
    update_report,
    update_session,
    delete_course,
    delete_session,
)
from app.utils.time import now_ts

logger = logging.getLogger(__name__)

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


class KeywordRead(BaseModel):
    """关键词输出结构。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    keyword_sets: str
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


@router.get("/keywords")
def list_keywords_endpoint(db: Session = Depends(get_db_session)):
    return _success(_serialize_models(list_keywords(db), KeywordRead))


@router.get("/keywords/{keyword_id}")
def get_keyword_endpoint(keyword_id: int, db: Session = Depends(get_db_session)):
    keyword = _require_keyword(db, keyword_id)
    return _success(_serialize_model(keyword, KeywordRead))


@router.get("/sessions/{session_id}/keywords")
def list_session_keywords_endpoint(
    session_id: int, db: Session = Depends(get_db_session)
):
    _require_session(db, session_id)
    return _success(
        _serialize_models(list_keywords_by_session(db, session_id), KeywordRead)
    )


@router.get("/quiz-items")
def list_quiz_items_endpoint(db: Session = Depends(get_db_session)):
    return _success(_serialize_models(list_quiz_items(db), QuizItemRead))


@router.get("/quiz-items/{quiz_item_id}")
def get_quiz_item_endpoint(quiz_item_id: int, db: Session = Depends(get_db_session)):
    quiz_item = _require_quiz_item(db, quiz_item_id)
    return _success(_serialize_model(quiz_item, QuizItemRead))


@router.get("/sessions/{session_id}/quiz-items")
def list_session_quiz_items_endpoint(
    session_id: int, db: Session = Depends(get_db_session)
):
    _require_session(db, session_id)
    return _success(
        _serialize_models(list_quiz_items_by_session(db, session_id), QuizItemRead)
    )


@router.get("/knowledge-points")
def list_knowledge_points_endpoint(db: Session = Depends(get_db_session)):
    return _success(_serialize_models(list_knowledge_points(db), KnowledgePointRead))


@router.get("/knowledge-points/{knowledge_point_id}")
def get_knowledge_point_endpoint(
    knowledge_point_id: int, db: Session = Depends(get_db_session)
):
    knowledge_point = _require_knowledge_point(db, knowledge_point_id)
    return _success(_serialize_model(knowledge_point, KnowledgePointRead))


@router.get("/sessions/{session_id}/knowledge-points")
def list_session_knowledge_points_endpoint(
    session_id: int, db: Session = Depends(get_db_session)
):
    _require_session(db, session_id)
    return _success(
        _serialize_models(
            list_knowledge_points_by_session(db, session_id), KnowledgePointRead
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


async def _generate_report_background(report_id: int, session_id: int, material: str):
    """后台异步生成报告，生成 PDF 并保存，更新数据库。"""
    try:
        logger.info("开始生成课后报告 (report_id=%d)", report_id)
        processor = ReportProcessor()
        html_content = processor.generate_report(material=material, max_iters=1)

        # 生成 PDF 文件
        pdf_file_path = await asyncio.to_thread(
            _save_report_as_pdf,
            report_id,
            session_id,
            html_content,
        )

        # 更新数据库中的报告内容和文件路径
        from app.db import get_engine

        with Session(get_engine()) as db:
            update_report(
                db,
                report_id,
                content=html_content,
                file_path=pdf_file_path,
            )

        logger.info("课后报告生成完成 (report_id=%d, pdf=%s)", report_id, pdf_file_path)
    except Exception as e:
        logger.error("课后报告生成失败 (report_id=%d): %s", report_id, e)
        # 记录错误信息到报告内容中
        from app.db import get_engine

        with Session(get_engine()) as db:
            update_report(db, report_id, content=f"<p>报告生成失败: {str(e)}</p>")


def _save_report_as_pdf(report_id: int, session_id: int, html_content: str) -> str:
    """将 HTML 报告转换为 PDF 并保存。返回相对文件路径。"""
    try:
        from weasyprint import HTML, CSS
    except ImportError:
        logger.error("weasyprint 未安装，无法生成 PDF")
        raise RuntimeError("PDF 生成库缺失，请安装 weasyprint")

    # 创建 data/reports 文件夹
    reports_dir = Path("data") / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # 生成文件名（使用报告 ID 和时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_filename = f"report_session{session_id}_id{report_id}_{timestamp}.pdf"
    pdf_path = reports_dir / pdf_filename

    try:
        # 使用 weasyprint 转换 HTML 为 PDF
        HTML(string=html_content).write_pdf(str(pdf_path))

        # 返回相对路径
        relative_path = str(pdf_path).replace("\\", "/")
        logger.info("PDF 已保存: %s", relative_path)
        return relative_path
    except Exception as e:
        logger.error("PDF 生成失败: %s", e)
        raise


def _build_report_material(
    session_id: int,
    course_id: int,
    db: Session,
) -> str:
    """收集所有课堂数据并构建报告材料（从旧到新排序，带标题）。"""
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
            parts.append(f"{transcript.text}")
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

    # 5. 问题（从旧到新）
    questions = list_questions_by_session(db, session_id)
    # 需要反序因为默认是新到旧
    questions_asc = sorted(questions, key=lambda x: x.created_at)
    if questions_asc:
        parts.append("# 课堂提问\n\n")
        for q in questions_asc:
            parts.append(f"{q.text}\n")
            parts.append(f"状态: {q.status or 'N/A'}\n")
            parts.append(f"分数: {q.score or 'N/A'}\n\n")

    # 6. 关键词（从旧到新）
    keywords = list_keywords_by_session(db, session_id)
    # 需要反序因为默认是新到旧
    keywords_asc = sorted(keywords, key=lambda x: x.created_at)
    if keywords_asc:
        parts.append("# 关键词\n\n")
        for kw in keywords_asc:
            try:
                keyword_list = json.loads(kw.keyword_sets)
                parts.append(f"{'、'.join(keyword_list)}\n\n")
            except (json.JSONDecodeError, TypeError):
                parts.append(f"{kw.keyword_sets}\n\n")

    # 7. 知识点（从旧到新）
    knowledge_points = list_knowledge_points_by_session(db, session_id)
    # 需要反序因为默认是新到旧
    kp_asc = sorted(knowledge_points, key=lambda x: x.created_at)
    if kp_asc:
        parts.append("# 知识点\n\n")
        for kp in kp_asc:
            parts.append(f"名称: {kp.name}\n")
            if kp.description:
                parts.append(f"描述: {kp.description}\n")
            if kp.difficulty:
                parts.append(f"难度: {kp.difficulty}\n")
            parts.append("\n")

    # 8. 小测题目（从旧到新）
    quiz_items = list_quiz_items_by_session(db, session_id)
    # 需要反序因为默认是新到旧
    quiz_asc = sorted(quiz_items, key=lambda x: x.created_at)
    if quiz_asc:
        parts.append("# 小测题目\n\n")
        for quiz in quiz_asc:
            parts.append(f"题型: {quiz.type or 'N/A'}\n")
            parts.append(f"问题: {quiz.question}\n")
            if quiz.answer:
                parts.append(f"答案: {quiz.answer}\n")
            if quiz.explanation:
                parts.append(f"解释: {quiz.explanation}\n")
            parts.append("\n")

    return "".join(parts)


@router.post("/sessions/{session_id}/reports")
def generate_report_endpoint(
    session_id: int,
    background_tasks: BackgroundTasks,
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
    background_tasks.add_task(
        _generate_report_background,
        report.id,
        session_id,
        material,
    )

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
