"""课堂主流程"""

import asyncio
import logging
import random
import time
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

        text = asr.transcribe(b"placeholder-audio") # TODO: 替换为实际音频输入
        logger.info("ASR 结果: %s", text)

        class_context.add_lecture_text(text_start_time=time.time(), text=text)

        asyncio.create_task(
            asyncio.to_thread(
                question_processor.generate_questions,
                class_context.get_questioning_texts(),
            )
        )

        ask_question = random.random() < 0.2    # TODO: 替换为实际决策逻辑
        if ask_question:
            question_to_ask = question_processor.get_latest_question_random()
            if question_to_ask:
                logger.info("决策通过，准备提问: %s", question_to_ask)
                tts.synthesize(question_to_ask) # TODO: 实际使用 TTS 输出
        else:
            logger.info("决策未通过，跳过")

        await asyncio.sleep(0)
