"""主流程测试。"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from sqlmodel import Session

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

import app.config as app_config
import app.db.session as db_session_module
from app.core.classcontext import ClassContext
from app.core.main_flow import (
    _background_tasks_processing,
    _background_keyword_extraction,
    _handle_task_result,
    handle_audio,
    start_background_tasks,
)
from app.core.question import ScoredQuestion
from app.db import init_db
from app.db.crud import (
    create_course,
    create_session,
    create_transcript,
    list_questions_by_session,
    list_segment_summaries_by_session,
    list_transcripts_by_session,
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

                mock_start_bg.assert_called_once_with(context, safe_ws)
                self.assertEqual(context.lecture_texts.get_count(), 1)
                self.assertEqual(
                    safe_ws.send_json.await_args_list[0].args[0]["type"], "transcript"
                )

    def test_background_keyword_extraction_uses_algorithm_and_persists(self):
        with (
            patch(
                "app.core.main_flow.keyword_processor.extract_keywords_algorithm",
                return_value=["机器学习", "神经网络"],
            ) as mock_extract,
            patch("app.core.main_flow._persist_keywords") as mock_persist,
        ):
            _background_keyword_extraction(1, "课堂文本", [10, 11])

        mock_extract.assert_called_once_with("课堂文本")
        mock_persist.assert_called_once_with(
            1,
            ["机器学习", "神经网络"],
            [10, 11],
            "algorithm",
        )

    def test_background_keyword_extraction_handles_algorithm_errors(self):
        with (
            patch(
                "app.core.main_flow.keyword_processor.extract_keywords_algorithm",
                side_effect=RuntimeError("算法失败"),
            ) as mock_extract,
            patch("app.core.main_flow._persist_keywords") as mock_persist,
        ):
            _background_keyword_extraction(1, "课堂文本", [10, 11])

        mock_extract.assert_called_once_with("课堂文本")
        mock_persist.assert_not_called()

    @patch("app.core.main_flow.random.random")
    async def test_handle_audio_sends_tts_out_when_asking(
        self,
        mock_random,
    ):
        """测试当决策为提问时，handle_audio 发送音频输出。"""
        mock_random.return_value = 0.1

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

                        sent_types = [
                            call.args[0]["type"]
                            for call in safe_ws.send_json.await_args_list
                        ]
                        self.assertIn("transcript", sent_types)
                        self.assertIn("tts_out", sent_types)


class TestBackgroundTasks(unittest.IsolatedAsyncioTestCase):
    async def test_background_tasks_processing_sends_summary_and_questions(
        self,
    ):
        """测试后台任务会把 summary 和 question 推送给前端。"""
        context = ClassContext(session_id=1)
        safe_ws = MagicMock(spec=SafeWebSocket)
        safe_ws.send_json = AsyncMock()

        context.get_recent_transcript_ids_for_questions = MagicMock(return_value=[])

        with patch.object(
            context,
            "generate_summary_if_needed",
            return_value={"text": "实时小结", "start": 0, "end": 0},
        ) as mock_generate_summary:
            with patch.object(
                context,
                "get_transcript_time_range",
                return_value=(None, None),
            ):
                with patch.object(context, "get_transcript_ids_range", return_value=[]):
                    with patch(
                        "app.core.main_flow._persist_summary",
                        return_value=123,
                    ):
                        with patch(
                            "app.core.main_flow._persist_questions",
                            return_value=[
                                ("问题一", 0.8, 11, 1712995600),
                                ("问题二", 0.9, 12, 1712995601),
                            ],
                        ):
                            with patch(
                                "app.core.main_flow.question_processor.generate_scored_questions",
                                return_value=[
                                    ScoredQuestion("问题一", 0.8),
                                    ScoredQuestion("问题二", 0.9),
                                ],
                            ) as mock_gen_questions:
                                await _background_tasks_processing(context, safe_ws)

                                mock_generate_summary.assert_called_once()
                                mock_gen_questions.assert_called_once()
                                sent_types = [
                                    call.args[0]["type"]
                                    for call in safe_ws.send_json.await_args_list
                                ]
                                self.assertIn("summary", sent_types)
                                self.assertIn("question", sent_types)

                                question_payload = next(
                                    call.args[0]
                                    for call in safe_ws.send_json.await_args_list
                                    if call.args[0]["type"] == "question"
                                )
                                self.assertTrue(question_payload["data"]["items"])
                                self.assertIn(
                                    "created_at", question_payload["data"]["items"][0]
                                )
                                self.assertIn(
                                    "score", question_payload["data"]["items"][0]
                                )

    def test_handle_task_result_catches_exception(
        self,
    ):
        """测试异常处理不会导致 Task exception was never retrieved。"""
        task = MagicMock(spec=asyncio.Task)
        task.cancelled.return_value = False
        task.exception.return_value = RuntimeError("Background task failed")

        with patch("app.core.main_flow.logger.exception") as mock_logger:
            _handle_task_result(task)
            mock_logger.assert_called_once()

    def test_start_background_tasks_creates_task_with_callback(
        self,
    ):
        """测试 start_background_tasks 创建任务并附加回调。"""
        context = ClassContext()
        safe_ws = MagicMock(spec=SafeWebSocket)

        with patch("app.core.main_flow.asyncio.create_task") as mock_create_task:
            mock_task = MagicMock(spec=asyncio.Task)
            mock_create_task.return_value = mock_task

            start_background_tasks(context, safe_ws)

            mock_create_task.assert_called_once()
            mock_task.add_done_callback.assert_called_once()
            created_coro = mock_create_task.call_args.args[0]
            created_coro.close()


class TestMainFlowDatabaseIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_main_flow.db"
        self.db_url = f"sqlite:///{self.db_path.as_posix()}"

        self.env_patcher = patch.dict(
            os.environ,
            {"DATABASE_URL": self.db_url, "DATABASE_ECHO": "false"},
            clear=False,
        )
        self.env_patcher.start()

        app_config.get_settings.cache_clear()
        db_session_module.get_engine.cache_clear()
        db_session_module.engine = db_session_module.get_engine()
        init_db()

        with Session(db_session_module.get_engine()) as db:
            course = create_course(db, code="MATH101", name="高等数学")
            session = create_session(db, course_id=course.id, title="测试课堂")
            self.session_id = session.id

    def tearDown(self):
        db_session_module.get_engine().dispose()
        self.env_patcher.stop()
        app_config.get_settings.cache_clear()
        db_session_module.get_engine.cache_clear()
        self.temp_dir.cleanup()

    @patch("app.core.main_flow.random.random")
    async def test_handle_audio_persists_transcript(self, mock_random):
        mock_random.return_value = 0.9

        context = ClassContext(session_id=self.session_id)
        safe_ws = MagicMock(spec=SafeWebSocket)
        safe_ws.send_json = AsyncMock()

        with patch("app.core.main_flow.asr.transcribe", return_value="已入库转写"):
            with patch("app.core.main_flow.start_background_tasks"):
                await handle_audio(
                    b"audio-data",
                    context,
                    safe_ws,
                    transcript_start_time=1712995200,
                    transcript_end_time=1712995210,
                )

        with Session(db_session_module.get_engine()) as db:
            transcripts = list_transcripts_by_session(db, self.session_id)
            self.assertEqual(len(transcripts), 1)
            self.assertEqual(transcripts[0].text, "已入库转写")
            self.assertEqual(transcripts[0].start_time, 1712995200)
            self.assertEqual(transcripts[0].end_time, 1712995210)

    async def test_background_tasks_persist_summary_and_questions(self):
        context = ClassContext(session_id=self.session_id)
        safe_ws = MagicMock(spec=SafeWebSocket)
        safe_ws.send_json = AsyncMock()

        with Session(db_session_module.get_engine()) as db:
            transcript1 = create_transcript(
                db,
                self.session_id,
                "第一段",
                seq=1,
                start_time=1712995200,
                end_time=1712995210,
            )
            transcript2 = create_transcript(
                db,
                self.session_id,
                "第二段",
                seq=2,
                start_time=1712995300,
                end_time=1712995400,
            )
            transcript1_id = transcript1.id
            transcript2_id = transcript2.id

        context.add_lecture_text(1.0, "第一段")
        context.add_lecture_text(2.0, "第二段")
        context.add_transcript_id(
            transcript1_id,
            start_time=1712995200,
            end_time=1712995210,
        )
        context.add_transcript_id(
            transcript2_id,
            start_time=1712995300,
            end_time=1712995400,
        )

        with patch.object(
            context,
            "generate_summary_if_needed",
            return_value={"text": "数据库小结", "start": 0, "end": 2},
        ):
            with patch(
                "app.core.main_flow.question_processor.generate_scored_questions",
                return_value=[
                    ScoredQuestion("数据库问题一", 0.8),
                    ScoredQuestion("数据库问题二", 0.9),
                ],
            ):
                await _background_tasks_processing(context, safe_ws)

        with Session(db_session_module.get_engine()) as db:
            summaries = list_segment_summaries_by_session(db, self.session_id)
            questions = list_questions_by_session(db, self.session_id)

            self.assertEqual(len(summaries), 1)
            self.assertEqual(summaries[0].text, "数据库小结")
            self.assertEqual(summaries[0].start_time, 1712995200)
            self.assertEqual(summaries[0].end_time, 1712995400)
            self.assertEqual(len(questions), 2)
            self.assertEqual(
                {item.text for item in questions}, {"数据库问题一", "数据库问题二"}
            )
            self.assertEqual({item.score for item in questions}, {0.8, 0.9})
            self.assertTrue(all(item.created_at is not None for item in questions))


if __name__ == "__main__":
    unittest.main()
