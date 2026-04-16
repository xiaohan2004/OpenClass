"""外部服务日志统计测试。"""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.asr import ASRService
from app.services.tts import TTSService


class TestServiceMetrics(unittest.TestCase):
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
