"""
LLM 服务层 - DeepSeek 集成
"""

import logging
from openai import OpenAI
from app.config import get_settings, SYSTEM_PROMPT_QUESTION

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
        return response.choices[0].message.content
    except Exception as e:
        logger.error("问题生成失败: %s", e)
        raise
