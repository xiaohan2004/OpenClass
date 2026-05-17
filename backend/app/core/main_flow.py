"""课堂主流程"""

import asyncio
import json
import logging
import time

from sqlmodel import Session

from app.config import get_settings
from app.db import get_engine
from app.db.crud import (
    create_keyword,
    create_knowledge_point,
    create_question,
    create_quiz_item,
    create_segment_summary,
    create_transcript,
    link_keyword_to_transcript,
    link_knowledge_point_to_transcript,
    link_question_to_transcript,
    link_quiz_item_to_transcript,
    link_segment_summary_to_transcript,
    list_transcripts_by_session,
    mark_question_asked,
)
from app.utils.websocket_utils import SafeWebSocket
from app.services.asr import get_asr_service
from app.services.tts import get_tts_service
from .classcontext import ClassContext
from .question import QuestionProcessor, ScoredQuestion
from .keyword import KeywordProcessor
from .knowledge import KnowledgeProcessor
from .quiz import QuizProcessor

logger = logging.getLogger(__name__)


question_processor = QuestionProcessor()  # 提问处理器实例
keyword_processor = KeywordProcessor()  # 关键词处理器实例
knowledge_processor = KnowledgeProcessor()  # 知识点处理器实例
quiz_processor = QuizProcessor()  # 小测处理器实例

# 计数器，用于控制关键词/知识点/小测处理的触发间隔
_handle_audio_call_count = 0


class _ServiceProxy:
    """按需获取最新服务实例的代理。"""

    def __init__(self, getter):
        self._getter = getter

    def __getattr__(self, item):
        return getattr(self._getter(), item)


asr = _ServiceProxy(get_asr_service)  # ASR 服务代理
tts = _ServiceProxy(get_tts_service)  # TTS 服务代理


async def handle_audio(
    audio_bytes: bytes,
    context: ClassContext,
    safe_ws: SafeWebSocket,
    transcript_start_time: int | None = None,
    transcript_end_time: int | None = None,
):
    """处理一次音频输入（单步主流程）"""
    global _handle_audio_call_count
    _handle_audio_call_count += 1

    # ASR
    text = await asyncio.to_thread(asr.transcribe, audio_bytes)
    logger.info("ASR 结果: %s", text)

    transcript_id = None
    if context.session_id is not None:
        transcript_id = await asyncio.to_thread(
            _persist_transcript,
            context.session_id,
            text,
            transcript_start_time,
            transcript_end_time,
        )

    await safe_ws.send_json(
        {
            "type": "transcript",
            "data": {
                "id": transcript_id,
                "text": text,
            },
        }
    )

    # 更新上下文
    context.add_lecture_text(
        text_start_time=float(transcript_start_time or time.time()),
        text=text,
    )
    if transcript_id is not None:
        context.add_transcript_id(
            transcript_id,
            start_time=transcript_start_time,
            end_time=transcript_end_time,
        )

    # 后台任务
    start_background_tasks(context, safe_ws)


async def ask_question(context: ClassContext, safe_ws: SafeWebSocket) -> None:
    """由前端显式触发一次开口提问。"""
    question_to_ask = question_processor.select_question_to_ask()
    if not question_to_ask:
        await safe_ws.send_json(
            {
                "type": "error",
                "data": {
                    "message": "当前没有可提问的问题",
                },
            }
        )
        return

    logger.info("准备提问: %s", question_to_ask)

    question_id = context.consume_generated_question_id(question_to_ask)
    if question_id is not None:
        await asyncio.to_thread(_mark_question_asked, question_id)

    audio_url = await asyncio.to_thread(tts.synthesize_to_url, question_to_ask)

    await safe_ws.send_json(
        {
            "type": "tts_out",
            "data": {
                "audio_url": audio_url,
                "text": question_to_ask,
            },
        }
    )


def start_background_tasks(context: ClassContext, safe_ws: SafeWebSocket) -> None:
    """启动后台任务。"""
    task = asyncio.create_task(
        _background_tasks_processing(context, safe_ws, _handle_audio_call_count)
    )
    task.add_done_callback(_handle_task_result)


