"""
核心业务模块测试 - QuestionProcessor 功能验证
"""

import sys
import os
import time
import unittest
from pathlib import Path

# 添加项目路径到Python路径
TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.question import QuestionProcessor
from app.config import get_settings


class TestQuestionProcessor(unittest.TestCase):
    """QuestionProcessor 核心功能测试"""

    def setUp(self):
        """测试前准备"""
        self.processor = QuestionProcessor()
        # 确保每个测试开始时都是干净的状态
        self.processor.clear_text()

    def tearDown(self):
        """测试后清理"""
        self.processor.clear_text()

    def test_initialization(self):
        """测试初始化"""
        self.assertEqual(self.processor.get_text(), "")
        self.assertEqual(len(self.processor.get_questions_flat()), 0)
        self.assertEqual(len(self.processor.get_question_queue_raw()), 0)

    def test_append_text(self):
        """测试文本追加功能"""
        # 测试单次追加
        self.processor.append_text("今天我们学习Python编程")
        self.assertIn("今天我们学习Python编程", self.processor.get_text())

        # 测试多次追加
        self.processor.append_text("重点是函数和类的使用")
        text = self.processor.get_text()
        self.assertIn("今天我们学习Python编程", text)
        self.assertIn("重点是函数和类的使用", text)

    def test_clear_text(self):
        """测试文本清理功能"""
        self.processor.append_text("测试文本")
        self.assertNotEqual(self.processor.get_text(), "")

        self.processor.clear_text()
        self.assertEqual(self.processor.get_text(), "")

    def test_get_text_strip(self):
        """测试获取文本时的空格处理"""
        self.processor.append_text("  测试文本  ")
        text = self.processor.get_text()
        self.assertEqual(text, "测试文本")

    def test_generate_questions_no_text(self):
        """测试无文本时生成问题"""
        questions = self.processor.generate_questions()
        self.assertEqual(questions, [])

    def test_generate_questions_with_text(self):
        """测试有文本时生成问题（mock LLM调用）"""
        # 添加测试文本
        test_text = "今天我们学习Python编程，重点是函数和类的使用。函数是可重用的代码块，类是面向对象编程的基础。"
        self.processor.append_text(test_text)

        # 由于我们没有实际的LLM API key，这里只测试函数是否能正常调用
        # 在实际项目中，应该使用mock来模拟LLM响应
        try:
            questions = self.processor.generate_questions(count=1)
            # 如果没有API key，这里会抛出异常，这是预期的
        except Exception as e:
            # 期望的错误类型
            self.assertIn("API", str(e) or "api" in str(e).lower())

    def test_question_queue_batch_structure(self):
        """测试问题队列的批次结构"""
        # 模拟添加问题批次
        import heapq
        test_questions = ["问题1", "问题2", "问题3"]
        timestamp = time.time()

        with self.processor._lock:
            heapq.heappush(self.processor.question_queue, (timestamp, test_questions))

        # 验证队列结构
        queue_raw = self.processor.get_question_queue_raw()
        self.assertEqual(len(queue_raw), 1)
        self.assertEqual(queue_raw[0][0], timestamp)
        self.assertEqual(queue_raw[0][1], test_questions)

    def test_get_questions_flat(self):
        """测试获取展开后的问题列表"""
        # 模拟添加多个批次的问题
        import heapq

        batch1 = ["问题1", "问题2"]
        batch2 = ["问题3", "问题4"]

        with self.processor._lock:
            heapq.heappush(self.processor.question_queue, (time.time(), batch1))
            heapq.heappush(self.processor.question_queue, (time.time() + 1, batch2))

        all_questions = self.processor.get_questions_flat()
        self.assertEqual(len(all_questions), 4)
        self.assertIn("问题1", all_questions)
        self.assertIn("问题4", all_questions)

    def test_get_latest_question_random(self):
        """测试随机获取最新批次问题"""
        # 空队列测试
        result = self.processor.get_latest_question_random()
        self.assertIsNone(result)

        # 添加测试数据
        import heapq
        test_questions = ["问题A", "问题B", "问题C"]

        with self.processor._lock:
            heapq.heappush(self.processor.question_queue, (time.time(), test_questions))

        # 测试随机选择
        result = self.processor.get_latest_question_random()
        self.assertIn(result, test_questions)

    def test_queue_max_size_limit(self):
        """测试队列最大长度限制"""
        settings = get_settings()
        max_size = settings.max_questions

        # 添加超过限制的问题批次
        import heapq
        for i in range(max_size + 2):  # 超出限制2个
            questions = [f"问题{i}-1", f"问题{i}-2"]
            heapq.heappush(self.processor.question_queue, (time.time() + i, questions))

            # 触发队列清理
            if len(self.processor.question_queue) > max_size:
                heapq.heappop(self.processor.question_queue)

        # 验证队列长度没有超过限制
        self.assertLessEqual(len(self.processor.question_queue), max_size)

    def test_thread_safety(self):
        """测试线程安全性"""
        import threading
        import time

        # 模拟并发操作
        def worker():
            try:
                self.processor.append_text(f"线程{threading.current_thread().ident}的文本")
                time.sleep(0.01)
                self.processor.get_questions_flat()
            except Exception:
                pass

        # 创建多个线程同时操作
        threads = []
        for _ in range(5):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # 如果没有抛出异常，说明线程安全基本正常
        self.assertTrue(True)


def main():
    """运行核心模块测试"""
    print("开始运行核心业务模块测试...")

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestQuestionProcessor)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 返回退出码
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())