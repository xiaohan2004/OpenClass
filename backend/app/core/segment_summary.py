"""核心业务逻辑 - 阶段小结处理器"""

import logging
from app.services.llm import generate_segment_summary

logger = logging.getLogger(__name__)


class SegmentSummaryProcessor:
    """基于课堂上下文生成阶段性小结"""

    def generate_summary(self, context: str) -> str | None:
        """基于当前课堂上下文生成阶段小结"""
        if not context:
            logger.warning("当前无课堂上下文，跳过阶段小结生成")
            return None

        summary = generate_segment_summary(context).strip()
        logger.info("阶段小结已生成")
        return summary
