"""
测试运行脚本 - 批量执行 tests 目录下所有 test_*.py 文件并生成总结报告
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 获取项目根目录
TESTS_DIR = Path(__file__).parent
PROJECT_ROOT = TESTS_DIR.parent


class TestRunner:
    """测试运行器"""

    def __init__(self):
        self.results = []
        self.start_time = None
        self.end_time = None

    def discover_test_files(self) -> list[Path]:
        """自动发现 tests 目录下所有 test_*.py 文件。"""
        return sorted(
            path
            for path in TESTS_DIR.glob("test_*.py")
            if path.is_file()
        )

    def run_test(self, test_file: str, test_name: str) -> bool:
        """
        运行单个测试文件

        Args:
            test_file: 测试文件名
            test_name: 测试名称

        Returns:
            True 表示测试通过，False 表示失败
        """
        test_path = TESTS_DIR / test_file

        if not test_path.exists():
            print(f"测试文件不存在: {test_path}")
            self.results.append((test_name, False, "文件不存在"))
            return False

        print(f"\n{'=' * 60}")
        print(f"运行: {test_name}")
        print(f"文件: {test_file}")
        print(f"{'=' * 60}")

        try:
            result = subprocess.run(
                [sys.executable, str(test_path)],
                cwd=str(PROJECT_ROOT),
                capture_output=False,
                timeout=300,
            )

            success = result.returncode == 0
            self.results.append((test_name, success, "通过" if success else "失败"))
            return success

        except subprocess.TimeoutExpired:
            print("测试超时")
            self.results.append((test_name, False, "超时"))
            return False
        except Exception as e:
            print(f"测试执行异常: {e}")
            self.results.append((test_name, False, str(e)))
            return False

    def run_all_tests(self) -> None:
        """运行 tests 目录下所有 test_*.py 测试文件。"""
        self.start_time = datetime.now()

        print("\n" + "=" * 60)
        print("OpenClass 测试套件")
        print("=" * 60)
        print(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"项目根目录: {PROJECT_ROOT}")
        print(f"测试目录: {TESTS_DIR}")

        test_files = self.discover_test_files()
        print(f"发现测试文件数: {len(test_files)}")

        for test_file in test_files:
            self.run_test(test_file.name, test_file.stem)

        self.end_time = datetime.now()

    def print_summary(self) -> None:
        """打印测试总结"""
        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)

        total = len(self.results)
        passed = sum(1 for _, success, _ in self.results if success)
        failed = total - passed

        print(f"\n{'测试名称':<30} {'状态':<10} {'备注':<20}")
        print("-" * 60)
        for test_name, success, remark in self.results:
            status = "通过" if success else "失败"
            print(f"{test_name:<30} {status:<10} {remark:<20}")

        print("\n" + "-" * 60)
        print(f"总计: {total} 个测试")
        if total > 0:
            print(f"通过: {passed} 个 ({passed / total * 100:.1f}%)")
            print(f"失败: {failed} 个 ({failed / total * 100:.1f}%)")
        else:
            print("通过: 0 个 (0.0%)")
            print("失败: 0 个 (0.0%)")

        duration = (self.end_time - self.start_time).total_seconds()
        print(f"耗时: {duration:.2f} 秒")

        print("\n" + "=" * 60)
        if failed == 0:
            print("所有测试通过")
        else:
            print(f"有 {failed} 个测试失败")
        print("=" * 60)

    def save_report(self, report_file: str = "TestReport.txt") -> None:
        """
        保存测试报告到文件

        Args:
            report_file: 报告文件名
        """
        report_path = TESTS_DIR / report_file

        total = len(self.results)
        passed = sum(1 for _, success, _ in self.results if success)
        failed = total - passed
        duration = (self.end_time - self.start_time).total_seconds()

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("OpenClass 测试报告\n")
            f.write("=" * 60 + "\n\n")

            f.write(f"生成时间: {self.end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"项目根目录: {PROJECT_ROOT}\n")
            f.write(f"测试目录: {TESTS_DIR}\n\n")

            f.write("测试结果\n")
            f.write("-" * 60 + "\n")
            f.write(f"{'测试名称':<30} {'状态':<10} {'备注':<20}\n")
            f.write("-" * 60 + "\n")

            for test_name, success, remark in self.results:
                status = "通过" if success else "失败"
                f.write(f"{test_name:<30} {status:<10} {remark:<20}\n")

            f.write("\n" + "-" * 60 + "\n")
            f.write(f"总计: {total} 个测试\n")
            if total > 0:
                f.write(f"通过: {passed} 个 ({passed / total * 100:.1f}%)\n")
                f.write(f"失败: {failed} 个 ({failed / total * 100:.1f}%)\n")
            else:
                f.write("通过: 0 个 (0.0%)\n")
                f.write("失败: 0 个 (0.0%)\n")
            f.write(f"耗时: {duration:.2f} 秒\n")

            f.write("\n" + "=" * 60 + "\n")
            if failed == 0:
                f.write("所有测试通过\n")
            else:
                f.write(f"有 {failed} 个测试失败\n")
            f.write("=" * 60 + "\n")

        print(f"\n测试报告已保存: {report_path}")


def main():
    """主函数"""
    runner = TestRunner()

    try:
        runner.run_all_tests()
        runner.print_summary()
        runner.save_report()

        failed = sum(1 for _, success, _ in runner.results if not success)
        sys.exit(0 if failed == 0 else 1)

    except KeyboardInterrupt:
        print("\n\n用户中断测试")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试运行异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
