"""
工具函数模块

提供各种通用工具类和函数，包括：
- TimestampQueue: 时间戳队列管理
"""

# 导出主要类
from .timestamp_queue import QuestionTimestampQueue, TimestampQueue

__all__ = [
    'TimestampQueue',
    'QuestionTimestampQueue',
]
