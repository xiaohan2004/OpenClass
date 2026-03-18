"""
LLM 集成测试 - DeepSeek API 服务验证
"""

import sys
import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加项目路径到Python路径
TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.services.llm import generate_question, get_llm_client
from app.config import get_settings, SYSTEM_PROMPT_QUESTION


class TestLLMIntegration(unittest.TestCase):
    """LLM 服务集成测试"""

    def setUp(self):
        """测试前准备"""
        self.test_context = "今天我们学习Python编程，重点是函数和类的使用。"

    def test_get_llm_client_no_api_key(self):
        """测试没有API key时的客户端创建"""
        # 重置全局客户端变量
        import app.services.llm
        app.services.llm._llm_client = None

        # 模拟没有API key的配置
        with patch('app.services.llm.get_settings') as mock_settings:
            mock_settings.return_value.deepseek_api_key = ""
            mock_settings.return_value.deepseek_base_url = "https://api.test.com"

            with self.assertRaises(ValueError) as context:
                get_llm_client()

            self.assertIn("DEEPSEEK_API_KEY", str(context.exception))

    @patch('app.services.llm.OpenAI')
    def test_get_llm_client_with_api_key(self, mock_openai):
        """测试有API key时的客户端创建"""
        # 重置全局客户端变量以确保重新创建
        import app.services.llm
        app.services.llm._llm_client = None

        # 模拟OpenAI客户端
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # 模拟配置
        with patch('app.services.llm.get_settings') as mock_settings:
            mock_settings.return_value.deepseek_api_key = "test-key"
            mock_settings.return_value.deepseek_base_url = "https://api.test.com"

            client = get_llm_client()

            # 验证客户端创建
            mock_openai.assert_called_once_with(
                api_key="test-key",
                base_url="https://api.test.com"
            )
            self.assertEqual(client, mock_client)

    @patch('app.services.llm.get_llm_client')
    def test_generate_question_success(self, mock_get_client):
        """测试成功生成问题"""
        # 模拟配置
        with patch('app.services.llm.get_settings') as mock_settings:
            mock_settings.return_value.model_name = "test-model"
            mock_settings.return_value.max_tokens = 1024
            mock_settings.return_value.temperature = 1.7

            # 模拟OpenAI客户端响应
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "什么是函数？"
            mock_client.chat.completions.create.return_value = mock_response
            mock_get_client.return_value = mock_client

            # 调用函数
            result = generate_question(self.test_context)

            # 验证调用参数
            mock_client.chat.completions.create.assert_called_once_with(
                model="test-model",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_QUESTION},
                    {"role": "user", "content": self.test_context}
                ],
                max_tokens=1024,
                temperature=1.7
            )

            # 验证结果
            self.assertEqual(result, "什么是函数？")

    @patch('app.services.llm.get_llm_client')
    def test_generate_question_api_error(self, mock_get_client):
        """测试API调用错误处理"""
        # 模拟API错误
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_get_client.return_value = mock_client

        # 验证异常传播
        with self.assertRaises(Exception) as context:
            generate_question(self.test_context)

        self.assertIn("API Error", str(context.exception))

    def test_system_prompt_content(self):
        """测试系统提示词内容"""
        # 验证提示词不为空
        self.assertIsNotNone(SYSTEM_PROMPT_QUESTION)
        self.assertGreater(len(SYSTEM_PROMPT_QUESTION), 0)

        # 验证提示词包含关键内容
        self.assertIn("学生", SYSTEM_PROMPT_QUESTION)
        self.assertIn("问题", SYSTEM_PROMPT_QUESTION)
        self.assertIn("50字", SYSTEM_PROMPT_QUESTION)

    @patch('app.services.llm.get_llm_client')
    def test_generate_question_empty_context(self, mock_get_client):
        """测试空上下文的问题生成"""
        # 模拟配置
        with patch('app.services.llm.get_settings') as mock_settings:
            mock_settings.return_value.model_name = "test-model"
            mock_settings.return_value.max_tokens = 1024
            mock_settings.return_value.temperature = 1.7

            # 模拟OpenAI客户端响应
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "nope"
            mock_client.chat.completions.create.return_value = mock_response
            mock_get_client.return_value = mock_client

            # 调用函数
            result = generate_question("")

            # 验证结果
            self.assertEqual(result, "nope")

    @patch('app.services.llm.get_llm_client')
    def test_generate_question_long_context(self, mock_get_client):
        """测试长文本上下文的问题生成"""
        # 生成长文本
        long_context = "Python编程" * 100  # 创建长文本

        # 模拟配置
        with patch('app.services.llm.get_settings') as mock_settings:
            mock_settings.return_value.model_name = "test-model"
            mock_settings.return_value.max_tokens = 1024
            mock_settings.return_value.temperature = 1.7

            # 模拟OpenAI客户端响应
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Python编程有什么特点？"
            mock_client.chat.completions.create.return_value = mock_response
            mock_get_client.return_value = mock_client

            # 调用函数
            result = generate_question(long_context)

            # 验证调用时传递了长文本
            call_args = mock_client.chat.completions.create.call_args
            messages = call_args[1]['messages']
            self.assertEqual(messages[1]['content'], long_context)
            self.assertEqual(result, "Python编程有什么特点？")

    def test_client_singleton_pattern(self):
        """测试客户端单例模式"""
        # 重置全局变量
        import app.services.llm
        app.services.llm._llm_client = None

        # 模拟配置
        with patch('app.services.llm.get_settings') as mock_settings:
            mock_settings.return_value.deepseek_api_key = "test-key"
            mock_settings.return_value.deepseek_base_url = "https://api.test.com"

            # 模拟OpenAI客户端
            with patch('app.services.llm.OpenAI') as mock_openai:
                mock_client = MagicMock()
                mock_openai.return_value = mock_client

                # 第一次调用
                client1 = get_llm_client()

                # 第二次调用
                client2 = get_llm_client()

                # 验证是同一个实例
                self.assertIs(client1, client2)
                self.assertIs(client1, mock_client)

                # 验证OpenAI只被调用了一次
                mock_openai.assert_called_once()


def main():
    """运行LLM集成测试"""
    print("开始运行LLM集成测试...")

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestLLMIntegration)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 返回退出码
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())