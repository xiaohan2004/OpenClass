"""问题记录 CRUD。"""

from typing import Optional

from sqlmodel import Session, select

from app.db.models import Question, QuestionTranscriptMap
from app.utils.time import now_ts


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


def get_question_by_id(db: Session, question_id: int) -> Optional[Question]:
    """按 ID 获取问题记录。"""
    return db.get(Question, question_id)


def list_questions(db: Session) -> list[Question]:
    """获取全部问题记录。"""
    statement = select(Question).order_by(Question.__table__.c.created_at.desc())
    return list(db.exec(statement))


def list_questions_by_session(db: Session, session_id: int) -> list[Question]:
    """按课堂获取问题记录。"""
    statement = (
        select(Question)
        .where(Question.session_id == session_id)
        .order_by(Question.__table__.c.created_at.desc())
    )
    return list(db.exec(statement))


def mark_question_asked(db: Session, question_id: int, asked_at: Optional[int] = None) -> Optional[Question]:
    """标记问题已提问。"""
    question = db.get(Question, question_id)
    if question is None:
        return None

    question.status = "asked"
    question.asked_at = asked_at or now_ts()
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def update_question(db: Session, question_id: int, **kwargs) -> Optional[Question]:
    """更新问题记录。"""
    question = db.get(Question, question_id)
    if question is None:
        return None

    for key, value in kwargs.items():
        setattr(question, key, value)

    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def delete_question(db: Session, question_id: int) -> bool:
    """删除问题记录。"""
    question = db.get(Question, question_id)
    if question is None:
        return False

    db.delete(question)
    db.commit()
    return True


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


def get_question_transcript_map_by_id(db: Session, mapping_id: int) -> Optional[QuestionTranscriptMap]:
    """按 ID 获取问题与转写映射。"""
    return db.get(QuestionTranscriptMap, mapping_id)


def list_question_transcript_maps(
    db: Session,
    question_id: Optional[int] = None,
    transcript_id: Optional[int] = None,
) -> list[QuestionTranscriptMap]:
    """查询问题与转写映射。"""
    statement = select(QuestionTranscriptMap)
    if question_id is not None:
        statement = statement.where(QuestionTranscriptMap.question_id == question_id)
    if transcript_id is not None:
        statement = statement.where(QuestionTranscriptMap.transcript_id == transcript_id)
    statement = statement.order_by(QuestionTranscriptMap.__table__.c.id.desc())
    return list(db.exec(statement))


def delete_question_transcript_map(db: Session, mapping_id: int) -> bool:
    """删除问题与转写映射。"""
    mapping = db.get(QuestionTranscriptMap, mapping_id)
    if mapping is None:
        return False

    db.delete(mapping)
    db.commit()
    return True
