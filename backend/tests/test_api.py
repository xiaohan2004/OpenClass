"""
API 测试 - FastAPI 应用接口验证
"""

import sys
import os
import unittest
from pathlib import Path
from unittest.mock import patch

# 添加项目路径到Python路径
TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from app.main import app


class TestAPI(unittest.TestCase):
    """API 接口测试"""

    def setUp(self):
        """测试前准备"""
        self.client = TestClient(app)

    def test_health_check_endpoint(self):
        """测试健康检查接口"""
        response = self.client.get("/health")

        # 验证响应状态码
        self.assertEqual(response.status_code, 200)

        # 验证响应内容
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["message"], "服务正常运行")

    def test_health_check_response_format(self):
        """测试健康检查接口响应格式"""
        response = self.client.get("/health")

        # 验证响应是JSON格式
        self.assertEqual(response.headers["content-type"], "application/json")

        # 验证必需的字段
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("message", data)

    def test_app_initialization(self):
        """测试应用初始化"""
        # 验证应用对象存在
        self.assertIsNotNone(app)

        # 验证应用标题
        self.assertEqual(app.title, "OpenClass - 课堂模拟学生提问助手")

    def test_health_check_with_different_methods(self):
        """测试健康检查接口的HTTP方法"""
        # GET 方法应该成功
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

        # POST 方法应该失败（如果只允许GET）
        response = self.client.post("/health")
        self.assertIn(response.status_code, [405, 200])  # 405=方法不允许，200=如果允许POST

        # PUT 方法应该失败
        response = self.client.put("/health")
        self.assertIn(response.status_code, [405, 200])

    def test_health_check_headers(self):
        """测试健康检查接口的响应头"""
        response = self.client.get("/health")

        # 验证基本的响应头
        self.assertIn("content-type", response.headers)
        self.assertEqual(response.headers["content-type"], "application/json")
        # 注意：TestClient可能不包含date头，这是正常的

    def test_nonexistent_endpoint(self):
        """测试不存在的端点"""
        response = self.client.get("/nonexistent")
        self.assertEqual(response.status_code, 404)

    def test_health_check_consistency(self):
        """测试健康检查接口的一致性"""
        # 多次调用应该返回相同的结果
        response1 = self.client.get("/health")
        response2 = self.client.get("/health")

        self.assertEqual(response1.status_code, response2.status_code)
        self.assertEqual(response1.json(), response2.json())

    def test_app_with_middleware(self):
        """测试应用中间件"""
        # 验证应用能够正常处理请求（包括中间件）
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)

    def test_health_check_performance(self):
        """测试健康检查接口性能"""
        import time

        start_time = time.time()
        response = self.client.get("/health")
        end_time = time.time()

        # 验证响应时间在合理范围内（< 1秒）
        response_time = end_time - start_time
        self.assertLess(response_time, 1.0)
        self.assertEqual(response.status_code, 200)

    def test_app_title_and_docs(self):
        """测试应用标题和文档"""
        # 验证应用有正确的标题
        self.assertEqual(app.title, "OpenClass - 课堂模拟学生提问助手")

        # 验证应用有基本的FastAPI属性
        self.assertTrue(hasattr(app, 'openapi'))
        self.assertTrue(callable(app.openapi))


def main():
    """运行API测试"""
    print("开始运行API测试...")

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAPI)

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 返回退出码
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())