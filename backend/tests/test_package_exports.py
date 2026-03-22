"""
包导出测试 - __init__ 暴露内容验证
"""

import sys
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))

import app
import app.core
import app.services
import app.utils


class TestPackageExports(unittest.TestCase):
    """包导出测试"""

    def test_app_package_importable(self):
        """测试 app 包可导入"""
        self.assertIsNotNone(app)

    def test_core_package_importable(self):
        """测试 core 包可导入"""
        self.assertIsNotNone(app.core)

    def test_services_package_importable(self):
        """测试 services 包可导入"""
        self.assertIsNotNone(app.services)

    def test_utils_exports_queue_classes(self):
        """测试 utils 包导出队列类"""
        self.assertTrue(hasattr(app.utils, "TimestampQueue"))
        self.assertTrue(hasattr(app.utils, "QuestionTimestampQueue"))


def main():
    """运行包导出测试"""
    print("开始运行包导出测试...")

    suite = unittest.TestLoader().loadTestsFromTestCase(TestPackageExports)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
