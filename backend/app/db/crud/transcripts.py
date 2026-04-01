"""转写片段 CRUD。"""

from typing import Optional

from sqlmodel import Session, select

from app.db.models import Transcript


def create_transcript(
    db: Session,
    session_id: int,
    text: str,
    seq: Optional[int] = None,
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
) -> Transcript:
    """创建转写片段。"""
    transcript = Transcript(
        session_id=session_id,
        seq=seq,
        text=text,
        start_time=start_time,
        end_time=end_time,
    )
    db.add(transcript)
    db.commit()
    db.refresh(transcript)
    return transcript


def get_transcript_by_id(db: Session, transcript_id: int) -> Optional[Transcript]:
    """按 ID 获取转写片段。"""
    return db.get(Transcript, transcript_id)


def list_transcripts_by_session(db: Session, session_id: int) -> list[Transcript]:
    """按课堂获取转写片段。"""
    statement = (
        select(Transcript)
        .where(Transcript.session_id == session_id)
        .order_by(Transcript.seq, Transcript.created_at)
    )
    return list(db.exec(statement))


def update_transcript(db: Session, transcript_id: int, **kwargs) -> Optional[Transcript]:
    """更新转写片段。"""
    transcript = db.get(Transcript, transcript_id)
    if transcript is None:
        return None

    for key, value in kwargs.items():
        setattr(transcript, key, value)

    db.add(transcript)
    db.commit()
    db.refresh(transcript)
    return transcript


def delete_transcript(db: Session, transcript_id: int) -> bool:
    """删除转写片段。"""
    transcript = db.get(Transcript, transcript_id)
    if transcript is None:
        return False

    db.delete(transcript)
    db.commit()
    return True
