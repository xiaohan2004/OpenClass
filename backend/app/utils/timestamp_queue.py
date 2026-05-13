"""
时间戳队列工具类

维护按时间戳排序的队列，保证队头到队尾时间戳递增，
并提供线程安全的插入、删除和查询操作
"""

import logging
from threading import Lock
from typing import Any, List, Optional, Tuple, Dict, cast

logger = logging.getLogger(__name__)


class TimestampQueue:
    """
    通用时间戳队列

    队列结构: [(timestamp, data), ...]，按时间戳递增排序
    """

    def __init__(self, max_size: int = -1):
        self._queue: List[Tuple[float, Any]] = []
        self._max_size = max_size
        self._lock = Lock()
        logger.debug("TimestampQueue 初始化完成，最大容量: %d", max_size)

    def add(self, timestamp: float, data: Any) -> List[Tuple[float, Any]]:
        """
        添加数据到队列，并保持时间戳有序

        Returns:
            被移除的旧数据列表
        """
        with self._lock:
            if not self._queue or timestamp >= self._queue[-1][0]:
                self._queue.append((timestamp, data))
            else:
                insert_pos = self._find_insert_position(timestamp)
                self._queue.insert(insert_pos, (timestamp, data))

            removed_batches = self._cleanup_if_needed()

            logger.debug(
                "数据 %.3f 添加完成，队列长度 %d，删除 %d 个旧数据",
                timestamp,
                len(self._queue),
                len(removed_batches),
            )
            return removed_batches

    def _find_insert_position(self, timestamp: float) -> int:
        """找到合适的插入位置，保持时间戳递增顺序"""
        insert_pos = len(self._queue)
        for i in range(len(self._queue) - 1, -1, -1):
            if timestamp >= self._queue[i][0]:
                insert_pos = i + 1
                break
            if i == 0:
                insert_pos = 0
                break
        return insert_pos

    def _cleanup_if_needed(self) -> List[Tuple[float, Any]]:
        """清理超过容量的最旧数据"""
        removed_batches: List[Tuple[float, Any]] = []

        if self._max_size == -1:
            return removed_batches

        while len(self._queue) > self._max_size:
            removed = self._queue.pop(0)
            removed_batches.append(removed)
            logger.debug("队列已满，删除最旧数据: %.3f", removed[0])

        return removed_batches

    def get_latest(self) -> Optional[Tuple[float, Any]]:
        """获取最新的数据"""
        with self._lock:
            if not self._queue:
                return None
            return self._queue[-1]

    def get_latest_n(self, n: int) -> List[Tuple[float, Any]]:
        """获取最新的 n 条数据"""
        with self._lock:
            if not self._queue or n <= 0:
                return []
            return self._queue[-n:]

    def is_empty(self) -> bool:
        """检查队列是否为空"""
        with self._lock:
            return len(self._queue) == 0

    def size(self) -> int:
        """获取队列当前大小"""
        with self._lock:
            return len(self._queue)

    def set_max_size(self, max_size: int) -> List[Tuple[float, Any]]:
        """设置新的最大容量，并在必要时清理旧数据"""
        with self._lock:
            self._max_size = max_size
            return self._cleanup_if_needed()

    def clear(self) -> None:
        """清空队列"""
        with self._lock:
            self._queue.clear()
            logger.debug("队列已清空")


class QuestionTimestampQueue(TimestampQueue):
    """问题时间戳队列，队列数据结构为 `List[str]`"""

    def add(self, timestamp: float, data: List[Any]) -> List[Tuple[float, List[Any]]]:
        return cast(List[Tuple[float, List[Any]]], super().add(timestamp, data))

    def get_latest_batch(self) -> Optional[Tuple[float, List[Any]]]:
        """获取最新的一批问题"""
        return cast(Optional[Tuple[float, List[Any]]], super().get_latest())

    def get_batches(self) -> List[Tuple[float, List[Any]]]:
        """获取当前全部问题批次，按时间从旧到新排序。"""
        with self._lock:
            return [(timestamp, list(batch_data)) for timestamp, batch_data in self._queue]

    def get_all_data_flat(self) -> List[str]:
        """获取队列中所有问题的扁平列表"""
        with self._lock:
            all_data: List[str] = []
            for _, batch_data in self._queue:
                for item in cast(List[Any], batch_data):
                    all_data.append(getattr(item, "text", str(item)))
            return all_data

    def remove_first_text(self, text: str) -> bool:
        """按文本移除第一个匹配的问题。"""
        with self._lock:
            for batch_index, (_, batch_data) in enumerate(self._queue):
                items = cast(List[Any], batch_data)
                for item_index, item in enumerate(items):
                    if getattr(item, "text", str(item)) == text:
                        items.pop(item_index)
                        if not items:
                            self._queue.pop(batch_index)
                        return True
            return False


class TextTimestampQueue(TimestampQueue):
    """上下文时间戳队列，队列数据结构为 `str`"""

    def add(self, timestamp: float, data: str) -> List[Tuple[float, str]]:
        return cast(List[Tuple[float, str]], super().add(timestamp, data))

    def get_latest_texts(self, n: Optional[int] = None) -> str:
        """获取最新的 n 条拼接后的文本数据（不传则全部）"""
        with self._lock:
            if not self._queue:
                return ""

            if n is None or n <= 0:
                batches = self._queue
            else:
                batches = self._queue[-n:]

            return "".join(str(data) for _, data in batches)

    def get_range_texts(self, start: int, end: int) -> str:
        """获取指定 index 范围内的拼接后的文本数据"""
        with self._lock:
            if not self._queue:
                return ""

            # 边界保护
            start = max(0, start)
            end = min(len(self._queue), end)

            if start >= end:
                return ""

            return "".join(str(data) for _, data in self._queue[start:end])

    def get_count(self) -> int:
        """获取队列中所有文本数据的数量"""
        with self._lock:
            return len(self._queue)


class HistorySummaryTimestampQueue(TimestampQueue):
    """历史总结时间戳队列"""

    def add(
        self, timestamp: float, data: Dict  # {"start": int, "end": int, "text": str}
    ) -> List[Tuple[float, Dict]]:
        return cast(List[Tuple[float, Dict]], super().add(timestamp, data))

    def get_valid_summaries(self, recent_start_index: int) -> str:
        """
        获取不与 recent 重叠的拼接后的 summary
        """
        with self._lock:
            valid_summaries = []
            for _, summary in self._queue:
                if summary["end"] <= recent_start_index:
                    valid_summaries.append(summary["text"])
            return "".join(valid_summaries)
