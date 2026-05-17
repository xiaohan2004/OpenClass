"""配置模块测试。"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlmodel import Session

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

import app.config
import app.db.session as db_session_module
from app.config import (
    SYSTEM_PROMPT_QUESTION,
    SYSTEM_PROMPT_SEGMENT_SUMMARY,
    Settings,
    get_settings,
    refresh_settings_cache,
)
from app.db import get_engine, init_db
from app.db.crud import list_settings, upsert_setting


class TestConfig(unittest.TestCase):
    def setUp(self):
        app.config.get_settings.cache_clear()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "config.db"
        self.env_patcher = patch.dict(
            os.environ,
            {
                "DATABASE_URL": f"sqlite:///{self.db_path.as_posix()}",
                "DATABASE_ECHO": "false",
            },
            clear=False,
        )
        self.env_patcher.start()
        db_session_module.get_engine.cache_clear()
        db_session_module.engine = db_session_module.get_engine()
        init_db()
        refresh_settings_cache()

    def tearDown(self):
        self.env_patcher.stop()
        app.config.get_settings.cache_clear()
        db_session_module.engine.dispose()
        db_session_module.get_engine.cache_clear()
        refresh_settings_cache()
        self.temp_dir.cleanup()

    def test_settings_default_values(self):
        settings = get_settings()

        self.assertEqual(settings.deepseek_base_url, "https://api.deepseek.com")
        self.assertEqual(settings.model_name, "deepseek-v4-flash")
        self.assertEqual(settings.max_tokens, 393216)
        self.assertEqual(settings.temperature, 1.0)
        self.assertEqual(settings.max_questions, 10)
        self.assertEqual(settings.question_concurrent_workers, 1)
        self.assertEqual(settings.system_prompt_question, SYSTEM_PROMPT_QUESTION)
        self.assertEqual(
            settings.system_prompt_segment_summary,
            SYSTEM_PROMPT_SEGMENT_SUMMARY,
        )

    def test_settings_from_database(self):
        with Session(get_engine()) as db:
            upsert_setting(db, "deepseek_api_key", "test-api-key")
            upsert_setting(db, "deepseek_base_url", "https://custom.api.com")
            upsert_setting(db, "model_name", "custom-model")
            upsert_setting(db, "max_tokens", "2048")
            upsert_setting(db, "temperature", "0.8")
            upsert_setting(db, "max_questions", "20")
            upsert_setting(db, "question_concurrent_workers", "3")
            upsert_setting(db, "recent_lecture_window", "120")
            upsert_setting(db, "history_summary_window", "500")
            upsert_setting(db, "settings_refresh_interval_seconds", "0.1")

        refresh_settings_cache()
        settings = get_settings()

        self.assertEqual(settings.deepseek_api_key, "test-api-key")
        self.assertEqual(settings.deepseek_base_url, "https://custom.api.com")
        self.assertEqual(settings.model_name, "custom-model")
        self.assertEqual(settings.max_tokens, 2048)
        self.assertEqual(settings.temperature, 0.8)
        self.assertEqual(settings.max_questions, 20)
        self.assertEqual(settings.question_concurrent_workers, 3)
        self.assertEqual(settings.recent_lecture_window, 120)
        self.assertEqual(settings.history_summary_window, 500)

    def test_settings_reload_after_database_update(self):
        with Session(get_engine()) as db:
            upsert_setting(db, "deepseek_api_key", "test-key")

        refresh_settings_cache()
        settings = get_settings()

        self.assertEqual(settings.deepseek_api_key, "test-key")
        self.assertEqual(settings.deepseek_base_url, "https://api.deepseek.com")
        self.assertEqual(settings.model_name, "deepseek-v4-flash")

    def test_settings_type_validation(self):
        with Session(get_engine()) as db:
            upsert_setting(db, "max_tokens", "invalid")

        refresh_settings_cache()
        settings = get_settings()

        self.assertEqual(settings.max_tokens, 393216)

    def test_prompts_exist(self):
        self.assertIn("学生", SYSTEM_PROMPT_QUESTION)
        self.assertIn("50", SYSTEM_PROMPT_QUESTION)
        self.assertIn("阶段小结", SYSTEM_PROMPT_SEGMENT_SUMMARY)
        self.assertIn("不要编造", SYSTEM_PROMPT_SEGMENT_SUMMARY)

    def test_settings_model_config(self):
        settings = Settings()
        self.assertEqual(settings.model_config.get("extra"), "ignore")

    def test_settings_seeded_into_database(self):
        with Session(get_engine()) as db:
            settings_rows = list_settings(db)

        self.assertGreater(len(settings_rows), 0)


if __name__ == "__main__":
    unittest.main()
