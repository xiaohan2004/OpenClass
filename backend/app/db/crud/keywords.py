"""关键词记录 CRUD。"""

from typing import Optional

from sqlmodel import Session, select

from app.db.models import Keyword, KeywordTranscriptMap


def create_keyword(db: Session, session_id: int, keyword_sets: str) -> Keyword:
    """创建关键词集合记录。"""
    keyword = Keyword(session_id=session_id, keyword_sets=keyword_sets)
    db.add(keyword)
    db.commit()
    db.refresh(keyword)
    return keyword


def get_keyword_by_id(db: Session, keyword_id: int) -> Optional[Keyword]:
    """按 ID 获取关键词集合记录。"""
    return db.get(Keyword, keyword_id)


def list_keywords(db: Session) -> list[Keyword]:
    """获取全部关键词集合记录。"""
    statement = select(Keyword).order_by(Keyword.__table__.c.created_at.desc())
    return list(db.exec(statement))


def list_keywords_by_session(db: Session, session_id: int) -> list[Keyword]:
    """按课堂获取关键词集合记录。"""
    statement = (
        select(Keyword)
        .where(Keyword.session_id == session_id)
        .order_by(Keyword.__table__.c.created_at.desc())
    )
    return list(db.exec(statement))


def update_keyword(db: Session, keyword_id: int, **kwargs) -> Optional[Keyword]:
    """更新关键词集合记录。"""
    keyword = db.get(Keyword, keyword_id)
    if keyword is None:
        return None

    for key, value in kwargs.items():
        setattr(keyword, key, value)

    db.add(keyword)
    db.commit()
    db.refresh(keyword)
    return keyword


def delete_keyword(db: Session, keyword_id: int) -> bool:
    """删除关键词集合记录。"""
    keyword = db.get(Keyword, keyword_id)
    if keyword is None:
        return False

    db.delete(keyword)
    db.commit()
    return True


def link_keyword_to_transcript(
    db: Session, keyword_id: int, transcript_id: int
) -> KeywordTranscriptMap:
    """建立关键词与转写片段的映射。"""
    mapping = KeywordTranscriptMap(keyword_id=keyword_id, transcript_id=transcript_id)
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


def get_keyword_transcript_map_by_id(
    db: Session, mapping_id: int
) -> Optional[KeywordTranscriptMap]:
    """按 ID 获取关键词与转写映射。"""
    return db.get(KeywordTranscriptMap, mapping_id)


def list_keyword_transcript_maps(
    db: Session,
    keyword_id: Optional[int] = None,
    transcript_id: Optional[int] = None,
) -> list[KeywordTranscriptMap]:
    """查询关键词与转写映射。"""
    statement = select(KeywordTranscriptMap)
    if keyword_id is not None:
        statement = statement.where(KeywordTranscriptMap.keyword_id == keyword_id)
    if transcript_id is not None:
        statement = statement.where(KeywordTranscriptMap.transcript_id == transcript_id)
    statement = statement.order_by(KeywordTranscriptMap.__table__.c.id.desc())
    return list(db.exec(statement))


def delete_keyword_transcript_map(db: Session, mapping_id: int) -> bool:
    """删除关键词与转写映射。"""
    mapping = db.get(KeywordTranscriptMap, mapping_id)
    if mapping is None:
        return False

    db.delete(mapping)
    db.commit()
    return True