async def _background_tasks_processing(
    context: ClassContext,
    safe_ws: SafeWebSocket,
    call_count: int = 1,
) -> None:
    """执行后台任务。"""
    settings = get_settings()
    trigger_interval = getattr(settings, "keyword_knowledge_quiz_trigger_interval", 24)

    summary_text, questions = await asyncio.gather(
        asyncio.to_thread(context.generate_summary_if_needed),
        asyncio.to_thread(
            question_processor.generate_scored_questions,
            context.get_questioning_texts(),
        ),
    )

    if summary_text:
        summary_id = None
        if context.session_id is not None:
            summary_start_time, summary_end_time = context.get_transcript_time_range(
                summary_text["start"], summary_text["end"]
            )
            summary_id = await asyncio.to_thread(
                _persist_summary,
                context.session_id,
                summary_text,
                context.get_transcript_ids_range(
                    summary_text["start"], summary_text["end"]
                ),
                summary_start_time,
                summary_end_time,
            )
        await safe_ws.send_json(
            {
                "type": "summary",
                "data": {
                    "id": summary_id,
                    "text": summary_text["text"],
                },
            }
        )

    if questions:
        question_records: list[tuple[str, float, int, int]] = []
        if context.session_id is not None:
            question_records = await asyncio.to_thread(
                _persist_questions,
                context.session_id,
                questions,
                context.get_recent_transcript_ids_for_questions(),
            )
            context.register_generated_questions(
                [
                    (question_text, question_id)
                    for question_text, _, question_id, _ in question_records
                ]
            )

        await safe_ws.send_json(
            {
                "type": "question",
                "data": {
                    "items": [
                        {
                            "id": question_id,
                            "text": question_text,
                            "score": score,
                            "created_at": created_at,
                        }
                        for question_text, score, question_id, created_at in question_records
                    ],
                    "questions": [question.text for question in questions],
                },
            }
        )

    # 定时处理关键词、知识点、小测（每 trigger_interval 次调用触发一次）
    if call_count % trigger_interval == 0:
        context_text = context.get_latest_lecture_texts()
        if context_text:
            # 获取用于关联的转写 ID
            transcript_ids = context.get_recent_transcript_ids_for_questions()

            # 并行执行关键词、知识点、小测处理
            keywords_result, knowledge_result, quiz_result = await asyncio.gather(
                asyncio.to_thread(keyword_processor.extract_keywords_llm, context_text),
                asyncio.to_thread(
                    knowledge_processor.generate_knowledge_point, context_text
                ),
                asyncio.to_thread(quiz_processor.generate_quiz_item, context_text),
                return_exceptions=True,
            )
            # 后台执行algorithm提取关键词（不阻塞主流程）
            asyncio.create_task(
                asyncio.to_thread(
                    _background_keyword_extraction,
                    context.session_id,
                    context_text,
                    transcript_ids,
                )
            )

            # 发送结果到前端
            if keywords_result and not isinstance(keywords_result, Exception):
                await safe_ws.send_json(
                    {
                        "type": "keywords",
                        "data": {"keywords": keywords_result},
                    }
                )

                # 持久化关键词
                if context.session_id is not None:
                    await asyncio.to_thread(
                        _persist_keywords,
                        context.session_id,
                        keywords_result,
                        transcript_ids,
                        "llm",
                    )

            if knowledge_result and not isinstance(knowledge_result, Exception):
                await safe_ws.send_json(
                    {
                        "type": "knowledge",
                        "data": knowledge_result,
                    }
                )

                # 持久化知识点
                if context.session_id is not None:
                    await asyncio.to_thread(
                        _persist_knowledge_point,
                        context.session_id,
                        knowledge_result,
                        transcript_ids,
                    )

            if quiz_result and not isinstance(quiz_result, Exception):
                await safe_ws.send_json(
                    {
                        "type": "quiz",
                        "data": quiz_result,
                    }
                )

                # 持久化小测题目
                if context.session_id is not None:
                    await asyncio.to_thread(
                        _persist_quiz_item,
                        context.session_id,
                        quiz_result,
                        transcript_ids,
                    )


def _handle_task_result(task: asyncio.Task) -> None:
    """统一处理异常（避免 Task exception was never retrieved）"""
    if task.cancelled():
        return

    exc = task.exception()
    if exc is not None:
        logger.exception("Background processing failed", exc_info=exc)


