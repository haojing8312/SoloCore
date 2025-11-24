#!/usr/bin/env python3
"""
Print语句到日志系统转换器
自动分析和替换项目中的print()语句为适当的日志调用
"""

import argparse
import ast
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from utils.enhanced_logging import get_enhanced_logger

logger = get_enhanced_logger("print_converter", file_path="logs/print_converter.log")


@dataclass
class PrintStatement:
    """Print语句信息"""

    line_number: int
    content: str
    indent: str
    context: str
    suggested_level: str
    suggested_replacement: str


class PrintAnalyzer(ast.NodeVisitor):
    """AST分析器，用于分析print语句"""

    def __init__(self, source_lines: List[str]):
        self.source_lines = source_lines
        self.print_statements: List[PrintStatement] = []
        self.current_function = None
        self.current_class = None

    def visit_FunctionDef(self, node):
        """访问函数定义"""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function

    def visit_ClassDef(self, node):
        """访问类定义"""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_Call(self, node):
        """访问函数调用"""
        if isinstance(node.func, ast.Name) and node.func.id == "print":

            line_num = node.lineno
            line_content = self.source_lines[line_num - 1]
            indent = len(line_content) - len(line_content.lstrip())
            indent_str = " " * indent

            # 分析print内容
            content = line_content.strip()
            context = self._get_context(line_num)
            level, replacement = self._analyze_print_content(content, context)

            print_stmt = PrintStatement(
                line_number=line_num,
                content=content,
                indent=indent_str,
                context=context,
                suggested_level=level,
                suggested_replacement=replacement,
            )
            self.print_statements.append(print_stmt)

        self.generic_visit(node)

    def _get_context(self, line_num: int) -> str:
        """获取print语句的上下文"""
        context_info = []

        if self.current_class:
            context_info.append(f"class:{self.current_class}")

        if self.current_function:
            context_info.append(f"function:{self.current_function}")

        # 检查周围行的内容
        start = max(0, line_num - 3)
        end = min(len(self.source_lines), line_num + 2)
        surrounding = []

        for i in range(start, end):
            if i == line_num - 1:
                continue
            line = self.source_lines[i].strip().lower()
            if any(
                keyword in line
                for keyword in ["error", "exception", "fail", "traceback"]
            ):
                surrounding.append("error_context")
            elif any(keyword in line for keyword in ["debug", "trace", "verbose"]):
                surrounding.append("debug_context")
            elif any(keyword in line for keyword in ["warn", "warning"]):
                surrounding.append("warning_context")
            elif any(keyword in line for keyword in ["try:", "except:", "finally:"]):
                surrounding.append("exception_handling")

        if surrounding:
            context_info.extend(surrounding)

        return "|".join(context_info) if context_info else "general"

    def _analyze_print_content(self, content: str, context: str) -> Tuple[str, str]:
        """分析print内容并确定适当的日志级别和替换内容"""
        content_lower = content.lower()

        # 错误相关关键词
        error_keywords = [
            "error",
            "exception",
            "fail",
            "traceback",
            "crash",
            "错误",
            "异常",
            "失败",
            "崩溃",
            "❌",
            "🚫",
        ]

        # 警告相关关键词
        warning_keywords = [
            "warn",
            "warning",
            "alert",
            "caution",
            "deprecated",
            "警告",
            "注意",
            "⚠️",
            "⚡",
        ]

        # 调试相关关键词
        debug_keywords = [
            "debug",
            "trace",
            "verbose",
            "dump",
            "inspect",
            "调试",
            "跟踪",
            "详细",
            "🔧",
            "🔍",
        ]

        # 成功/完成相关关键词
        success_keywords = [
            "success",
            "complete",
            "finish",
            "done",
            "ok",
            "ready",
            "成功",
            "完成",
            "完毕",
            "就绪",
            "✅",
            "🎉",
            "🚀",
        ]

        # 进度相关关键词
        progress_keywords = [
            "progress",
            "processing",
            "loading",
            "step",
            "stage",
            "进度",
            "处理",
            "加载",
            "步骤",
            "阶段",
            "📊",
            "⏳",
        ]

        # 根据内容和上下文确定日志级别
        if any(keyword in content_lower for keyword in error_keywords):
            level = "error"
        elif "exception_handling" in context or "error_context" in context:
            level = "error"
        elif any(keyword in content_lower for keyword in warning_keywords):
            level = "warning"
        elif "warning_context" in context:
            level = "warning"
        elif any(keyword in content_lower for keyword in debug_keywords):
            level = "debug"
        elif "debug_context" in context:
            level = "debug"
        elif any(keyword in content_lower for keyword in success_keywords):
            level = "info"
        elif any(keyword in content_lower for keyword in progress_keywords):
            level = "info"
        else:
            # 默认级别
            level = "info"

        # 生成替换内容
        replacement = self._generate_replacement(content, level)

        return level, replacement

    def _generate_replacement(self, content: str, level: str) -> str:
        """生成替换的日志调用"""
        # 提取print()中的参数
        print_match = re.match(r"(\s*)print\((.*)\)(\s*)", content)
        if not print_match:
            return content

        indent, args, trailing = print_match.groups()

        # 清理参数
        args = args.strip()

        # 如果参数以f开头（f-string），保持原样
        if args.startswith('f"') or args.startswith("f'"):
            log_args = args
        # 如果是多个参数，需要转换为单个字符串
        elif "," in args and not args.startswith('"') and not args.startswith("'"):
            # 简单处理：将多个参数转为f-string
            log_args = f'f"{args}"' if not ('"' in args or "'" in args) else args
        else:
            log_args = args

        # 生成日志调用
        replacement = f"{indent}log_{level}({log_args}){trailing}"

        return replacement


