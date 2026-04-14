"""核心业务模块测试。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.classcontext import ClassContext
from app.core.question import QuestionProcessor
from app.core.segment_summary import SegmentSummaryProcessor


class TestQuestionProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = QuestionProcessor()

    def test_initialization(self):
        self.assertGreater(self.processor.max_questions, 0)
        self.assertEqual(self.processor.get_questions_flat(), [])

    def test_generate_questions_without_context(self):
        result = self.processor.generate_questions("")
        self.assertEqual(result, [])
        self.assertEqual(self.processor.get_questions_flat(), [])

    @patch("app.core.question.generate_question")
    def test_generate_questions_success(self, mock_generate_question):
        mock_generate_question.side_effect = ["问题一", "问题二", "问题三"]

        result = self.processor.generate_questions("课堂上下文", count=3)

        self.assertEqual(result, ["问题一", "问题二", "问题三"])
        self.assertEqual(
            self.processor.get_questions_flat(), ["问题一", "问题二", "问题三"]
        )

    @patch("app.core.question.generate_question")
    def test_generate_questions_uses_default_worker_count(self, mock_generate_question):
        mock_generate_question.return_value = "默认问题"

        with patch("app.core.question.get_settings") as mock_get_settings:
            mock_get_settings.return_value.question_concurrent_workers = 2
            result = self.processor.generate_questions("课堂上下文")

        self.assertEqual(result, ["默认问题", "默认问题"])
        self.assertEqual(mock_generate_question.call_count, 2)

    @patch("app.core.question.generate_question")
    @patch("app.core.question.random.choice")
    def test_get_latest_question_random(self, mock_choice, mock_generate_question):
        mock_generate_question.side_effect = ["旧问题", "新问题"]

        self.processor.generate_questions("旧上下文", count=1)
        self.processor.generate_questions("新上下文", count=1)
        mock_choice.return_value = "新问题"

        result = self.processor.get_latest_question_random()

        self.assertEqual(result, "新问题")
        mock_choice.assert_called_once_with(["新问题"])


class TestClassContext(unittest.TestCase):
    def setUp(self):
        with patch("app.core.classcontext.get_settings") as mock_get_settings:
            mock_get_settings.return_value.recent_lecture_window = 2
            mock_get_settings.return_value.history_summary_window = 2
            self.context = ClassContext()

    def test_add_lecture_text(self):
        self.context.add_lecture_text(1.0, "第一段")
        self.context.add_lecture_text(2.0, "第二段")

        self.assertEqual(self.context.lecture_texts.get_latest_texts(), "第一段第二段")
        self.assertEqual(self.context.last_summary_index, 0)

    @patch("app.core.classcontext.segment_summary_processor.generate_summary")
    def test_generate_summary_if_needed_generates_summary_when_window_reached(
        self,
        mock_generate_summary,
    ):
        mock_generate_summary.return_value = "阶段小结"

        self.context.add_lecture_text(1.0, "第一段")
        self.context.add_lecture_text(2.0, "第二段")
        generated = self.context.generate_summary_if_needed()

        self.assertEqual(
            generated, {"text": "阶段小结", "start": 0, "end": 2}
        )
        self.assertEqual(self.context.last_summary_index, 2)
        self.assertEqual(
            self.context.history_summaries.get_valid_summaries(10), "阶段小结"
        )

    @patch("app.core.classcontext.segment_summary_processor.generate_summary")
    def test_generate_summary_if_needed_returns_false_before_window_reached(
        self,
        mock_generate_summary,
    ):
        mock_generate_summary.return_value = "阶段小结"

        self.context.add_lecture_text(1.0, "第一段")

        generated = self.context.generate_summary_if_needed()

        self.assertIsNone(generated)
        self.assertEqual(self.context.last_summary_index, 0)
        self.assertTrue(self.context.history_summaries.is_empty())

    def test_get_questioning_texts(self):
        self.context.lecture_texts.add(1.0, "第一段")
        self.context.lecture_texts.add(2.0, "第二段")
        self.context.history_summaries.add(
            3.0, {"start": 0, "end": 0, "text": "历史总结"}
        )

        result = self.context.get_questioning_texts()

        self.assertIn("历史总结", result)
        self.assertIn("第一段第二段", result)


class TestSegmentSummaryProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = SegmentSummaryProcessor()

    def test_generate_summary_without_context(self):
        self.assertIsNone(self.processor.generate_summary(""))

    @patch("app.core.segment_summary.generate_segment_summary")
    def test_generate_summary_success(self, mock_generate_segment_summary):
        mock_generate_segment_summary.return_value = "  小结内容  "

        result = self.processor.generate_summary("课堂上下文")

        self.assertEqual(result, "小结内容")
        mock_generate_segment_summary.assert_called_once_with("课堂上下文")


if __name__ == "__main__":
    unittest.main()
