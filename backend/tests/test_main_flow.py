"""主流程测试。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core import main_flow


class TestMainFlow(unittest.IsolatedAsyncioTestCase):
    @patch("app.core.main_flow.asyncio.create_task")
    @patch("app.core.main_flow.asyncio.to_thread", new_callable=MagicMock)
    @patch("app.core.main_flow.random.random")
    async def test_run_main_flow_dispatches_question_generation(
        self,
        mock_random,
        mock_to_thread,
        mock_create_task,
    ):
        mock_random.return_value = 0.9
        mock_to_thread.return_value = "thread-task"
        main_flow.asr = MagicMock()
        main_flow.asr.transcribe.return_value = "讲课文本"
        main_flow.class_context = MagicMock()
        main_flow.class_context.get_questioning_texts.return_value = "提问上下文"
        main_flow.question_processor = MagicMock()

        with patch("app.core.main_flow.asyncio.sleep", new=AsyncMock(side_effect=RuntimeError("stop"))):
            with self.assertRaises(RuntimeError):
                await main_flow.run_main_flow()

        main_flow.asr.transcribe.assert_called_once_with(b"placeholder-audio")
        main_flow.class_context.add_lecture_text.assert_called_once()
        mock_to_thread.assert_called_once_with(
            main_flow.question_processor.generate_questions,
            "提问上下文",
        )
        mock_create_task.assert_called_once_with("thread-task")


if __name__ == "__main__":
    unittest.main()
