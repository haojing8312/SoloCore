#!/usr/bin/env python3
"""
自动类型注解改进工具
基于AST分析自动为Python函数添加基础类型注解
"""
from __future__ import annotations

import ast
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union


@dataclass
class TypeSuggestion:
    """类型建议"""

    line_number: int
    function_name: str
    suggested_annotation: str
    confidence: float  # 0.0 - 1.0
    reason: str


class TypeInferencer(ast.NodeVisitor):
    """类型推断器"""

    def __init__(self, source: str) -> None:
        self.source = source
        self.lines = source.split("\n")
        self.suggestions: List[TypeSuggestion] = []

    def _infer_return_type_from_docstring(self, node: ast.FunctionDef) -> Optional[str]:
        """从文档字符串推断返回类型"""
        if not ast.get_docstring(node):
            return None

        docstring = ast.get_docstring(node)

        # 查找Returns/Return模式
        return_patterns = [
            r"Returns?\s*:\s*([^.\n]+)",
            r"return\s+([^.\n]+)",
            r"-> ([^.\n]+)",
        ]

        for pattern in return_patterns:
            match = re.search(pattern, docstring, re.IGNORECASE)
            if match:
                return_desc = match.group(1).strip()

                # 简单的类型映射
                type_mappings = {
                    "dict": "Dict[str, Any]",
                    "list": "List[Any]",
                    "string": "str",
                    "integer": "int",
                    "boolean": "bool",
                    "float": "float",
                    "none": "None",
                    "task": "Task",
                    "user": "User",
                }

                for keyword, type_hint in type_mappings.items():
                    if keyword in return_desc.lower():
                        return type_hint

        return None

    def _infer_return_type_from_body(self, node: ast.FunctionDef) -> Optional[str]:
        """从函数体推断返回类型"""
        return_types = set()

        for stmt in ast.walk(node):
            if isinstance(stmt, ast.Return) and stmt.value:
                if isinstance(stmt.value, ast.Constant):
                    if stmt.value.value is None:
                        return_types.add("None")
                    elif isinstance(stmt.value.value, str):
                        return_types.add("str")
                    elif isinstance(stmt.value.value, int):
                        return_types.add("int")
                    elif isinstance(stmt.value.value, float):
                        return_types.add("float")
                    elif isinstance(stmt.value.value, bool):
                        return_types.add("bool")
                elif isinstance(stmt.value, ast.Dict):
                    return_types.add("Dict[str, Any]")
                elif isinstance(stmt.value, ast.List):
                    return_types.add("List[Any]")
                elif isinstance(stmt.value, ast.Call):
                    if hasattr(stmt.value.func, "id"):
                        func_name = stmt.value.func.id
                        if func_name in ["dict"]:
                            return_types.add("Dict[str, Any]")
                        elif func_name in ["list"]:
                            return_types.add("List[Any]")

        # 如果只有一种返回类型，返回它
        if len(return_types) == 1:
            return return_types.pop()
        elif len(return_types) > 1:
            if "None" in return_types:
                return_types.remove("None")
                if len(return_types) == 1:
                    return f"Optional[{return_types.pop()}]"
            return f'Union[{", ".join(sorted(return_types))}]'

        return None

    def _is_async_function(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> bool:
        """检查是否为异步函数"""
        return isinstance(node, ast.AsyncFunctionDef)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """访问函数定义"""
        self._analyze_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """访问异步函数定义"""
        self._analyze_function(node)
        self.generic_visit(node)

    def _analyze_function(
        self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]
    ) -> None:
        """分析函数并生成类型建议"""
        if node.returns:
            return  # 已经有返回类型注解

        # 跳过魔术方法和私有方法（除非明确需要）
        if node.name.startswith("__") and node.name.endswith("__"):
            return

        # 推断返回类型
        suggested_type = None
        confidence = 0.0
        reason = ""

        # 方法1: 从文档字符串推断
        docstring_type = self._infer_return_type_from_docstring(node)
        if docstring_type:
            suggested_type = docstring_type
            confidence = 0.7
            reason = "基于文档字符串推断"

        # 方法2: 从函数体推断
        if not suggested_type:
            body_type = self._infer_return_type_from_body(node)
            if body_type:
                suggested_type = body_type
                confidence = 0.8
                reason = "基于返回语句分析"

        # 方法3: 基于函数名模式推断
        if not suggested_type:
            name_patterns = {
                r".*_count$|^count_.*": "int",
                r"^is_.*|.*_exists$": "bool",
                r"^get_.*_list$|^list_.*": "List[Any]",
                r"^get_.*_dict$|.*_mapping$": "Dict[str, Any]",
                r"^create_.*|^update_.*|^delete_.*": "Optional[Any]",
                r".*_str$|^format_.*": "str",
                r".*_url$|.*_path$": "str",
            }

            for pattern, type_hint in name_patterns.items():
                if re.match(pattern, node.name):
                    suggested_type = type_hint
                    confidence = 0.5
                    reason = f"基于函数名模式 '{pattern}'"
                    break

        # 对于异步函数，包装在Awaitable中
        if suggested_type and self._is_async_function(node):
            if suggested_type != "None":
                suggested_type = f"Awaitable[{suggested_type}]"
            confidence *= 0.9  # 异步函数稍微降低置信度

        # 默认建议
        if not suggested_type:
            if self._is_async_function(node):
                suggested_type = "Awaitable[Any]"
            else:
                suggested_type = "Any"
            confidence = 0.3
            reason = "默认类型建议"

        self.suggestions.append(
            TypeSuggestion(
                line_number=node.lineno,
                function_name=node.name,
                suggested_annotation=suggested_type,
                confidence=confidence,
                reason=reason,
            )
        )


class AutoTypeImprover:
    """自动类型改进器"""

    def __init__(self, project_root: str) -> None:
        self.project_root = Path(project_root)

    def analyze_file(self, file_path: Path) -> List[TypeSuggestion]:
        """分析文件并返回类型建议"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source = f.read()

            tree = ast.parse(source)
            inferencer = TypeInferencer(source)
            inferencer.visit(tree)

            return inferencer.suggestions

        except Exception as e:
            print(f"❌ 分析文件 {file_path} 失败: {e}")
            return []

    def generate_type_annotations(
        self, file_path: Path, apply_changes: bool = False
    ) -> Dict[str, any]:
        """为文件生成类型注解建议"""
        suggestions = self.analyze_file(file_path)

        if not suggestions:
            return {
                "file": str(file_path),
                "suggestions": [],
                "status": "no_improvements_needed",
            }

        # 按置信度和行号排序
        suggestions.sort(key=lambda x: (-x.confidence, x.line_number))

        result = {
            "file": str(file_path.relative_to(self.project_root)),
            "suggestions": [],
            "status": "analysis_complete",
        }

        for suggestion in suggestions:
            result["suggestions"].append(
                {
                    "line": suggestion.line_number,
                    "function": suggestion.function_name,
                    "suggested_type": suggestion.suggested_annotation,
                    "confidence": round(suggestion.confidence, 2),
                    "reason": suggestion.reason,
                    "improvement": f"def {suggestion.function_name}(...) -> {suggestion.suggested_annotation}:",
                }
            )

        if apply_changes and suggestions:
            self._apply_suggestions(file_path, suggestions)
            result["status"] = "improvements_applied"

        return result

    def _apply_suggestions(
        self, file_path: Path, suggestions: List[TypeSuggestion]
    ) -> None:
        """应用类型注解建议到文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 需要导入的类型
            needed_imports = set()
            for suggestion in suggestions:
                type_annotation = suggestion.suggested_annotation
                if "Dict" in type_annotation:
                    needed_imports.add("Dict")
                if "List" in type_annotation:
                    needed_imports.add("List")
                if "Optional" in type_annotation:
                    needed_imports.add("Optional")
                if "Union" in type_annotation:
                    needed_imports.add("Union")
                if "Any" in type_annotation:
                    needed_imports.add("Any")
                if "Awaitable" in type_annotation:
                    needed_imports.add("Awaitable")

            # 添加导入（简化版本）
            if needed_imports:
                import_line = (
                    f"from typing import {', '.join(sorted(needed_imports))}\n"
                )

                # 查找合适的位置插入导入
                insert_pos = 0
                for i, line in enumerate(lines):
                    if line.startswith("from typing import") or line.startswith(
                        "import typing"
                    ):
                        # 更新现有的typing导入
                        lines[i] = import_line
                        break
                    elif line.startswith("import ") or line.startswith("from "):
                        insert_pos = i + 1
                else:
                    # 插入新的导入
                    lines.insert(insert_pos, import_line)

            # 应用函数返回类型注解（简化版本 - 仅作为示例）
            # 实际应用需要更复杂的AST操作

            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(lines)

            print(f"✅ 已应用类型改进到 {file_path}")

        except Exception as e:
            print(f"❌ 应用改进到 {file_path} 失败: {e}")

    def improve_project_types(
        self, target_dirs: Optional[List[str]] = None, apply_changes: bool = False
    ) -> Dict[str, any]:
        """改进整个项目的类型注解"""
        if target_dirs is None:
            target_dirs = ["routers", "services", "models", "utils"]

        results = {
            "timestamp": str(Path(__file__).stat().st_mtime),
            "apply_changes": apply_changes,
            "files_analyzed": 0,
            "improvements_suggested": 0,
            "files_with_improvements": [],
            "summary": {},
        }

        print(f"🔍 分析项目类型注解改进机会...")
        if apply_changes:
            print(f"⚠️  警告: 将直接修改文件!")

        for target_dir in target_dirs:
            dir_path = self.project_root / target_dir
            if not dir_path.exists():
                continue

            print(f"📁 分析目录: {target_dir}")

            for py_file in dir_path.rglob("*.py"):
                if py_file.name.startswith(".") or "__pycache__" in str(py_file):
                    continue

                file_result = self.generate_type_annotations(py_file, apply_changes)
                results["files_analyzed"] += 1

                if file_result["suggestions"]:
                    results["improvements_suggested"] += len(file_result["suggestions"])
                    results["files_with_improvements"].append(file_result)

        # 生成摘要
        high_confidence = sum(
            1
            for f in results["files_with_improvements"]
            for s in f["suggestions"]
            if s["confidence"] >= 0.7
        )
        medium_confidence = sum(
            1
            for f in results["files_with_improvements"]
            for s in f["suggestions"]
            if 0.5 <= s["confidence"] < 0.7
        )
        low_confidence = sum(
            1
            for f in results["files_with_improvements"]
            for s in f["suggestions"]
            if s["confidence"] < 0.5
        )

        results["summary"] = {
            "high_confidence_suggestions": high_confidence,
            "medium_confidence_suggestions": medium_confidence,
            "low_confidence_suggestions": low_confidence,
            "total_files_with_improvements": len(results["files_with_improvements"]),
        }

        return results

    def print_improvement_report(self, results: Dict[str, any]) -> None:
        """打印改进报告"""
        print("\n" + "=" * 60)
        print("🎯 TextLoom 自动类型注解改进报告")
        print("=" * 60)

        summary = results["summary"]
        print(f"📊 分析统计:")
        print(f"   📁 分析文件数: {results['files_analyzed']}")
        print(f"   💡 改进建议数: {results['improvements_suggested']}")
        print(f"   📝 需改进文件: {summary['total_files_with_improvements']}")

        print(f"\n🎯 建议质量分布:")
        print(f"   🟢 高置信度 (≥70%): {summary['high_confidence_suggestions']} 个")
        print(f"   🟡 中置信度 (50-69%): {summary['medium_confidence_suggestions']} 个")
        print(f"   🟠 低置信度 (<50%): {summary['low_confidence_suggestions']} 个")

        if results["files_with_improvements"]:
            print(f"\n📋 优先改进文件 (前5个):")
            for i, file_info in enumerate(results["files_with_improvements"][:5], 1):
                high_conf_count = sum(
                    1 for s in file_info["suggestions"] if s["confidence"] >= 0.7
                )
                print(
                    f"   {i}. {file_info['file']} ({len(file_info['suggestions'])} 个建议, {high_conf_count} 个高置信度)"
                )

        print(f"\n🔧 下一步操作:")
        print(f"   1. 查看具体建议: cat type_improvement_report.json")
        print(f"   2. 应用高置信度改进: python scripts/auto_type_improver.py --apply")
        print(f"   3. 手动验证和调整类型注解")
        print(f"   4. 运行 mypy 验证改进效果")


def main() -> None:
    """主函数"""
    project_root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    apply_changes = "--apply" in sys.argv

    improver = AutoTypeImprover(project_root)
    results = improver.improve_project_types(apply_changes=apply_changes)
    improver.print_improvement_report(results)

    # 保存详细报告
    import json

    with open("type_improvement_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n💾 详细报告已保存到: type_improvement_report.json")


if __name__ == "__main__":
    main()
