"""工具模块测试。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.utils import (
    HistorySummaryTimestampQueue,
    QuestionTimestampQueue,
    TextTimestampQueue,
    TimestampQueue,
)


class TestTimestampQueue(unittest.TestCase):
    def test_add_keeps_timestamp_order(self):
        queue = TimestampQueue(max_size=10)
        queue.add(3.0, "third")
        queue.add(1.0, "first")
        queue.add(2.0, "second")

        self.assertEqual(queue._queue, [(1.0, "first"), (2.0, "second"), (3.0, "third")])

    def test_add_returns_removed_items_when_queue_overflows(self):
        queue = TimestampQueue(max_size=2)
        queue.add(1.0, "a")
        queue.add(2.0, "b")
        removed = queue.add(3.0, "c")

        self.assertEqual(removed, [(1.0, "a")])
        self.assertEqual(queue._queue, [(2.0, "b"), (3.0, "c")])

    def test_clear(self):
        queue = TimestampQueue(max_size=2)
        queue.add(1.0, "a")
        queue.clear()

        self.assertTrue(queue.is_empty())
        self.assertIsNone(queue.get_latest())


class TestTextQueues(unittest.TestCase):
    def test_text_timestamp_queue(self):
        queue = TextTimestampQueue()
        queue.add(1.0, "一")
        queue.add(2.0, "二")
        queue.add(3.0, "三")

        self.assertEqual(queue.get_latest_texts(), "一二三")
        self.assertEqual(queue.get_latest_texts(2), "二三")
        self.assertEqual(queue.get_range_texts(1, 3), "二三")
        self.assertEqual(queue.get_count(), 3)

    def test_history_summary_timestamp_queue(self):
        queue = HistorySummaryTimestampQueue()
        queue.add(1.0, {"start": 0, "end": 2, "text": "总结一"})
        queue.add(2.0, {"start": 2, "end": 4, "text": "总结二"})
        queue.add(3.0, {"start": 4, "end": 6, "text": "总结三"})

        self.assertEqual(queue.get_valid_summaries(4), "总结一总结二")

    def test_question_timestamp_queue(self):
        queue = QuestionTimestampQueue(max_size=10)
        queue.add(1.0, ["问题1"])
        queue.add(2.0, ["问题2", "问题3"])

        self.assertEqual(queue.get_latest_batch(), (2.0, ["问题2", "问题3"]))
        self.assertEqual(queue.get_all_data_flat(), ["问题1", "问题2", "问题3"])


if __name__ == "__main__":
    unittest.main()
