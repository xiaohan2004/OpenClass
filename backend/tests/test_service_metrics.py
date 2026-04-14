"""外部服务日志统计测试。"""

from __future__ import annotations

import io
import sys
import unittest
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.asr import ASRService
from app.services.tts import TTSService
from app.services.asr import _get_audio_duration_seconds


class TestServiceMetrics(unittest.TestCase):
    @patch("app.services.asr.mutagen_file")
    def test_asr_duration_uses_mutagen_when_available(self, mock_mutagen_file):
        mock_audio = MagicMock()
        mock_audio.info = MagicMock(length=2.5)
        mock_mutagen_file.return_value = mock_audio

        duration = _get_audio_duration_seconds(b"not-wav")

        self.assertEqual(duration, 2.5)

    @patch("app.services.asr.mutagen_file", None)
    def test_asr_duration_falls_back_to_zero_when_unparseable(self):
        duration = _get_audio_duration_seconds(b"invalid-audio")
        self.assertEqual(duration, 0.0)

    @patch("app.services.asr.mutagen_file", None)
    def test_asr_duration_parses_wav_in_fallback(self):
        sample_rate = 16000
        duration_seconds = 1
        frame_count = sample_rate * duration_seconds
        wav_buffer = io.BytesIO()

        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"\x00\x00" * frame_count)

        duration = _get_audio_duration_seconds(wav_buffer.getvalue())
        self.assertAlmostEqual(duration, 1.0, places=3)

    @patch("app.services.asr.mutagen_file", None)
    def test_asr_duration_parses_half_second_wav_in_fallback(self):
        sample_rate = 16000
        frame_count = sample_rate // 2
        wav_buffer = io.BytesIO()

        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"\x00\x00" * frame_count)

        duration = _get_audio_duration_seconds(wav_buffer.getvalue())
        self.assertAlmostEqual(duration, 0.5, places=3)

    @patch("app.services.asr.record_service_usage")
    @patch("app.services.asr._extract_text_from_response", return_value="转写结果")
    @patch("app.services.asr.dashscope.MultiModalConversation.call")
    def test_asr_transcribe_records_usage(
        self,
        mock_call,
        _mock_extract_text,
        mock_record_usage,
    ):
        mock_call.return_value = MagicMock(
            status_code=200,
            usage=MagicMock(input_tokens=15, output_tokens=7),
        )

        with patch("app.services.asr.settings.qwen_api_key", "test-key"):
            service = ASRService(model="test-asr")
            result = service.transcribe(b"fake-audio")

        self.assertEqual(result, "转写结果")
        mock_record_usage.assert_called_once()
        self.assertEqual(mock_record_usage.call_args.kwargs["service_type"], "asr")
        self.assertEqual(mock_record_usage.call_args.kwargs["status"], "success")

    @patch("app.services.tts.record_service_usage")
    @patch("app.services.tts._extract_audio_url", return_value="http://audio.url")
    @patch("app.services.tts.dashscope.MultiModalConversation.call")
    def test_tts_synthesize_to_url_records_usage(
        self,
        mock_call,
        _mock_extract_audio_url,
        mock_record_usage,
    ):
        mock_call.return_value = MagicMock(
            status_code=200,
            usage=MagicMock(input_tokens=8, output_tokens=4),
        )

        with patch("app.services.tts.settings.qwen_api_key", "test-key"):
            service = TTSService(model="test-tts")
            result = service.synthesize_to_url("你好，测试一下")

        self.assertEqual(result, "http://audio.url")
        mock_record_usage.assert_called_once()
        self.assertEqual(mock_record_usage.call_args.kwargs["service_type"], "tts")
        self.assertEqual(mock_record_usage.call_args.kwargs["status"], "success")


if __name__ == "__main__":
    unittest.main()
