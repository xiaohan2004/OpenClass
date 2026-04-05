"""
配置管理 - 提示词、模型参数
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        protected_namespaces=("settings_",),
    )

    # LLM 配置
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    qwen_api_key: str = ""

    # 模型参数
    model_name: str = "deepseek-chat"
    max_tokens: int = 1024
    temperature: float = 1.7

    # 提问队列配置
    max_questions: int = 10  # 问题队列最大长度

    # 并发配置
    question_concurrent_workers: int = 1  # 并发提问的线程数
    
    # 上下文维护配置
    recent_lecture_window: int = 240  # 最近讲解文本的段落数
    history_summary_window: int = 600  # 总结历史要点的段落数
    
    # 数据库配置
    database_url: str = "sqlite:///backend/data/openclass.db"
    database_echo: bool = False

@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 提示词配置
SYSTEM_PROMPT_QUESTION = """你是一名正在课堂上认真听讲的初学者学生。我会提供两部分内容：
1. 【历史要点】：之前讲过的内容概要，供你了解上下文
2. 【近期讲解】：老师刚刚讲的内容（可能存在语音转文字的不准确之处）

请你主要针对【近期讲解】提出一个在听课过程中自然想到、可能会当场举手问老师的问题。可以结合【历史要点】来思考。

提问优先级：
首先，老师讲述有错误，要优先提出质疑性的问题。
其次，如果存在不能理解的内容，提出澄清性的问题。
最后，基于老师讲解内容的延伸性问题，可以是结合自身经验也可以是对知识的扩展。

要求：
- 你只是一个初学者，不要提出过于专业或复杂的问题，问题的复杂度和深度不要过高
- 问问题的方式要简洁，要考虑这个是要转换成语音的
- 字数控制在50字以内
- 问题要紧扣老师的讲解内容，体现你在理解时的思考
- 不要自己解答问题，不要带着答案问问题，不要像一个已经学过的相关知识的学生提问
- 提问语气要真实、口语化，像真实课堂上的学生发问
- 只输出问题本身，不要回答、解释或添加多余文字"""

SYSTEM_PROMPT_SEGMENT_SUMMARY = """你是一名课堂内容整理助手。

我会提供一段老师刚刚讲的内容（可能存在语音转文字的不准确之处），请你基于这段内容生成一段简要的阶段小结。

要求：
- 聚焦老师刚刚讲过的核心内容
- 语言简洁、通顺、清晰、自然
- 适合作为课堂进行中的阶段性小结
- 不要编造上下文中没有的信息
- 只输出小结本身，不要添加标题、说明或其他额外文字"""
