"""ASR 服务框架。"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_asr_service: Optional[ASRService] = None


def get_asr_service() -> ASRService:
    """获取 ASR 服务单例。"""
    global _asr_service
    if _asr_service is None:
        _asr_service = ASRService()
    return _asr_service

class ASRService:
    """
    音频转文字服务。

    当前只提供稳定的调用框架和占位实现，后续可以在 `transcribe`
    内部接入真实的本地模型、云服务或流式 ASR。
    """

    def transcribe(self, audio_bytes: bytes) -> str:
        """传入音频字节，返回文字结果。"""
        if not audio_bytes:
            raise ValueError("audio_bytes 不能为空")

        text = "这是一个占位的 ASR 转录结果，实际实现需要接入真实的 ASR 模型或服务。"

        return text

def transcribe_audio(self, audio_bytes: bytes) -> str:
    """外部调用接口，传入音频字节，返回转录文本。"""
    return self.transcribe(audio_bytes)
