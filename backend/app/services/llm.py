"""
LLM 服务层 - DeepSeek 集成
"""

import logging
import time

from openai import OpenAI

from app.config import (
    SYSTEM_PROMPT_QUESTION,
    SYSTEM_PROMPT_SEGMENT_SUMMARY,
    get_settings,
)
from app.services.metrics import record_service_usage
from app.utils.time import now_ts

logger = logging.getLogger(__name__)

_llm_client = None


def get_llm_client() -> OpenAI:
    """获取 DeepSeek 客户端单例"""
    global _llm_client
    if _llm_client is None:
        settings = get_settings()
        api_key = settings.deepseek_api_key
        base_url = settings.deepseek_base_url

        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY 未在环境变量中设置，请检查 .env 文件")

        _llm_client = OpenAI(api_key=api_key, base_url=base_url)

    return _llm_client


def _usage_value(usage, key: str) -> int:
    """从响应 usage 中提取数值。"""
    if usage is None:
        return 0

    value = getattr(usage, key, None)
    if value is None and isinstance(usage, dict):
        value = usage.get(key)

    return int(value or 0)


def generate_question(context: str) -> str:
    """
    根据教师讲课文本生成学生可能提出的问题

    Args:
        context: 讲课上下文

    Returns:
        生成的问题字符串
    """
    settings = get_settings()
    client = get_llm_client()
    request_start_time = now_ts()
    start_time = time.perf_counter()

    try:
        response = client.chat.completions.create(
            model=settings.model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_QUESTION},
                {"role": "user", "content": context},
            ],
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
        )
        content = response.choices[0].message.content
        usage = getattr(response, "usage", None)
        record_service_usage(
            service_type="llm",
            request_model_name=settings.model_name,
            input_value=_usage_value(usage, "prompt_tokens") or len(context),
            output_value=_usage_value(usage, "completion_tokens") or len(content or ""),
            start_time=request_start_time,
            latency=int((time.perf_counter() - start_time) * 1000),
            status="success",
            request_content=context,
            response_content=response,
        )
        return content
    except Exception as e:
        logger.error("问题生成失败: %s", e)
        record_service_usage(
            service_type="llm",
            request_model_name=settings.model_name,
            input_value=len(context),
            output_value=0,
            start_time=request_start_time,
            latency=int((time.perf_counter() - start_time) * 1000),
            status="failed",
            error=str(e),
            request_content=context,
        )
        raise


def generate_segment_summary(context: str) -> str:
    """
    根据课堂上下文生成阶段小结。

    Args:
        context: 课堂上下文

    Returns:
        生成的阶段小结文本
    """
    settings = get_settings()
    client = get_llm_client()
    request_start_time = now_ts()
    start_time = time.perf_counter()

    try:
        response = client.chat.completions.create(
            model=settings.model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_SEGMENT_SUMMARY},
                {"role": "user", "content": context},
            ],
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
        )
        content = response.choices[0].message.content
        usage = getattr(response, "usage", None)
        record_service_usage(
            service_type="llm",
            request_model_name=settings.model_name,
            input_value=_usage_value(usage, "prompt_tokens") or len(context),
            output_value=_usage_value(usage, "completion_tokens") or len(content or ""),
            start_time=request_start_time,
            latency=int((time.perf_counter() - start_time) * 1000),
            status="success",
            request_content=context,
            response_content=response,
        )
        return content
    except Exception as e:
        logger.error("阶段小结生成失败: %s", e)
        record_service_usage(
            service_type="llm",
            request_model_name=settings.model_name,
            input_value=len(context),
            output_value=0,
            start_time=request_start_time,
            latency=int((time.perf_counter() - start_time) * 1000),
            status="failed",
            error=str(e),
            request_content=context,
        )
        raise
