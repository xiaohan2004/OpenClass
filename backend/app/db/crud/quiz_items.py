"""小测题目 CRUD。"""

from typing import Optional

from sqlmodel import Session, select

from app.db.models import QuizItem, QuizItemTranscriptMap


def create_quiz_item(
    db: Session,
    session_id: int,
    question: str,
    item_type: Optional[str] = None,
    answer: Optional[str] = None,
    explanation: Optional[str] = None,
) -> QuizItem:
    """创建小测题目。"""
    quiz_item = QuizItem(
        session_id=session_id,
        type=item_type,
        question=question,
        answer=answer,
        explanation=explanation,
    )
    db.add(quiz_item)
    db.commit()
    db.refresh(quiz_item)
    return quiz_item


def get_quiz_item_by_id(db: Session, quiz_item_id: int) -> Optional[QuizItem]:
    """按 ID 获取小测题目。"""
    return db.get(QuizItem, quiz_item_id)


def list_quiz_items(db: Session) -> list[QuizItem]:
    """获取全部小测题目。"""
    statement = select(QuizItem).order_by(QuizItem.__table__.c.created_at.desc())
    return list(db.exec(statement))


def list_quiz_items_by_session(db: Session, session_id: int) -> list[QuizItem]:
    """按课堂获取小测题目。"""
    statement = (
        select(QuizItem)
        .where(QuizItem.session_id == session_id)
        .order_by(QuizItem.__table__.c.created_at.desc())
    )
    return list(db.exec(statement))


def update_quiz_item(db: Session, quiz_item_id: int, **kwargs) -> Optional[QuizItem]:
    """更新小测题目。"""
    quiz_item = db.get(QuizItem, quiz_item_id)
    if quiz_item is None:
        return None

    for key, value in kwargs.items():
        if key == "item_type":
            setattr(quiz_item, "type", value)
        else:
            setattr(quiz_item, key, value)

    db.add(quiz_item)
    db.commit()
    db.refresh(quiz_item)
    return quiz_item


def delete_quiz_item(db: Session, quiz_item_id: int) -> bool:
    """删除小测题目。"""
    quiz_item = db.get(QuizItem, quiz_item_id)
    if quiz_item is None:
        return False

    db.delete(quiz_item)
    db.commit()
    return True


def link_quiz_item_to_transcript(
    db: Session, quiz_item_id: int, transcript_id: int
) -> QuizItemTranscriptMap:
    """建立小测题目与转写片段的映射。"""
    mapping = QuizItemTranscriptMap(
        quiz_item_id=quiz_item_id,
        transcript_id=transcript_id,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


def get_quiz_item_transcript_map_by_id(
    db: Session,
    mapping_id: int,
) -> Optional[QuizItemTranscriptMap]:
    """按 ID 获取小测题目与转写映射。"""
    return db.get(QuizItemTranscriptMap, mapping_id)


def list_quiz_item_transcript_maps(
    db: Session,
    quiz_item_id: Optional[int] = None,
    transcript_id: Optional[int] = None,
) -> list[QuizItemTranscriptMap]:
    """查询小测题目与转写映射。"""
    statement = select(QuizItemTranscriptMap)
    if quiz_item_id is not None:
        statement = statement.where(QuizItemTranscriptMap.quiz_item_id == quiz_item_id)
    if transcript_id is not None:
        statement = statement.where(
            QuizItemTranscriptMap.transcript_id == transcript_id
        )
    statement = statement.order_by(QuizItemTranscriptMap.__table__.c.id.desc())
    return list(db.exec(statement))


def delete_quiz_item_transcript_map(db: Session, mapping_id: int) -> bool:
    """删除小测题目与转写映射。"""
    mapping = db.get(QuizItemTranscriptMap, mapping_id)
    if mapping is None:
        return False

    db.delete(mapping)
    db.commit()
    return True
