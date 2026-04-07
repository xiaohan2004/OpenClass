"""主流程测试。"""

from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.classcontext import ClassContext
from app.core.main_flow import (
    handle_audio,
    start_background_tasks,
    _background_tasks_processing,
    _handle_task_result,
)
from app.utils.websocket_utils import SafeWebSocket


class TestHandleAudio(unittest.IsolatedAsyncioTestCase):
    @patch("app.core.main_flow.random.random")
    async def test_handle_audio_updates_context_and_dispatches_background_tasks(
        self,
        mock_random,
    ):
        """测试 handle_audio 处理音频输入的完整流程。"""
        mock_random.return_value = 0.9

        context = ClassContext()
        safe_ws = MagicMock(spec=SafeWebSocket)
        safe_ws.send_json = AsyncMock()

        with patch("app.core.main_flow.asr.transcribe", return_value="讲课文本"):
            with patch("app.core.main_flow.start_background_tasks") as mock_start_bg:
                await handle_audio(b"audio-data", context, safe_ws)

                # 验证 ASR 被调用
                mock_start_bg.assert_called_once_with(context)
                # 验证上下文被更新
                self.assertEqual(context.lecture_texts.get_count(), 1)

    @patch("app.core.main_flow.random.random")
    async def test_handle_audio_sends_tts_output_when_asking(
        self,
        mock_random,
    ):
        """测试当决策为提问时，handle_audio 发送 TTS 输出。"""
        mock_random.return_value = 0.1  # 决策通过

        context = ClassContext()
        safe_ws = MagicMock(spec=SafeWebSocket)
        safe_ws.send_json = AsyncMock()

        with patch("app.core.main_flow.asr.transcribe", return_value="讲课文本"):
            with patch("app.core.main_flow.start_background_tasks"):
                with patch(
                    "app.core.main_flow.question_processor.get_latest_question_random",
                    return_value="提问内容",
                ):
                    with patch(
                        "app.core.main_flow.tts.synthesize_to_url",
                        return_value="http://audio.url",
                    ):
                        await handle_audio(b"audio-data", context, safe_ws)

                        # 验证 WS 发送了数据
                        safe_ws.send_json.assert_called_once()
                        call_args = safe_ws.send_json.call_args
                        self.assertEqual(call_args[0][0]["type"], "tts_out")


class TestBackgroundTasks(unittest.IsolatedAsyncioTestCase):
    async def test_background_tasks_processing_runs_both_tasks(
        self,
    ):
        """测试后台任务并发执行 summary 生成和问题生成。"""
        context = ClassContext()

        # 先添加足够的讲课文本，使 generate_summary_if_needed 可以触发
        for i in range(5):
            context.add_lecture_text(float(i), f"讲课内容 {i}")

        # Mock question_processor.generate_questions 避免调用真实 LLM
        with patch(
            "app.core.main_flow.question_processor.generate_questions"
        ) as mock_gen_questions:
            mock_gen_questions.return_value = None

            # 执行后台任务处理
            await _background_tasks_processing(context)

            # 验证 questions 生成被调用
            mock_gen_questions.assert_called_once()

    def test_handle_task_result_catches_exception(
        self,
    ):
        """测试异常处理不会导致 Task exception was never retrieved。"""
        task = MagicMock(spec=asyncio.Task)
        task.result.side_effect = RuntimeError("Background task failed")

        with patch("app.core.main_flow.logger.exception") as mock_logger:
            _handle_task_result(task)

            # 验证异常被记录
            mock_logger.assert_called_once()

    def test_start_background_tasks_creates_task_with_callback(
        self,
    ):
        """测试 start_background_tasks 创建任务并附加回调。"""
        context = ClassContext()

        with patch("app.core.main_flow.asyncio.create_task") as mock_create_task:
            mock_task = MagicMock(spec=asyncio.Task)
            mock_create_task.return_value = mock_task

            start_background_tasks(context)

            # 验证任务被创建
            mock_create_task.assert_called_once()
            # 验证回调被附加
            mock_task.add_done_callback.assert_called_once()


if __name__ == "__main__":
    unittest.main()
