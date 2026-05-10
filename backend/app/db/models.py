"""SQLModel 数据模型定义。"""

from typing import Optional

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.utils.time import now_ts


class Course(SQLModel, table=True):
    """课程记录。"""

    __tablename__ = "courses"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    teacher: Optional[str] = Field(default=None)
    created_at: int = Field(default_factory=now_ts, nullable=False)


class SessionRecord(SQLModel, table=True):
    """课堂会话记录。"""

    __tablename__ = "sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="courses.id", index=True)
    seq: Optional[int] = Field(default=None)
    title: Optional[str] = Field(default=None)
    start_time: Optional[int] = Field(default=None)
    end_time: Optional[int] = Field(default=None)
    config: Optional[str] = Field(default=None)
    created_at: int = Field(default_factory=now_ts, nullable=False)


class Transcript(SQLModel, table=True):
    """课堂转写片段。"""

    __tablename__ = "transcripts"
    __table_args__ = (
        Index("idx_transcripts_session", "session_id"),
        Index("idx_transcripts_time", "session_id", "start_time"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="sessions.id", nullable=False)
    seq: Optional[int] = Field(default=None)
    text: str = Field(nullable=False)
    start_time: Optional[int] = Field(default=None)
    end_time: Optional[int] = Field(default=None)
    created_at: int = Field(default_factory=now_ts, nullable=False)


class Question(SQLModel, table=True):
    """课堂提问记录。"""

    __tablename__ = "questions"
    __table_args__ = (
        Index("idx_questions_session", "session_id"),
        Index("idx_questions_status", "status"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="sessions.id", nullable=False)
    text: str = Field(nullable=False)
    status: Optional[str] = Field(default="generated")
    score: Optional[float] = Field(default=None)
    created_at: int = Field(default_factory=now_ts, nullable=False)
    asked_at: Optional[int] = Field(default=None)


class QuestionTranscriptMap(SQLModel, table=True):
    """问题与转写上下文映射。"""

    __tablename__ = "question_transcript_map"
    __table_args__ = (
        Index("idx_qt_question", "question_id"),
        Index("idx_qt_transcript", "transcript_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    question_id: int = Field(foreign_key="questions.id", nullable=False)
    transcript_id: int = Field(foreign_key="transcripts.id", nullable=False)


class SegmentSummary(SQLModel, table=True):
    """课堂分段小结。"""

    __tablename__ = "segment_summaries"
    __table_args__ = (
        Index("idx_seg_sum_session", "session_id"),
        Index("idx_seg_sum_time", "session_id", "start_time"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="sessions.id", nullable=False)
    text: str = Field(nullable=False)
    start_time: Optional[int] = Field(default=None)
    end_time: Optional[int] = Field(default=None)
    score: Optional[float] = Field(default=None)
    created_at: int = Field(default_factory=now_ts, nullable=False)


class SegmentSummaryTranscriptMap(SQLModel, table=True):
    """分段小结与转写映射。"""

    __tablename__ = "segment_summary_transcript_map"
    __table_args__ = (
        Index("idx_seg_sum_map_summary", "segment_summary_id"),
        Index("idx_seg_sum_map_transcript", "transcript_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    segment_summary_id: int = Field(foreign_key="segment_summaries.id", nullable=False)
    transcript_id: int = Field(foreign_key="transcripts.id", nullable=False)


class Keyword(SQLModel, table=True):
    """课堂关键词集合。"""

    __tablename__ = "keywords"
    __table_args__ = (
        Index("idx_keywords_session", "session_id"),
        Index("idx_keywords_source", "session_id", "source"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="sessions.id", nullable=False)
    keyword_sets: str = Field(nullable=False)
    source: str = Field(default=None)
    created_at: int = Field(default_factory=now_ts, nullable=False)


class KeywordTranscriptMap(SQLModel, table=True):
    """关键词与转写上下文映射。"""

    __tablename__ = "keyword_transcript_map"
    __table_args__ = (
        Index("idx_kt_keyword", "keyword_id"),
        Index("idx_kt_transcript", "transcript_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    keyword_id: int = Field(foreign_key="keywords.id", nullable=False)
    transcript_id: int = Field(foreign_key="transcripts.id", nullable=False)


class QuizItem(SQLModel, table=True):
    """课堂小测题目。"""

    __tablename__ = "quiz_items"
    __table_args__ = (
        Index("idx_quiz_session", "session_id"),
        Index("idx_quiz_type", "type"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="sessions.id", nullable=False)
    type: Optional[str] = Field(default=None)
    question: str = Field(nullable=False)
    answer: Optional[str] = Field(default=None)
    explanation: Optional[str] = Field(default=None)
    created_at: int = Field(default_factory=now_ts, nullable=False)


class QuizItemTranscriptMap(SQLModel, table=True):
    """小测题目与转写上下文映射。"""

    __tablename__ = "quiz_item_transcript_map"
    __table_args__ = (
        Index("idx_qitm_quiz", "quiz_item_id"),
        Index("idx_qitm_transcript", "transcript_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    quiz_item_id: int = Field(foreign_key="quiz_items.id", nullable=False)
    transcript_id: int = Field(foreign_key="transcripts.id", nullable=False)


class KnowledgePoint(SQLModel, table=True):
    """课堂知识点。"""

    __tablename__ = "knowledge_points"
    __table_args__ = (
        Index("idx_kp_name", "name"),
        Index("idx_kp_session", "session_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="sessions.id", nullable=False)
    name: str = Field(nullable=False)
    description: Optional[str] = Field(default=None)
    difficulty: Optional[str] = Field(default=None)
    created_at: int = Field(default_factory=now_ts, nullable=False)


class KnowledgePointTranscriptMap(SQLModel, table=True):
    """知识点与转写上下文映射。"""

    __tablename__ = "knowledge_point_transcript_map"
    __table_args__ = (
        Index("idx_kpt_kp", "knowledge_point_id"),
        Index("idx_kpt_transcript", "transcript_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    knowledge_point_id: int = Field(foreign_key="knowledge_points.id", nullable=False)
    transcript_id: int = Field(foreign_key="transcripts.id", nullable=False)


class Report(SQLModel, table=True):
    """课后报告。"""

    __tablename__ = "reports"
    __table_args__ = (Index("idx_reports_session", "session_id"),)

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="sessions.id", nullable=False)
    content: Optional[str] = Field(default=None)
    file_path: Optional[str] = Field(default=None)
    created_at: int = Field(default_factory=now_ts, nullable=False)


class LLMInfo(SQLModel, table=True):
    """LLM 模型价格信息。"""

    __tablename__ = "llm_infos"

    name: str = Field(primary_key=True)
    input: Optional[float] = Field(default=None)
    output: Optional[float] = Field(default=None)
    cache_read: Optional[float] = Field(default=None)
    cache_write: Optional[float] = Field(default=None)


class RelayLog(SQLModel, table=True):
    """请求日志。"""

    __tablename__ = "relay_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    time: int = Field(nullable=False)
    service_type: str = Field(nullable=False, index=True)
    request_model_name: Optional[str] = Field(default=None)
    input_value: Optional[float] = Field(default=0)
    output_value: Optional[float] = Field(default=0)
    latency: Optional[int] = Field(default=None)
    first_response_time: Optional[int] = Field(default=None)
    status: Optional[str] = Field(default=None)
    request_content: Optional[str] = Field(default=None)
    response_content: Optional[str] = Field(default=None)
    error: Optional[str] = Field(default=None)
    attempts: Optional[str] = Field(default=None)
    total_attempts: Optional[int] = Field(default=None)


class StatsTotal(SQLModel, table=True):
    """全量累计统计。"""

    __tablename__ = "stats_totals"

    id: Optional[int] = Field(default=None, primary_key=True)
    service_type: str = Field(nullable=False, index=True)
    input_value: Optional[int] = Field(default=0)
    output_value: Optional[int] = Field(default=0)
    wait_time: Optional[int] = Field(default=None)
    request_success: Optional[int] = Field(default=0)
    request_failed: Optional[int] = Field(default=0)


class StatsDaily(SQLModel, table=True):
    """按日统计。"""

    __tablename__ = "stats_dailies"

    date: str = Field(primary_key=True)
    service_type: str = Field(primary_key=True)
    input_value: Optional[int] = Field(default=0)
    output_value: Optional[int] = Field(default=0)
    wait_time: Optional[int] = Field(default=None)
    request_success: Optional[int] = Field(default=0)
    request_failed: Optional[int] = Field(default=0)


class StatsHourly(SQLModel, table=True):
    """按小时统计。"""

    __tablename__ = "stats_hourlies"

    date: str = Field(primary_key=True)
    hour: int = Field(primary_key=True)
    service_type: str = Field(primary_key=True)
    input_value: Optional[int] = Field(default=0)
    output_value: Optional[int] = Field(default=0)
    wait_time: Optional[int] = Field(default=None)
    request_success: Optional[int] = Field(default=0)
    request_failed: Optional[int] = Field(default=0)


class Setting(SQLModel, table=True):
    """系统设置键值对。"""

    __tablename__ = "settings"

    key: str = Field(primary_key=True)
    value: str = Field(nullable=False)


class MigrationRecord(SQLModel, table=True):
    """数据库迁移版本记录。"""

    __tablename__ = "migration_records"

    version: Optional[int] = Field(default=None, primary_key=True)
    status: Optional[int] = Field(default=None)