class PrintConverter:
    """Print语句转换器"""

    def __init__(self, project_root: Path, dry_run: bool = True, backup: bool = True):
        self.project_root = project_root
        self.dry_run = dry_run
        self.backup = backup
        self.conversion_stats = {
            "files_processed": 0,
            "print_statements_found": 0,
            "conversions_made": 0,
            "errors": 0,
        }

    def find_python_files(self, exclude_patterns: List[str] = None) -> List[Path]:
        """查找所有Python文件"""
        if exclude_patterns is None:
            exclude_patterns = [
                "*/.venv/*",
                "*/venv/*",
                "*/__pycache__/*",
                "*/site-packages/*",
                "*/migrations/*",
                "*/.git/*",
            ]

        python_files = []
        for py_file in self.project_root.rglob("*.py"):
            # 检查是否应该排除
            should_exclude = any(py_file.match(pattern) for pattern in exclude_patterns)
            if not should_exclude:
                python_files.append(py_file)

        return python_files

    def analyze_file(self, file_path: Path) -> List[PrintStatement]:
        """分析单个文件中的print语句"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()

            # 解析AST
            tree = ast.parse(content)
            analyzer = PrintAnalyzer(lines)
            analyzer.visit(tree)

            return analyzer.print_statements

        except Exception as e:
            logger.error(f"分析文件失败: {file_path}, 错误: {e}")
            self.conversion_stats["errors"] += 1
            return []

    def convert_file(
        self, file_path: Path, print_statements: List[PrintStatement]
    ) -> bool:
        """转换单个文件"""
        if not print_statements:
            return True

        try:
            # 读取原文件
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 备份原文件
            if self.backup and not self.dry_run:
                backup_path = file_path.with_suffix(f"{file_path.suffix}.backup")
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                logger.info(f"创建备份文件: {backup_path}")

            # 按行号排序（从后往前处理，避免行号变化）
            sorted_statements = sorted(
                print_statements, key=lambda x: x.line_number, reverse=True
            )

            # 检查是否需要添加导入
            has_log_import = any(
                "from utils.enhanced_logging import" in line for line in lines
            )

            # 替换print语句
            for stmt in sorted_statements:
                line_idx = stmt.line_number - 1
                if line_idx < len(lines):
                    lines[line_idx] = stmt.suggested_replacement + "\n"
                    self.conversion_stats["conversions_made"] += 1

            # 添加导入语句（如果需要）
            if not has_log_import and not self.dry_run:
                # 找到合适的位置插入导入
                insert_idx = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith("import ") or line.strip().startswith(
                        "from "
                    ):
                        insert_idx = i + 1
                    elif line.strip() and not line.strip().startswith("#"):
                        break

                import_line = "from utils.enhanced_logging import log_debug, log_info, log_warning, log_error, log_critical\n"
                lines.insert(insert_idx, import_line)
                logger.info(f"添加日志导入: {file_path}")

            # 写回文件
            if not self.dry_run:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.writelines(lines)
                logger.info(
                    f"文件转换完成: {file_path}, 转换了 {len(print_statements)} 个print语句"
                )
            else:
                logger.info(
                    f"[DRY RUN] 将转换文件: {file_path}, {len(print_statements)} 个print语句"
                )

            return True

        except Exception as e:
            logger.error(f"转换文件失败: {file_path}, 错误: {e}")
            self.conversion_stats["errors"] += 1
            return False

    def generate_report(
        self, analysis_results: Dict[Path, List[PrintStatement]]
    ) -> str:
        """生成转换报告"""
        report_lines = [
            "=" * 80,
            "Print语句到日志系统转换报告",
            "=" * 80,
            f"项目根目录: {self.project_root}",
            f"运行模式: {'DRY RUN (预览模式)' if self.dry_run else 'LIVE (实际转换)'}",
            f"备份文件: {'是' if self.backup else '否'}",
            "",
            "统计信息:",
            f"  处理文件数: {self.conversion_stats['files_processed']}",
            f"  发现print语句: {self.conversion_stats['print_statements_found']}",
            f"  转换语句数: {self.conversion_stats['conversions_made']}",
            f"  错误数: {self.conversion_stats['errors']}",
            "",
            "级别分布:",
        ]

        # 统计各级别的分布
        level_counts = {"debug": 0, "info": 0, "warning": 0, "error": 0, "critical": 0}
        for statements in analysis_results.values():
            for stmt in statements:
                level_counts[stmt.suggested_level] += 1

        for level, count in level_counts.items():
            report_lines.append(f"  {level.upper()}: {count}")

        report_lines.extend(
            [
                "",
                "文件详情:",
            ]
        )

        # 文件详情
        for file_path, statements in analysis_results.items():
            if statements:
                report_lines.append(f"\n📄 {file_path}")
                for stmt in statements:
                    report_lines.append(
                        f"  行 {stmt.line_number:3d}: {stmt.suggested_level.upper():7s} | {stmt.content}"
                    )
                    if self.dry_run:
                        report_lines.append(
                            f"         建议替换: {stmt.suggested_replacement}"
                        )

        return "\n".join(report_lines)

    def convert_project(
        self, target_files: List[str] = None
    ) -> Dict[Path, List[PrintStatement]]:
        """转换整个项目"""
        logger.info("开始转换项目中的print语句")

        # 查找文件
        if target_files:
            python_files = [Path(f) for f in target_files if Path(f).exists()]
        else:
            python_files = self.find_python_files()

        logger.info(f"找到 {len(python_files)} 个Python文件")

        analysis_results = {}

        for file_path in python_files:
            self.conversion_stats["files_processed"] += 1

            # 分析文件
            print_statements = self.analyze_file(file_path)
            analysis_results[file_path] = print_statements
            self.conversion_stats["print_statements_found"] += len(print_statements)

            if print_statements:
                logger.info(f"发现 {len(print_statements)} 个print语句: {file_path}")

                # 转换文件
                if not self.dry_run:
                    self.convert_file(file_path, print_statements)

        return analysis_results


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Convert print statements to logging calls"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="预览模式，不实际修改文件"
    )
    parser.add_argument("--no-backup", action="store_true", help="不创建备份文件")
    parser.add_argument("--files", nargs="*", help="指定要处理的文件列表")
    parser.add_argument(
        "--report-file", default="logs/print_conversion_report.txt", help="报告文件路径"
    )

    args = parser.parse_args()

    # 创建转换器
    converter = PrintConverter(
        project_root=project_root, dry_run=args.dry_run, backup=not args.no_backup
    )

    try:
        # 执行转换
        results = converter.convert_project(target_files=args.files)

        # 生成报告
        report = converter.generate_report(results)

        # 保存报告
        report_path = Path(args.report_file)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)

        # 输出报告到控制台
        print(report)
        print(f"\n详细报告已保存到: {report_path}")

        if args.dry_run:
            print("\n这是预览模式。要实际执行转换，请移除 --dry-run 参数。")

    except Exception as e:
        logger.error(f"转换过程中发生错误: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