def _persist_transcript(
    session_id: int,
    text: str,
    start_time: int | None = None,
    end_time: int | None = None,
) -> int:
    """将转写结果写入数据库。"""
    with Session(get_engine()) as db:
        next_seq = len(list_transcripts_by_session(db, session_id)) + 1
        transcript = create_transcript(
            db,
            session_id=session_id,
            text=text,
            seq=next_seq,
            start_time=start_time,
            end_time=end_time,
        )
        return transcript.id


def _persist_summary(
    session_id: int,
    summary_info: dict,
    transcript_ids: list[int],
    start_time: int | None = None,
    end_time: int | None = None,
) -> int:
    """将实时小结及其映射写入数据库。"""
    with Session(get_engine()) as db:
        summary = create_segment_summary(
            db,
            session_id=session_id,
            text=summary_info["text"],
            start_time=start_time,
            end_time=end_time,
        )
        for transcript_id in transcript_ids:
            link_segment_summary_to_transcript(db, summary.id, transcript_id)
        return summary.id


def _persist_questions(
    session_id: int,
    questions: list[ScoredQuestion],
    transcript_ids: list[int],
) -> list[tuple[str, float, int, int]]:
    """将生成的问题及其映射写入数据库。"""
    created_questions: list[tuple[str, float, int, int]] = []
    with Session(get_engine()) as db:
        for scored_question in questions:
            question = create_question(
                db,
                session_id=session_id,
                text=scored_question.text,
                score=scored_question.score,
            )
            created_questions.append(
                (
                    scored_question.text,
                    scored_question.score,
                    question.id,
                    question.created_at,
                )
            )
            for transcript_id in transcript_ids:
                link_question_to_transcript(db, question.id, transcript_id)
    return created_questions


def _mark_question_asked(question_id: int) -> None:
    """将问题状态更新为已提问。"""
    with Session(get_engine()) as db:
        mark_question_asked(db, question_id)


def _persist_keywords(
    session_id: int,
    keywords: list[str],
    transcript_ids: list[int],
    source: str = "llm",
) -> int:
    """将关键词集合及其映射写入数据库。"""
    with Session(get_engine()) as db:
        # 将关键词列表序列化为 JSON 字符串存储
        keyword_sets_json = json.dumps(keywords, ensure_ascii=False)
        keyword = create_keyword(
            db,
            session_id=session_id,
            keyword_sets=keyword_sets_json,
            source=source,
        )

        # 建立与转写的映射
        for transcript_id in transcript_ids:
            link_keyword_to_transcript(db, keyword.id, transcript_id)

        return keyword.id


def _persist_knowledge_point(
    session_id: int,
    knowledge_info: dict,
    transcript_ids: list[int],
) -> int:
    """将知识点及其映射写入数据库。"""
    with Session(get_engine()) as db:
        knowledge_point = create_knowledge_point(
            db,
            session_id=session_id,
            name=knowledge_info.get("name", ""),
            description=knowledge_info.get("description"),
            difficulty=knowledge_info.get("difficulty"),
        )

        # 建立与转写的映射
        for transcript_id in transcript_ids:
            link_knowledge_point_to_transcript(db, knowledge_point.id, transcript_id)

        return knowledge_point.id


def _persist_quiz_item(
    session_id: int,
    quiz_info: dict,
    transcript_ids: list[int],
) -> int:
    """将小测题目及其映射写入数据库。"""
    with Session(get_engine()) as db:
        quiz_item = create_quiz_item(
            db,
            session_id=session_id,
            question=quiz_info.get("question", ""),
            item_type=quiz_info.get("type"),
            answer=quiz_info.get("answer"),
            explanation=quiz_info.get("explanation"),
        )

        # 建立与转写的映射
        for transcript_id in transcript_ids:
            link_quiz_item_to_transcript(db, quiz_item.id, transcript_id)

        return quiz_item.id

def _background_keyword_extraction(
    session_id: int,
    context_text: str,
    transcript_ids: list[int],
) -> None:
    """后台执行关键词提取（不阻塞主流程）"""
    try:
        keywords_result = keyword_processor.extract_keywords_algorithm(context_text)

        if keywords_result:
            logger.info("后台关键词提取结果: %s", keywords_result)

            # 持久化关键词
            _persist_keywords(
                session_id,
                keywords_result,
                transcript_ids,
                "algorithm",
            )
    except Exception as e:
        logger.error("后台关键词提取失败: %s", e)
