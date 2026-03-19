"""
核心业务逻辑 - 学生提问处理器
"""

import logging
import time
import random
from concurrent.futures import ThreadPoolExecutor

from app.config import get_settings
from app.services.llm import generate_question
from app.utils.timestamp_queue import TimestampQueue

logger = logging.getLogger(__name__)


class QuestionProcessor:
    """
    学生提问处理器

    被动接收文本，由外部控制提问触发时机
    并发生成问题并入队，使用 TimestampQueue 维护按时间戳排序的队列
    """

    def __init__(self):
        settings = get_settings()
        self.max_questions = settings.max_questions
        self._question_queue = TimestampQueue(max_size=settings.max_questions)
        self.text = ""  # 当前讲课文本
        logger.info("QuestionProcessor 初始化完成")

    def append_text(self, text: str) -> None:
        """
        追加新的讲课文本片段

        Args:
            text: 新增的文本片段
        """
        self.text += text + " "
        preview = text[:50] + "..." if len(text) > 50 else text
        logger.info("教师新增讲课片段: %s", preview)
        logger.debug("当前文本长度: %d字", len(self.text))

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

        logger.info("触发并发提问 (并发数: %d)", count)
        logger.debug("文本长度: %d字", len(text))

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
                    logger.error("提问处理失败: %s", e)

        # 将整批问题作为一个组入队
        if batch_questions:
            removed_batches = self._question_queue.add_batch(batch_timestamp, batch_questions)

            if removed_batches:
                for removed_timestamp, removed_questions in removed_batches:
                    logger.debug(
                        "队列已满，删除最旧批次 %.3f: %s",
                        removed_timestamp, ', '.join(removed_questions)
                    )

            logger.info("批次 %.3f: %d 个问题入队", batch_timestamp, len(batch_questions))

        logger.info("本轮生成 %d 个有效问题", len(batch_questions))
        return batch_questions

    def get_questions_flat(self) -> list[str]:
        """获取当前问题队列中的所有问题（展开后的问题列表）"""
        return self._question_queue.get_all_data_flat()

    def get_latest_question_random(self) -> str | None:
        """
        从最新批次的问题中随机选择一个

        Returns:
            随机选择的问题，如果没有问题则返回 None
        """
        latest_batch = self._question_queue.get_latest_batch()

        if latest_batch is None:
            logger.debug("问题队列为空")
            return None

        _, questions = latest_batch

        if not questions:
            logger.debug("最新批次无有效问题")
            return None

        selected = random.choice(questions)
        logger.info("从最新批次随机选择问题: %s", selected)
        return selected

    def get_question_queue_raw(self) -> list[tuple[float, list[str]]]:
        """
        获取原始队列结构（包含时间戳和问题批次）

        Returns:
            [(timestamp, [question1, question2, ...]), ...]
        """
        return self._question_queue.get_raw_queue()
