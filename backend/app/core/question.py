"""
核心业务逻辑 - 学生提问处理器
"""

import logging
import time
import heapq
import random
from threading import Lock

from app.config import get_settings
from app.services.llm import generate_question
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class QuestionProcessor:
    """
    学生提问处理器

    被动接收文本，由外部控制提问触发时机
    并发生成问题并入队，使用 heapq 自动按时间戳排序
    队列结构: [(timestamp, [question1, question2, ...]), ...]
    """

    def __init__(self):
        settings = get_settings()
        self.max_questions = settings.max_questions
        self.question_queue = []  # heapq: [(timestamp, [question1, question2, ...]), ...] 自动排序
        self.text = ""  # 当前讲课文本
        self._lock = Lock()  # 线程锁
        logger.info("QuestionProcessor 初始化完成")

    def append_text(self, text: str) -> None:
        """
        追加新的讲课文本片段

        Args:
            text: 新增的文本片段
        """
        self.text += text + " "
        preview = text[:50] + "..." if len(text) > 50 else text
        logger.info(f"教师新增讲课片段: {preview}")
        logger.debug(f"当前文本长度: {len(self.text)}字")

    def get_text(self) -> str:
        """获取当前文本"""
        return self.text.strip()

    def clear_text(self) -> None:
        """清空所有文本"""
        self.text = ""
        logger.info("文本已清空")

    def generate_questions(self, count: int = None) -> list[str]:
        """
        基于当前文本并发生成提问

        并发生成问题，将同一批问题作为一组按时间戳插入堆队列

        Args:
            count: 并发生成的问题数量，默认使用配置值

        Returns:
            生成的问题列表
        """
        settings = get_settings()

        if count is None:
            count = settings.concurrent_workers

        # 检查是否有文本
        text = self.get_text()
        if not text:
            logger.warning("当前无文本内容，跳过提问生成")
            return []

        logger.info(f"触发并发提问 (并发数: {count})")
        logger.debug(f"文本长度: {len(text)}字")

        batch_timestamp = time.time()  # 使用同一时间戳作为批次标识
        batch_questions = []

        def generate_single_question() -> str:
            """生成单个问题"""
            return generate_question(text)

        with ThreadPoolExecutor(max_workers=count) as executor:
            futures = [executor.submit(generate_single_question) for _ in range(count)]

            for future in futures:
                try:
                    question = future.result().strip()

                    batch_questions.append(question)

                except Exception as e:
                    logger.error(f"提问处理失败: {e}")

        # 将整批问题作为一个组入队
        if batch_questions:
            with self._lock:
                heapq.heappush(self.question_queue, (batch_timestamp, batch_questions))

                # 超过最大长度时删除最旧的（队头）
                if len(self.question_queue) > self.max_questions:
                    removed = heapq.heappop(self.question_queue)
                    removed_questions = ', '.join(removed[1])
                    logger.debug(f"队列已满，删除最旧批次: {removed_questions}")

            logger.info(f"批次 {batch_timestamp:.3f}: {len(batch_questions)} 个问题入队")

        logger.info(f"本轮生成 {len(batch_questions)} 个有效问题")
        return batch_questions

    def get_questions_flat(self) -> list[str]:
        """获取当前问题队列中的所有问题（展开后的问题列表）"""
        with self._lock:
            all_questions = []
            for _, question_batch in self.question_queue:
                all_questions.extend(question_batch)
            return all_questions

    def get_latest_question_random(self) -> str | None:
        """
        从最新批次的问题中随机选择一个

        Returns:
            随机选择的问题，如果没有问题则返回 None
        """
        with self._lock:
            if not self.question_queue:
                logger.debug("问题队列为空")
                return None

            # 获取最新的批次（heapq 队尾是最新）
            latest_batch = self.question_queue[-1]
            _, questions = latest_batch

            if not questions:
                logger.debug("最新批次无有效问题")
                return None

            selected = random.choice(questions)
            logger.info(f"从最新批次随机选择问题: {selected}")
            return selected

    def get_question_queue_raw(self) -> list[tuple[float, list[str]]]:
        """
        获取原始队列结构（包含时间戳和问题批次）

        Returns:
            [(timestamp, [question1, question2, ...]), ...]
        """
        with self._lock:
            return [(timestamp, questions.copy()) for timestamp, questions in self.question_queue]
