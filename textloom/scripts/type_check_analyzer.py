#!/usr/bin/env python3
"""
TypeScript风格的Python类型检查分析器
分析项目的类型注解覆盖率和类型安全性
"""
from __future__ import annotations

import ast
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class TypeCoverageStats:
    """类型覆盖率统计"""

    total_functions: int = 0
    typed_functions: int = 0
    total_methods: int = 0
    typed_methods: int = 0
    total_classes: int = 0
    typed_classes: int = 0
    total_variables: int = 0
    typed_variables: int = 0

    @property
    def function_coverage(self) -> float:
        return (
            (self.typed_functions / self.total_functions * 100)
            if self.total_functions > 0
            else 0.0
        )

    @property
    def method_coverage(self) -> float:
        return (
            (self.typed_methods / self.total_methods * 100)
            if self.total_methods > 0
            else 0.0
        )

    @property
    def overall_coverage(self) -> float:
        total_items = self.total_functions + self.total_methods
        typed_items = self.typed_functions + self.typed_methods
        return (typed_items / total_items * 100) if total_items > 0 else 0.0


@dataclass
class FileAnalysis:
    """文件分析结果"""

    file_path: str
    stats: TypeCoverageStats
    issues: List[str]
    suggestions: List[str]


class TypeAnalyzer(ast.NodeVisitor):
    """TypeScript风格的类型分析器"""

    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.stats = TypeCoverageStats()
        self.issues: List[str] = []
        self.suggestions: List[str] = []
        self.current_class: Optional[str] = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """分析函数定义"""
        if self.current_class:
            self.stats.total_methods += 1
            if node.returns:
                self.stats.typed_methods += 1
            else:
                self.issues.append(
                    f"方法 {self.current_class}.{node.name} 缺少返回类型注解"
                )
                self.suggestions.append(
                    f"为 {self.current_class}.{node.name} 添加返回类型: -> ReturnType"
                )
        else:
            self.stats.total_functions += 1
            if node.returns:
                self.stats.typed_functions += 1
            else:
                self.issues.append(f"函数 {node.name} 缺少返回类型注解")
                self.suggestions.append(f"为 {node.name} 添加返回类型: -> ReturnType")

        # 检查参数类型注解
        for arg in node.args.args:
            if not arg.annotation and arg.arg != "self":
                self.issues.append(f"参数 {arg.arg} 在 {node.name} 中缺少类型注解")

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """分析异步函数定义"""
        if self.current_class:
            self.stats.total_methods += 1
            if node.returns:
                self.stats.typed_methods += 1
            else:
                self.issues.append(
                    f"异步方法 {self.current_class}.{node.name} 缺少返回类型注解"
                )
                self.suggestions.append(
                    f"为 {self.current_class}.{node.name} 添加返回类型: -> Awaitable[ReturnType]"
                )
        else:
            self.stats.total_functions += 1
            if node.returns:
                self.stats.typed_functions += 1
            else:
                self.issues.append(f"异步函数 {node.name} 缺少返回类型注解")
                self.suggestions.append(
                    f"为 {node.name} 添加返回类型: -> Awaitable[ReturnType]"
                )

        # 检查参数类型注解
        for arg in node.args.args:
            if not arg.annotation and arg.arg != "self":
                self.issues.append(f"参数 {arg.arg} 在异步 {node.name} 中缺少类型注解")

        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """分析类定义"""
        self.stats.total_classes += 1
        old_class = self.current_class
        self.current_class = node.name

        # 检查是否有类型注解的属性
        has_typed_attrs = False
        for item in node.body:
            if isinstance(item, ast.AnnAssign):
                has_typed_attrs = True
                break

        if has_typed_attrs:
            self.stats.typed_classes += 1
        else:
            self.suggestions.append(f"考虑为类 {node.name} 的属性添加类型注解")

        self.generic_visit(node)
        self.current_class = old_class

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """分析类型注解的赋值"""
        self.stats.typed_variables += 1
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """分析普通赋值"""
        self.stats.total_variables += 1
        self.generic_visit(node)


