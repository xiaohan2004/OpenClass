"""数据库模块测试。"""

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sqlalchemy import inspect
from sqlmodel import Session

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

import app.config as app_config
import app.db.session as db_session_module
from app.db import (
    LLMInfo,
    MigrationRecord,
    Question,
    QuestionTranscriptMap,
    RelayLog,
    SegmentSummary,
    SegmentSummaryTranscriptMap,
    SessionRecord,
    Setting,
    StatsDaily,
    StatsHourly,
    StatsTotal,
    Transcript,
    init_db,
)
from app.db.crud import (
    create_llm_info,
    create_migration_record,
    create_question,
    create_relay_log,
    create_segment_summary,
    create_session,
    create_stats_hourly,
    create_stats_total,
    create_transcript,
    get_setting,
    link_question_to_transcript,
    link_segment_summary_to_transcript,
    list_questions_by_session,
    list_relay_logs,
    list_segment_summaries_by_session,
    list_sessions,
    list_transcripts_by_session,
    mark_question_asked,
    upsert_setting,
    upsert_stats_daily,
)
from app.main import app as fastapi_app


class TestDatabase(unittest.TestCase):
    """数据库功能测试。"""

    @staticmethod
    async def _run_app_lifespan():
        """执行一次应用生命周期。"""
        async with fastapi_app.router.lifespan_context(fastapi_app):
            return None

    def setUp(self):
        """为每个测试创建独立数据库。"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_openclass.db"
        self.db_url = f"sqlite:///{self.db_path.as_posix()}"

        self.env_patcher = mock.patch.dict(
            os.environ,
            {"DATABASE_URL": self.db_url, "DATABASE_ECHO": "false"},
            clear=False,
        )
        self.env_patcher.start()

        app_config.get_settings.cache_clear()
        db_session_module.get_engine.cache_clear()
        db_session_module.engine = db_session_module.get_engine()

    def tearDown(self):
        """清理缓存与临时文件。"""
        db_session_module.get_engine().dispose()
        self.env_patcher.stop()
        app_config.get_settings.cache_clear()
        db_session_module.get_engine.cache_clear()
        self.temp_dir.cleanup()

    def test_init_db_creates_tables_and_crud_records(self):
        """初始化数据库后应支持最新表结构的基础读写。"""
        init_db()

        with Session(db_session_module.get_engine()) as db:
            session = create_session(db, title="测试课堂")
            transcript = create_transcript(db, session.id, "这是转写内容", seq=1, start_time=0.0, end_time=3.2)
            question = create_question(db, session.id, "这里为什么要这样做？", score=0.9)
            question_map = link_question_to_transcript(db, question.id, transcript.id)

            summary = create_segment_summary(db, session.id, "这是分段小结", start_time=0.0, end_time=3.2, score=0.8)
            summary_map = link_segment_summary_to_transcript(db, summary.id, transcript.id)

            llm_info = create_llm_info(db, "deepseek-chat", input_price=0.1, output_price=0.2)
            relay_log = create_relay_log(db, request_model_name="deepseek-chat", input_tokens=10, output_tokens=20)
            stats_total = create_stats_total(db, input_token=100, output_token=50)
            stats_daily = upsert_stats_daily(db, "2026-04-01", input_token=60, output_token=30)
            stats_hourly = create_stats_hourly(db, "2026-04-01", input_token=10, output_token=5)
            setting = upsert_setting(db, "app.mode", "dev")
            migration_record = create_migration_record(db, status=1)

            self.assertIsNotNone(session.id)
            self.assertIsNotNone(transcript.id)
            self.assertIsNotNone(question.id)
            self.assertIsNotNone(question_map.id)
            self.assertIsNotNone(summary.id)
            self.assertIsNotNone(summary_map.id)
            self.assertEqual(llm_info.name, "deepseek-chat")
            self.assertIsNotNone(relay_log.id)
            self.assertIsNotNone(stats_total.id)
            self.assertEqual(stats_daily.date, "2026-04-01")
            self.assertIsNotNone(stats_hourly.hour)
            self.assertEqual(setting.key, "app.mode")
            self.assertIsNotNone(migration_record.version)

            self.assertEqual(len(list_sessions(db)), 1)
            self.assertEqual(len(list_transcripts_by_session(db, session.id)), 1)
            self.assertEqual(len(list_questions_by_session(db, session.id)), 1)
            self.assertEqual(len(list_segment_summaries_by_session(db, session.id)), 1)
            self.assertEqual(len(list_relay_logs(db)), 1)
            self.assertEqual(get_setting(db, "app.mode").value, "dev")

    def test_mark_question_asked_updates_status(self):
        """问题应能被标记为已提问。"""
        init_db()

        with Session(db_session_module.get_engine()) as db:
            session = create_session(db, title="状态测试")
            question = create_question(db, session.id, "状态会变化吗？")

            updated_question = mark_question_asked(db, question.id)

            self.assertIsNotNone(updated_question)
            self.assertEqual(updated_question.status, "asked")
            self.assertIsNotNone(updated_question.asked_at)

    def test_app_startup_initializes_all_tables(self):
        """应用启动时应自动初始化最新数据库表。"""
        asyncio.run(self._run_app_lifespan())
        self.assertTrue(self.db_path.exists())

        inspector = inspect(db_session_module.get_engine())
        tables = set(inspector.get_table_names())

        expected_tables = {
            SessionRecord.__tablename__,
            Transcript.__tablename__,
            Question.__tablename__,
            QuestionTranscriptMap.__tablename__,
            SegmentSummary.__tablename__,
            SegmentSummaryTranscriptMap.__tablename__,
            LLMInfo.__tablename__,
            RelayLog.__tablename__,
            StatsTotal.__tablename__,
            StatsDaily.__tablename__,
            StatsHourly.__tablename__,
            Setting.__tablename__,
            MigrationRecord.__tablename__,
        }

        self.assertTrue(expected_tables.issubset(tables))


def main():
    """运行数据库测试。"""
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDatabase)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
