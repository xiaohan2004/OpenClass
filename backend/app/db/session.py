"""数据库连接与初始化。"""

from functools import lru_cache
import os
from pathlib import Path
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config_defaults import DEFAULT_DATABASE_ECHO, DEFAULT_DATABASE_URL
from app.db.config_store import ensure_default_settings


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _resolve_database_url(database_url: str) -> str:
    """将相对 SQLite 路径转换为项目根目录下的绝对路径。"""
    sqlite_prefix = "sqlite:///"
    if not database_url.startswith(sqlite_prefix):
        return database_url

    raw_path = database_url[len(sqlite_prefix) :]
    if not raw_path or raw_path == ":memory:":
        return database_url

    path = Path(raw_path)
    if path.is_absolute():
        return database_url

    absolute_path = (PROJECT_ROOT / path).resolve()
    return f"{sqlite_prefix}{absolute_path.as_posix()}"


@lru_cache()
def get_engine():
    """获取数据库引擎单例。"""
    database_url = _resolve_database_url(
        os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    )
    database_echo_env = os.environ.get("DATABASE_ECHO")
    if database_echo_env is None:
        database_echo = DEFAULT_DATABASE_ECHO
    else:
        database_echo = database_echo_env.strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
            "on",
        }
    connect_args = (
        {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    return create_engine(
        database_url,
        echo=database_echo,
        connect_args=connect_args,
    )


engine = get_engine()


def init_db() -> None:
    """初始化数据库并创建所有表。"""
    database_url = _resolve_database_url(
        os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    )
    if database_url.startswith("sqlite:///"):
        db_path = Path(database_url.replace("sqlite:///", "", 1))
        db_path.parent.mkdir(parents=True, exist_ok=True)

    engine_instance = get_engine()
    SQLModel.metadata.create_all(engine_instance)

    with Session(engine_instance) as db:
        ensure_default_settings(db)


def get_session() -> Generator[Session, None, None]:
    """提供数据库会话。"""
    with Session(get_engine()) as session:
        yield session
