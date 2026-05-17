"""包导出测试。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

import app
import app.core
import app.services
import app.utils


class TestPackageExports(unittest.TestCase):
    def test_core_exports(self):
        self.assertTrue(hasattr(app.core, "ClassContext"))
        self.assertTrue(hasattr(app.core, "KnowledgeProcessor"))
        self.assertTrue(hasattr(app.core, "QuestionProcessor"))
        self.assertTrue(hasattr(app.core, "QuizProcessor"))
        self.assertTrue(hasattr(app.core, "ReportProcessor"))
        self.assertTrue(hasattr(app.core, "SegmentSummaryProcessor"))
        self.assertTrue(hasattr(app.core, "ask_question"))
        self.assertTrue(hasattr(app.core, "handle_audio"))
        self.assertTrue(hasattr(app.core, "start_background_tasks"))

    def test_services_exports(self):
        self.assertTrue(hasattr(app.services, "get_asr_service"))
        self.assertTrue(hasattr(app.services, "get_tts_service"))
        self.assertTrue(hasattr(app.services, "generate_question"))
        self.assertTrue(hasattr(app.services, "generate_keywords"))
        self.assertTrue(hasattr(app.services, "generate_knowledge"))
        self.assertTrue(hasattr(app.services, "generate_quiz"))
        self.assertTrue(hasattr(app.services, "generate_segment_summary"))
        self.assertTrue(hasattr(app.services, "get_llm_client"))

    def test_utils_exports(self):
        self.assertTrue(hasattr(app.utils, "TimestampQueue"))
        self.assertTrue(hasattr(app.utils, "QuestionTimestampQueue"))
        self.assertTrue(hasattr(app.utils, "TextTimestampQueue"))
        self.assertTrue(hasattr(app.utils, "HistorySummaryTimestampQueue"))


if __name__ == "__main__":
    unittest.main()
