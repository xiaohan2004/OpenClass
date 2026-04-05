"""课堂上下文维护"""

import time

from app.config import get_settings
from app.utils.timestamp_queue import HistorySummaryTimestampQueue, TextTimestampQueue

from .segment_summary import SegmentSummaryProcessor

segment_summary_processor = SegmentSummaryProcessor()  # 讲课内容总结处理器实例


class ClassContext:
    """维护课堂讲课文本及历史阶段小结"""

    def __init__(self) -> None:
        settings = get_settings()
        self.lecture_texts = TextTimestampQueue()
        self.history_summaries = HistorySummaryTimestampQueue()
        self.recent_lecture_window = settings.recent_lecture_window
        self.history_summary_window = settings.history_summary_window
        self.last_summary_index = 0

    def add_lecture_text(self, text_start_time: float, text: str) -> None:
        """新增一段讲课文本，并在达到窗口时生成阶段小结"""
        self.lecture_texts.add(timestamp=text_start_time, data=text)
        if self._need_summary():
            self._do_summary()

    def get_questioning_texts(self) -> str:
        """获取用于提问生成的上下文"""
        total_len = self.lecture_texts.get_count()
        if total_len == 0:
            return ""

        # ===== recent =====
        recent_lecture = self.lecture_texts.get_latest_texts(self.recent_lecture_window)
        recent_start = max(0, total_len - self.recent_lecture_window)
        history_summary = self.history_summaries.get_valid_summaries(recent_start)
        return f"【历史要点】\n{history_summary}\n\n【近期讲解】\n{recent_lecture}"

    def _need_summary(self) -> bool:
        """判断当前是否需要生成阶段小结"""
        total_len = self.lecture_texts.get_count()

        # 未总结的段落数
        unsummarized_count = total_len - self.last_summary_index
        return unsummarized_count >= self.history_summary_window

    def _do_summary(self) -> None:
        """对尚未总结的讲课文本生成一个阶段小结"""
        start = self.last_summary_index
        end = self.lecture_texts.get_count()
        if start >= end:
            return

        texts = self.lecture_texts.get_range_texts(start, end)
        if not texts:
            return

        summary_text = segment_summary_processor.generate_summary(texts)
        if not summary_text:
            return

        # 加入 summary 队列
        self.history_summaries.add(
            timestamp=time.time(),
            data={"start": start, "end": end, "text": summary_text},
        )
        self.last_summary_index = end
