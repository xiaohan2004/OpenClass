"""课堂上下文维护"""

import time
from collections import defaultdict
from threading import Lock

from app.config import get_settings
from app.utils.timestamp_queue import HistorySummaryTimestampQueue, TextTimestampQueue

from .segment_summary import SegmentSummaryProcessor

segment_summary_processor = SegmentSummaryProcessor()  # 讲课内容总结处理器实例


def _resolve_refresh_interval(value: object, fallback: float) -> float:
    if isinstance(value, (int, float)) and value > 0:
        return float(value)
    return fallback


class ClassContext:
    """维护课堂讲课文本及历史阶段小结"""

    def __init__(self, session_id: int | None = None) -> None:
        settings = get_settings()
        self.session_id = session_id
        self.lecture_texts = TextTimestampQueue()
        self.history_summaries = HistorySummaryTimestampQueue()
        self.recent_lecture_window = settings.recent_lecture_window
        self.history_summary_window = settings.history_summary_window
        self._config_refresh_interval_seconds = _resolve_refresh_interval(
            getattr(settings, "settings_refresh_interval_seconds", 3.0), 3.0
        )
        self._config_loaded_at = time.monotonic()
        self.last_summary_index = 0
        self._summary_lock = Lock()
        self._transcript_lock = Lock()
        self._question_lock = Lock()
        self._transcript_ids: list[int] = []
        self._transcript_time_ranges: list[tuple[int | None, int | None]] = []
        self._generated_question_ids: dict[str, list[int]] = defaultdict(list)

    def _sync_config(self) -> None:
        """同步热更新配置。"""
        elapsed = time.monotonic() - self._config_loaded_at
        if elapsed < self._config_refresh_interval_seconds:
            return

        settings = get_settings()
        recent_lecture_window = getattr(
            settings, "recent_lecture_window", self.recent_lecture_window
        )
        history_summary_window = getattr(
            settings, "history_summary_window", self.history_summary_window
        )

        if isinstance(recent_lecture_window, int) and recent_lecture_window > 0:
            self.recent_lecture_window = recent_lecture_window

        if isinstance(history_summary_window, int) and history_summary_window > 0:
            self.history_summary_window = history_summary_window

        self._config_refresh_interval_seconds = _resolve_refresh_interval(
            getattr(
                settings,
                "settings_refresh_interval_seconds",
                self._config_refresh_interval_seconds,
            ),
            self._config_refresh_interval_seconds,
        )
        self._config_loaded_at = time.monotonic()

    def add_lecture_text(self, text_start_time: float, text: str) -> None:
        """新增一段讲课文本。"""
        self.lecture_texts.add(timestamp=text_start_time, data=text)

    def add_transcript_id(
        self,
        transcript_id: int,
        start_time: int | None = None,
        end_time: int | None = None,
    ) -> None:
        """记录已入库的转写 ID，保持与 lecture_texts 顺序一致。"""
        with self._transcript_lock:
            self._transcript_ids.append(transcript_id)
            self._transcript_time_ranges.append((start_time, end_time))

    def get_transcript_ids_range(self, start: int, end: int) -> list[int]:
        """获取指定文本索引范围对应的转写 ID。"""
        with self._transcript_lock:
            return list(self._transcript_ids[start:end])

    def get_transcript_time_range(
        self, start: int, end: int
    ) -> tuple[int | None, int | None]:
        """按文本索引范围聚合最早开始时间与最晚结束时间。"""
        with self._transcript_lock:
            ranges = list(self._transcript_time_ranges[start:end])

        if not ranges:
            return None, None

        start_candidates = [
            start_time for start_time, _ in ranges if start_time is not None
        ]
        end_candidates = [end_time for _, end_time in ranges if end_time is not None]
        summary_start_time = min(start_candidates) if start_candidates else None
        summary_end_time = max(end_candidates) if end_candidates else None
        return summary_start_time, summary_end_time

    def get_recent_transcript_ids_for_questions(self) -> list[int]:
        """获取当前提问上下文对应的最近转写 ID。"""
        self._sync_config()
        with self._transcript_lock:
            total_len = len(self._transcript_ids)
            recent_start = max(0, total_len - self.recent_lecture_window)
            return list(self._transcript_ids[recent_start:])

    def register_generated_questions(
        self, question_pairs: list[tuple[str, int]]
    ) -> None:
        """登记已入库的问题 ID，供后续提问时回写状态。"""
        with self._question_lock:
            for question_text, question_id in question_pairs:
                self._generated_question_ids[question_text].append(question_id)

    def consume_generated_question_id(self, question_text: str) -> int | None:
        """按问题文本取出一个待提问的问题 ID。"""
        with self._question_lock:
            question_ids = self._generated_question_ids.get(question_text)
            if not question_ids:
                return None

            question_id = question_ids.pop(0)
            if not question_ids:
                self._generated_question_ids.pop(question_text, None)
            return question_id

    def get_questioning_texts(self) -> str:
        """获取用于提问生成的上下文"""
        self._sync_config()
        total_len = self.lecture_texts.get_count()
        if total_len == 0:
            return ""

        # ===== recent =====
        recent_lecture = self.lecture_texts.get_latest_texts(self.recent_lecture_window)
        recent_start = max(0, total_len - self.recent_lecture_window)
        history_summary = self.history_summaries.get_valid_summaries(recent_start)
        return f"【历史要点】\n{history_summary}\n\n【近期讲解】\n{recent_lecture}"

    def get_latest_lecture_texts(self) -> str:
        """获取最近讲解的纯文本（不包含历史要点）"""
        self._sync_config()
        return self.lecture_texts.get_latest_texts(self.recent_lecture_window)

    def generate_summary_if_needed(self) -> dict | None:
        """在需要时生成阶段小结，返回生成结果及其对应范围。"""
        self._sync_config()
        with self._summary_lock:
            if not self._need_summary():
                return None

            start = self.last_summary_index
            end = self.lecture_texts.get_count()

        if start >= end:
            return None

        texts = self.lecture_texts.get_range_texts(start, end)
        if not texts:
            return None

        summary_text = segment_summary_processor.generate_summary(texts)
        if not summary_text:
            return None

        with self._summary_lock:
            self.history_summaries.add(
                timestamp=time.time(),
                data={"start": start, "end": end, "text": summary_text},
            )
            self.last_summary_index = end

        return {"text": summary_text, "start": start, "end": end}

    def _need_summary(self) -> bool:
        """判断当前是否需要生成阶段小结"""
        self._sync_config()
        total_len = self.lecture_texts.get_count()

        # 未总结的段落数
        unsummarized_count = total_len - self.last_summary_index
        return unsummarized_count >= self.history_summary_window
