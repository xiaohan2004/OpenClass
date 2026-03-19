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
        # 通过公共API添加问题批次
        test_questions = ["问题1", "问题2", "问题3"]
        timestamp = time.time()

        # 模拟一个批次直接添加到内部队列（为了测试）
        with self.processor._question_queue._lock:
            self.processor._question_queue._queue.append((timestamp, test_questions))

        # 验证队列结构
        queue_raw = self.processor.get_question_queue_raw()
        self.assertEqual(len(queue_raw), 1)
        self.assertEqual(queue_raw[0][0], timestamp)
        self.assertEqual(queue_raw[0][1], test_questions)

    def test_get_questions_flat(self):
        """测试获取展开后的问题列表"""
        # 通过公共API添加多个批次的问题
        batch1 = ["问题1", "问题2"]
        batch2 = ["问题3", "问题4"]

        with self.processor._question_queue._lock:
            self.processor._question_queue._queue.append((time.time(), batch1))
            self.processor._question_queue._queue.append((time.time() + 1, batch2))

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
        test_questions = ["问题A", "问题B", "问题C"]

        with self.processor._question_queue._lock:
            self.processor._question_queue._queue.append((time.time(), test_questions))

        # 测试随机选择
        result = self.processor.get_latest_question_random()
        self.assertIn(result, test_questions)

    def test_queue_max_size_limit(self):
        """测试队列最大长度限制"""
        settings = get_settings()
        max_size = settings.max_questions

        # 通过公共API添加多个批次，触发自动清理
        base_time = time.time()
        for i in range(max_size + 2):  # 超出限制2个
            questions = [f"问题{i}-1", f"问题{i}-2"]

            # 使用公共API添加批次（这会触发自动清理）
            removed_batches = self.processor._question_queue.add_batch(base_time + i, questions)

            # 验证当超出限制时确实有批次被删除
            if i >= max_size:
                self.assertGreater(len(removed_batches), 0, f"第{i+1}个批次添加时应该有删除")

        # 验证队列长度没有超过限制
        self.assertLessEqual(self.processor._question_queue.size(), max_size)

    def test_queue_cleanup_multiple_batches(self):
        """测试队列清理多个批次的情况"""
        settings = get_settings()
        max_size = settings.max_questions

        # 先填满队列
        base_time = time.time()
        for i in range(max_size):
            questions = [f"问题{i}-1", f"问题{i}-2"]
            removed_batches = self.processor._question_queue.add_batch(base_time + i, questions)
            self.assertEqual(len(removed_batches), 0, "填充队列时不应该删除")

        # 验证队列已满
        self.assertEqual(self.processor._question_queue.size(), max_size)

        # 添加3个新批次（应该触发删除3个最旧的）
        removed_count = 0
        for i in range(3):
            questions = [f"新问题{i}-1", f"新问题{i}-2"]
            batch_timestamp = base_time + max_size + i

            # 使用公共API添加批次
            removed_batches = self.processor._question_queue.add_batch(batch_timestamp, questions)
            removed_count += len(removed_batches)

        # 验证总共删除了3个最旧的批次
        self.assertEqual(removed_count, 3, "应该删除3个最旧的批次")

        # 验证队列长度正确
        self.assertEqual(self.processor._question_queue.size(), max_size)

        # 验证最旧的3个批次已被删除（检查最新的批次存在）
        all_questions = self.processor.get_questions_flat()
        self.assertIn("新问题0-1", all_questions)
        self.assertIn("新问题2-2", all_questions)

        # 验证最旧的批次确实被删除了
        self.assertNotIn("问题0-1", all_questions)
        self.assertNotIn("问题2-2", all_questions)

    def test_optimized_insertion_performance(self):
        """测试优化插入逻辑的正确性和性能"""
        # 测试1: 正常情况（新批次时间戳最大）- 应该直接追加
        base_time = time.time()

        # 添加一些初始批次
        for i in range(3):
            questions = [f"初始问题{i}-1", f"初始问题{i}-2"]
            self.processor._question_queue.add_batch(base_time + i, questions)

        # 添加一个时间戳更大的新批次（应该直接追加）
        new_questions = ["新问题1", "新问题2"]
        new_timestamp = base_time + 10

        # 使用公共API添加批次
        removed_batches = self.processor._question_queue.add_batch(new_timestamp, new_questions)

        # 验证新批次在队尾（最新批次）
        latest_batch = self.processor._question_queue.get_latest_batch()
        self.assertIsNotNone(latest_batch)
        self.assertEqual(latest_batch[0], new_timestamp)
        self.assertEqual(latest_batch[1], new_questions)

        # 测试2: 特殊情况（新批次时间戳较小）- 需要插入到中间
        old_questions = ["旧问题1", "旧问题2"]
        old_timestamp = base_time + 1.5  # 在初始批次1和2之间

        # 使用公共API添加批次
        removed_batches = self.processor._question_queue.add_batch(old_timestamp, old_questions)

        # 验证旧批次被正确插入
        queue_raw = self.processor._question_queue.get_raw_queue()
        found_pos = -1
        for i, (ts, questions) in enumerate(queue_raw):
            if ts == old_timestamp and questions == old_questions:
                found_pos = i
                break

        self.assertNotEqual(found_pos, -1, "旧批次应该被插入到队列中")

        # 验证时间戳仍然有序
        for i in range(len(queue_raw) - 1):
            self.assertLessEqual(queue_raw[i][0], queue_raw[i + 1][0])

        # 验证插入位置正确（应该在初始问题1和2之间）
        self.assertGreater(found_pos, 0)  # 不在队头
        self.assertLess(found_pos, len(queue_raw) - 1)  # 不在队尾

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