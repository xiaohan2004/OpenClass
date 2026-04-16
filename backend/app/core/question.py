"""
核心业务逻辑 - 学生提问处理器

基于统一课堂上下文，实现并发生成学生提问，维护提问队列
"""

import logging
import time
import random
from concurrent.futures import ThreadPoolExecutor

from app.config import get_settings
from app.services.llm import generate_question
from app.utils.timestamp_queue import QuestionTimestampQueue

logger = logging.getLogger(__name__)


class QuestionProcessor:
    """
    学生提问处理器

    基于统一课堂上下文被动接收文本，由外部控制提问触发时机
    并发生成问题并入队，使用 TimestampQueue 维护按时间戳排序的队列
    """

    def __init__(self):
        settings = get_settings()
        self.max_questions = settings.max_questions
        self._question_queue = QuestionTimestampQueue(max_size=settings.max_questions)
        self._config_refresh_interval_seconds = getattr(
            settings, "settings_refresh_interval_seconds", 3.0
        )
        self._config_loaded_at = time.monotonic()
        logger.info("QuestionProcessor 初始化完成")

    def _sync_config(self) -> None:
        """同步热更新配置。"""
        elapsed = time.monotonic() - self._config_loaded_at
        if elapsed < self._config_refresh_interval_seconds:
            return

        settings = get_settings()
        max_questions = getattr(settings, "max_questions", self.max_questions)
        if (
            isinstance(max_questions, int)
            and max_questions > 0
            and max_questions != self.max_questions
        ):
            self.max_questions = max_questions
            self._question_queue.set_max_size(max_questions)

        self._config_refresh_interval_seconds = getattr(
            settings,
            "settings_refresh_interval_seconds",
            self._config_refresh_interval_seconds,
        )
        self._config_loaded_at = time.monotonic()

    def generate_questions(self, context: str, count: int = None) -> list[str]:
        """
        基于当前课堂上下文并发生成提问

        Args:
            context: 课堂上下文文本，由外部获取并传入
            count: 并发生成的问题数量，默认使用配置值

        Returns:
            生成的问题列表
        """
        self._sync_config()
        settings = get_settings()

        if count is None:
            count = settings.question_concurrent_workers

        if not context:
            logger.warning("当前无课堂上下文，跳过提问生成")
            return []

        logger.info("触发并发提问 (并发数: %d)", count)
        logger.debug("上下文长度: %d字", len(context))

        batch_timestamp = time.time()
        batch_questions = []

        with ThreadPoolExecutor(max_workers=count) as executor:
            futures = [
                executor.submit(generate_question, context) for _ in range(count)
            ]

            for future in futures:
                future_exc = future.exception()
                if future_exc is not None:
                    logger.error("提问处理失败: %s", future_exc)
                    continue

                question = future.result().strip()
                if question:
                    batch_questions.append(question)

        if batch_questions:
            removed_batches = self._question_queue.add(batch_timestamp, batch_questions)

            if removed_batches:
                for removed_timestamp, removed_questions in removed_batches:
                    logger.debug(
                        "队列已满，删除最旧批次 %.3f: %s",
                        removed_timestamp,
                        ", ".join(removed_questions),
                    )

            logger.info(
                "批次 %.3f: %d 个问题入队", batch_timestamp, len(batch_questions)
            )

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
        self._sync_config()
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
