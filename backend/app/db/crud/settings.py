"""设置与统计类 CRUD。"""

from typing import Optional

from sqlmodel import Session, select

from app.db.models import (
    LLMInfo,
    MigrationRecord,
    RelayLog,
    Setting,
    StatsDaily,
    StatsHourly,
    StatsTotal,
)


def upsert_setting(db: Session, key: str, value: str) -> Setting:
    """写入或更新系统设置。"""
    setting = db.get(Setting, key)
    if setting is None:
        setting = Setting(key=key, value=value)
    else:
        setting.value = value

    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


def get_setting(db: Session, key: str) -> Optional[Setting]:
    """按键获取系统设置。"""
    return db.get(Setting, key)


def create_llm_info(
    db: Session,
    name: str,
    input_price: Optional[float] = None,
    output_price: Optional[float] = None,
    cache_read: Optional[float] = None,
    cache_write: Optional[float] = None,
) -> LLMInfo:
    """写入或更新 LLM 价格信息。"""
    llm_info = db.get(LLMInfo, name)
    if llm_info is None:
        llm_info = LLMInfo(name=name)

    llm_info.input = input_price
    llm_info.output = output_price
    llm_info.cache_read = cache_read
    llm_info.cache_write = cache_write
    db.add(llm_info)
    db.commit()
    db.refresh(llm_info)
    return llm_info


def create_relay_log(db: Session, **kwargs) -> RelayLog:
    """创建请求日志。"""
    relay_log = RelayLog(**kwargs)
    db.add(relay_log)
    db.commit()
    db.refresh(relay_log)
    return relay_log


def list_relay_logs(db: Session) -> list[RelayLog]:
    """获取请求日志列表。"""
    statement = select(RelayLog).order_by(RelayLog.id.desc())
    return list(db.exec(statement))


def create_stats_total(db: Session, **kwargs) -> StatsTotal:
    """创建全量累计统计。"""
    stats_total = StatsTotal(**kwargs)
    db.add(stats_total)
    db.commit()
    db.refresh(stats_total)
    return stats_total


def upsert_stats_daily(db: Session, date: str, **kwargs) -> StatsDaily:
    """写入或更新按日统计。"""
    stats_daily = db.get(StatsDaily, date)
    if stats_daily is None:
        stats_daily = StatsDaily(date=date)

    for key, value in kwargs.items():
        setattr(stats_daily, key, value)

    db.add(stats_daily)
    db.commit()
    db.refresh(stats_daily)
    return stats_daily


def create_stats_hourly(db: Session, date: str, **kwargs) -> StatsHourly:
    """创建按小时统计。"""
    stats_hourly = StatsHourly(date=date, **kwargs)
    db.add(stats_hourly)
    db.commit()
    db.refresh(stats_hourly)
    return stats_hourly


def create_migration_record(db: Session, status: Optional[int] = None) -> MigrationRecord:
    """创建数据库迁移记录。"""
    record = MigrationRecord(status=status)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
