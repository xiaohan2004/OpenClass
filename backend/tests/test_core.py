"""
核心业务模块测试 - QuestionProcessor 功能验证
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# 添加项目路径到 Python 路径
TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.question import QuestionProcessor


class TestQuestionProcessor(unittest.TestCase):
    """QuestionProcessor 核心功能测试"""

    def setUp(self):
        self.processor = QuestionProcessor()
        self.processor._question_queue.clear()

    def test_initialization(self):
        """测试初始化状态"""
        self.assertEqual(self.processor.max_questions, self.processor._question_queue._max_size)
        self.assertTrue(self.processor._question_queue.is_empty())
        self.assertEqual(self.processor.get_questions_flat(), [])

    def test_generate_questions_without_context(self):
        """测试无上下文时不生成问题"""
        result = self.processor.generate_questions("")
        self.assertEqual(result, [])
        self.assertTrue(self.processor._question_queue.is_empty())

    @patch("app.core.question.generate_question")
    def test_generate_questions_success(self, mock_generate_question):
        """测试成功生成问题并入队"""
        mock_generate_question.side_effect = [
            "问题一",
            "问题二",
            "问题三",
        ]

        result = self.processor.generate_questions("课堂上下文", count=3)

        self.assertEqual(result, ["问题一", "问题二", "问题三"])
        self.assertEqual(self.processor.get_questions_flat(), ["问题一", "问题二", "问题三"])

        latest_batch = self.processor._question_queue.get_latest_batch()
        self.assertIsNotNone(latest_batch)
        self.assertEqual(latest_batch[1], ["问题一", "问题二", "问题三"])

    @patch("app.core.question.generate_question")
    def test_generate_questions_skips_empty_results(self, mock_generate_question):
        """测试空字符串问题会被过滤"""
        mock_generate_question.side_effect = [
            "有效问题",
            "   ",
            "",
        ]

        result = self.processor.generate_questions("课堂上下文", count=3)

        self.assertEqual(result, ["有效问题"])
        self.assertEqual(self.processor.get_questions_flat(), ["有效问题"])

    @patch("app.core.question.generate_question")
    def test_generate_questions_ignores_worker_errors(self, mock_generate_question):
        """测试单个任务异常不会影响其它问题生成"""
        mock_generate_question.side_effect = [
            "问题一",
            Exception("生成失败"),
            "问题二",
        ]

        result = self.processor.generate_questions("课堂上下文", count=3)

        self.assertEqual(result, ["问题一", "问题二"])
        self.assertEqual(self.processor.get_questions_flat(), ["问题一", "问题二"])

    @patch("app.core.question.generate_question")
    def test_generate_questions_uses_default_worker_count(self, mock_generate_question):
        """测试默认并发数来自配置"""
        mock_generate_question.return_value = "默认问题"

        with patch("app.core.question.get_settings") as mock_get_settings:
            mock_get_settings.return_value.concurrent_workers = 2
            result = self.processor.generate_questions("课堂上下文")

        self.assertEqual(result, ["默认问题", "默认问题"])
        self.assertEqual(mock_generate_question.call_count, 2)

    def test_get_latest_question_random_on_empty_queue(self):
        """测试空队列随机取问题返回 None"""
        self.assertIsNone(self.processor.get_latest_question_random())

    @patch("app.core.question.random.choice")
    def test_get_latest_question_random(self, mock_choice):
        """测试从最新批次随机获取问题"""
        self.processor._question_queue.add(1.0, ["旧问题"])
        self.processor._question_queue.add(2.0, ["新问题1", "新问题2"])
        mock_choice.return_value = "新问题2"

        result = self.processor.get_latest_question_random()

        self.assertEqual(result, "新问题2")
        mock_choice.assert_called_once_with(["新问题1", "新问题2"])

    def test_question_queue_respects_max_size(self):
        """测试问题队列最大长度限制"""
        self.processor._question_queue.set_max_size(2)

        removed_1 = self.processor._question_queue.add(1.0, ["问题1"])
        removed_2 = self.processor._question_queue.add(2.0, ["问题2"])
        removed_3 = self.processor._question_queue.add(3.0, ["问题3"])

        self.assertEqual(removed_1, [])
        self.assertEqual(removed_2, [])
        self.assertEqual(removed_3, [(1.0, ["问题1"])])
        self.assertEqual(self.processor.get_questions_flat(), ["问题2", "问题3"])


def main():
    """运行核心模块测试"""
    print("开始运行核心业务模块测试...")

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestQuestionProcessor)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
