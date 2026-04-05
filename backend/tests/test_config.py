"""配置模块测试。"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

import app.config
from app.config import (
    SYSTEM_PROMPT_QUESTION,
    SYSTEM_PROMPT_SEGMENT_SUMMARY,
    Settings,
    get_settings,
)


class TestConfig(unittest.TestCase):
    def setUp(self):
        app.config.get_settings.cache_clear()
        self.original_env_file = Settings.model_config.get("env_file")
        Settings.model_config["env_file"] = None

    def tearDown(self):
        Settings.model_config["env_file"] = self.original_env_file
        app.config.get_settings.cache_clear()

    def test_settings_default_values(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = get_settings()

        self.assertEqual(settings.deepseek_base_url, "https://api.deepseek.com")
        self.assertEqual(settings.model_name, "deepseek-chat")
        self.assertEqual(settings.max_tokens, 1024)
        self.assertEqual(settings.temperature, 1.7)
        self.assertEqual(settings.max_questions, 10)
        self.assertEqual(settings.question_concurrent_workers, 1)

    def test_settings_from_env(self):
        env_vars = {
            "DEEPSEEK_API_KEY": "test-api-key",
            "DEEPSEEK_BASE_URL": "https://custom.api.com",
            "MODEL_NAME": "custom-model",
            "MAX_TOKENS": "2048",
            "TEMPERATURE": "0.8",
            "MAX_QUESTIONS": "20",
            "QUESTION_CONCURRENT_WORKERS": "3",
            "RECENT_LECTURE_WINDOW": "120",
            "HISTORY_SUMMARY_WINDOW": "500",
        }
        with patch.dict(os.environ, env_vars, clear=True):
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

    def test_settings_case_insensitive(self):
        with patch.dict(
            os.environ,
            {
                "deepseek_api_key": "test-key",
                "DEEPSEEK_BASE_URL": "https://test.com",
                "Model_Name": "test-model",
            },
            clear=True,
        ):
            settings = get_settings()

        self.assertEqual(settings.deepseek_api_key, "test-key")
        self.assertEqual(settings.deepseek_base_url, "https://test.com")
        self.assertEqual(settings.model_name, "test-model")

    def test_settings_type_validation(self):
        with patch.dict(os.environ, {"MAX_TOKENS": "invalid"}, clear=True):
            with self.assertRaises(ValueError):
                get_settings()

    def test_prompts_exist(self):
        self.assertIn("学生", SYSTEM_PROMPT_QUESTION)
        self.assertIn("50", SYSTEM_PROMPT_QUESTION)
        self.assertIn("阶段小结", SYSTEM_PROMPT_SEGMENT_SUMMARY)
        self.assertIn("不要编造", SYSTEM_PROMPT_SEGMENT_SUMMARY)

    def test_settings_model_config(self):
        settings = Settings()
        self.assertEqual(settings.model_config.get("case_sensitive"), False)


if __name__ == "__main__":
    unittest.main()
