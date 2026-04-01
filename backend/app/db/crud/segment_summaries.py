"""分段小结 CRUD。"""

from typing import Optional

from sqlmodel import Session, select

from app.db.models import SegmentSummary, SegmentSummaryTranscriptMap


def create_segment_summary(
    db: Session,
    session_id: int,
    text: str,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    score: Optional[float] = None,
) -> SegmentSummary:
    """创建分段小结。"""
    summary = SegmentSummary(
        session_id=session_id,
        text=text,
        start_time=start_time,
        end_time=end_time,
        score=score,
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return summary


def list_segment_summaries_by_session(db: Session, session_id: int) -> list[SegmentSummary]:
    """按课堂获取分段小结。"""
    statement = (
        select(SegmentSummary)
        .where(SegmentSummary.session_id == session_id)
        .order_by(SegmentSummary.start_time, SegmentSummary.created_at)
    )
    return list(db.exec(statement))


def link_segment_summary_to_transcript(
    db: Session,
    segment_summary_id: int,
    transcript_id: int,
) -> SegmentSummaryTranscriptMap:
    """建立分段小结与转写片段的映射。"""
    mapping = SegmentSummaryTranscriptMap(
        segment_summary_id=segment_summary_id,
        transcript_id=transcript_id,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping
