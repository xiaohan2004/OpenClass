"""设置、日志与统计类 CRUD。"""

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


def list_settings(db: Session) -> list[Setting]:
    """获取全部系统设置。"""
    statement = select(Setting).order_by(Setting.key)
    return list(db.exec(statement))


def delete_setting(db: Session, key: str) -> bool:
    """删除系统设置。"""
    setting = db.get(Setting, key)
    if setting is None:
        return False

    db.delete(setting)
    db.commit()
    return True


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


def get_llm_info_by_name(db: Session, name: str) -> Optional[LLMInfo]:
    """按名称获取 LLM 价格信息。"""
    return db.get(LLMInfo, name)


def list_llm_infos(db: Session) -> list[LLMInfo]:
    """获取全部 LLM 价格信息。"""
    statement = select(LLMInfo).order_by(LLMInfo.name)
    return list(db.exec(statement))


def delete_llm_info(db: Session, name: str) -> bool:
    """删除 LLM 价格信息。"""
    llm_info = db.get(LLMInfo, name)
    if llm_info is None:
        return False

    db.delete(llm_info)
    db.commit()
    return True


def create_relay_log(db: Session, **kwargs) -> RelayLog:
    """创建请求日志。"""
    relay_log = RelayLog(**kwargs)
    db.add(relay_log)
    db.commit()
    db.refresh(relay_log)
    return relay_log


def get_relay_log_by_id(db: Session, relay_log_id: int) -> Optional[RelayLog]:
    """按 ID 获取请求日志。"""
    return db.get(RelayLog, relay_log_id)


def list_relay_logs(
    db: Session,
    *,
    service_type: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> list[RelayLog]:
    """获取请求日志列表，支持服务分类和分页。"""
    statement = select(RelayLog)

    if service_type:
        statement = statement.where(RelayLog.service_type == service_type)

    statement = statement.order_by(RelayLog.__table__.c.id.desc())

    if offset is not None and offset > 0:
        statement = statement.offset(offset)

    if limit is not None and limit > 0:
        statement = statement.limit(limit)

    return list(db.exec(statement))


def update_relay_log(db: Session, relay_log_id: int, **kwargs) -> Optional[RelayLog]:
    """更新请求日志。"""
    relay_log = db.get(RelayLog, relay_log_id)
    if relay_log is None:
        return None

    for key, value in kwargs.items():
        setattr(relay_log, key, value)

    db.add(relay_log)
    db.commit()
    db.refresh(relay_log)
    return relay_log


def delete_relay_log(db: Session, relay_log_id: int) -> bool:
    """删除请求日志。"""
    relay_log = db.get(RelayLog, relay_log_id)
    if relay_log is None:
        return False

    db.delete(relay_log)
    db.commit()
    return True


def create_stats_total(db: Session, **kwargs) -> StatsTotal:
    """创建全量累计统计。"""
    stats_total = StatsTotal(**kwargs)
    db.add(stats_total)
    db.commit()
    db.refresh(stats_total)
    return stats_total


def get_stats_total_by_id(db: Session, stats_total_id: int) -> Optional[StatsTotal]:
    """按 ID 获取全量累计统计。"""
    return db.get(StatsTotal, stats_total_id)


def get_stats_total_by_service_type(
    db: Session, service_type: str
) -> Optional[StatsTotal]:
    """按服务类型获取全量累计统计。"""
    statement = (
        select(StatsTotal)
        .where(StatsTotal.service_type == service_type)
        .order_by(StatsTotal.__table__.c.id.desc())
    )
    return db.exec(statement).first()


def list_stats_totals(db: Session) -> list[StatsTotal]:
    """获取全部全量累计统计。"""
    statement = select(StatsTotal).order_by(
        StatsTotal.__table__.c.service_type, StatsTotal.__table__.c.id.desc()
    )
    return list(db.exec(statement))


def update_stats_total(
    db: Session, stats_total_id: int, **kwargs
) -> Optional[StatsTotal]:
    """更新全量累计统计。"""
    stats_total = db.get(StatsTotal, stats_total_id)
    if stats_total is None:
        return None

    for key, value in kwargs.items():
        setattr(stats_total, key, value)

    db.add(stats_total)
    db.commit()
    db.refresh(stats_total)
    return stats_total


def upsert_stats_total(
    db: Session,
    service_type: str,
    **kwargs,
) -> StatsTotal:
    """按服务类型写入或更新全量累计统计。"""
    stats_total = get_stats_total_by_service_type(db, service_type)
    if stats_total is None:
        stats_total = StatsTotal(service_type=service_type)

    for key, value in kwargs.items():
        setattr(stats_total, key, value)

    db.add(stats_total)
    db.commit()
    db.refresh(stats_total)
    return stats_total


def delete_stats_total(db: Session, stats_total_id: int) -> bool:
    """删除全量累计统计。"""
    stats_total = db.get(StatsTotal, stats_total_id)
    if stats_total is None:
        return False

    db.delete(stats_total)
    db.commit()
    return True


def upsert_stats_daily(
    db: Session, date: str, service_type: str, **kwargs
) -> StatsDaily:
    """按日期和服务类型写入或更新按日统计。"""
    stats_daily = db.get(StatsDaily, (date, service_type))
    if stats_daily is None:
        stats_daily = StatsDaily(date=date, service_type=service_type)

    for key, value in kwargs.items():
        setattr(stats_daily, key, value)

    db.add(stats_daily)
    db.commit()
    db.refresh(stats_daily)
    return stats_daily


def get_stats_daily_by_date(
    db: Session, date: str, service_type: str
) -> Optional[StatsDaily]:
    """按日期和服务类型获取按日统计。"""
    return db.get(StatsDaily, (date, service_type))


def list_stats_dailies(db: Session) -> list[StatsDaily]:
    """获取全部按日统计。"""
    statement = select(StatsDaily).order_by(
        StatsDaily.__table__.c.date.desc(),
        StatsDaily.__table__.c.service_type,
    )
    return list(db.exec(statement))


def delete_stats_daily(db: Session, date: str, service_type: str) -> bool:
    """删除按日统计。"""
    stats_daily = db.get(StatsDaily, (date, service_type))
    if stats_daily is None:
        return False

    db.delete(stats_daily)
    db.commit()
    return True


def create_stats_hourly(
    db: Session, date: str, hour: int, service_type: str, **kwargs
) -> StatsHourly:
    """创建按小时统计。"""
    stats_hourly = StatsHourly(
        date=date, hour=hour, service_type=service_type, **kwargs
    )
    db.add(stats_hourly)
    db.commit()
    db.refresh(stats_hourly)
    return stats_hourly


def upsert_stats_hourly(
    db: Session,
    date: str,
    hour: int,
    service_type: str,
    **kwargs,
) -> StatsHourly:
    """按日期、小时和服务类型写入或更新按小时统计。"""
    stats_hourly = db.get(StatsHourly, (date, hour, service_type))
    if stats_hourly is None:
        stats_hourly = StatsHourly(date=date, hour=hour, service_type=service_type)

    for key, value in kwargs.items():
        setattr(stats_hourly, key, value)

    db.add(stats_hourly)
    db.commit()
    db.refresh(stats_hourly)
    return stats_hourly


def get_stats_hourly_by_hour(
    db: Session, date: str, hour: int, service_type: str
) -> Optional[StatsHourly]:
    """按日期、小时和服务类型获取按小时统计。"""
    return db.get(StatsHourly, (date, hour, service_type))


def list_stats_hourlies(db: Session) -> list[StatsHourly]:
    """获取全部按小时统计。"""
    statement = select(StatsHourly).order_by(
        StatsHourly.__table__.c.date.desc(),
        StatsHourly.__table__.c.hour.desc(),
        StatsHourly.__table__.c.service_type,
    )
    return list(db.exec(statement))


def update_stats_hourly(
    db: Session,
    date: str,
    hour: int,
    service_type: str,
    **kwargs,
) -> Optional[StatsHourly]:
    """更新按小时统计。"""
    stats_hourly = db.get(StatsHourly, (date, hour, service_type))
    if stats_hourly is None:
        return None

    for key, value in kwargs.items():
        setattr(stats_hourly, key, value)

    db.add(stats_hourly)
    db.commit()
    db.refresh(stats_hourly)
    return stats_hourly


def delete_stats_hourly(db: Session, date: str, hour: int, service_type: str) -> bool:
    """删除按小时统计。"""
    stats_hourly = db.get(StatsHourly, (date, hour, service_type))
    if stats_hourly is None:
        return False

    db.delete(stats_hourly)
    db.commit()
    return True


def create_migration_record(
    db: Session, status: Optional[int] = None
) -> MigrationRecord:
    """创建数据库迁移记录。"""
    record = MigrationRecord(status=status)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def get_migration_record_by_version(
    db: Session, version: int
) -> Optional[MigrationRecord]:
    """按版本获取迁移记录。"""
    return db.get(MigrationRecord, version)


def list_migration_records(db: Session) -> list[MigrationRecord]:
    """获取全部迁移记录。"""
    statement = select(MigrationRecord).order_by(
        MigrationRecord.__table__.c.version.desc()
    )
    return list(db.exec(statement))


def update_migration_record(
    db: Session, version: int, **kwargs
) -> Optional[MigrationRecord]:
    """更新迁移记录。"""
    record = db.get(MigrationRecord, version)
    if record is None:
        return None

    for key, value in kwargs.items():
        setattr(record, key, value)

    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def delete_migration_record(db: Session, version: int) -> bool:
    """删除迁移记录。"""
    record = db.get(MigrationRecord, version)
    if record is None:
        return False

    db.delete(record)
    db.commit()
    return True
