"""课堂主流程"""

import asyncio
import logging
import random
import time
from app.utils.websocket_utils import SafeWebSocket
from app.services.asr import get_asr_service
from app.services.tts import get_tts_service
from .classcontext import ClassContext
from .question import QuestionProcessor

logger = logging.getLogger(__name__)


question_processor = QuestionProcessor()  # 提问处理器实例
asr = get_asr_service()  # ASR 服务实例
tts = get_tts_service()  # TTS 服务实例


async def handle_audio(
    audio_bytes: bytes,
    context: ClassContext,
    safe_ws: SafeWebSocket,
):
    """处理一次音频输入（单步主流程）"""

    # ASR
    text = await asyncio.to_thread(asr.transcribe, audio_bytes)
    logger.info("ASR 结果: %s", text)

    # 更新上下文
    context.add_lecture_text(text_start_time=time.time(), text=text)

    # 后台任务
    start_background_tasks(context)

    # 决策
    ask_question = random.random() < 0.2

    if ask_question:
        question_to_ask = question_processor.get_latest_question_random()
        if question_to_ask:
            logger.info("准备提问: %s", question_to_ask)

            # TTS
            audio_url = await asyncio.to_thread(tts.synthesize_to_url, question_to_ask)

            # 通过 WS 发回前端
            await safe_ws.send_json(
                {
                    "type": "tts_out",
                    "data": {
                        "audio_url": audio_url,
                        "text": question_to_ask,
                    },
                }
            )


def start_background_tasks(context: ClassContext) -> None:
    """启动后台任务。"""
    task = asyncio.create_task(_background_tasks_processing(context))
    task.add_done_callback(_handle_task_result)


async def _background_tasks_processing(context: ClassContext) -> None:
    """执行后台任务。"""
    await asyncio.gather(
        asyncio.to_thread(context.generate_summary_if_needed),
        asyncio.to_thread(
            question_processor.generate_questions,
            context.get_questioning_texts(),
        ),
    )


def _handle_task_result(task: asyncio.Task) -> None:
    """统一处理异常（避免 Task exception was never retrieved）"""
    try:
        task.result()
    except Exception:
        logger.exception("Background processing failed")
