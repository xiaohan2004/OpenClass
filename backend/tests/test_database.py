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
    create_course,
    create_llm_info,
    create_migration_record,
    create_question,
    create_relay_log,
    create_segment_summary,
    create_session,
    create_stats_hourly,
    create_stats_total,
    create_transcript,
    delete_course,
    delete_llm_info,
    delete_migration_record,
    delete_question,
    delete_question_transcript_map,
    delete_relay_log,
    delete_segment_summary,
    delete_segment_summary_transcript_map,
    delete_session,
    delete_setting,
    delete_stats_daily,
    delete_stats_hourly,
    delete_stats_total,
    delete_transcript,
    get_course_by_id,
    get_llm_info_by_name,
    get_migration_record_by_version,
    get_question_by_id,
    get_question_transcript_map_by_id,
    get_relay_log_by_id,
    get_segment_summary_by_id,
    get_segment_summary_transcript_map_by_id,
    get_session_by_id,
    get_setting,
    get_stats_daily_by_date,
    get_stats_hourly_by_hour,
    get_stats_total_by_id,
    get_stats_total_by_service_type,
    get_transcript_by_id,
    link_question_to_transcript,
    link_segment_summary_to_transcript,
    list_courses,
    list_llm_infos,
    list_migration_records,
    list_question_transcript_maps,
    list_questions,
    list_questions_by_session,
    list_relay_logs,
    list_segment_summaries,
    list_segment_summaries_by_session,
    list_segment_summary_transcript_maps,
    list_sessions,
    list_settings,
    list_stats_dailies,
    list_stats_hourlies,
    list_stats_totals,
    list_transcripts_by_session,
    mark_question_asked,
    update_course,
    update_migration_record,
    update_question,
    update_relay_log,
    update_segment_summary,
    update_session,
    update_stats_hourly,
    update_stats_total,
    update_transcript,
    upsert_setting,
    upsert_stats_daily,
    upsert_stats_hourly,
    upsert_stats_total,
)
from app.main import app as fastapi_app


