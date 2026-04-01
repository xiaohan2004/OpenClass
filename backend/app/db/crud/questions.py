"""问题记录 CRUD。"""

from datetime import datetime
from typing import Optional

from sqlmodel import Session, select

from app.db.models import Question, QuestionTranscriptMap


def create_question(
    db: Session,
    session_id: int,
    text: str,
    status: str = "generated",
    score: Optional[float] = None,
) -> Question:
    """创建问题记录。"""
    question = Question(
        session_id=session_id,
        text=text,
        status=status,
        score=score,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def list_questions_by_session(db: Session, session_id: int) -> list[Question]:
    """按课堂获取问题记录。"""
    statement = (
        select(Question)
        .where(Question.session_id == session_id)
        .order_by(Question.created_at.desc())
    )
    return list(db.exec(statement))


def mark_question_asked(db: Session, question_id: int, asked_at: Optional[datetime] = None) -> Optional[Question]:
    """标记问题已提问。"""
    question = db.get(Question, question_id)
    if question is None:
        return None

    question.status = "asked"
    question.asked_at = asked_at or datetime.utcnow()
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def link_question_to_transcript(db: Session, question_id: int, transcript_id: int) -> QuestionTranscriptMap:
    """建立问题与转写片段的映射。"""
    mapping = QuestionTranscriptMap(
        question_id=question_id,
        transcript_id=transcript_id,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping
