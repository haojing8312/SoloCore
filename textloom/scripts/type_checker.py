#!/usr/bin/env python3
"""
类型检查工具 - 用于分析和改进代码库的类型注解覆盖率
"""

import ast
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple


@dataclass
class FunctionInfo:
    """函数信息"""

    name: str
    file_path: str
    line_number: int
    has_return_annotation: bool
    has_param_annotations: bool
    missing_annotations: List[str]
    is_async: bool


@dataclass
class TypeCoverageReport:
    """类型覆盖率报告"""

    total_functions: int
    annotated_functions: int
    partially_annotated_functions: int
    unannotated_functions: int
    coverage_percentage: float
    module_reports: Dict[str, "ModuleTypeReport"]


@dataclass
class ModuleTypeReport:
    """模块类型报告"""

    module_name: str
    total_functions: int
    annotated_functions: int
    unannotated_functions: List[FunctionInfo]
    coverage_percentage: float


class TypeAnnotationAnalyzer:
    """类型注解分析器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.exclude_dirs = {
            "__pycache__",
            "venv",
            ".venv",
            "build",
            "dist",
            "workspace",
            "logs",
            "test",
            "alembic/versions",
            ".mypy_cache",
            ".git",
        }
        self.exclude_files = {"__init__.py"}

    def find_python_files(self) -> List[Path]:
        """查找所有Python文件"""
        python_files = []
        for root, dirs, files in os.walk(self.project_root):
            # 过滤排除的目录
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]

            for file in files:
                if file.endswith(".py") and file not in self.exclude_files:
                    file_path = Path(root) / file
                    # 跳过备份文件
                    if ".backup" in file or ".bak" in file:
                        continue
                    python_files.append(file_path)

        return python_files

    def analyze_file(self, file_path: Path) -> List[FunctionInfo]:
        """分析单个文件的类型注解"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, PermissionError):
            return []

        try:
            tree = ast.parse(content)
        except SyntaxError:
            print(f"警告: 无法解析文件 {file_path} (语法错误)")
            return []

        functions = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = self._analyze_function(node, file_path)
                functions.append(func_info)

        return functions

    def _analyze_function(self, node: ast.FunctionDef, file_path: Path) -> FunctionInfo:
        """分析单个函数的类型注解"""
        missing_annotations = []

        # 检查返回类型注解
        has_return_annotation = node.returns is not None
        if not has_return_annotation and node.name not in [
            "__init__",
            "__str__",
            "__repr__",
        ]:
            missing_annotations.append("return")

        # 检查参数类型注解
        has_param_annotations = True
        for arg in node.args.args:
            if arg.annotation is None and arg.arg != "self" and arg.arg != "cls":
                has_param_annotations = False
                missing_annotations.append(f"param:{arg.arg}")

        # 检查关键字参数
        for arg in node.args.kwonlyargs:
            if arg.annotation is None:
                has_param_annotations = False
                missing_annotations.append(f"kwarg:{arg.arg}")

        # 检查varargs和kwargs
        if node.args.vararg and node.args.vararg.annotation is None:
            has_param_annotations = False
            missing_annotations.append(f"*{node.args.vararg.arg}")

        if node.args.kwarg and node.args.kwarg.annotation is None:
            has_param_annotations = False
            missing_annotations.append(f"**{node.args.kwarg.arg}")

        return FunctionInfo(
            name=node.name,
            file_path=str(file_path.relative_to(self.project_root)),
            line_number=node.lineno,
            has_return_annotation=has_return_annotation,
            has_param_annotations=has_param_annotations,
            missing_annotations=missing_annotations,
            is_async=isinstance(node, ast.AsyncFunctionDef),
        )

    def generate_coverage_report(self) -> TypeCoverageReport:
        """生成类型覆盖率报告"""
        python_files = self.find_python_files()
        all_functions = []
        module_reports = {}

        for file_path in python_files:
            functions = self.analyze_file(file_path)
            all_functions.extend(functions)

            # 计算模块级别的覆盖率
            if functions:
                module_name = str(file_path.relative_to(self.project_root))
                annotated_count = sum(
                    1
                    for f in functions
                    if f.has_return_annotation and f.has_param_annotations
                )
                unannotated = [
                    f
                    for f in functions
                    if not (f.has_return_annotation and f.has_param_annotations)
                ]

                coverage = (annotated_count / len(functions)) * 100 if functions else 0

                module_reports[module_name] = ModuleTypeReport(
                    module_name=module_name,
                    total_functions=len(functions),
                    annotated_functions=annotated_count,
                    unannotated_functions=unannotated,
                    coverage_percentage=coverage,
                )

        # 计算总体覆盖率
        total_functions = len(all_functions)
        annotated_functions = sum(
            1
            for f in all_functions
            if f.has_return_annotation and f.has_param_annotations
        )
        partially_annotated = sum(
            1
            for f in all_functions
            if (f.has_return_annotation or f.has_param_annotations)
            and not (f.has_return_annotation and f.has_param_annotations)
        )
        unannotated_functions = (
            total_functions - annotated_functions - partially_annotated
        )

        coverage_percentage = (
            (annotated_functions / total_functions) * 100 if total_functions > 0 else 0
        )

        return TypeCoverageReport(
            total_functions=total_functions,
            annotated_functions=annotated_functions,
            partially_annotated_functions=partially_annotated,
            unannotated_functions=unannotated_functions,
            coverage_percentage=coverage_percentage,
            module_reports=module_reports,
        )


