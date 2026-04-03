"""
ASR / TTS 服务框架测试。
"""

import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services import get_asr_service, get_tts_service


class TestASRAndTTSService(unittest.TestCase):
    """ASR / TTS 占位服务测试。"""

    def test_asr_transcribe_returns_text_result(self):
        service = get_asr_service()

        result = service.transcribe(b"fake-audio-bytes")

        self.assertIsInstance(result, str)
        self.assertEqual(
            result,
            "这是一个占位的 ASR 转录结果，实际实现需要接入真实的 ASR 模型或服务。",
        )

    def test_asr_transcribe_requires_audio_bytes(self):
        service = get_asr_service()

        with self.assertRaises(ValueError):
            service.transcribe(b"")

    def test_tts_synthesize_returns_audio_bytes(self):
        service = get_tts_service()

        result = service.synthesize("这是一个占位语音结果")

        self.assertIsInstance(result, bytes)
        self.assertEqual(result, "这是一个占位语音结果".encode("utf-8"))

    def test_tts_synthesize_requires_text(self):
        service = get_tts_service()

        with self.assertRaises(ValueError):
            service.synthesize("   ")


def main():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestASRAndTTSService)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
