"""课堂主流程"""

import asyncio
import logging
import time
import random
from app.services.asr import get_asr_service
from app.services.tts import get_tts_service
from .classcontext import ClassContext
from .question import QuestionProcessor

logger = logging.getLogger(__name__)

class_context = ClassContext()  # 课堂上下文实例
question_processor = QuestionProcessor()  # 提问处理器实例
asr = get_asr_service()  # ASR 服务实例
tts = get_tts_service()  # TTS 服务实例


async def run_main_flow() -> None:
    """持续运行课堂主流程"""
    logger.info("课堂提问助手主流程已启动")

    while True:
        logger.info("等待音频输入")

        # Audio -> ASR -> Text
        text = asr.transcribe("")  # TODO: 传入实际的音频字节

        logger.info("ASR 结果: %s", text)

        # 上下文维护
        class_context.add_lecture_text(text_start_time=time.time(), text=text)

        # 触发异步任务，不阻塞主流程
        asyncio.create_task(
            question_processor.generate_questions(
                class_context.get_recent_lecture_text()
            )
        )

        # 提问决策
        ask_question = random.random() < 0.2  # 20%概率触发提问，暂时代替实际的决策逻辑

        if ask_question:
            # [提问] -> TTS -> 播放
            question_to_ask = question_processor.get_latest_question_random()
            if question_to_ask:
                logger.info("决策通过，准备提问: %s", question_to_ask)
                audio_output = tts.synthesize(question_to_ask)
                # TODO: 使用实际的 TTS 输出
        else:
            # [不提问] 分支
            logger.info("决策未通过，跳过")
