"""
测试工具模块 - 提供测试数据和辅助函数
"""

import sys
import os
import unittest
from pathlib import Path

# 添加项目路径到Python路径
TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))


class TestUtils:
    """测试工具类"""

    @staticmethod
    def get_sample_teaching_texts():
        """获取示例教学文本"""
        return [
            "今天我们学习Python编程，重点是函数和类的使用。",
            "递归算法是一种重要的编程技巧，函数调用自身来解决问题。",
            "面向对象编程中，类是对象的蓝图，包含属性和方法。",
            "数据结构中的栈和队列是线性表的特殊形式，遵循特定的操作规则。",
            "数据库索引可以大大提高查询效率，但会增加写入开销。"
        ]

    @staticmethod
    def get_sample_questions():
        """获取示例问题"""
        return [
            "什么是函数？",
            "类和对象有什么区别？",
            "递归有什么优缺点？",
            "栈和队列的应用场景是什么？",
            "什么时候应该使用数据库索引？"
        ]

    @staticmethod
    def get_long_teaching_text():
        """获取长教学文本用于测试"""
        return """
        今天我们深入学习Python编程语言的高级特性。首先，让我们回顾一下基础知识：
        Python是一种解释型、高级、通用编程语言，由Guido van Rossum创建，并于1991年首次发布。
        Python的设计哲学强调代码的可读性和简洁性，这使得它成为初学者的理想选择。

        现在让我们进入高级主题。装饰器是Python中非常强大的功能，它允许我们修改函数或类的行为
        而无需永久修改它们。装饰器本质上是一个接受函数作为参数并返回新函数的函数。

        接下来是生成器，它使用yield关键字来创建迭代器。生成器函数在每次调用时不会立即执行，
        而是在需要时才计算值，这大大节省了内存使用。

        上下文管理器通过with语句来管理资源，确保资源的正确分配和释放。最常见的例子是文件操作。

        最后，让我们讨论元类。元类是创建类的类，它允许我们在类创建时动态地修改类的行为。
        虽然元类功能强大，但应该谨慎使用，因为它们会使代码更加复杂。
        """

    @staticmethod
    def create_test_question_batches(count=3):
        """创建测试问题批次"""
        import time
        batches = []

        for i in range(count):
            batch = [
                f"问题{i}-1",
                f"问题{i}-2",
                f"问题{i}-3"
            ]
            timestamp = time.time() + i
            batches.append((timestamp, batch))

        return batches

    @staticmethod
    def mock_llm_response(question_text="这是一个测试问题？"):
        """创建模拟的LLM响应"""
        class MockChoice:
            def __init__(self, content):
                self.message = type('Message', (), {'content': content})()

        class MockResponse:
            def __init__(self, content):
                self.choices = [MockChoice(content)]

        return MockResponse(question_text)


def run_all_tests():
    """运行所有测试模块"""
    # 动态导入所有测试模块
    test_modules = [
        'test_config',
        'test_api',
        'test_core',
        'test_llm_integration'
    ]

    results = []

    for module_name in test_modules:
        print(f"\n{'='*60}")
        print(f"运行测试模块: {module_name}")
        print(f"{'='*60}")

        try:
            # 动态导入并运行测试
            module = __import__(module_name)
            if hasattr(module, 'main'):
                result = module.main()
                results.append((module_name, result == 0))
            else:
                print(f"⚠️  模块 {module_name} 没有main函数")
                results.append((module_name, False))

        except ImportError as e:
            print(f"❌ 无法导入模块 {module_name}: {e}")
            results.append((module_name, False))
        except Exception as e:
            print(f"❌ 运行模块 {module_name} 时出错: {e}")
            results.append((module_name, False))

    # 打印总结
    print(f"\n{'='*60}")
    print("测试总结")
    print(f"{'='*60}")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for module_name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{module_name:<25} {status}")

    print(f"\n总计: {total} 个模块, {passed} 个通过, {total-passed} 个失败")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())