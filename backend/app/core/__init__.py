"""核心业务逻辑模块。"""

import os

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


_DISABLE_KEYWORD_ALGORITHM = os.environ.get(
    "DISABLE_KEYWORD_ALGORITHM",
    "",
).lower() in ("1", "true", "yes")
if not _DISABLE_KEYWORD_ALGORITHM:
    from .keyword_extraction_algorithm import KeywordExtractor, KeywordScore

    __all__.extend(["KeywordExtractor", "KeywordScore"])