class ProjectTypeAnalyzer:
    """项目级别的类型分析器"""

    def __init__(self, project_root: str) -> None:
        self.project_root = Path(project_root)
        self.file_analyses: List[FileAnalysis] = []

    def analyze_file(self, file_path: Path) -> FileAnalysis:
        """分析单个Python文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source)
            analyzer = TypeAnalyzer(str(file_path))
            analyzer.visit(tree)

            return FileAnalysis(
                file_path=str(file_path.relative_to(self.project_root)),
                stats=analyzer.stats,
                issues=analyzer.issues,
                suggestions=analyzer.suggestions,
            )
        except Exception as e:
            return FileAnalysis(
                file_path=str(file_path.relative_to(self.project_root)),
                stats=TypeCoverageStats(),
                issues=[f"解析错误: {str(e)}"],
                suggestions=[],
            )

    def analyze_project(
        self, exclude_patterns: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """分析整个项目"""
        if exclude_patterns is None:
            exclude_patterns = [
                "venv",
                ".venv",
                "__pycache__",
                ".git",
                "node_modules",
                "alembic/versions",
                "logs",
                "workspace",
                "test",
                "tests",
            ]

        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            # 排除指定目录
            dirs[:] = [
                d for d in dirs if not any(pattern in d for pattern in exclude_patterns)
            ]

            for file in files:
                if file.endswith(".py") and not file.startswith("."):
                    file_path = Path(root) / file
                    python_files.append(file_path)

        # 分析所有文件
        self.file_analyses = []
        for file_path in python_files:
            analysis = self.analyze_file(file_path)
            self.file_analyses.append(analysis)

        return self.generate_report()

    def generate_report(self) -> Dict[str, Any]:
        """生成类型检查报告"""
        total_stats = TypeCoverageStats()
        high_priority_issues = []
        improvement_suggestions = []

        # 聚合统计
        for analysis in self.file_analyses:
            stats = analysis.stats
            total_stats.total_functions += stats.total_functions
            total_stats.typed_functions += stats.typed_functions
            total_stats.total_methods += stats.total_methods
            total_stats.typed_methods += stats.typed_methods
            total_stats.total_classes += stats.total_classes
            total_stats.typed_classes += stats.typed_classes
            total_stats.total_variables += stats.total_variables
            total_stats.typed_variables += stats.typed_variables

            # 收集问题和建议
            if analysis.issues:
                high_priority_issues.extend(
                    [
                        f"{analysis.file_path}: {issue}"
                        for issue in analysis.issues[:3]  # 限制每个文件最多3个问题
                    ]
                )

            if analysis.suggestions:
                improvement_suggestions.extend(
                    [
                        f"{analysis.file_path}: {suggestion}"
                        for suggestion in analysis.suggestions[
                            :2
                        ]  # 限制每个文件最多2个建议
                    ]
                )

        # 按覆盖率排序文件
        files_by_coverage = sorted(
            [
                (analysis.file_path, analysis.stats.overall_coverage)
                for analysis in self.file_analyses
            ],
            key=lambda x: x[1],
        )

        return {
            "analysis_timestamp": datetime.now().isoformat(),
            "overall_statistics": {
                "total_files_analyzed": len(self.file_analyses),
                "function_coverage": round(total_stats.function_coverage, 2),
                "method_coverage": round(total_stats.method_coverage, 2),
                "overall_coverage": round(total_stats.overall_coverage, 2),
                "total_functions": total_stats.total_functions,
                "typed_functions": total_stats.typed_functions,
                "total_methods": total_stats.total_methods,
                "typed_methods": total_stats.typed_methods,
                "total_classes": total_stats.total_classes,
                "typed_classes": total_stats.typed_classes,
            },
            "coverage_by_category": {
                "excellent": [f for f, c in files_by_coverage if c >= 90],
                "good": [f for f, c in files_by_coverage if 70 <= c < 90],
                "needs_improvement": [f for f, c in files_by_coverage if 50 <= c < 70],
                "poor": [f for f, c in files_by_coverage if c < 50],
            },
            "priority_improvements": {
                "high_priority_issues": high_priority_issues[
                    :20
                ],  # 最多20个高优先级问题
                "improvement_suggestions": improvement_suggestions[
                    :15
                ],  # 最多15个改进建议
                "recommended_next_steps": self._generate_recommendations(total_stats),
            },
            "file_details": [
                {
                    "file": analysis.file_path,
                    "coverage": round(analysis.stats.overall_coverage, 2),
                    "functions": f"{analysis.stats.typed_functions}/{analysis.stats.total_functions}",
                    "methods": f"{analysis.stats.typed_methods}/{analysis.stats.total_methods}",
                    "issues_count": len(analysis.issues),
                }
                for analysis in sorted(
                    self.file_analyses, key=lambda x: x.stats.overall_coverage
                )
            ],
        }

    def _generate_recommendations(self, stats: TypeCoverageStats) -> List[str]:
        """生成改进建议"""
        recommendations = []

        if stats.overall_coverage < 50:
            recommendations.append("立即开始为核心函数添加返回类型注解")
            recommendations.append("优先处理公共API和关键业务逻辑函数")
        elif stats.overall_coverage < 80:
            recommendations.append("继续完善剩余函数的类型注解")
            recommendations.append("考虑启用mypy的strict模式")
        else:
            recommendations.append("类型覆盖率良好，考虑启用更严格的类型检查")
            recommendations.append("添加类属性和复杂数据结构的类型注解")

        if stats.function_coverage > stats.method_coverage:
            recommendations.append("重点改进类方法的类型注解覆盖率")

        recommendations.extend(
            [
                "设置pre-commit hook执行类型检查",
                "在CI/CD流水线中集成mypy检查",
                "考虑使用dataclasses或Pydantic进行数据建模",
            ]
        )

        return recommendations


def main() -> None:
    """主函数"""
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = os.getcwd()

    print("🔍 开始TypeScript风格的Python类型分析...")
    print(f"📁 项目根目录: {project_root}")

    analyzer = ProjectTypeAnalyzer(project_root)
    report = analyzer.analyze_project()

    # 输出报告
    print("\n" + "=" * 60)
    print("📊 TextLoom 项目类型注解分析报告")
    print("=" * 60)

    stats = report["overall_statistics"]
    print(f"📈 总体覆盖率: {stats['overall_coverage']}%")
    print(
        f"🔧 函数覆盖率: {stats['function_coverage']}% ({stats['typed_functions']}/{stats['total_functions']})"
    )
    print(
        f"⚙️  方法覆盖率: {stats['method_coverage']}% ({stats['typed_methods']}/{stats['total_methods']})"
    )
    print(f"📁 分析文件数: {stats['total_files_analyzed']}")

    print(f"\n📊 覆盖率分类:")
    categories = report["coverage_by_category"]
    print(f"  🟢 优秀 (≥90%): {len(categories['excellent'])} 个文件")
    print(f"  🟡 良好 (70-89%): {len(categories['good'])} 个文件")
    print(f"  🟠 需改进 (50-69%): {len(categories['needs_improvement'])} 个文件")
    print(f"  🔴 较差 (<50%): {len(categories['poor'])} 个文件")

    if categories["poor"]:
        print(f"\n⚠️  需要优先改进的文件:")
        for file in categories["poor"][:5]:
            print(f"   - {file}")

    print(f"\n🎯 改进建议:")
    for i, suggestion in enumerate(
        report["priority_improvements"]["recommended_next_steps"][:5], 1
    ):
        print(f"   {i}. {suggestion}")

    # 保存详细报告
    report_file = (
        f"type_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n💾 详细报告已保存到: {report_file}")
    print("✅ 分析完成!")


if __name__ == "__main__":
    main()
