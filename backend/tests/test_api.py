"""
API 测试 - FastAPI 应用接口验证
"""

import asyncio
import sys
import time
import unittest
from pathlib import Path

import httpx

# 添加项目路径到 Python 路径
TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app


class TestAPI(unittest.TestCase):
    """API 接口测试"""

    async def _request(self, method: str, path: str):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://testserver"
        ) as client:
            return await client.request(method, path)

    def request(self, method: str, path: str):
        return asyncio.run(self._request(method, path))

    def test_health_check_endpoint(self):
        """测试健康检查接口"""
        response = self.request("GET", "/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "message": "服务正常运行"})

    def test_health_check_response_format(self):
        """测试健康检查接口响应格式"""
        response = self.request("GET", "/health")

        self.assertIn("application/json", response.headers["content-type"])
        data = response.json()
        self.assertIn("status", data)
        self.assertIn("message", data)

    def test_app_initialization(self):
        """测试应用初始化"""
        self.assertIsNotNone(app)
        self.assertEqual(app.title, "OpenClass - 课堂模拟学生提问助手")

    def test_health_check_with_different_methods(self):
        """测试健康检查接口的 HTTP 方法"""
        self.assertEqual(self.request("GET", "/health").status_code, 200)
        self.assertEqual(self.request("POST", "/health").status_code, 405)
        self.assertEqual(self.request("PUT", "/health").status_code, 405)

    def test_nonexistent_endpoint(self):
        """测试不存在的端点"""
        response = self.request("GET", "/nonexistent")
        self.assertEqual(response.status_code, 404)

    def test_health_check_consistency(self):
        """测试健康检查接口结果一致"""
        response1 = self.request("GET", "/health")
        response2 = self.request("GET", "/health")

        self.assertEqual(response1.status_code, response2.status_code)
        self.assertEqual(response1.json(), response2.json())

    def test_health_check_performance(self):
        """测试健康检查接口性能"""
        start = time.time()
        response = self.request("GET", "/health")
        duration = time.time() - start

        self.assertEqual(response.status_code, 200)
        self.assertLess(duration, 1.0)

    def test_app_openapi_available(self):
        """测试应用 openapi 能力存在"""
        self.assertTrue(hasattr(app, "openapi"))
        self.assertTrue(callable(app.openapi))

    def test_websocket_route_registered(self):
        """测试 WebSocket 路由已注册"""
        # 检查路由是否存在
        websocket_routes = [
            route
            for route in app.routes
            if hasattr(route, "path") and "ws" in route.path
        ]
        self.assertGreater(len(websocket_routes), 0, "WebSocket 路由未找到")

        # 检查特定路由
        ws_paths = {route.path for route in websocket_routes if hasattr(route, "path")}
        self.assertIn("/ws/session/{session_id}", ws_paths)


def main():
    """运行 API 测试"""
    print("开始运行 API 测试...")

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAPI)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
