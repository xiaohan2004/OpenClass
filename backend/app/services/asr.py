"""ASR 服务实现"""

from __future__ import annotations

import base64
import io
import logging
import time
import wave
from typing import Any, Optional

import dashscope
from mutagen import File as mutagen_file

from app.config import get_settings
from app.services.metrics import record_service_usage
from app.utils.time import now_ts

logger = logging.getLogger(__name__)

DEFAULT_ASR_MODEL = "qwen3-asr-flash"
DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
settings = get_settings()

_asr_service: Optional["ASRService"] = None


def get_asr_service() -> "ASRService":
    """获取 ASR 服务单例"""
    global _asr_service
    if _asr_service is None:
        _asr_service = ASRService()
    return _asr_service


def _guess_audio_mime_type(audio_bytes: bytes) -> str:
    """根据常见文件头猜测 MIME 类型"""
    if audio_bytes.startswith(b"ID3") or audio_bytes[:2] == b"\xff\xfb":
        return "audio/mpeg"
    if audio_bytes.startswith(b"RIFF") and audio_bytes[8:12] == b"WAVE":
        return "audio/wav"
    if audio_bytes.startswith(b"OggS"):
        return "audio/ogg"
    if audio_bytes.startswith(b"fLaC"):
        return "audio/flac"
    if len(audio_bytes) > 12 and audio_bytes[4:8] == b"ftyp":
        return "audio/mp4"
    return "audio/wav"


def _build_data_uri(audio_bytes: bytes) -> str:
    """将音频字节编码为 data URI"""
    mime_type = _guess_audio_mime_type(audio_bytes)
    base64_str = base64.b64encode(audio_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{base64_str}"


def _extract_text_from_response(response: Any) -> str:
    """从 DashScope message 格式响应中提取转录文本"""
    output = getattr(response, "output", None)
    if output is None:
        return ""

    choices = getattr(output, "choices", None)
    if not choices:
        return ""

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return ""

    message = first_choice.get("message")
    if not isinstance(message, dict):
        return ""

    content = message.get("content")
    if isinstance(content, str):
        return content.strip()

    if not isinstance(content, list):
        return ""

    parts: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue

        text = item.get("text")
        if isinstance(text, str) and text.strip():
            parts.append(text.strip())
            continue

        audio_item = item.get("audio")
        if isinstance(audio_item, dict):
            nested_text = audio_item.get("text")
            if isinstance(nested_text, str) and nested_text.strip():
                parts.append(nested_text.strip())

    return "\n".join(parts).strip()


def _get_audio_duration_seconds(audio_bytes: bytes) -> float:
    """尽量从音频中解析时长（秒）。优先多格式解析，失败后降级到 WAV。"""
    if mutagen_file is not None:
        try:
            audio_file = mutagen_file(io.BytesIO(audio_bytes))
            info = getattr(audio_file, "info", None)
            length = getattr(info, "length", None) if info is not None else None
            if isinstance(length, (int, float)) and length > 0:
                return float(length)
        except Exception:
            pass

    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
            frame_rate = wav_file.getframerate()
            frame_count = wav_file.getnframes()
            if frame_rate <= 0:
                return 0.0
            return frame_count / frame_rate
    except Exception:
        logger.debug("音频时长解析失败，按 0 秒记录")
        return 0.0


class ASRService:
    """音频转文字服务"""

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        enable_itn: bool = False,
        language: Optional[str] = "zh",
    ) -> None:
        self.model = model or DEFAULT_ASR_MODEL
        self.enable_itn = enable_itn
        self.language = language

    def transcribe(self, audio_bytes: bytes) -> str:
        """传入音频字节，返回转录文本"""
        if not audio_bytes:
            raise ValueError("audio_bytes 不能为空")

        audio_duration_seconds = _get_audio_duration_seconds(audio_bytes)
        request_start_time = now_ts()
        start_time = time.perf_counter()
        api_key = settings.qwen_api_key
        if not api_key:
            raise ValueError("Qwen_API_Key 未配置，无法调用 ASR 服务")

        dashscope.base_http_api_url = DEFAULT_BASE_URL
        data_uri = _build_data_uri(audio_bytes)

        asr_options: dict[str, Any] = {"enable_itn": self.enable_itn}
        if self.language:
            asr_options["language"] = self.language

        try:
            response = dashscope.MultiModalConversation.call(
                api_key=api_key,
                model=self.model,
                messages=[{"role": "user", "content": [{"audio": data_uri}]}],
                result_format="message",
                asr_options=asr_options,
            )
        except Exception as exc:
            logger.exception("ASR 转录失败")
            record_service_usage(
                service_type="asr",
                request_model_name=self.model,
                input_value=audio_duration_seconds,
                output_value=0,
                start_time=request_start_time,
                latency=int((time.perf_counter() - start_time) * 1000),
                status="failed",
                error=str(exc),
            )
            raise RuntimeError(f"ASR 转录失败: {exc}") from exc

        status_code = getattr(response, "status_code", None)
        if status_code is not None and status_code != 200:
            message = getattr(response, "message", "未知错误")
            record_service_usage(
                service_type="asr",
                request_model_name=self.model,
                input_value=audio_duration_seconds,
                output_value=0,
                start_time=request_start_time,
                latency=int((time.perf_counter() - start_time) * 1000),
                status="failed",
                error=message,
                response_content=response,
            )
            raise RuntimeError(f"ASR 请求失败: {message}")

        text = _extract_text_from_response(response)
        if not text:
            message = "ASR 服务返回成功，但未解析到转录文本"
            record_service_usage(
                service_type="asr",
                request_model_name=self.model,
                input_value=audio_duration_seconds,
                output_value=0,
                start_time=request_start_time,
                latency=int((time.perf_counter() - start_time) * 1000),
                status="failed",
                error=message,
            )
            raise RuntimeError(message)

        record_service_usage(
            service_type="asr",
            request_model_name=self.model,
            input_value=audio_duration_seconds,
            output_value=0,
            start_time=request_start_time,
            latency=int((time.perf_counter() - start_time) * 1000),
            status="success",
            request_content=f"audio_duration_seconds={audio_duration_seconds}",
            response_content=response,
        )

        logger.info("ASR 转录成功，文本长度=%s", len(text))
        return text

    def transcribe_audio(self, audio_bytes: bytes) -> str:
        """对外兼容接口"""
        return self.transcribe(audio_bytes)
