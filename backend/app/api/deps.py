"""API 依赖注入。"""

from typing import Generator

from sqlmodel import Session

from app.db import get_session


def get_db_session() -> Generator[Session, None, None]:
    """为 API 路由提供数据库会话。"""
    yield from get_session()
