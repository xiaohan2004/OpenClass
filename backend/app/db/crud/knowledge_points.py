"""知识点 CRUD。"""

from typing import Optional

from sqlmodel import Session, select

from app.db.models import KnowledgePoint, KnowledgePointTranscriptMap


def create_knowledge_point(
    db: Session,
    session_id: int,
    name: str,
    description: Optional[str] = None,
    difficulty: Optional[str] = None,
) -> KnowledgePoint:
    """创建知识点。"""
    knowledge_point = KnowledgePoint(
        session_id=session_id,
        name=name,
        description=description,
        difficulty=difficulty,
    )
    db.add(knowledge_point)
    db.commit()
    db.refresh(knowledge_point)
    return knowledge_point


def get_knowledge_point_by_id(
    db: Session,
    knowledge_point_id: int,
) -> Optional[KnowledgePoint]:
    """按 ID 获取知识点。"""
    return db.get(KnowledgePoint, knowledge_point_id)


def list_knowledge_points(db: Session) -> list[KnowledgePoint]:
    """获取全部知识点。"""
    statement = select(KnowledgePoint).order_by(
        KnowledgePoint.__table__.c.created_at.desc()
    )
    return list(db.exec(statement))


def list_knowledge_points_by_session(
    db: Session, session_id: int
) -> list[KnowledgePoint]:
    """按课堂获取知识点。"""
    statement = (
        select(KnowledgePoint)
        .where(KnowledgePoint.session_id == session_id)
        .order_by(KnowledgePoint.__table__.c.created_at.desc())
    )
    return list(db.exec(statement))


def update_knowledge_point(
    db: Session,
    knowledge_point_id: int,
    **kwargs,
) -> Optional[KnowledgePoint]:
    """更新知识点。"""
    knowledge_point = db.get(KnowledgePoint, knowledge_point_id)
    if knowledge_point is None:
        return None

    for key, value in kwargs.items():
        setattr(knowledge_point, key, value)

    db.add(knowledge_point)
    db.commit()
    db.refresh(knowledge_point)
    return knowledge_point


def delete_knowledge_point(db: Session, knowledge_point_id: int) -> bool:
    """删除知识点。"""
    knowledge_point = db.get(KnowledgePoint, knowledge_point_id)
    if knowledge_point is None:
        return False

    db.delete(knowledge_point)
    db.commit()
    return True


def link_knowledge_point_to_transcript(
    db: Session, knowledge_point_id: int, transcript_id: int
) -> KnowledgePointTranscriptMap:
    """建立知识点与转写片段的映射。"""
    mapping = KnowledgePointTranscriptMap(
        knowledge_point_id=knowledge_point_id,
        transcript_id=transcript_id,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


def get_knowledge_point_transcript_map_by_id(
    db: Session,
    mapping_id: int,
) -> Optional[KnowledgePointTranscriptMap]:
    """按 ID 获取知识点与转写映射。"""
    return db.get(KnowledgePointTranscriptMap, mapping_id)


def list_knowledge_point_transcript_maps(
    db: Session,
    knowledge_point_id: Optional[int] = None,
    transcript_id: Optional[int] = None,
) -> list[KnowledgePointTranscriptMap]:
    """查询知识点与转写映射。"""
    statement = select(KnowledgePointTranscriptMap)
    if knowledge_point_id is not None:
        statement = statement.where(
            KnowledgePointTranscriptMap.knowledge_point_id == knowledge_point_id
        )
    if transcript_id is not None:
        statement = statement.where(
            KnowledgePointTranscriptMap.transcript_id == transcript_id
        )
    statement = statement.order_by(KnowledgePointTranscriptMap.__table__.c.id.desc())
    return list(db.exec(statement))


def delete_knowledge_point_transcript_map(db: Session, mapping_id: int) -> bool:
    """删除知识点与转写映射。"""
    mapping = db.get(KnowledgePointTranscriptMap, mapping_id)
    if mapping is None:
        return False

    db.delete(mapping)
    db.commit()
    return True
