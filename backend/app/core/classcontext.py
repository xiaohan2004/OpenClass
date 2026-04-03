"""课堂上下文维护"""

from app.utils.timestamp_queue import TextTimestampQueue


class ClassContext:
    """维护课堂讲课文本上下文"""

    def __init__(self) -> None:
        self.lecture_texts = TextTimestampQueue()

    def add_lecture_text(self, text_start_time: float, text: str) -> None:
        """新增一段讲课文本"""
        self.lecture_texts.add(timestamp=text_start_time, data=text)

    def get_recent_lecture_text(self) -> str:
        """获取最新的讲课文本"""
        return self.lecture_texts.get_latest_texts()
