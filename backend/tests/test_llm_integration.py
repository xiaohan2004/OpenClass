"""LLM 集成测试。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.config import SYSTEM_PROMPT_QUESTION, SYSTEM_PROMPT_SEGMENT_SUMMARY
from app.services.llm import (
    generate_keywords,
    generate_knowledge,
    generate_quiz,
    generate_question,
    generate_segment_summary,
    get_llm_client,
)


class TestLLMIntegration(unittest.TestCase):
    def setUp(self):
        self.test_context = "今天我们学习 Python 函数。"
        import app.services.llm

        app.services.llm._llm_client = None

    def test_get_llm_client_no_api_key(self):
        with patch("app.services.llm.get_settings") as mock_settings:
            mock_settings.return_value.deepseek_api_key = ""
            mock_settings.return_value.deepseek_base_url = "https://api.test.com"

            with self.assertRaises(ValueError):
                get_llm_client()

    @patch("app.services.llm.OpenAI")
    def test_get_llm_client_with_api_key(self, mock_openai):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        with patch("app.services.llm.get_settings") as mock_settings:
            mock_settings.return_value.deepseek_api_key = "test-key"
            mock_settings.return_value.deepseek_base_url = "https://api.test.com"

            client = get_llm_client()

        self.assertIs(client, mock_client)
        mock_openai.assert_called_once_with(
            api_key="test-key", base_url="https://api.test.com"
        )

    @patch("app.services.llm.record_service_usage")
    @patch("app.services.llm.get_llm_client")
    def test_generate_question_success(self, mock_get_client, mock_record_usage):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "什么是函数？"
        mock_response.usage = MagicMock(prompt_tokens=12, completion_tokens=6)
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        with patch("app.services.llm.get_settings") as mock_settings:
            mock_settings.return_value.model_name = "test-model"
            mock_settings.return_value.max_tokens = 1024
            mock_settings.return_value.temperature = 1.7

            result = generate_question(self.test_context)

        self.assertEqual(result, "什么是函数？")
        mock_client.chat.completions.create.assert_called_once_with(
            model="test-model",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_QUESTION},
                {"role": "user", "content": self.test_context},
            ],
            max_tokens=1024,
            temperature=1.7,
        )
        mock_record_usage.assert_called_once()

    @patch("app.services.llm.record_service_usage")
    @patch("app.services.llm.get_llm_client")
    def test_generate_segment_summary_success(self, mock_get_client, mock_record_usage):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "这段内容介绍了函数的基本概念。"
        mock_response.usage = MagicMock(prompt_tokens=15, completion_tokens=9)
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        with patch("app.services.llm.get_settings") as mock_settings:
            mock_settings.return_value.model_name = "test-model"
            mock_settings.return_value.max_tokens = 1024
            mock_settings.return_value.temperature = 1.7

            result = generate_segment_summary(self.test_context)

        self.assertEqual(result, "这段内容介绍了函数的基本概念。")
        mock_client.chat.completions.create.assert_called_once_with(
            model="test-model",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_SEGMENT_SUMMARY},
                {"role": "user", "content": self.test_context},
            ],
            max_tokens=1024,
            temperature=1.7,
        )
        mock_record_usage.assert_called_once()

    @patch("app.services.llm.record_service_usage")
    @patch("app.services.llm.get_llm_client")
    def test_generate_keywords_success(self, mock_get_client, mock_record_usage):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '["机器学习","神经网络","监督学习"]'
        mock_response.usage = MagicMock(prompt_tokens=20, completion_tokens=8)
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        with patch("app.services.llm.get_settings") as mock_settings:
            mock_settings.return_value.model_name = "test-model"
            mock_settings.return_value.max_tokens = 1024
            mock_settings.return_value.temperature = 1.7
            mock_settings.return_value.system_prompt_keywords = (
                "请提取关键词，最多输出{limit}个，输出JSON数组"
            )

            result = generate_keywords(self.test_context, limit=3)

        self.assertEqual(result, '["机器学习","神经网络","监督学习"]')
        called_messages = mock_client.chat.completions.create.call_args.kwargs[
            "messages"
        ]
        self.assertEqual(
            called_messages[1], {"role": "user", "content": self.test_context}
        )
        self.assertEqual(
            called_messages[0]["content"], "请提取关键词，最多输出3个，输出JSON数组"
        )
        mock_record_usage.assert_called_once()

    @patch("app.services.llm.record_service_usage")
    @patch("app.services.llm.get_llm_client")
    def test_generate_knowledge_success(self, mock_get_client, mock_record_usage):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"name":"函数","description":"...","difficulty":{"level":"easy"}}'
        )
        mock_response.usage = MagicMock(prompt_tokens=18, completion_tokens=7)
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        with patch("app.services.llm.get_settings") as mock_settings:
            mock_settings.return_value.model_name = "test-model"
            mock_settings.return_value.max_tokens = 1024
            mock_settings.return_value.temperature = 1.7
            mock_settings.return_value.system_prompt_knowledge = (
                "请提取知识点，输出JSON对象"
            )

            result = generate_knowledge(self.test_context)

        self.assertEqual(
            result,
            '{"name":"函数","description":"...","difficulty":{"level":"easy"}}',
        )
        called_messages = mock_client.chat.completions.create.call_args.kwargs[
            "messages"
        ]
        self.assertEqual(called_messages[0]["content"], "请提取知识点，输出JSON对象")
        mock_record_usage.assert_called_once()

    @patch("app.services.llm.record_service_usage")
    @patch("app.services.llm.get_llm_client")
    def test_generate_quiz_success(self, mock_get_client, mock_record_usage):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            '{"type":"short_answer","question":"什么是函数？","answer":"...","explanation":"..."}'
        )
        mock_response.usage = MagicMock(prompt_tokens=18, completion_tokens=7)
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        with patch("app.services.llm.get_settings") as mock_settings:
            mock_settings.return_value.model_name = "test-model"
            mock_settings.return_value.max_tokens = 1024
            mock_settings.return_value.temperature = 1.7
            mock_settings.return_value.system_prompt_quiz = "请生成小测，输出JSON对象"

            result = generate_quiz(self.test_context)

        self.assertEqual(
            result,
            '{"type":"short_answer","question":"什么是函数？","answer":"...","explanation":"..."}',
        )
        called_messages = mock_client.chat.completions.create.call_args.kwargs[
            "messages"
        ]
        self.assertEqual(called_messages[0]["content"], "请生成小测，输出JSON对象")
        mock_record_usage.assert_called_once()


if __name__ == "__main__":
    unittest.main()
