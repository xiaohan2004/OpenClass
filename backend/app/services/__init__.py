"""外部服务集成模块。"""

from .asr import ASRService, get_asr_service
from .tts import TTSService, get_tts_service

__all__ = [
    "ASRService",
    "TTSService",
    "get_asr_service",
    "get_tts_service",
]
