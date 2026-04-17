"""
核心业务逻辑 - 关键词处理器

基于统一课堂上下文和历史摘要的关键词提取服务
"""

import logging
import json
import re
import time

from app.config import get_settings
from app.core.keyword_extraction_algorithm import KeywordExtractor, KeywordScore
from app.services.llm import generate_keywords

logger = logging.getLogger(__name__)


class KeywordProcessor:
    """
    关键词处理器

    管理关键词提取的配置和缓存，提供统一的关键词提取接口
    """

    def __init__(self):
        settings = get_settings()
        self._config_refresh_interval_seconds = getattr(
            settings, "settings_refresh_interval_seconds", 3.0
        )
        self._config_loaded_at = time.monotonic()

        # 初始化提取器
        self.extractor = self._create_extractor(settings)
        logger.info("KeywordProcessor 初始化完成")

    def _create_extractor(self, settings) -> KeywordExtractor:
        """从配置创建KeywordExtractor实例"""
        embedding_model = getattr(
            settings, "keyword_embedding_model", "all-MiniLM-L6-v2"
        )
        top_n_tfidf = getattr(settings, "keyword_top_n_tfidf", 20)
        top_n_keybert = getattr(settings, "keyword_top_n_keybert", 20)
        top_m_history = getattr(settings, "keyword_top_m_history", 15)
        top_k_output = getattr(settings, "keyword_top_k_output", 10)

        return KeywordExtractor(
            embedding_model=embedding_model,
            top_n_tfidf=top_n_tfidf,
            top_n_keybert=top_n_keybert,
            top_m_history=top_m_history,
            top_k_output=top_k_output,
        )

    def _sync_config(self) -> None:
        """同步热更新配置。"""
        elapsed = time.monotonic() - self._config_loaded_at
        if elapsed < self._config_refresh_interval_seconds:
            return

        settings = get_settings()
        # 重新创建提取器以获取最新配置
        self.extractor = self._create_extractor(settings)
        self._config_refresh_interval_seconds = getattr(
            settings,
            "settings_refresh_interval_seconds",
            self._config_refresh_interval_seconds,
        )
        self._config_loaded_at = time.monotonic()
        logger.debug("关键词处理器配置已同步")

    def extract_keywords(
        self,
        transcript: str,
        history_summary: str | None = None,
    ) -> list[str]:
        """
        提取关键词

        Args:
            transcript: 近期讲解文本（课堂语音转写文本，可能存在噪声）
            history_summary: 历史要点摘要（可选）

        Returns:
            关键词列表（按重要性降序排列）
        """
        self._sync_config()

        if not transcript:
            logger.warning("输入的讲解文本为空")
            return []

        logger.info("触发关键词提取，transcript长度=%d", len(transcript))

        try:
            keyword_scores = self.extractor.extract_keywords(
                transcript=transcript,
                history_summary=history_summary,
            )
            keywords = [score.keyword for score in keyword_scores]

            if keywords:
                logger.info("成功提取%d个关键词", len(keywords))
            else:
                logger.warning("未提取到关键词")

            return keywords

        except Exception as e:
            logger.error("关键词提取失败: %s", e)
            raise

    def extract_keywords_with_scores(
        self,
        transcript: str,
        history_summary: str | None = None,
    ) -> list[KeywordScore]:
        """
        提取关键词并返回详细分数

        Args:
            transcript: 近期讲解文本
            history_summary: 历史要点摘要（可选）

        Returns:
            KeywordScore列表（包含各项分数）
        """
        self._sync_config()

        if not transcript:
            logger.warning("输入的讲解文本为空")
            return []

        logger.debug("触发详细关键词提取，transcript长度=%d", len(transcript))

        try:
            keyword_scores = self.extractor.extract_keywords(
                transcript=transcript,
                history_summary=history_summary,
            )
            return keyword_scores

        except Exception as e:
            logger.error("详细关键词提取失败: %s", e)
            raise

    def extract_keywords_with_details(
        self,
        transcript: str,
        history_summary: str | None = None,
    ) -> dict:
        """
        提取关键词并返回调试详情

        Args:
            transcript: 近期讲解文本
            history_summary: 历史要点摘要（可选）

        Returns:
            包含关键词和各项分数的字典
        """
        self._sync_config()

        if not transcript:
            return {"keywords": [], "details": []}

        logger.debug("触发关键词详情提取")

        try:
            return self.extractor.extract_keywords_with_details(
                transcript=transcript,
                history_summary=history_summary,
            )

        except Exception as e:
            logger.error("关键词详情提取失败: %s", e)
            raise

    @staticmethod
    def _parse_llm_keywords(raw_text: str, limit: int) -> list[str]:
        """将 LLM 返回文本解析为关键词列表。"""
        text = (raw_text or "").strip()
        if not text:
            return []

        def _normalize(items: list[str]) -> list[str]:
            normalized: list[str] = []
            for item in items:
                candidate = item.strip().strip("\"'[]")
                candidate = re.sub(r"^\d+[\.、\)\s-]*", "", candidate).strip()
                if candidate and candidate not in normalized:
                    normalized.append(candidate)
                if len(normalized) >= limit:
                    break
            return normalized

        def _try_parse_json_array(candidate: str) -> list[str] | None:
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, list):
                    return _normalize([str(item) for item in parsed])
            except Exception:
                return None
            return None

        parsed_keywords = _try_parse_json_array(text)
        if parsed_keywords is not None:
            return parsed_keywords

        code_block_matches = re.findall(r"```(?:json)?\s*(\[[\s\S]*?\])\s*```", text)
        for block in code_block_matches:
            parsed_keywords = _try_parse_json_array(block.strip())
            if parsed_keywords is not None:
                return parsed_keywords

        array_match = re.search(r"\[[\s\S]*\]", text)
        if array_match:
            parsed_keywords = _try_parse_json_array(array_match.group(0).strip())
            if parsed_keywords is not None:
                return parsed_keywords

        unified = (
            text.replace("，", ",")
            .replace("、", ",")
            .replace("；", ",")
            .replace(";", ",")
            .replace("\n", ",")
        )
        return _normalize([part for part in unified.split(",") if part.strip()])

    def extract_keywords_llm(
        self,
        transcript: str,
        history_summary: str | None = None,
        limit: int = 10,
    ) -> list[str]:
        """
        直接使用 LLM 提取关键词。

        Args:
            transcript: 近期讲解文本
            history_summary: 历史要点摘要（可选）
            limit: 返回关键词最大数量

        Returns:
            关键词列表（去重后，按模型输出顺序）
        """
        self._sync_config()

        if not transcript:
            logger.warning("输入的讲解文本为空")
            return []

        keyword_limit = max(1, int(limit))
        context = transcript.strip()
        if history_summary:
            context = (
                f"【历史要点】\n{history_summary.strip()}\n\n"
                f"【近期讲解】\n{transcript.strip()}"
            )

        try:
            raw_keywords = generate_keywords(context, limit=keyword_limit).strip()
            keywords = self._parse_llm_keywords(raw_keywords, keyword_limit)
            logger.info("LLM关键词提取完成：%d个", len(keywords))
            return keywords
        except Exception as e:
            logger.error("LLM关键词提取失败: %s", e)
            raise
