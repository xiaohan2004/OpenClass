"""分段小结 CRUD。"""

from typing import Optional

from sqlmodel import Session, select

from app.db.models import SegmentSummary, SegmentSummaryTranscriptMap


def create_segment_summary(
    db: Session,
    session_id: int,
    text: str,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
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


def get_segment_summary_by_id(db: Session, summary_id: int) -> Optional[SegmentSummary]:
    """按 ID 获取分段小结。"""
    return db.get(SegmentSummary, summary_id)


def list_segment_summaries(db: Session) -> list[SegmentSummary]:
    """获取全部分段小结。"""
    statement = select(SegmentSummary).order_by(SegmentSummary.__table__.c.created_at.desc())
    return list(db.exec(statement))


def list_segment_summaries_by_session(db: Session, session_id: int) -> list[SegmentSummary]:
    """按课堂获取分段小结。"""
    statement = (
        select(SegmentSummary)
        .where(SegmentSummary.session_id == session_id)
        .order_by(SegmentSummary.start_time, SegmentSummary.created_at)
    )
    return list(db.exec(statement))


def update_segment_summary(db: Session, summary_id: int, **kwargs) -> Optional[SegmentSummary]:
    """更新分段小结。"""
    summary = db.get(SegmentSummary, summary_id)
    if summary is None:
        return None

    for key, value in kwargs.items():
        setattr(summary, key, value)

    db.add(summary)
    db.commit()
    db.refresh(summary)
    return summary


def delete_segment_summary(db: Session, summary_id: int) -> bool:
    """删除分段小结。"""
    summary = db.get(SegmentSummary, summary_id)
    if summary is None:
        return False

    db.delete(summary)
    db.commit()
    return True


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


def get_segment_summary_transcript_map_by_id(
    db: Session,
    mapping_id: int,
) -> Optional[SegmentSummaryTranscriptMap]:
    """按 ID 获取小结与转写映射。"""
    return db.get(SegmentSummaryTranscriptMap, mapping_id)


def list_segment_summary_transcript_maps(
    db: Session,
    segment_summary_id: Optional[int] = None,
    transcript_id: Optional[int] = None,
) -> list[SegmentSummaryTranscriptMap]:
    """查询小结与转写映射。"""
    statement = select(SegmentSummaryTranscriptMap)
    if segment_summary_id is not None:
        statement = statement.where(SegmentSummaryTranscriptMap.segment_summary_id == segment_summary_id)
    if transcript_id is not None:
        statement = statement.where(SegmentSummaryTranscriptMap.transcript_id == transcript_id)
    statement = statement.order_by(SegmentSummaryTranscriptMap.__table__.c.id.desc())
    return list(db.exec(statement))


def delete_segment_summary_transcript_map(db: Session, mapping_id: int) -> bool:
    """删除小结与转写映射。"""
    mapping = db.get(SegmentSummaryTranscriptMap, mapping_id)
    if mapping is None:
        return False

    db.delete(mapping)
    db.commit()
    return True
