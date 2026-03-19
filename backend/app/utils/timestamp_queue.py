"""
时间戳队列工具类

维护按时间戳排序的队列，保证队头到队尾时间戳递增
提供线程安全的队列操作
"""

import logging
from threading import Lock
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class TimestampQueue:
    """
    时间戳队列 - 维护按时间戳排序的数据结构

    队列结构: [(timestamp, data), ...]，按时间戳递增排序
    提供线程安全的插入、删除和查询操作
    """

    def __init__(self, max_size: int):
        """
        初始化时间戳队列

        Args:
            max_size: 队列最大容量
        """
        self._queue: List[Tuple[float, List[str]]] = []
        self._max_size = max_size
        self._lock = Lock()
        logger.debug("TimestampQueue 初始化完成，最大容量: %d", max_size)

    def add_batch(self, timestamp: float, data: List[str]) -> List[Tuple[float, List[str]]]:
        """
        添加新批次到队列，保持时间戳有序

        优化策略：99% 情况下新批次是最新的，直接追加
        只有少数情况需要插入到中间位置

        Args:
            timestamp: 批次时间戳
            data: 批次数据

        Returns:
            被删除的最旧批次列表（如果有）
        """
        with self._lock:
            # 优化插入：先检查最常见情况（新批次时间戳最大）
            if not self._queue or timestamp >= self._queue[-1][0]:
                # 最常见情况：新批次时间戳最大，直接追加到队尾
                self._queue.append((timestamp, data))
            else:
                # 少数情况：需要插入到中间位置
                insert_pos = self._find_insert_position(timestamp)
                self._queue.insert(insert_pos, (timestamp, data))

            # 清理超出的旧批次
            removed_batches = self._cleanup_if_needed()

            logger.debug(
                "批次 %.3f 添加完成，队列长度: %d，删除 %d 个旧批次",
                timestamp, len(self._queue), len(removed_batches)
            )

            return removed_batches

    def _find_insert_position(self, timestamp: float) -> int:
        """
        找到合适的插入位置，保持时间戳递增顺序

        从后往前扫描，因为新数据通常时间戳较大

        Args:
            timestamp: 要插入的时间戳

        Returns:
            插入位置索引
        """
        # 从后往前扫描找到合适的插入位置
        insert_pos = len(self._queue)
        for i in range(len(self._queue) - 1, -1, -1):
            if timestamp >= self._queue[i][0]:
                insert_pos = i + 1
                break
            # 如果已经到队头，insert_pos 保持为 0
            if i == 0:
                insert_pos = 0
                break

        return insert_pos

    def _cleanup_if_needed(self) -> List[Tuple[float, List[str]]]:
        """
        清理超容量的最旧批次

        Returns:
            被删除的批次列表
        """
        removed_batches = []

        # 删除所有超出的最旧批次
        while len(self._queue) > self._max_size:
            removed = self._queue.pop(0)
            removed_batches.append(removed)
            logger.debug("队列已满，删除最旧批次: %s", ', '.join(removed[1]))

        return removed_batches

    def get_latest_batch(self) -> Optional[Tuple[float, List[str]]]:
        """
        获取最新的批次（队尾）

        Returns:
            (timestamp, data) 元组，如果队列为空则返回 None
        """
        with self._lock:
            if not self._queue:
                return None
            return self._queue[-1]

    def get_all_data_flat(self) -> List[str]:
        """
        获取所有数据（展开后的列表）

        Returns:
            所有批次数据的扁平列表
        """
        with self._lock:
            all_data = []
            for _, batch_data in self._queue:
                all_data.extend(batch_data)
            return all_data

    def get_raw_queue(self) -> List[Tuple[float, List[str]]]:
        """
        获取原始队列结构（深拷贝）

        Returns:
            队列的深拷贝
        """
        with self._lock:
            return [(timestamp, data.copy()) for timestamp, data in self._queue]

    def is_empty(self) -> bool:
        """检查队列是否为空"""
        with self._lock:
            return len(self._queue) == 0

    def size(self) -> int:
        """获取队列当前大小"""
        with self._lock:
            return len(self._queue)

    def set_max_size(self, max_size: int) -> List[Tuple[float, List[str]]]:
        """
        设置新的最大容量，如果变小则清理旧批次

        Args:
            max_size: 新的最大容量

        Returns:
            被删除的批次列表
        """
        with self._lock:
            self._max_size = max_size
            return self._cleanup_if_needed()

    def clear(self) -> None:
        """清空队列"""
        with self._lock:
            self._queue.clear()
            logger.debug("队列已清空")