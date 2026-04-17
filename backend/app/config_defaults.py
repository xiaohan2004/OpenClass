"""配置默认值与元数据。"""

DEFAULT_DEEPSEEK_API_KEY = ""
DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_QWEN_API_KEY = ""
DEFAULT_MODEL_NAME = "deepseek-chat"
DEFAULT_MAX_TOKENS = 1024
DEFAULT_TEMPERATURE = 1.7
DEFAULT_MAX_QUESTIONS = 10
DEFAULT_QUESTION_CONCURRENT_WORKERS = 1
DEFAULT_RECENT_LECTURE_WINDOW = 240
DEFAULT_HISTORY_SUMMARY_WINDOW = 600
DEFAULT_KEYWORD_KNOWLEDGE_QUIZ_TRIGGER_INTERVAL = 24
DEFAULT_SETTINGS_REFRESH_INTERVAL_SECONDS = 3.0
DEFAULT_DATABASE_URL = "sqlite:///backend/data/openclass.db"
DEFAULT_DATABASE_ECHO = False

DEFAULT_SYSTEM_PROMPT_QUESTION = """你是一名正在课堂上认真听讲的初学者学生。我会提供两部分内容：
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

DEFAULT_SYSTEM_PROMPT_SEGMENT_SUMMARY = """你是一名课堂内容整理助手。

我会提供一段老师刚刚讲的内容（可能存在语音转文字的不准确之处），请你基于这段内容生成一段简要的阶段小结。

要求：
- 聚焦老师刚刚讲过的最核心、最重点内容
- 语言简洁、通顺、清晰、自然
- 适合作为课堂进行中的阶段性小结
- 用于帮助学生回顾和巩固刚刚讲过的内容
- 不要编造上下文中没有的信息
- 只输出小结本身，不要添加标题、说明或其他额外文字
- 不要有任何格式，直接输出一段文本
- 字数严格控制在150字以内，严谨超出
- 内容撑不起150字时不必凑够150字，只是上限150字，不能超过
- 核心宗旨是：就算刚刚没听老师上课，光看给出的150字以内小结也能了解老师刚刚讲了什么"""

DEFAULT_SYSTEM_PROMPT_KEYWORDS = """你是课堂关键词提取助手。

请基于输入内容提取最重要的关键词，优先保留学科概念、术语和方法名。

要求：
- 最多输出{limit}个关键词
- 如果输入内容较少或不够提取出{limit}个关键词，可以适当减少输出数量，但不要输出过多无关或不重要的词
- 输出必须是严格合法的 JSON 数组字符串
- 示例：["机器学习","神经网络"]
- 不要输出 Markdown，不要代码块，不要解释，不要编号，不要输出数组之外的任何文本"""

DEFAULT_SYSTEM_PROMPT_KNOWLEDGE = """你是课堂知识点提取助手。

请基于输入内容提取最重要的知识点，优先保留标准概念、术语和核心方法名。

要求：
- 只输出 1 个知识点
- 输出必须是严格合法的 JSON 对象字符串
- 必须包含 name、description、difficulty 三个字段
- difficulty 必须是 JSON 对象，至少包含 level 字段，level 只能是 easy / medium / hard 之一
- 示例：{"name":"机器学习","description":"...","difficulty":{"level":"medium","reason":"..."}}
- 不要输出 Markdown，不要代码块，不要解释，不要编号，不要输出对象之外的任何文本"""

DEFAULT_SYSTEM_PROMPT_QUIZ = """你是课堂小测生成助手。

请基于输入内容生成用于课堂复习的小测题目，优先覆盖核心知识点。

要求：
- 只输出 1 道题
- 你需要根据当前内容自行判断更适合出什么题型：选择题或简答题
- 输出必须是严格合法的 JSON 对象字符串
- 必须包含 type、question、answer、explanation 四个字段
- type 只能是 choice 或 short_answer
- 如果 type 是 choice，还必须包含 options 字段，且 options 必须是字符串数组
- 如果 type 是 short_answer，则不要包含 options 字段
- 示例：{"type":"choice","question":"...","options":["A...","B..."],"answer":"A","explanation":"..."}
- 不要输出 Markdown，不要代码块，不要解释，不要编号，不要输出对象之外的任何文本"""

DEFAULT_ASR_MODEL = "qwen3-asr-flash"
DEFAULT_ASR_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
DEFAULT_ASR_ENABLE_ITN = False
DEFAULT_ASR_LANGUAGE = "zh"

DEFAULT_TTS_MODEL = "qwen3-tts-flash"
DEFAULT_TTS_BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
DEFAULT_TTS_VOICE = "Cherry"
DEFAULT_TTS_LANGUAGE_TYPE = "Chinese"
DEFAULT_TTS_INSTRUCTIONS = ""
DEFAULT_TTS_OPTIMIZE_INSTRUCTIONS = False

DEFAULT_SETTINGS_VALUES = {
    "deepseek_api_key": DEFAULT_DEEPSEEK_API_KEY,
    "deepseek_base_url": DEFAULT_DEEPSEEK_BASE_URL,
    "qwen_api_key": DEFAULT_QWEN_API_KEY,
    "model_name": DEFAULT_MODEL_NAME,
    "max_tokens": DEFAULT_MAX_TOKENS,
    "temperature": DEFAULT_TEMPERATURE,
    "max_questions": DEFAULT_MAX_QUESTIONS,
    "question_concurrent_workers": DEFAULT_QUESTION_CONCURRENT_WORKERS,
    "recent_lecture_window": DEFAULT_RECENT_LECTURE_WINDOW,
    "history_summary_window": DEFAULT_HISTORY_SUMMARY_WINDOW,
    "keyword_knowledge_quiz_trigger_interval": DEFAULT_KEYWORD_KNOWLEDGE_QUIZ_TRIGGER_INTERVAL,
    "settings_refresh_interval_seconds": DEFAULT_SETTINGS_REFRESH_INTERVAL_SECONDS,
    "database_url": DEFAULT_DATABASE_URL,
    "database_echo": DEFAULT_DATABASE_ECHO,
    "system_prompt_question": DEFAULT_SYSTEM_PROMPT_QUESTION,
    "system_prompt_segment_summary": DEFAULT_SYSTEM_PROMPT_SEGMENT_SUMMARY,
    "system_prompt_keywords": DEFAULT_SYSTEM_PROMPT_KEYWORDS,
    "system_prompt_knowledge": DEFAULT_SYSTEM_PROMPT_KNOWLEDGE,
    "system_prompt_quiz": DEFAULT_SYSTEM_PROMPT_QUIZ,
    "asr_model": DEFAULT_ASR_MODEL,
    "asr_base_url": DEFAULT_ASR_BASE_URL,
    "asr_enable_itn": DEFAULT_ASR_ENABLE_ITN,
    "asr_language": DEFAULT_ASR_LANGUAGE,
    "tts_model": DEFAULT_TTS_MODEL,
    "tts_base_url": DEFAULT_TTS_BASE_URL,
    "tts_voice": DEFAULT_TTS_VOICE,
    "tts_language_type": DEFAULT_TTS_LANGUAGE_TYPE,
    "tts_instructions": DEFAULT_TTS_INSTRUCTIONS,
    "tts_optimize_instructions": DEFAULT_TTS_OPTIMIZE_INSTRUCTIONS,
}

SENSITIVE_SETTING_KEYS = {"deepseek_api_key", "qwen_api_key"}
BOOTSTRAP_SETTING_KEYS = {"database_url", "database_echo"}
