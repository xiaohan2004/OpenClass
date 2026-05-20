"""核心业务逻辑模块。"""

from .classcontext import ClassContext
from .knowledge import KnowledgeProcessor
from .keyword import KeywordProcessor
from .main_flow import ask_question, handle_audio, start_background_tasks
from .quiz import QuizProcessor
from .question import QuestionProcessor
from .report import (
    LectureReportAgent,
    ReportProcessor,
    create_default_lecture_report_agent,
)
from .segment_summary import SegmentSummaryProcessor

__all__ = [
    "ClassContext",
    "KnowledgeProcessor",
    "KeywordProcessor",
    "QuestionProcessor",
    "LectureReportAgent",
    "ReportProcessor",
    "create_default_lecture_report_agent",
    "QuizProcessor",
    "SegmentSummaryProcessor",
    "ask_question",
    "handle_audio",
    "start_background_tasks",
]


# 延迟加载重量级类型，仅在传统算法未禁用时才导入
_keyword_extraction_algorithm = None


def __getattr__(name: str):
    """延迟导入 KeywordExtractor 和 KeywordScore。"""
    global _keyword_extraction_algorithm
    import os
    _DISABLE_KEYWORD_ALGORITHM = os.environ.get("DISABLE_KEYWORD_ALGORITHM", "").lower() in ("1", "true", "yes")
    if _DISABLE_KEYWORD_ALGORITHM:
        raise ImportError(
            "KeywordExtractor 和 KeywordScore 已被 DISABLE_KEYWORD_ALGORITHM 禁用"
        )
    if name in ("KeywordExtractor", "KeywordScore"):
        if _keyword_extraction_algorithm is None:
            from . import keyword_extraction_algorithm
            _keyword_extraction_algorithm = keyword_extraction_algorithm
        return getattr(_keyword_extraction_algorithm, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
