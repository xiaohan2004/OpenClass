"""核心业务模块测试。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.classcontext import ClassContext
from app.core.knowledge import KnowledgeProcessor
from app.core.keyword import KeywordProcessor
from app.core.keyword_extraction_algorithm import KeywordScore
from app.core.question import QuestionProcessor
from app.core.quiz import QuizProcessor
from app.core.report import LectureReportAgent, ReportProcessor
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

        self.assertEqual(generated, {"text": "阶段小结", "start": 0, "end": 2})
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


class TestKeywordProcessor(unittest.TestCase):
    def setUp(self):
        with patch("app.core.keyword.get_settings") as mock_get_settings:
            mock_get_settings.return_value.settings_refresh_interval_seconds = 999
            self.processor = KeywordProcessor()

    def test_extract_keywords_llm_without_transcript(self):
        self.assertEqual(self.processor.extract_keywords_llm(""), [])

    @patch("app.core.keyword.generate_keywords")
    def test_extract_keywords_llm_success(self, mock_generate_keywords):
        mock_generate_keywords.return_value = '["机器学习","神经网络","监督学习"]'

        result = self.processor.extract_keywords_llm("课堂内容", limit=3)

        self.assertEqual(result, ["机器学习", "神经网络", "监督学习"])
        mock_generate_keywords.assert_called_once()

    def test_extract_keywords_algorithm_delegates_to_local_extractor(self):
        self.processor.extractor = Mock()
        self.processor.extractor.extract_keywords.return_value = [
            KeywordScore(
                keyword="机器学习",
                tfidf_score=0.8,
                keybert_score=0.7,
                history_sim=0.1,
                novelty_score=0.9,
                final_score=0.75,
            )
        ]

        result = self.processor.extract_keywords_algorithm("课堂内容")

        self.assertEqual(result, ["机器学习"])
        self.processor.extractor.extract_keywords.assert_called_once_with(
            transcript="课堂内容",
            history_summary=None,
        )


class TestKnowledgeProcessor(unittest.TestCase):
    def setUp(self):
        with patch("app.core.knowledge.get_settings") as mock_get_settings:
            mock_get_settings.return_value.settings_refresh_interval_seconds = 999
            self.processor = KnowledgeProcessor()

    def test_generate_knowledge_points_without_context(self):
        self.assertIsNone(self.processor.generate_knowledge_points(""))

    @patch("app.core.knowledge.generate_knowledge")
    def test_generate_knowledge_points_success(self, mock_generate_knowledge):
        mock_generate_knowledge.return_value = '{"name":"HTTP协议","description":"超文本传输协议","difficulty":"medium"}'

        result = self.processor.generate_knowledge_point("课堂内容")

        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "HTTP协议")
        self.assertEqual(result["difficulty"], "medium")
        mock_generate_knowledge.assert_called_once()

    def test_normalize_difficulty_strips_string(self):
        self.assertEqual(self.processor._normalize_difficulty(" medium "), "medium")
        self.assertEqual(self.processor._normalize_difficulty(None), "")


class TestQuizProcessor(unittest.TestCase):
    def setUp(self):
        with patch("app.core.quiz.get_settings") as mock_get_settings:
            mock_get_settings.return_value.settings_refresh_interval_seconds = 999
            self.processor = QuizProcessor()

    def test_generate_quiz_items_without_context(self):
        self.assertIsNone(self.processor.generate_quiz_items(""))

    @patch("app.core.quiz.generate_quiz")
    def test_generate_quiz_items_success(self, mock_generate_quiz):
        mock_generate_quiz.return_value = '{"type":"choice","question":"函数是什么？","options":["A. 代码块","B. 数据表"],"answer":"A","explanation":"函数是代码块"}'

        result = self.processor.generate_quiz_item("课堂内容")

        self.assertIsNotNone(result)
        self.assertEqual(result["type"], "choice")
        self.assertEqual(result["options"], ["A. 代码块", "B. 数据表"])
        mock_generate_quiz.assert_called_once()


class TestLectureReportAgent(unittest.TestCase):
    def test_parse_steps_supports_numbering_and_bullets(self):
        agent = LectureReportAgent(lambda _prompt: "")

        parsed = agent.parse_steps("1. 引言\n2) 数据结构\n- 列表\n* 总结")

        self.assertEqual(parsed, ["引言", "数据结构", "列表", "总结"])

    def test_run_pipeline_returns_refined_html(self):
        calls: list[str] = []

        def fake_llm(prompt: str) -> str:
            calls.append(prompt)
            if "整理内容" in prompt:
                return "整理后的课堂内容"
            if "设计报告结构" in prompt:
                return "1. 引言\n2. 主题讲解\n3. 总结"
            if "输出该部分正文" in prompt:
                if "引言" in prompt:
                    return "这是引言"
                if "主题讲解" in prompt:
                    return "这是主题"
                return "这是总结"
            if "给出具体修改建议" in prompt:
                return "建议补充术语定义"
            if "根据以下意见修改报告" in prompt:
                return "修订后的报告"
            if "输出优化版本" in prompt:
                return "优化后的报告"
            if "输出完整HTML" in prompt:
                return "<html><body><h1>初稿</h1></body></html>"
            if "必须具体指出问题" in prompt:
                return "段落间距偏紧"
            if "输出最终HTML" in prompt:
                return "<html><body><h1>最终稿</h1></body></html>"
            return ""

        agent = LectureReportAgent(fake_llm)
        html = agent.run("课堂原始材料", max_iters=1)

        self.assertEqual(html, "<html><body><h1>最终稿</h1></body></html>")
        self.assertGreaterEqual(len(calls), 10)


class TestReportProcessor(unittest.TestCase):
    @patch("app.core.report.generate_report")
    def test_generate_report_extracts_html_from_wrapped_response(
        self, mock_generate_report
    ):
        mock_generate_report.return_value = (
            "下面是生成的报告：\n"
            "```html\n"
            "<html><body><h1>报告</h1></body></html>\n"
            "```"
        )

        processor = ReportProcessor()
        html = processor.generate_report("课堂材料")

        self.assertEqual(html, "<html><body><h1>报告</h1></body></html>")
        mock_generate_report.assert_called_once_with("课堂材料")


if __name__ == "__main__":
    unittest.main()
