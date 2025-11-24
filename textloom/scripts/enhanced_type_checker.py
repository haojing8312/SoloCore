#!/usr/bin/env python3
"""
增强的TypeScript风格类型检查工具
结合mypy、自定义分析器和实用工具
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class EnhancedTypeChecker:
    """增强的类型检查器"""

    def __init__(self, project_root: str) -> None:
        self.project_root = Path(project_root)
        self.results: Dict[str, Any] = {}

    def run_mypy_analysis(self) -> Dict[str, Any]:
        """运行mypy类型检查"""
        print("🔍 运行 mypy 类型检查...")

        try:
            # 基础mypy检查
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "mypy",
                    ".",
                    "--show-error-codes",
                    "--no-error-summary",
                    "--json-report",
                    "mypy_report",
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=120,
            )

            mypy_output = result.stdout + result.stderr

            # 尝试读取JSON报告
            mypy_json_report = {}
            json_report_path = self.project_root / "mypy_report" / "index.json"
            if json_report_path.exists():
                try:
                    with open(json_report_path, "r") as f:
                        mypy_json_report = json.load(f)
                except Exception as e:
                    print(f"⚠️ 无法读取mypy JSON报告: {e}")

            return {
                "status": "completed" if result.returncode == 0 else "failed",
                "return_code": result.returncode,
                "output": mypy_output[:2000],  # 限制输出长度
                "json_report": mypy_json_report,
                "error_count": mypy_output.count("error:"),
                "warning_count": mypy_output.count("warning:"),
            }

        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": "mypy 检查超时"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def run_custom_analysis(self) -> Dict[str, Any]:
        """运行自定义类型分析"""
        print("📊 运行自定义类型分析...")

        try:
            # 运行我们的自定义分析器
            from type_check_analyzer import ProjectTypeAnalyzer

            analyzer = ProjectTypeAnalyzer(str(self.project_root))
            return analyzer.analyze_project()

        except Exception as e:
            return {"status": "error", "error": f"自定义分析失败: {str(e)}"}

    def check_import_quality(self) -> Dict[str, Any]:
        """检查导入质量"""
        print("📦 检查导入质量...")

        try:
            # 运行isort检查
            result = subprocess.run(
                ["uv", "run", "isort", ".", "--check-only", "--diff"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            import_issues = []
            if result.returncode != 0:
                import_issues = result.stdout.split("\n")[:10]  # 限制输出

            return {
                "imports_sorted": result.returncode == 0,
                "issues": import_issues,
                "suggestion": (
                    "运行 'uv run isort .' 自动修复导入排序" if import_issues else None
                ),
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def analyze_complexity(self) -> Dict[str, Any]:
        """分析代码复杂度"""
        print("🧮 分析代码复杂度...")

        complex_files = []

        # 简单的复杂度启发式分析
        for py_file in self.project_root.rglob("*.py"):
            if any(
                exclude in str(py_file)
                for exclude in ["venv", ".venv", "__pycache__", "alembic/versions"]
            ):
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # 简单的复杂度指标
                line_count = len(content.split("\n"))
                function_count = content.count("def ")
                class_count = content.count("class ")

                if line_count > 300 or function_count > 15:
                    complex_files.append(
                        {
                            "file": str(py_file.relative_to(self.project_root)),
                            "lines": line_count,
                            "functions": function_count,
                            "classes": class_count,
                            "complexity_score": (line_count / 50)
                            + (function_count * 2)
                            + (class_count * 3),
                        }
                    )

            except Exception:
                continue

        # 按复杂度排序
        complex_files.sort(key=lambda x: x["complexity_score"], reverse=True)

        return {
            "complex_files": complex_files[:10],  # 最复杂的10个文件
            "suggestions": (
                [
                    "考虑拆分大型文件为多个模块",
                    "为复杂函数添加详细的类型注解",
                    "考虑使用抽象基类简化继承关系",
                ]
                if complex_files
                else []
            ),
        }

    def generate_recommendations(self) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 基于mypy结果的建议
        if "mypy" in self.results:
            mypy_result = self.results["mypy"]
            if mypy_result.get("error_count", 0) > 10:
                recommendations.append("🔴 高优先级: 修复关键的mypy类型错误")
            elif mypy_result.get("error_count", 0) > 0:
                recommendations.append("🟡 中优先级: 修复剩余的mypy类型错误")
            else:
                recommendations.append("✅ mypy检查通过，类型系统健康")

        # 基于覆盖率的建议
        if "custom_analysis" in self.results:
            analysis = self.results["custom_analysis"]
            if "overall_statistics" in analysis:
                coverage = analysis["overall_statistics"].get("overall_coverage", 0)
                if coverage < 50:
                    recommendations.append("🔴 立即为核心函数添加类型注解")
                elif coverage < 80:
                    recommendations.append("🟡 继续提升类型注解覆盖率")
                else:
                    recommendations.append("🟢 类型覆盖率良好，考虑启用严格模式")

        # 基于导入质量的建议
        if "imports" in self.results:
            if not self.results["imports"].get("imports_sorted", True):
                recommendations.append("🔧 运行 isort 修复导入排序")

        # 基于复杂度的建议
        if "complexity" in self.results:
            complex_files = self.results["complexity"].get("complex_files", [])
            if complex_files:
                recommendations.append(f"♻️ 重构 {len(complex_files)} 个复杂文件")

        # 通用建议
        recommendations.extend(
            [
                "📋 在CI/CD中集成类型检查",
                "🎯 为公共API添加详细的类型注解",
                "📚 考虑使用Protocol定义接口",
                "🛡️ 启用mypy的严格模式配置",
            ]
        )

        return recommendations[:8]  # 限制建议数量

    def run_full_analysis(self) -> Dict[str, Any]:
        """运行完整的类型分析"""
        print("🚀 开始完整的TypeScript风格类型分析...\n")

        self.results = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
        }

        # 1. MyPy分析
        self.results["mypy"] = self.run_mypy_analysis()

        # 2. 自定义分析
        self.results["custom_analysis"] = self.run_custom_analysis()

        # 3. 导入质量检查
        self.results["imports"] = self.check_import_quality()

        # 4. 复杂度分析
        self.results["complexity"] = self.analyze_complexity()

        # 5. 生成建议
        self.results["recommendations"] = self.generate_recommendations()

        return self.results

    def print_summary(self) -> None:
        """打印分析摘要"""
        print("\n" + "=" * 60)
        print("📊 TextLoom TypeScript风格类型分析摘要")
        print("=" * 60)

        # MyPy结果
        if "mypy" in self.results:
            mypy = self.results["mypy"]
            status_icon = "✅" if mypy.get("return_code", 1) == 0 else "❌"
            print(f"{status_icon} MyPy检查: {mypy.get('status', '未知')}")
            if mypy.get("error_count", 0) > 0:
                print(f"   ❌ 错误数量: {mypy['error_count']}")
            if mypy.get("warning_count", 0) > 0:
                print(f"   ⚠️ 警告数量: {mypy['warning_count']}")

        # 自定义分析结果
        if (
            "custom_analysis" in self.results
            and "overall_statistics" in self.results["custom_analysis"]
        ):
            stats = self.results["custom_analysis"]["overall_statistics"]
            coverage = stats.get("overall_coverage", 0)
            coverage_icon = "🟢" if coverage >= 80 else "🟡" if coverage >= 50 else "🔴"
            print(f"{coverage_icon} 类型覆盖率: {coverage:.1f}%")
            print(f"   📊 函数: {stats.get('function_coverage', 0):.1f}%")
            print(f"   ⚙️ 方法: {stats.get('method_coverage', 0):.1f}%")

        # 导入质量
        if "imports" in self.results:
            imports_icon = (
                "✅" if self.results["imports"].get("imports_sorted", True) else "⚠️"
            )
            print(
                f"{imports_icon} 导入排序: {'正确' if self.results['imports'].get('imports_sorted', True) else '需要修复'}"
            )

        # 复杂度
        if "complexity" in self.results:
            complex_count = len(self.results["complexity"].get("complex_files", []))
            complexity_icon = (
                "🟢" if complex_count == 0 else "🟡" if complex_count <= 3 else "🔴"
            )
            print(f"{complexity_icon} 复杂文件: {complex_count} 个")

        # 改进建议
        print(f"\n🎯 改进建议:")
        for i, rec in enumerate(self.results.get("recommendations", [])[:5], 1):
            print(f"   {i}. {rec}")

        print(f"\n💡 下一步行动:")
        print(f"   • 修复 mypy 错误")
        print(f"   • 提升类型注解覆盖率")
        print(f"   • 启用严格类型检查")
        print(f"   • 集成 CI/CD 检查")


def main() -> None:
    """主函数"""
    project_root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()

    checker = EnhancedTypeChecker(project_root)
    results = checker.run_full_analysis()
    checker.print_summary()

    # 保存详细结果
    report_file = (
        f"enhanced_type_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n💾 详细报告已保存到: {report_file}")

    # 返回退出码
    mypy_success = results.get("mypy", {}).get("return_code", 1) == 0
    coverage_good = (
        results.get("custom_analysis", {})
        .get("overall_statistics", {})
        .get("overall_coverage", 0)
        >= 50
    )

    if mypy_success and coverage_good:
        print("🎉 类型检查通过！")
        sys.exit(0)
    else:
        print("⚠️ 需要改进类型注解")
        sys.exit(1)


if __name__ == "__main__":
    main()
