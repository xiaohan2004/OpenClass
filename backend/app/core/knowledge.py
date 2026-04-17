"""核心业务逻辑 - 知识点处理器"""

import json
import logging
import re
import time

from app.config import get_settings
from app.services.llm import generate_knowledge

logger = logging.getLogger(__name__)


class KnowledgeProcessor:
    """基于课堂上下文生成知识点。"""

    def __init__(self):
        settings = get_settings()
        self._config_refresh_interval_seconds = getattr(
            settings, "settings_refresh_interval_seconds", 3.0
        )
        self._config_loaded_at = time.monotonic()
        logger.info("KnowledgeProcessor 初始化完成")

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
        """从 LLM 输出中解析知识点 JSON 对象。"""
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
    def _normalize_difficulty(value) -> dict:
        if isinstance(value, dict):
            return value

        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return {}

            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass

            return {"level": stripped}

        if value is None:
            return {}

        return {"level": str(value)}

    def _normalize_item(self, item: object) -> dict | None:
        if not isinstance(item, dict):
            return None

        name = str(item.get("name", "")).strip()
        if not name:
            return None

        description = item.get("description")
        difficulty = self._normalize_difficulty(item.get("difficulty"))

        normalized = {
            "name": name,
            "description": str(description).strip() if description is not None else "",
            "difficulty": difficulty,
        }
        return normalized

    def generate_knowledge_point(
        self,
        context: str,
    ) -> dict | None:
        """基于当前课堂上下文生成单个知识点。"""
        self._sync_config()

        if not context:
            logger.warning("当前无课堂上下文，跳过知识点生成")
            return None

        logger.info("触发知识点生成")
        logger.debug("上下文长度: %d字", len(context))

        try:
            raw_text = generate_knowledge(context)
            parsed_item = self._parse_llm_json_object(raw_text)
            normalized = self._normalize_item(parsed_item) if parsed_item else None

            if normalized is None:
                logger.warning("未解析到有效知识点")
                return None

            logger.info("本轮生成 1 个有效知识点")
            return normalized

        except Exception as e:
            logger.error("知识点生成失败: %s", e)
            raise

    def generate_knowledge_points(
        self,
        context: str,
    ) -> dict | None:
        """向后兼容：保留原方法名，但仅返回单个知识点。"""
        return self.generate_knowledge_point(context=context)
