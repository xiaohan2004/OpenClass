"""SQLModel 数据模型定义。"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Index
from sqlmodel import Field, SQLModel


class Course(SQLModel, table=True):
    """课程记录。"""

    __tablename__ = "courses"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: Optional[str] = Field(default=None)
    name: Optional[str] = Field(default=None)
    description: Optional[str] = Field(default=None)
    teacher: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


class SessionRecord(SQLModel, table=True):
    """课堂会话记录。"""

    __tablename__ = "sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    course_id: int = Field(foreign_key="courses.id", index=True)
    seq: Optional[int] = Field(default=None)
    title: Optional[str] = Field(default=None)
    start_time: Optional[datetime] = Field(default=None)
    end_time: Optional[datetime] = Field(default=None)
    config: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


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
    start_time: Optional[float] = Field(default=None)
    end_time: Optional[float] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


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
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    asked_at: Optional[datetime] = Field(default=None)


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
    start_time: Optional[float] = Field(default=None)
    end_time: Optional[float] = Field(default=None)
    score: Optional[float] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


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
    time: Optional[int] = Field(default=None)
    request_model_name: Optional[str] = Field(default=None)
    request_api_key_name: Optional[str] = Field(default=None)
    channel_id: Optional[int] = Field(default=None)
    channel_name: Optional[str] = Field(default=None)
    actual_model_name: Optional[str] = Field(default=None)
    input_tokens: Optional[int] = Field(default=None)
    output_tokens: Optional[int] = Field(default=None)
    ftut: Optional[int] = Field(default=None)
    use_time: Optional[int] = Field(default=None)
    cost: Optional[float] = Field(default=None)
    request_content: Optional[str] = Field(default=None)
    response_content: Optional[str] = Field(default=None)
    error: Optional[str] = Field(default=None)
    attempts: Optional[str] = Field(default=None)
    total_attempts: Optional[int] = Field(default=None)


class StatsTotal(SQLModel, table=True):
    """全量累计统计。"""

    __tablename__ = "stats_totals"

    id: Optional[int] = Field(default=None, primary_key=True)
    input_token: Optional[int] = Field(default=None)
    output_token: Optional[int] = Field(default=None)
    input_cost: Optional[float] = Field(default=None)
    output_cost: Optional[float] = Field(default=None)
    wait_time: Optional[int] = Field(default=None)
    request_success: Optional[int] = Field(default=None)
    request_failed: Optional[int] = Field(default=None)


class StatsDaily(SQLModel, table=True):
    """按日统计。"""

    __tablename__ = "stats_dailies"

    date: str = Field(primary_key=True)
    input_token: Optional[int] = Field(default=None)
    output_token: Optional[int] = Field(default=None)
    input_cost: Optional[float] = Field(default=None)
    output_cost: Optional[float] = Field(default=None)
    wait_time: Optional[int] = Field(default=None)
    request_success: Optional[int] = Field(default=None)
    request_failed: Optional[int] = Field(default=None)


class StatsHourly(SQLModel, table=True):
    """按小时统计。"""

    __tablename__ = "stats_hourlies"

    hour: Optional[int] = Field(default=None, primary_key=True)
    date: str = Field(nullable=False)
    input_token: Optional[int] = Field(default=None)
    output_token: Optional[int] = Field(default=None)
    input_cost: Optional[float] = Field(default=None)
    output_cost: Optional[float] = Field(default=None)
    wait_time: Optional[int] = Field(default=None)
    request_success: Optional[int] = Field(default=None)
    request_failed: Optional[int] = Field(default=None)


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
