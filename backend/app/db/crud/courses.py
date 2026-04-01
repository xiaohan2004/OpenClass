"""课程 CRUD。"""

from typing import Optional

from sqlmodel import Session, select

from app.db.models import Course


def create_course(
    db: Session,
    code: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    teacher: Optional[str] = None,
) -> Course:
    """创建课程。"""
    course = Course(
        code=code,
        name=name,
        description=description,
        teacher=teacher,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def get_course_by_id(db: Session, course_id: int) -> Optional[Course]:
    """按 ID 获取课程。"""
    return db.get(Course, course_id)


def list_courses(db: Session) -> list[Course]:
    """获取全部课程。"""
    statement = select(Course).order_by(Course.created_at.desc())
    return list(db.exec(statement))
