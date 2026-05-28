"""
核心业务逻辑 - 关键词处理器

基于统一课堂上下文和历史摘要的关键词提取服务
"""

import logging
import json
import os
import re
import time

from app.config import get_settings
from app.services.llm import generate_keywords

logger = logging.getLogger(__name__)

_DISABLE_KEYWORD_ALGORITHM = os.environ.get(
    "DISABLE_KEYWORD_ALGORITHM",
    "",
).lower() in ("1", "true", "yes")

# 程序启动阶段加载重量级依赖，仅在启用传统算法时导入
if _DISABLE_KEYWORD_ALGORITHM:
    _keyword_extraction_algorithm = None
else:
    _t_keyword_algorithm = time.perf_counter()
    from . import keyword_extraction_algorithm as _keyword_extraction_algorithm
    logger.info(
        "[启动耗时] keyword.py | keyword_extraction_algorithm 导入完成 | 耗时=%.3fs",
        time.perf_counter() - _t_keyword_algorithm,
    )


def _get_keyword_extraction_module():
    """返回启动时加载的关键词提取算法模块。"""
    return _keyword_extraction_algorithm


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
        self.extractor = None
        if not _DISABLE_KEYWORD_ALGORITHM:
            self.extractor = self._create_extractor(settings)
        logger.info("KeywordProcessor 初始化完成")

    def _create_extractor(self, settings):
        """从配置创建KeywordExtractor实例"""
        mod = _get_keyword_extraction_module()
        if mod is None:
            raise RuntimeError(
                "传统算法关键词提取已被 DISABLE_KEYWORD_ALGORITHM 禁用"
            )
        embedding_model = getattr(
            settings, "keyword_embedding_model", "all-MiniLM-L6-v2"
        )
        top_n_tfidf = getattr(settings, "keyword_top_n_tfidf", 20)
        top_n_keybert = getattr(settings, "keyword_top_n_keybert", 20)
        top_m_history = getattr(settings, "keyword_top_m_history", 15)
        top_k_output = getattr(settings, "keyword_top_k_output", 10)

        return mod.KeywordExtractor(
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
        if _DISABLE_KEYWORD_ALGORITHM:
            self.extractor = None
            self._config_refresh_interval_seconds = getattr(
                settings,
                "settings_refresh_interval_seconds",
                self._config_refresh_interval_seconds,
            )
            self._config_loaded_at = time.monotonic()
            return

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

        if _DISABLE_KEYWORD_ALGORITHM:
            logger.info("传统算法关键词提取已禁用，跳过")
            return []

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

    def extract_keywords_algorithm(
        self,
        transcript: str,
        history_summary: str | None = None,
    ) -> list[str]:
        """
        使用本地算法提取关键词。

        该方法作为主流程后台算法提取的显式入口，区别于
        extract_keywords_llm 的大模型提取路径。

        当 DISABLE_KEYWORD_ALGORITHM=1 时返回空列表。
        """
        if _DISABLE_KEYWORD_ALGORITHM:
            logger.info("传统算法关键词提取已禁用，跳过")
            return []
        return self.extract_keywords(transcript, history_summary)

    def extract_keywords_with_scores(
        self,
        transcript: str,
        history_summary: str | None = None,
    ) -> list:
        """
        提取关键词并返回详细分数

        Args:
            transcript: 近期讲解文本
            history_summary: 历史要点摘要（可选）

        Returns:
            KeywordScore列表（包含各项分数）
        """
        self._sync_config()

        if _DISABLE_KEYWORD_ALGORITHM:
            logger.info("传统算法关键词详细提取已禁用，跳过")
            return []

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

        if _DISABLE_KEYWORD_ALGORITHM:
            logger.info("传统算法关键词详情提取已禁用，跳过")
            return {"keywords": [], "details": []}

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
        # LLM 提示词由 generate_keywords 内部的 get_settings() 按刷新间隔读取；
        # 这里不调用 _sync_config()，避免 LLM 路径依赖传统算法 extractor。
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
