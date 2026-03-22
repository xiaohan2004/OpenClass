"""
工具模块测试 - 时间戳队列与工具包导出验证
"""

import sys
import unittest
from pathlib import Path

# 添加项目路径到 Python 路径
TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils import QuestionTimestampQueue, TimestampQueue


class TestTimestampQueue(unittest.TestCase):
    """TimestampQueue 测试"""

    def test_add_keeps_timestamp_order(self):
        """测试插入后按时间戳有序"""
        queue = TimestampQueue(max_size=10)

        queue.add(3.0, "third")
        queue.add(1.0, "first")
        queue.add(2.0, "second")

        self.assertEqual(queue.size(), 3)
        self.assertEqual(queue.get_latest(), (3.0, "third"))
        self.assertEqual(queue._queue, [
            (1.0, "first"),
            (2.0, "second"),
            (3.0, "third"),
        ])

    def test_add_returns_removed_items_when_queue_overflows(self):
        """测试超出容量时返回被移除的数据"""
        queue = TimestampQueue(max_size=2)

        self.assertEqual(queue.add(1.0, "a"), [])
        self.assertEqual(queue.add(2.0, "b"), [])
        removed = queue.add(3.0, "c")

        self.assertEqual(removed, [(1.0, "a")])
        self.assertEqual(queue._queue, [(2.0, "b"), (3.0, "c")])

    def test_max_size_minus_one_means_unlimited(self):
        """测试 max_size 为 -1 时不限制长度"""
        queue = TimestampQueue(max_size=-1)

        for i in range(5):
            removed = queue.add(float(i), f"item-{i}")
            self.assertEqual(removed, [])

        self.assertEqual(queue.size(), 5)
        self.assertEqual(queue.get_latest(), (4.0, "item-4"))

    def test_set_max_size_triggers_cleanup(self):
        """测试缩小最大长度时立即清理旧数据"""
        queue = TimestampQueue(max_size=-1)
        queue.add(1.0, "a")
        queue.add(2.0, "b")
        queue.add(3.0, "c")

        removed = queue.set_max_size(2)

        self.assertEqual(removed, [(1.0, "a")])
        self.assertEqual(queue.size(), 2)

    def test_clear_is_empty_and_get_latest(self):
        """测试清空、空队列状态和最新元素读取"""
        queue = TimestampQueue(max_size=2)
        self.assertTrue(queue.is_empty())
        self.assertIsNone(queue.get_latest())

        queue.add(1.0, "a")
        self.assertFalse(queue.is_empty())

        queue.clear()
        self.assertTrue(queue.is_empty())
        self.assertIsNone(queue.get_latest())


class TestQuestionTimestampQueue(unittest.TestCase):
    """QuestionTimestampQueue 测试"""

    def test_get_latest_batch(self):
        """测试获取最新问题批次"""
        queue = QuestionTimestampQueue(max_size=10)
        queue.add(1.0, ["问题1"])
        queue.add(2.0, ["问题2", "问题3"])

        self.assertEqual(queue.get_latest_batch(), (2.0, ["问题2", "问题3"]))

    def test_get_all_data_flat(self):
        """测试平铺所有问题"""
        queue = QuestionTimestampQueue(max_size=10)
        queue.add(1.0, ["问题1", "问题2"])
        queue.add(2.0, ["问题3"])

        self.assertEqual(queue.get_all_data_flat(), ["问题1", "问题2", "问题3"])

    def test_utils_package_exports(self):
        """测试 utils 包正确导出队列类"""
        self.assertEqual(TimestampQueue.__name__, "TimestampQueue")
        self.assertEqual(QuestionTimestampQueue.__name__, "QuestionTimestampQueue")


def main():
    """运行工具模块测试"""
    print("开始运行工具模块测试...")

    suite = unittest.TestSuite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestTimestampQueue))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestQuestionTimestampQueue))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
