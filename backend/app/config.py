"""
配置管理 - 提示词、模型参数
"""

import time
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict
from sqlmodel import Session

from app.config_defaults import (
    DEFAULT_KEYWORD_KNOWLEDGE_QUIZ_TRIGGER_INTERVAL,
    DEFAULT_SETTINGS_VALUES,
    DEFAULT_SYSTEM_PROMPT_KNOWLEDGE,
    DEFAULT_SYSTEM_PROMPT_KEYWORDS,
    DEFAULT_SYSTEM_PROMPT_QUIZ,
    DEFAULT_SYSTEM_PROMPT_QUESTION,
    DEFAULT_SYSTEM_PROMPT_SEGMENT_SUMMARY,
    DEFAULT_SYSTEM_PROMPT_REPORT,
)
from app.db import get_engine
from app.db.config_store import load_settings_dict


class Settings(BaseModel):
    """应用配置。"""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # LLM 配置
    deepseek_api_key: str = DEFAULT_SETTINGS_VALUES["deepseek_api_key"]
    deepseek_base_url: str = DEFAULT_SETTINGS_VALUES["deepseek_base_url"]
    qwen_api_key: str = DEFAULT_SETTINGS_VALUES["qwen_api_key"]

    # 模型参数
    model_name: str = DEFAULT_SETTINGS_VALUES["model_name"]
    max_tokens: int = DEFAULT_SETTINGS_VALUES["max_tokens"]
    temperature: float = DEFAULT_SETTINGS_VALUES["temperature"]

    # 提问队列配置
    max_questions: int = DEFAULT_SETTINGS_VALUES["max_questions"]

    # 并发配置
    question_concurrent_workers: int = DEFAULT_SETTINGS_VALUES[
        "question_concurrent_workers"
    ]

    # 上下文维护配置
    recent_lecture_window: int = DEFAULT_SETTINGS_VALUES["recent_lecture_window"]
    history_summary_window: int = DEFAULT_SETTINGS_VALUES["history_summary_window"]
    keyword_knowledge_quiz_trigger_interval: int = DEFAULT_SETTINGS_VALUES[
        "keyword_knowledge_quiz_trigger_interval"
    ]
    settings_refresh_interval_seconds: float = DEFAULT_SETTINGS_VALUES[
        "settings_refresh_interval_seconds"
    ]
    keyword_knowledge_quiz_trigger_interval: int = DEFAULT_KEYWORD_KNOWLEDGE_QUIZ_TRIGGER_INTERVAL

    # 数据库配置
    database_url: str = DEFAULT_SETTINGS_VALUES["database_url"]
    database_echo: bool = DEFAULT_SETTINGS_VALUES["database_echo"]

    # 提示词配置
    system_prompt_question: str = DEFAULT_SETTINGS_VALUES["system_prompt_question"]
    system_prompt_segment_summary: str = DEFAULT_SETTINGS_VALUES[
        "system_prompt_segment_summary"
    ]
    system_prompt_keywords: str = DEFAULT_SETTINGS_VALUES["system_prompt_keywords"]
    system_prompt_knowledge: str = DEFAULT_SETTINGS_VALUES["system_prompt_knowledge"]
    system_prompt_quiz: str = DEFAULT_SETTINGS_VALUES["system_prompt_quiz"]
    system_prompt_report: str = DEFAULT_SETTINGS_VALUES["system_prompt_report"]
    # ASR 配置
    asr_model: str = DEFAULT_SETTINGS_VALUES["asr_model"]
    asr_base_url: str = DEFAULT_SETTINGS_VALUES["asr_base_url"]
    asr_enable_itn: bool = DEFAULT_SETTINGS_VALUES["asr_enable_itn"]
    asr_language: str = DEFAULT_SETTINGS_VALUES["asr_language"]

    # TTS 配置
    tts_model: str = DEFAULT_SETTINGS_VALUES["tts_model"]
    tts_base_url: str = DEFAULT_SETTINGS_VALUES["tts_base_url"]
    tts_voice: str = DEFAULT_SETTINGS_VALUES["tts_voice"]
    tts_language_type: str = DEFAULT_SETTINGS_VALUES["tts_language_type"]
    tts_instructions: str = DEFAULT_SETTINGS_VALUES["tts_instructions"]
    tts_optimize_instructions: bool = DEFAULT_SETTINGS_VALUES[
        "tts_optimize_instructions"
    ]


@dataclass
class _SettingsCache:
    settings: Settings | None = None
    loaded_at: float = 0.0

    def clear(self) -> None:
        self.settings = None
        self.loaded_at = 0.0


_settings_cache = _SettingsCache()


def _build_settings() -> Settings:
    """从数据库读取并构建配置快照。"""
    with Session(get_engine()) as db:
        settings_dict = load_settings_dict(db)
    return Settings(**settings_dict)


def refresh_settings_cache() -> None:
    """清空配置缓存。"""
    _settings_cache.clear()


def get_settings() -> Settings:
    """获取配置快照，按刷新间隔自动从数据库重新加载。"""
    if _settings_cache.settings is not None:
        elapsed = time.monotonic() - _settings_cache.loaded_at
        if elapsed < _settings_cache.settings.settings_refresh_interval_seconds:
            return _settings_cache.settings

    settings = _build_settings()
    _settings_cache.settings = settings
    _settings_cache.loaded_at = time.monotonic()
    return settings


def _cache_clear() -> None:
    refresh_settings_cache()


get_settings.cache_clear = _cache_clear  # type: ignore[attr-defined]


SYSTEM_PROMPT_QUESTION = DEFAULT_SYSTEM_PROMPT_QUESTION
SYSTEM_PROMPT_SEGMENT_SUMMARY = DEFAULT_SYSTEM_PROMPT_SEGMENT_SUMMARY
SYSTEM_PROMPT_KEYWORDS = DEFAULT_SYSTEM_PROMPT_KEYWORDS
SYSTEM_PROMPT_KNOWLEDGE = DEFAULT_SYSTEM_PROMPT_KNOWLEDGE
SYSTEM_PROMPT_QUIZ = DEFAULT_SYSTEM_PROMPT_QUIZ
SYSTEM_PROMPT_REPORT = DEFAULT_SYSTEM_PROMPT_REPORT
