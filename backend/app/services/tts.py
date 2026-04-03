"""TTS 服务框架。"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_tts_service: Optional[TTSService] = None


def get_tts_service() -> TTSService:
    """获取 TTS 服务单例。"""
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service

class TTSService:
    """
    文字转音频服务。

    当前只保留稳定的服务接口，真正的语音合成逻辑后续再接入。
    """

    def synthesize(self, text: str,) -> bytes:
        """传入文字，返回音频结果。"""
        normalized_text = " ".join(text.split()).strip()
        if not normalized_text:
            raise ValueError("text 不能为空")

        # 这里只返回可追踪的占位字节，方便后续接口联调。
        audio_bytes = normalized_text.encode("utf-8")

        return audio_bytes

def synthesize_text(self, text: str) -> bytes:
    """外部调用接口，传入文字，返回音频字节。"""
    return self.synthesize(text)