"""课后报告 CRUD。"""

from typing import Optional

from sqlmodel import Session, select

from app.db.models import Report


def create_report(
    db: Session,
    session_id: int,
    content: Optional[str] = None,
    file_path: Optional[str] = None,
) -> Report:
    """创建课后报告。"""
    report = Report(session_id=session_id, content=content, file_path=file_path)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_report_by_id(db: Session, report_id: int) -> Optional[Report]:
    """按 ID 获取课后报告。"""
    return db.get(Report, report_id)


def list_reports(db: Session) -> list[Report]:
    """获取全部课后报告。"""
    statement = select(Report).order_by(Report.__table__.c.created_at.desc())
    return list(db.exec(statement))


def list_reports_by_session(db: Session, session_id: int) -> list[Report]:
    """按课堂获取课后报告。"""
    statement = (
        select(Report)
        .where(Report.session_id == session_id)
        .order_by(Report.__table__.c.created_at.desc())
    )
    return list(db.exec(statement))


def update_report(db: Session, report_id: int, **kwargs) -> Optional[Report]:
    """更新课后报告。"""
    report = db.get(Report, report_id)
    if report is None:
        return None

    for key, value in kwargs.items():
        setattr(report, key, value)

    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def delete_report(db: Session, report_id: int) -> bool:
    """删除课后报告。"""
    report = db.get(Report, report_id)
    if report is None:
        return False

    db.delete(report)
    db.commit()
    return True
