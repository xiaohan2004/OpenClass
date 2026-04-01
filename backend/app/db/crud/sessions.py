"""课堂会话 CRUD。"""

from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.db.models import SessionRecord


def create_session(
    db: Session,
    title: Optional[str] = None,
    start_time: Optional[datetime] = None,
    config: Optional[str] = None,
) -> SessionRecord:
    """创建课堂会话。"""
    session_record = SessionRecord(
        title=title,
        start_time=start_time or datetime.utcnow(),
        config=config,
    )
    db.add(session_record)
    db.commit()
    db.refresh(session_record)
    return session_record


def get_session_by_id(db: Session, session_id: int) -> Optional[SessionRecord]:
    """按 ID 获取课堂会话。"""
    return db.get(SessionRecord, session_id)


def list_sessions(db: Session) -> list[SessionRecord]:
    """获取全部课堂会话。"""
    statement = select(SessionRecord).order_by(SessionRecord.created_at.desc())
    return list(db.exec(statement))


def close_session(db: Session, session_id: int, end_time: Optional[datetime] = None) -> Optional[SessionRecord]:
    """结束课堂会话。"""
    session_record = db.get(SessionRecord, session_id)
    if session_record is None:
        return None

    session_record.end_time = end_time or datetime.utcnow()
    db.add(session_record)
    db.commit()
    db.refresh(session_record)
    return session_record
