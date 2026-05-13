"""外部服务集成模块。"""

from .asr import ASRService, get_asr_service
from .llm import (
    evaluate_question_quality,
    generate_with_prompt,
    generate_keywords,
    generate_knowledge,
    generate_quiz,
    generate_question,
    generate_segment_summary,
    get_llm_client,
)
from .tts import TTSService, get_tts_service

__all__ = [
    "ASRService",
    "TTSService",
    "generate_question",
    "evaluate_question_quality",
    "generate_with_prompt",
    "generate_keywords",
    "generate_knowledge",
    "generate_quiz",
    "generate_segment_summary",
    "get_asr_service",
    "get_llm_client",
    "get_tts_service",
]
