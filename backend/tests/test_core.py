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
        self.processor._question_queue.clear()

    def test_initialization(self):
        self.assertEqual(self.processor.max_questions, self.processor._question_queue._max_size)
        self.assertTrue(self.processor._question_queue.is_empty())
        self.assertEqual(self.processor.get_questions_flat(), [])

    def test_generate_questions_without_context(self):
        result = self.processor.generate_questions("")
        self.assertEqual(result, [])
        self.assertTrue(self.processor._question_queue.is_empty())

    @patch("app.core.question.generate_question")
    def test_generate_questions_success(self, mock_generate_question):
        mock_generate_question.side_effect = ["问题一", "问题二", "问题三"]

        result = self.processor.generate_questions("课堂上下文", count=3)

        self.assertEqual(result, ["问题一", "问题二", "问题三"])
        self.assertEqual(self.processor.get_questions_flat(), ["问题一", "问题二", "问题三"])
        self.assertEqual(self.processor._question_queue.get_latest_batch()[1], ["问题一", "问题二", "问题三"])

    @patch("app.core.question.generate_question")
    def test_generate_questions_uses_default_worker_count(self, mock_generate_question):
        mock_generate_question.return_value = "默认问题"

        with patch("app.core.question.get_settings") as mock_get_settings:
            mock_get_settings.return_value.question_concurrent_workers = 2
            result = self.processor.generate_questions("课堂上下文")

        self.assertEqual(result, ["默认问题", "默认问题"])
        self.assertEqual(mock_generate_question.call_count, 2)

    @patch("app.core.question.random.choice")
    def test_get_latest_question_random(self, mock_choice):
        self.processor._question_queue.add(1.0, ["旧问题"])
        self.processor._question_queue.add(2.0, ["新问题1", "新问题2"])
        mock_choice.return_value = "新问题2"

        result = self.processor.get_latest_question_random()

        self.assertEqual(result, "新问题2")
        mock_choice.assert_called_once_with(["新问题1", "新问题2"])


class TestClassContext(unittest.TestCase):
    def setUp(self):
        with patch("app.core.classcontext.get_settings") as mock_get_settings:
            mock_get_settings.return_value.recent_lecture_window = 2
            mock_get_settings.return_value.history_summary_window = 2
            self.context = ClassContext()

    def test_add_lecture_text(self):
        with patch("app.core.classcontext.segment_summary_processor.generate_summary", return_value="阶段小结"):
            self.context.add_lecture_text(1.0, "第一段")
            self.context.add_lecture_text(2.0, "第二段")

        self.assertEqual(self.context.lecture_texts.get_latest_texts(), "第一段第二段")

    @patch("app.core.classcontext.segment_summary_processor.generate_summary")
    def test_add_lecture_text_generates_summary_when_window_reached(self, mock_generate_summary):
        mock_generate_summary.return_value = "阶段小结"

        self.context.add_lecture_text(1.0, "第一段")
        self.context.add_lecture_text(2.0, "第二段")

        self.assertEqual(self.context.last_summary_index, 2)
        self.assertEqual(self.context.history_summaries.get_valid_summaries(10), "阶段小结")

    def test_get_questioning_texts(self):
        self.context.lecture_texts.add(1.0, "第一段")
        self.context.lecture_texts.add(2.0, "第二段")
        self.context.history_summaries.add(3.0, {"start": 0, "end": 0, "text": "历史总结"})

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
