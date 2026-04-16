"""
LLM 服务层 - DeepSeek 集成
"""

import logging
import time
from functools import lru_cache

from openai import OpenAI

from app.config import (
    SYSTEM_PROMPT_QUESTION,
    SYSTEM_PROMPT_SEGMENT_SUMMARY,
    get_settings,
)
from app.services.metrics import record_service_usage
from app.utils.request_capture import capture_request
from app.utils.time import now_ts
from app.utils.usage import extract_usage, usage_value

logger = logging.getLogger(__name__)


def _resolve_string_setting(value: object, fallback: str) -> str:
    if isinstance(value, str) and value:
        return value
    return fallback


@lru_cache(maxsize=8)
def _build_llm_client(api_key: str, base_url: str) -> OpenAI:
    return OpenAI(api_key=api_key, base_url=base_url)


def get_llm_client() -> OpenAI:
    """获取 DeepSeek 客户端单例"""
    settings = get_settings()
    api_key = settings.deepseek_api_key
    if not api_key:
        raise ValueError("DeepSeek API Key 未配置，无法调用 LLM 服务")

    return _build_llm_client(api_key, settings.deepseek_base_url)


def _generate_with_prompt(
    *,
    context: str,
    system_prompt: str,
) -> str:
    """按给定系统提示词调用 LLM 并记录服务统计。"""
    settings = get_settings()
    client = get_llm_client()
    request_start_time = now_ts()
    start_time = time.perf_counter()

    try:
        response, request = capture_request(client.chat.completions.create)(
            model=settings.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": context},
            ],
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
        )
    except Exception as e:
        request = getattr(e, "request_record", None)
        record_service_usage(
            service_type="llm",
            request_model_name=settings.model_name,
            input_value=0,
            output_value=0,
            start_time=request_start_time,
            latency=int((time.perf_counter() - start_time) * 1000),
            status="failed",
            error=str(e),
            request_content=request,
        )
        raise

    try:
        content = response.choices[0].message.content
        usage = extract_usage(response)
        record_service_usage(
            service_type="llm",
            request_model_name=settings.model_name,
            input_value=usage_value(usage, "prompt_tokens"),
            output_value=usage_value(usage, "completion_tokens"),
            start_time=request_start_time,
            latency=int((time.perf_counter() - start_time) * 1000),
            status="success",
            request_content=request,
            response_content=response,
        )
        return content
    except Exception as e:
        record_service_usage(
            service_type="llm",
            request_model_name=settings.model_name,
            input_value=0,
            output_value=0,
            start_time=request_start_time,
            latency=int((time.perf_counter() - start_time) * 1000),
            status="failed",
            error=str(e),
            request_content=request,
            response_content=response,
        )
        raise


def generate_question(context: str) -> str:
    """
    根据教师讲课文本生成学生可能提出的问题

    Args:
        context: 讲课上下文

    Returns:
        生成的问题字符串
    """
    try:
        settings = get_settings()
        system_prompt = _resolve_string_setting(
            getattr(settings, "system_prompt_question", None),
            SYSTEM_PROMPT_QUESTION,
        )
        return _generate_with_prompt(
            context=context,
            system_prompt=system_prompt,
        )
    except Exception as e:
        logger.error("问题生成失败: %s", e)
        raise


def generate_segment_summary(context: str) -> str:
    """
    根据课堂上下文生成阶段小结。

    Args:
        context: 课堂上下文

    Returns:
        生成的阶段小结文本
    """
    try:
        settings = get_settings()
        system_prompt = _resolve_string_setting(
            getattr(settings, "system_prompt_segment_summary", None),
            SYSTEM_PROMPT_SEGMENT_SUMMARY,
        )
        return _generate_with_prompt(
            context=context,
            system_prompt=system_prompt,
        )
    except Exception as e:
        logger.error("阶段小结生成失败: %s", e)
        raise
