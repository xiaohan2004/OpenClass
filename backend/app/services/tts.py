"""TTS 服务实现。"""

from __future__ import annotations

import logging
import time
from functools import lru_cache
from typing import Any, Optional
from urllib.request import urlopen

import dashscope

from app.config import get_settings
from app.services.metrics import record_service_usage
from app.utils.request_capture import capture_request
from app.utils.time import now_ts
from app.utils.usage import extract_usage, usage_value

logger = logging.getLogger(__name__)


class _SettingsProxy:
    def __init__(self) -> None:
        self._overrides: dict[str, object] = {}

    def __getattr__(self, item: str) -> object:
        if item in self._overrides:
            return self._overrides[item]
        return getattr(get_settings(), item)

    def __setattr__(self, key: str, value: object) -> None:
        if key == "_overrides":
            object.__setattr__(self, key, value)
            return
        self._overrides[key] = value

    def __delattr__(self, item: str) -> None:
        self._overrides.pop(item, None)


settings = _SettingsProxy()


@lru_cache(maxsize=8)
def _build_tts_service(
    model: str,
    base_url: str,
    voice: str,
    language_type: str,
    instructions: str,
    optimize_instructions: bool,
) -> "TTSService":
    return TTSService(
        model=model,
        voice=voice,
        language_type=language_type,
        instructions=instructions,
        optimize_instructions=optimize_instructions,
        base_url=base_url,
    )


def get_tts_service() -> "TTSService":
    """获取 TTS 服务单例"""
    runtime_settings = get_settings()
    return _build_tts_service(
        runtime_settings.tts_model,
        runtime_settings.tts_base_url,
        runtime_settings.tts_voice,
        runtime_settings.tts_language_type,
        runtime_settings.tts_instructions,
        runtime_settings.tts_optimize_instructions,
    )


def _extract_audio_url(response: Any) -> str:
    """从 DashScope 响应中提取音频 URL"""
    output = getattr(response, "output", None)
    if output is None:
        return ""

    audio = getattr(output, "audio", None)
    if audio is not None:
        url = getattr(audio, "url", None)
        if isinstance(url, str) and url.strip():
            return url.strip()

    if isinstance(output, dict):
        audio_dict = output.get("audio")
        if isinstance(audio_dict, dict):
            url = audio_dict.get("url")
            if isinstance(url, str) and url.strip():
                return url.strip()

    return ""


class TTSService:
    """文字转语音服务"""

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        voice: str | None = None,
        language_type: str | None = None,
        instructions: Optional[str] = None,
        optimize_instructions: bool = False,
        base_url: Optional[str] = None,
    ) -> None:
        runtime_settings = get_settings()
        self.model = model or runtime_settings.tts_model
        self.voice = voice or runtime_settings.tts_voice
        self.language_type = language_type or runtime_settings.tts_language_type
        self.instructions = (
            instructions
            if instructions is not None
            else runtime_settings.tts_instructions
        )
        self.optimize_instructions = (
            optimize_instructions or runtime_settings.tts_optimize_instructions
        )
        self.base_url = base_url or runtime_settings.tts_base_url

    def synthesize_to_url(self, text: str) -> str:
        """合成文本并返回音频 URL"""
        normalized_text = " ".join(text.split()).strip()
        if not normalized_text:
            raise ValueError("text 不能为空")

        request_start_time = now_ts()
        start_time = time.perf_counter()
        api_key = settings.qwen_api_key
        if not api_key:
            raise ValueError("Qwen_API_Key 未配置，无法调用 TTS 服务")

        dashscope.base_http_api_url = self.base_url

        call_kwargs: dict[str, Any] = {
            "model": self.model,
            "api_key": api_key,
            "text": normalized_text,
            "voice": self.voice,
            "language_type": self.language_type,
            "stream": False,
        }
        if self.instructions:
            call_kwargs["instructions"] = self.instructions
            call_kwargs["optimize_instructions"] = self.optimize_instructions

        try:
            response, request = capture_request(dashscope.MultiModalConversation.call)(
                **call_kwargs
            )
        except Exception as exc:
            request = getattr(exc, "request_record", None)
            logger.exception("TTS 合成失败")
            record_service_usage(
                service_type="tts",
                request_model_name=self.model,
                input_value=0,
                output_value=0,
                start_time=request_start_time,
                latency=int((time.perf_counter() - start_time) * 1000),
                status="failed",
                error=str(exc),
                request_content=request,
            )
            raise RuntimeError(f"TTS 合成失败: {exc}") from exc

        status_code = getattr(response, "status_code", None)
        if status_code is not None and status_code != 200:
            message = getattr(response, "message", "未知错误")
            record_service_usage(
                service_type="tts",
                request_model_name=self.model,
                input_value=0,
                output_value=0,
                start_time=request_start_time,
                latency=int((time.perf_counter() - start_time) * 1000),
                status="failed",
                error=message,
                request_content=request,
                response_content=response,
            )
            raise RuntimeError(f"TTS 请求失败: {message}")

        audio_url = _extract_audio_url(response)
        if not audio_url:
            message = "TTS 服务返回成功，但未解析到音频地址"
            record_service_usage(
                service_type="tts",
                request_model_name=self.model,
                input_value=0,
                output_value=0,
                start_time=request_start_time,
                latency=int((time.perf_counter() - start_time) * 1000),
                status="failed",
                error=message,
                request_content=request,
                response_content=response,
            )
            raise RuntimeError(message)

        usage = extract_usage(response)
        record_service_usage(
            service_type="tts",
            request_model_name=self.model,
            input_value=usage_value(usage, "characters"),
            output_value=0,
            start_time=request_start_time,
            latency=int((time.perf_counter() - start_time) * 1000),
            status="success",
            request_content=request,
            response_content=response,
        )
        return audio_url

    def synthesize(self, text: str) -> bytes:
        """传入文本，返回音频字节"""
        audio_url = self.synthesize_to_url(text)

        try:
            with urlopen(audio_url) as audio_response:
                audio_bytes = audio_response.read()
        except Exception as exc:
            logger.exception("TTS 音频下载失败")
            raise RuntimeError(f"TTS 音频下载失败: {exc}") from exc

        if not audio_bytes:
            raise RuntimeError("TTS 音频下载成功，但内容为空")

        logger.info("TTS 合成成功，音频大小=%s 字节", len(audio_bytes))
        return audio_bytes

    def synthesize_text(self, text: str) -> bytes:
        """对外兼容接口"""
        return self.synthesize(text)
