"""ASR / TTS 真实服务集成测试"""

import os
import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

from app.services import get_asr_service, get_tts_service

WELCOME_AUDIO_PATH = PROJECT_ROOT / "data" / "welcome.mp3"


class TestASRAndTTSService(unittest.TestCase):
    """ASR / TTS 真实服务测试"""

    def test_asr_transcribe_with_real_audio_file(self):
        self.assertTrue(WELCOME_AUDIO_PATH.exists(), f"测试音频不存在: {WELCOME_AUDIO_PATH}")

        service = get_asr_service()
        audio_bytes = WELCOME_AUDIO_PATH.read_bytes()
        result = service.transcribe(audio_bytes)

        self.assertIsInstance(result, str)
        self.assertTrue(result.strip(), "ASR 返回的文本不应为空")

    def test_asr_transcribe_requires_audio_bytes(self):
        service = get_asr_service()

        with self.assertRaises(ValueError):
            service.transcribe(b"")

    def test_tts_synthesize_returns_audio_bytes(self):
        service = get_tts_service()

        result = service.synthesize("你好，这是 OpenClass 的真实 TTS 集成测试")

        self.assertIsInstance(result, bytes)
        self.assertTrue(result, "TTS 返回的音频字节不应为空")

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