class TypeChecker:
    """类型检查器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.analyzer = TypeAnnotationAnalyzer(project_root)

    def run_mypy_check(self, files: Optional[List[str]] = None) -> Tuple[bool, str]:
        """运行mypy类型检查"""
        cmd = ["uv", "run", "mypy"]

        if files:
            cmd.extend(files)
        else:
            cmd.append(".")

        # 添加配置选项
        cmd.extend(
            [
                "--config-file",
                "pyproject.toml",
                "--show-error-codes",
                "--show-column-numbers",
            ]
        )

        try:
            result = subprocess.run(
                cmd, cwd=self.project_root, capture_output=True, text=True, timeout=300
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, "mypy检查超时"
        except Exception as e:
            return False, f"运行mypy时出错: {e}"

    def generate_type_stubs(self, module_name: str) -> bool:
        """为模块生成类型存根"""
        cmd = ["uv", "run", "stubgen", "-p", module_name, "-o", "stubs"]

        try:
            result = subprocess.run(
                cmd, cwd=self.project_root, capture_output=True, text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def analyze_coverage(self) -> TypeCoverageReport:
        """分析类型注解覆盖率"""
        return self.analyzer.generate_coverage_report()

    def suggest_improvements(self, report: TypeCoverageReport) -> List[str]:
        """提供改进建议"""
        suggestions = []

        # 总体建议
        if report.coverage_percentage < 50:
            suggestions.append("类型注解覆盖率较低，建议优先为核心模块添加类型注解")
        elif report.coverage_percentage < 80:
            suggestions.append("类型注解覆盖率中等，继续完善剩余模块的类型注解")
        else:
            suggestions.append("类型注解覆盖率良好，关注细节优化和复杂类型场景")

        # 模块级别建议
        low_coverage_modules = [
            name
            for name, module in report.module_reports.items()
            if module.coverage_percentage < 60 and module.total_functions > 5
        ]

        if low_coverage_modules:
            suggestions.append(
                f"优先改进以下模块的类型注解: {', '.join(low_coverage_modules[:5])}"
            )

        # 具体改进建议
        high_priority_modules = ["routers/", "services/", "models/", "utils/"]
        for priority_module in high_priority_modules:
            matching_modules = [
                name
                for name in report.module_reports.keys()
                if name.startswith(priority_module)
            ]

            if matching_modules:
                avg_coverage = sum(
                    report.module_reports[name].coverage_percentage
                    for name in matching_modules
                ) / len(matching_modules)

                if avg_coverage < 70:
                    suggestions.append(f"重点关注 {priority_module} 模块的类型注解完善")

        return suggestions


def print_coverage_report(report: TypeCoverageReport):
    """打印覆盖率报告"""
    print("=" * 60)
    print("类型注解覆盖率报告")
    print("=" * 60)
    print(f"总函数数量: {report.total_functions}")
    print(f"完全注解函数: {report.annotated_functions}")
    print(f"部分注解函数: {report.partially_annotated_functions}")
    print(f"未注解函数: {report.unannotated_functions}")
    print(f"覆盖率: {report.coverage_percentage:.1f}%")
    print()

    # 按覆盖率排序显示模块
    sorted_modules = sorted(
        report.module_reports.items(), key=lambda x: x[1].coverage_percentage
    )

    print("模块详细信息 (按覆盖率排序):")
    print("-" * 80)
    print(f"{'模块名':<40} {'函数数':<8} {'已注解':<8} {'覆盖率':<8}")
    print("-" * 80)

    for module_name, module_report in sorted_modules:
        if module_report.total_functions > 0:  # 只显示有函数的模块
            print(
                f"{module_name:<40} {module_report.total_functions:<8} "
                f"{module_report.annotated_functions:<8} "
                f"{module_report.coverage_percentage:<7.1f}%"
            )

    print()

    # 显示需要改进的函数
    print("需要添加类型注解的函数 (前20个):")
    print("-" * 80)

    all_unannotated = []
    for module_report in report.module_reports.values():
        all_unannotated.extend(module_report.unannotated_functions)

    # 优先显示重要模块的函数
    priority_modules = ["routers/", "services/", "models/", "utils/"]
    priority_functions = []
    other_functions = []

    for func in all_unannotated:
        is_priority = any(func.file_path.startswith(pm) for pm in priority_modules)
        if is_priority:
            priority_functions.append(func)
        else:
            other_functions.append(func)

    # 显示优先级函数
    shown_count = 0
    for func in priority_functions[:15]:
        missing_str = ", ".join(func.missing_annotations[:3])
        if len(func.missing_annotations) > 3:
            missing_str += f" (+{len(func.missing_annotations) - 3} more)"

        print(
            f"{func.file_path}:{func.line_number} - {func.name}() "
            f"缺少: {missing_str}"
        )
        shown_count += 1

    # 如果还有空间，显示其他函数
    for func in other_functions[: 20 - shown_count]:
        missing_str = ", ".join(func.missing_annotations[:2])
        if len(func.missing_annotations) > 2:
            missing_str += "..."

        print(
            f"{func.file_path}:{func.line_number} - {func.name}() "
            f"缺少: {missing_str}"
        )


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="TextLoom 类型检查工具")
    parser.add_argument("--check", action="store_true", help="运行mypy类型检查")
    parser.add_argument("--coverage", action="store_true", help="分析类型注解覆盖率")
    parser.add_argument("--suggest", action="store_true", help="提供改进建议")
    parser.add_argument("--files", nargs="*", help="指定要检查的文件")
    parser.add_argument("--json", action="store_true", help="以JSON格式输出结果")
    parser.add_argument("--strict", action="store_true", help="使用严格模式检查")

    args = parser.parse_args()

    # 确定项目根目录
    project_root = Path(__file__).parent.parent
    type_checker = TypeChecker(str(project_root))

    if args.coverage or (not args.check and not args.suggest):
        # 分析类型注解覆盖率
        print("正在分析类型注解覆盖率...")
        report = type_checker.analyze_coverage()

        if args.json:
            # JSON输出
            json_data = {
                "total_functions": report.total_functions,
                "annotated_functions": report.annotated_functions,
                "coverage_percentage": report.coverage_percentage,
                "modules": {
                    name: {
                        "total_functions": mod.total_functions,
                        "annotated_functions": mod.annotated_functions,
                        "coverage_percentage": mod.coverage_percentage,
                    }
                    for name, mod in report.module_reports.items()
                },
            }
            print(json.dumps(json_data, indent=2, ensure_ascii=False))
        else:
            print_coverage_report(report)

            if args.suggest:
                suggestions = type_checker.suggest_improvements(report)
                print("\n改进建议:")
                print("-" * 40)
                for i, suggestion in enumerate(suggestions, 1):
                    print(f"{i}. {suggestion}")

    if args.check:
        # 运行mypy检查
        print("正在运行mypy类型检查...")
        success, output = type_checker.run_mypy_check(args.files)

        if success:
            print("✅ mypy检查通过!")
        else:
            print("❌ mypy检查发现问题:")
            print(output)
            sys.exit(1)

        if output.strip():
            print("\nmypy输出:")
            print(output)


if __name__ == "__main__":
    main()
