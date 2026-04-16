"""课堂会话 CRUD。"""

from typing import Optional

from sqlalchemy import func
from sqlmodel import Session, select

from app.db.models import SessionRecord
from app.utils.time import now_ts


def create_session(
    db: Session,
    course_id: int,
    title: Optional[str] = None,
    start_time: Optional[int] = None,
) -> SessionRecord:
    """创建课堂会话。"""
    max_seq_statement = select(func.max(SessionRecord.seq)).where(
        SessionRecord.course_id == course_id
    )
    max_seq = db.exec(max_seq_statement).one()
    next_seq = (max_seq or 0) + 1

    session_record = SessionRecord(
        course_id=course_id,
        seq=next_seq,
        title=title,
        start_time=start_time,
    )
    db.add(session_record)
    db.commit()
    db.refresh(session_record)
    return session_record


def get_session_by_id(db: Session, session_id: int) -> Optional[SessionRecord]:
    """按 ID 获取课堂会话。"""
    return db.get(SessionRecord, session_id)


def list_sessions(db: Session, course_id: Optional[int] = None) -> list[SessionRecord]:
    """获取课堂会话列表（支持按课程筛选）。"""
    statement = select(SessionRecord)

    if course_id is not None:
        statement = statement.where(SessionRecord.course_id == course_id)

    statement = statement.order_by(SessionRecord.__table__.c.created_at.desc())

    return list(db.exec(statement))


def close_session(
    db: Session, session_id: int, end_time: Optional[int] = None
) -> Optional[SessionRecord]:
    """结束课堂会话。"""
    session_record = db.get(SessionRecord, session_id)
    if session_record is None:
        return None

    session_record.end_time = end_time or now_ts()
    db.add(session_record)
    db.commit()
    db.refresh(session_record)
    return session_record


def update_session(db: Session, session_id: int, **kwargs) -> Optional[SessionRecord]:
    """更新课堂会话。"""
    session_record = db.get(SessionRecord, session_id)
    if session_record is None:
        return None

    for key, value in kwargs.items():
        setattr(session_record, key, value)

    db.add(session_record)
    db.commit()
    db.refresh(session_record)
    return session_record


def delete_session(db: Session, session_id: int) -> bool:
    """删除课堂会话。"""
    session_record = db.get(SessionRecord, session_id)
    if session_record is None:
        return False

    db.delete(session_record)
    db.commit()
    return True