class TestDatabase(unittest.TestCase):
    """数据库功能测试。"""

    @staticmethod
    async def _run_app_lifespan():
        async with fastapi_app.router.lifespan_context(fastapi_app):
            return None

    def setUp(self):
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
        db_session_module.get_engine().dispose()
        self.env_patcher.stop()
        app_config.get_settings.cache_clear()
        db_session_module.get_engine.cache_clear()
        self.temp_dir.cleanup()

    def test_init_db_creates_tables_and_crud_records(self):
        init_db()

        with Session(db_session_module.get_engine()) as db:
            course = create_course(
                db,
                code="MATH101",
                name="高等数学",
                description="极限、导数与积分",
                teacher="张老师",
            )
            session = create_session(db, course_id=course.id, title="测试课堂")
            transcript = create_transcript(
                db, session.id, "这是转写内容", seq=1, start_time=0, end_time=3
            )
            question = create_question(
                db, session.id, "这里为什么要这样做？", score=0.9
            )
            question_map = link_question_to_transcript(db, question.id, transcript.id)
            summary = create_segment_summary(
                db, session.id, "这是分段小结", start_time=0, end_time=3, score=0.8
            )
            summary_map = link_segment_summary_to_transcript(
                db, summary.id, transcript.id
            )

            llm_info = create_llm_info(
                db, "deepseek-chat", input_price=0.1, output_price=0.2
            )
            relay_log = create_relay_log(
                db,
                time=1712995200,
                service_type="llm",
                request_model_name="deepseek-chat",
                input_value=10,
                output_value=20,
                latency=300,
                status="success",
            )
            stats_total = create_stats_total(
                db,
                service_type="llm",
                input_value=100,
                output_value=50,
                wait_time=3000,
            )
            stats_daily = upsert_stats_daily(
                db,
                "2026-04-01",
                "llm",
                input_value=60,
                output_value=30,
            )
            stats_hourly = create_stats_hourly(
                db,
                "2026-04-01",
                8,
                "llm",
                input_value=10,
                output_value=5,
            )
            setting = upsert_setting(db, "app.mode", "dev")
            migration_record = create_migration_record(db, status=1)

            self.assertIsNotNone(course.id)
            self.assertIsNotNone(session.id)
            self.assertEqual(session.seq, 1)
            self.assertIsNotNone(transcript.id)
            self.assertIsNotNone(question.id)
            self.assertIsNotNone(question_map.id)
            self.assertIsNotNone(summary.id)
            self.assertIsNotNone(summary_map.id)
            self.assertEqual(llm_info.name, "deepseek-chat")
            self.assertIsNotNone(relay_log.id)
            self.assertIsNotNone(stats_total.id)
            self.assertEqual(stats_daily.date, "2026-04-01")
            self.assertEqual(stats_daily.service_type, "llm")
            self.assertEqual(stats_hourly.hour, 8)
            self.assertEqual(setting.key, "app.mode")
            self.assertIsNotNone(migration_record.version)

            self.assertEqual(get_course_by_id(db, course.id).code, "MATH101")
            self.assertEqual(len(list_courses(db)), 1)
            self.assertEqual(len(list_sessions(db)), 1)
            self.assertEqual(len(list_transcripts_by_session(db, session.id)), 1)
            self.assertEqual(len(list_questions_by_session(db, session.id)), 1)
            self.assertEqual(len(list_segment_summaries_by_session(db, session.id)), 1)
            self.assertEqual(len(list_relay_logs(db)), 1)
            self.assertEqual(get_setting(db, "app.mode").value, "dev")

    def test_mark_question_asked_updates_status(self):
        init_db()

        with Session(db_session_module.get_engine()) as db:
            course = create_course(db, code="TEST101", name="状态测试课程")
            session = create_session(db, course_id=course.id, title="状态测试")
            question = create_question(db, session.id, "状态会变化吗？")

            updated_question = mark_question_asked(db, question.id)

            self.assertIsNotNone(updated_question)
            self.assertEqual(updated_question.status, "asked")
            self.assertIsNotNone(updated_question.asked_at)

    def test_full_crud_coverage_for_all_tables(self):
        init_db()

        with Session(db_session_module.get_engine()) as db:
            course = create_course(db, code="PHYS101", name="大学物理")
            self.assertEqual(get_course_by_id(db, course.id).name, "大学物理")
            updated_course = update_course(db, course.id, teacher="李老师")
            self.assertEqual(updated_course.teacher, "李老师")
            self.assertEqual(len(list_courses(db)), 1)

            session = create_session(db, course_id=course.id, title="第二节")
            self.assertEqual(get_session_by_id(db, session.id).seq, 1)
            second_session = create_session(db, course_id=course.id, title="第三节")
            self.assertEqual(get_session_by_id(db, second_session.id).seq, 2)
            updated_session = update_session(db, session.id, title="第二节课")
            self.assertEqual(updated_session.title, "第二节课")
            self.assertEqual(len(list_sessions(db)), 2)

            transcript = create_transcript(db, session.id, "初始转写", seq=1)
            self.assertEqual(get_transcript_by_id(db, transcript.id).text, "初始转写")
            updated_transcript = update_transcript(db, transcript.id, text="更新转写")
            self.assertEqual(updated_transcript.text, "更新转写")
            self.assertEqual(len(list_transcripts_by_session(db, session.id)), 1)

            question = create_question(db, session.id, "最初问题")
            self.assertEqual(get_question_by_id(db, question.id).text, "最初问题")
            updated_question = update_question(
                db, question.id, text="更新问题", score=0.7
            )
            self.assertEqual(updated_question.text, "更新问题")
            self.assertEqual(updated_question.score, 0.7)
            self.assertEqual(len(list_questions(db)), 1)
            self.assertEqual(len(list_questions_by_session(db, session.id)), 1)

            question_map = link_question_to_transcript(db, question.id, transcript.id)
            self.assertEqual(
                get_question_transcript_map_by_id(db, question_map.id).question_id,
                question.id,
            )
            self.assertEqual(
                len(list_question_transcript_maps(db, question_id=question.id)), 1
            )

            summary = create_segment_summary(db, session.id, "最初小结")
            self.assertEqual(get_segment_summary_by_id(db, summary.id).text, "最初小结")
            updated_summary = update_segment_summary(
                db, summary.id, text="更新小结", score=0.95
            )
            self.assertEqual(updated_summary.text, "更新小结")
            self.assertEqual(len(list_segment_summaries(db)), 1)
            self.assertEqual(len(list_segment_summaries_by_session(db, session.id)), 1)

            summary_map = link_segment_summary_to_transcript(
                db, summary.id, transcript.id
            )
            self.assertEqual(
                get_segment_summary_transcript_map_by_id(
                    db, summary_map.id
                ).segment_summary_id,
                summary.id,
            )
            self.assertEqual(
                len(
                    list_segment_summary_transcript_maps(
                        db, segment_summary_id=summary.id
                    )
                ),
                1,
            )

            llm_info = create_llm_info(db, "model-a", input_price=1.0)
            self.assertEqual(get_llm_info_by_name(db, "model-a").input, 1.0)
            create_llm_info(db, "model-a", input_price=2.0, output_price=3.0)
            self.assertEqual(get_llm_info_by_name(db, "model-a").input, 2.0)
            self.assertEqual(len(list_llm_infos(db)), 1)

            relay_log = create_relay_log(
                db,
                time=1712995200,
                service_type="tts",
                request_model_name="model-a",
                input_value=11,
                output_value=22,
                status="success",
            )
            self.assertEqual(get_relay_log_by_id(db, relay_log.id).input_value, 11)
            updated_relay_log = update_relay_log(db, relay_log.id, error="timeout")
            self.assertEqual(updated_relay_log.error, "timeout")
            self.assertEqual(len(list_relay_logs(db)), 1)

            stats_total = create_stats_total(db, service_type="llm", input_value=10)
            self.assertEqual(get_stats_total_by_id(db, stats_total.id).input_value, 10)
            updated_stats_total = update_stats_total(
                db, stats_total.id, output_value=20
            )
            self.assertEqual(updated_stats_total.output_value, 20)
            upsert_stats_total(db, "asr", input_value=5, output_value=6)
            self.assertEqual(get_stats_total_by_service_type(db, "asr").output_value, 6)
            self.assertEqual(len(list_stats_totals(db)), 2)

            stats_daily = upsert_stats_daily(db, "2026-04-02", "llm", input_value=100)
            self.assertEqual(
                get_stats_daily_by_date(db, "2026-04-02", "llm").input_value, 100
            )
            upsert_stats_daily(db, "2026-04-02", "llm", output_value=50)
            self.assertEqual(
                get_stats_daily_by_date(db, "2026-04-02", "llm").output_value, 50
            )
            self.assertEqual(len(list_stats_dailies(db)), 1)

            stats_hourly = create_stats_hourly(
                db, "2026-04-02", 9, "llm", input_value=7
            )
            self.assertEqual(
                get_stats_hourly_by_hour(db, "2026-04-02", 9, "llm").input_value, 7
            )
            updated_stats_hourly = update_stats_hourly(
                db, "2026-04-02", 9, "llm", output_value=8
            )
            self.assertEqual(updated_stats_hourly.output_value, 8)
            upsert_stats_hourly(db, "2026-04-02", 10, "asr", input_value=9)
            self.assertEqual(
                get_stats_hourly_by_hour(db, "2026-04-02", 10, "asr").input_value, 9
            )
            self.assertEqual(len(list_stats_hourlies(db)), 2)

            setting = upsert_setting(db, "feature.flag", "on")
            self.assertEqual(get_setting(db, "feature.flag").value, "on")
            upsert_setting(db, "feature.flag", "off")
            self.assertEqual(get_setting(db, "feature.flag").value, "off")
            self.assertGreater(len(list_settings(db)), 1)
            self.assertIsNotNone(get_setting(db, "deepseek_base_url"))

            migration_record = create_migration_record(db, status=0)
            self.assertEqual(
                get_migration_record_by_version(db, migration_record.version).status, 0
            )
            updated_migration = update_migration_record(
                db, migration_record.version, status=1
            )
            self.assertEqual(updated_migration.status, 1)
            self.assertEqual(len(list_migration_records(db)), 1)

            self.assertTrue(delete_question_transcript_map(db, question_map.id))
            self.assertEqual(len(list_question_transcript_maps(db)), 0)

            self.assertTrue(delete_segment_summary_transcript_map(db, summary_map.id))
            self.assertEqual(len(list_segment_summary_transcript_maps(db)), 0)

            self.assertTrue(delete_question(db, question.id))
            self.assertEqual(len(list_questions(db)), 0)

            self.assertTrue(delete_segment_summary(db, summary.id))
            self.assertEqual(len(list_segment_summaries(db)), 0)

            self.assertTrue(delete_transcript(db, transcript.id))
            self.assertEqual(len(list_transcripts_by_session(db, session.id)), 0)

            self.assertTrue(delete_stats_hourly(db, "2026-04-02", 9, "llm"))
            self.assertTrue(delete_stats_hourly(db, "2026-04-02", 10, "asr"))
            self.assertEqual(len(list_stats_hourlies(db)), 0)

            self.assertTrue(
                delete_stats_daily(db, stats_daily.date, stats_daily.service_type)
            )
            self.assertEqual(len(list_stats_dailies(db)), 0)

            self.assertTrue(delete_stats_total(db, stats_total.id))
            self.assertTrue(
                delete_stats_total(db, get_stats_total_by_service_type(db, "asr").id)
            )
            self.assertEqual(len(list_stats_totals(db)), 0)

            self.assertTrue(delete_relay_log(db, relay_log.id))
            self.assertEqual(len(list_relay_logs(db)), 0)

            self.assertTrue(delete_llm_info(db, llm_info.name))
            self.assertEqual(len(list_llm_infos(db)), 0)

            self.assertTrue(delete_setting(db, setting.key))
            self.assertGreater(len(list_settings(db)), 0)

            self.assertTrue(delete_migration_record(db, migration_record.version))
            self.assertEqual(len(list_migration_records(db)), 0)

            self.assertTrue(delete_session(db, session.id))
            self.assertTrue(delete_session(db, second_session.id))
            self.assertEqual(len(list_sessions(db)), 0)

            self.assertTrue(delete_course(db, course.id))
            self.assertEqual(len(list_courses(db)), 0)

    def test_app_startup_initializes_all_tables(self):
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
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDatabase)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
