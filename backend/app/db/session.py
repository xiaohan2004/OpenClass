"""数据库连接与初始化。"""

from functools import lru_cache
import logging
import os
from pathlib import Path
from typing import Generator

from sqlalchemy import inspect
from sqlmodel import Session, SQLModel, create_engine

from app.config_defaults import DEFAULT_DATABASE_ECHO, DEFAULT_DATABASE_URL
from app.db.config_store import ensure_default_settings


logger = logging.getLogger(__name__)
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

    log_schema_status(engine_instance)


def log_schema_status(engine_instance=None) -> bool:
    """输出当前数据库表结构与模型定义的对比结果。"""
    engine_instance = engine_instance or get_engine()
    inspector = inspect(engine_instance)
    model_tables = SQLModel.metadata.tables
    db_tables = set(inspector.get_table_names())
    model_table_names = sorted(model_tables.keys())

    logger.info("开始检查数据库表结构")
    logger.info("模型表数量: %d, 数据库表数量: %d", len(model_table_names), len(db_tables))

    all_matched = True
    for table_name in model_table_names:
        table = model_tables[table_name]
        expected_columns = [column.name for column in table.columns]

        if table_name not in db_tables:
            logger.warning(
                "表缺失: %s | 期望列: %s",
                table_name,
                expected_columns,
            )
            all_matched = False
            continue

        db_columns = inspector.get_columns(table_name)
        actual_columns = [column["name"] for column in db_columns]
        missing_columns = [
            column_name for column_name in expected_columns if column_name not in actual_columns
        ]
        extra_columns = [
            column_name for column_name in actual_columns if column_name not in expected_columns
        ]

        column_diffs: list[str] = []
        actual_column_map = {column["name"]: column for column in db_columns}
        for column in table.columns:
            actual_column = actual_column_map.get(column.name)
            if actual_column is None:
                continue

            issues: list[str] = []
            if bool(actual_column.get("primary_key", False)) != bool(column.primary_key):
                issues.append(
                    f"primary_key 期望={bool(column.primary_key)} 实际={bool(actual_column.get('primary_key', False))}"
                )
            if bool(actual_column.get("nullable", True)) != bool(column.nullable):
                issues.append(
                    f"nullable 期望={bool(column.nullable)} 实际={bool(actual_column.get('nullable', True))}"
                )
            if issues:
                column_diffs.append(f"{column.name}: " + "; ".join(issues))

        if missing_columns or extra_columns or column_diffs:
            all_matched = False
            logger.warning(
                "表不匹配: %s | 期望列: %s | 实际列: %s | 缺失列: %s | 多余列: %s | 详细差异: %s",
                table_name,
                expected_columns,
                actual_columns,
                missing_columns,
                extra_columns,
                column_diffs,
            )
        else:
            logger.info("表一致: %s | 列: %s", table_name, actual_columns)

    extra_tables = sorted(db_tables - set(model_tables.keys()))
    for table_name in extra_tables:
        logger.warning("数据库存在多余表: %s", table_name)
        all_matched = False

    logger.info(
        "数据库结构检查完成：%s",
        "一致" if all_matched else "存在差异",
    )
    return all_matched


def get_session() -> Generator[Session, None, None]:
    """提供数据库会话。"""
    with Session(get_engine()) as session:
        yield session
