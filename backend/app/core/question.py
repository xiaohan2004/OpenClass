"""
核心业务逻辑 - 学生提问处理器

基于统一课堂上下文，实现并发生成学生提问，维护提问队列
"""

import json
import logging
import time
import random
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.config import get_settings
from app.services.llm import evaluate_question_quality, generate_question
from app.utils.timestamp_queue import QuestionTimestampQueue

logger = logging.getLogger(__name__)

RECENCY_WEIGHT = 0.55
QUALITY_WEIGHT = 0.45
QUESTION_QUALITY_DIMENSION_WEIGHTS = {
    "relevance": 0.35,
    "value": 0.25,
    "clarity": 0.15,
    "authenticity": 0.15,
    "brevity": 0.10,
}


@dataclass(frozen=True)
class ScoredQuestion:
    text: str
    score: float


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

    def generate_scored_questions(
        self, context: str, count: int = None
    ) -> list[ScoredQuestion]:
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
        batch_questions: list[ScoredQuestion] = []

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
                    score = self._evaluate_question_score(question, context)
                    batch_questions.append(ScoredQuestion(text=question, score=score))

        if batch_questions:
            removed_batches = self._question_queue.add(batch_timestamp, batch_questions)

            if removed_batches:
                for removed_timestamp, removed_questions in removed_batches:
                    logger.debug(
                        "队列已满，删除最旧批次 %.3f: %s",
                        removed_timestamp,
                        ", ".join(
                            getattr(question, "text", str(question))
                            for question in removed_questions
                        ),
                    )

            logger.info(
                "批次 %.3f: %d 个问题入队", batch_timestamp, len(batch_questions)
            )

        logger.info("本轮生成 %d 个有效问题", len(batch_questions))
        return batch_questions

    def generate_questions(self, context: str, count: int = None) -> list[str]:
        """兼容旧调用方：生成带评分问题，但只返回文本列表。"""
        return [
            question.text
            for question in self.generate_scored_questions(context=context, count=count)
        ]

    def _evaluate_question_score(self, question: str, context: str) -> float:
        """评估问题质量，失败时返回低默认分。"""
        try:
            raw_result = evaluate_question_quality(question, context)
            return self._parse_quality_score(raw_result)
        except Exception as exc:
            logger.warning("问题质量评分失败，使用默认低分: %s", exc)
            return 0.0

    def _parse_quality_score(self, raw_result: str) -> float:
        """从 LLM 返回中尽力解析 score，并归一到 -1.0-1.0。"""
        payload = self._parse_quality_payload(raw_result)
        score = payload.get("score")
        if not isinstance(score, (int, float)):
            raise ValueError("评分 JSON 缺少数字 score 字段")

        reported_score = float(score)
        calculated_score = self._calculate_quality_score_from_dimensions(payload)
        if calculated_score is None:
            normalized_score = self._apply_fatal_dimension(reported_score, payload)
        else:
            normalized_score = calculated_score
            if abs(reported_score - calculated_score) > 0.02:
                logger.warning(
                    "LLM 问题评分总分与维度不一致: reported=%.3f calculated=%.3f；后端始终以维度重算分为准",
                    reported_score,
                    calculated_score,
                )
        normalized_score = max(-1.0, min(1.0, normalized_score))
        return float(
            Decimal(str(normalized_score)).quantize(
                Decimal("0.001"), rounding=ROUND_HALF_UP
            )
        )

    def _calculate_quality_score_from_dimensions(
        self, payload: dict[str, Any]
    ) -> float | None:
        """按 fatal + 五个正向维度重算最终分；维度不完整时返回 None。"""
        dimensions = payload.get("dimensions")
        if not isinstance(dimensions, dict):
            return None

        fatal = dimensions.get("fatal")
        if not isinstance(fatal, (int, float)):
            return None
        fatal_score = -1.0 if float(fatal) < 0 else 0.0

        base_score = 0.0
        for dimension_name, weight in QUESTION_QUALITY_DIMENSION_WEIGHTS.items():
            dimension_score = dimensions.get(dimension_name)
            if not isinstance(dimension_score, (int, float)):
                return None
            clamped_dimension_score = max(0.0, min(1.0, float(dimension_score)))
            base_score += weight * clamped_dimension_score

        return base_score + fatal_score

    def _apply_fatal_dimension(self, score: float, payload: dict[str, Any]) -> float:
        """fatal 维度为 -1 时，确保最终分数带上致命惩罚。"""
        dimensions = payload.get("dimensions")
        if not isinstance(dimensions, dict):
            return score

        fatal = dimensions.get("fatal")
        if not isinstance(fatal, (int, float)) or fatal >= 0:
            return score

        if score < 0:
            return score

        return score + max(-1.0, float(fatal))

    def _parse_quality_payload(self, raw_result: str) -> dict[str, Any]:
        if not isinstance(raw_result, str) or not raw_result.strip():
            raise ValueError("评分结果为空")

        text = raw_result.strip()
        candidates = [text]

        if text.startswith("```"):
            stripped = text.strip("`").strip()
            if stripped.lower().startswith("json"):
                stripped = stripped[4:].strip()
            candidates.append(stripped)

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and start < end:
            candidates.append(text[start : end + 1])

        last_error: Exception | None = None
        for candidate in candidates:
            try:
                payload = json.loads(candidate)
                if isinstance(payload, dict):
                    return payload
            except json.JSONDecodeError as exc:
                last_error = exc

        raise ValueError(f"无法解析评分 JSON: {last_error}")

    def get_questions_flat(self) -> list[str]:
        """获取当前问题队列中的所有问题（展开后的问题列表）"""
        return self._question_queue.get_all_data_flat()

    def get_latest_question_random(self) -> str | None:
        """从当前队列中按新鲜度和质量分综合选择一个问题。"""
        self._sync_config()
        batches = self._question_queue.get_batches()

        if not batches:
            logger.debug("问题队列为空")
            return None

        batch_count = len(batches)
        best_score = -1.0
        best_questions: list[ScoredQuestion] = []
        skipped_fatal_count = 0

        for batch_index in range(batch_count - 1, -1, -1):
            _, questions = batches[batch_index]
            recency_score = (
                1.0 if batch_count == 1 else batch_index / (batch_count - 1)
            )
            max_possible_score = RECENCY_WEIGHT * recency_score + QUALITY_WEIGHT

            if best_score >= 0 and max_possible_score < best_score:
                logger.debug(
                    "旧批次理论最高分 %.3f 低于当前最佳 %.3f，提前停止扫描",
                    max_possible_score,
                    best_score,
                )
                break

            for question in questions:
                scored_question = self._coerce_scored_question(question)
                if scored_question.score < 0:
                    skipped_fatal_count += 1
                    continue

                combined_score = (
                    RECENCY_WEIGHT * recency_score
                    + QUALITY_WEIGHT * scored_question.score
                )
                if combined_score > best_score:
                    best_score = combined_score
                    best_questions = [scored_question]
                elif combined_score == best_score:
                    best_questions.append(scored_question)

        if not best_questions:
            logger.debug("问题队列无可提问问题，已跳过 %d 个负分问题", skipped_fatal_count)
            return None

        selected = self._coerce_scored_question(random.choice(best_questions))
        self._question_queue.remove_first_text(selected.text)
        logger.info(
            "按新鲜度和质量分选择问题: %s (score=%.3f, combined=%.3f)",
            selected.text,
            selected.score,
            best_score,
        )
        return selected.text

    def _coerce_scored_question(self, question: object) -> ScoredQuestion:
        if isinstance(question, ScoredQuestion):
            return question
        return ScoredQuestion(text=str(question), score=0.0)
