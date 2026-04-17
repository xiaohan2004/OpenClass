"""核心业务逻辑 - 小测处理器"""

import json
import logging
import re
import time

from app.config import get_settings
from app.services.llm import generate_quiz

logger = logging.getLogger(__name__)


class QuizProcessor:
    """基于课堂上下文生成小测题目。"""

    def __init__(self):
        settings = get_settings()
        self._config_refresh_interval_seconds = getattr(
            settings, "settings_refresh_interval_seconds", 3.0
        )
        self._config_loaded_at = time.monotonic()
        logger.info("QuizProcessor 初始化完成")

    def _sync_config(self) -> None:
        """同步热更新配置。"""
        elapsed = time.monotonic() - self._config_loaded_at
        if elapsed < self._config_refresh_interval_seconds:
            return

        settings = get_settings()
        self._config_refresh_interval_seconds = getattr(
            settings,
            "settings_refresh_interval_seconds",
            self._config_refresh_interval_seconds,
        )
        self._config_loaded_at = time.monotonic()

    @staticmethod
    def _parse_llm_json_object(raw_text: str) -> dict | None:
        """从 LLM 输出中解析小测 JSON 对象。"""
        text = (raw_text or "").strip()
        if not text:
            return None

        def _try_parse(candidate: str):
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
                if isinstance(parsed, list) and parsed:
                    first_item = parsed[0]
                    if isinstance(first_item, dict):
                        return first_item
            except Exception:
                return None
            return None

        parsed = _try_parse(text)
        if parsed is not None:
            return parsed

        code_blocks = re.findall(
            r"```(?:json)?\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```", text
        )
        for block in code_blocks:
            parsed = _try_parse(block.strip())
            if parsed is not None:
                return parsed

        object_match = re.search(r"\{[\s\S]*\}", text)
        if object_match:
            parsed = _try_parse(object_match.group(0).strip())
            if parsed is not None:
                return parsed

        array_match = re.search(r"\[[\s\S]*\]", text)
        if array_match:
            parsed = _try_parse(array_match.group(0).strip())
            if parsed is not None:
                return parsed

        return None

    @staticmethod
    def _normalize_item(item: object) -> dict | None:
        if not isinstance(item, dict):
            return None

        question = str(item.get("question", "")).strip()
        if not question:
            return None

        quiz_type = str(item.get("type", "")).strip() or "short_answer"
        answer = item.get("answer")
        explanation = item.get("explanation")

        normalized = {
            "type": quiz_type,
            "question": question,
            "answer": str(answer).strip() if answer is not None else "",
            "explanation": str(explanation).strip() if explanation is not None else "",
        }

        options = item.get("options")
        if isinstance(options, list) and options:
            normalized["options"] = [
                str(option).strip() for option in options if str(option).strip()
            ]

        return normalized

    def generate_quiz_item(
        self,
        context: str,
    ) -> dict | None:
        """基于当前课堂上下文生成单个小测题目。"""
        self._sync_config()

        if not context:
            logger.warning("当前无课堂上下文，跳过小测生成")
            return None

        logger.info("触发小测生成")
        logger.debug("上下文长度: %d字", len(context))

        try:
            raw_text = generate_quiz(context)
            parsed_item = self._parse_llm_json_object(raw_text)
            normalized = self._normalize_item(parsed_item) if parsed_item else None

            if normalized is None:
                logger.warning("未解析到有效小测题目")
                return None

            logger.info("本轮生成 1 个有效小测题目")
            return normalized

        except Exception as e:
            logger.error("小测生成失败: %s", e)
            raise

    def generate_quiz_items(
        self,
        context: str,
    ) -> dict | None:
        """向后兼容：保留原方法名，但仅返回单个题目。"""
        return self.generate_quiz_item(context=context)
