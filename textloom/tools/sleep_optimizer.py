#!/usr/bin/env python3
"""
TextLoom Sleep调用优化器
========================

自动检测并优化项目中的阻塞sleep调用，提升异步性能。

功能：
1. 扫描所有Python文件中的time.sleep()调用
2. 识别同步/异步上下文
3. 生成优化建议和自动替换
4. 性能影响分析

Usage:
    python tools/sleep_optimizer.py --analyze
    python tools/sleep_optimizer.py --optimize --dry-run
    python tools/sleep_optimizer.py --optimize --apply
"""

import argparse
import ast
import logging
import os
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings


class SleepContext(Enum):
    """Sleep调用上下文类型"""

    SYNC_FUNCTION = "sync_function"  # 同步函数中
    ASYNC_FUNCTION = "async_function"  # 异步函数中
    CELERY_TASK = "celery_task"  # Celery任务中
    TEST_MOCK = "test_mock"  # 测试模拟延迟
    SCRIPT_TOOL = "script_tool"  # 独立脚本/工具
    RETRY_MECHANISM = "retry_mechanism"  # 重试机制
    POLLING_LOOP = "polling_loop"  # 轮询循环


@dataclass
class SleepCall:
    """Sleep调用信息"""

    file_path: str
    line_number: int
    function_name: str
    context: SleepContext
    sleep_duration: Optional[float]
    surrounding_code: str
    optimization_suggestion: str
    priority: str  # HIGH, MEDIUM, LOW


class SleepAnalyzer:
    """Sleep调用分析器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.sleep_calls: List[SleepCall] = []
        self.logger = self._setup_logging()

        # 排除的文件模式
        self.exclude_patterns = [
            "*/.venv/*",
            "*/venv/*",
            "*/env/*",
            "*/.git/*",
            "*/__pycache__/*",
            "*/node_modules/*",
            "*/dist/*",
            "*/build/*",
            "*/.env/*",
        ]

        # 异步关键词
        self.async_keywords = ["async def", "await", "asyncio", "aiohttp", "async with"]

        # Celery任务关键词
        self.celery_keywords = [
            "@celery.task",
            "@app.task",
            "celery_app",
            "from celery",
        ]

        # 测试文件关键词
        self.test_keywords = [
            "pytest",
            "unittest",
            "mock",
            "test_",
            "Mock",
            "MagicMock",
        ]

    def _setup_logging(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger("sleep_optimizer")
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def scan_project(self) -> List[SleepCall]:
        """扫描项目中的所有sleep调用"""
        self.logger.info(f"🔍 扫描项目目录: {self.project_root}")

        python_files = []
        for py_file in self.project_root.rglob("*.py"):
            # 检查是否应该排除
            if any(py_file.match(pattern) for pattern in self.exclude_patterns):
                continue
            python_files.append(py_file)

        self.logger.info(f"找到 {len(python_files)} 个Python文件")

        for file_path in python_files:
            try:
                self._analyze_file(file_path)
            except Exception as e:
                self.logger.warning(f"分析文件失败 {file_path}: {e}")

        self.logger.info(f"总共发现 {len(self.sleep_calls)} 个sleep调用")
        return self.sleep_calls

    def _analyze_file(self, file_path: Path):
        """分析单个文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (UnicodeDecodeError, PermissionError):
            return

        # 查找time.sleep调用
        sleep_pattern = r"time\.sleep\s*\(\s*([^)]+)\s*\)"
        matches = re.finditer(sleep_pattern, content)

        for match in matches:
            line_start = content.rfind("\n", 0, match.start()) + 1
            line_number = content[: match.start()].count("\n") + 1

            # 获取上下文信息
            context = self._determine_context(content, file_path, match.start())
            function_name = self._find_function_name(content, match.start())
            sleep_duration = self._extract_sleep_duration(match.group(1))
            surrounding_code = self._get_surrounding_code(content, match.start())

            # 生成优化建议
            suggestion = self._generate_optimization_suggestion(
                context, sleep_duration, file_path
            )

            # 确定优先级
            priority = self._determine_priority(context, file_path)

            sleep_call = SleepCall(
                file_path=str(file_path.relative_to(self.project_root)),
                line_number=line_number,
                function_name=function_name,
                context=context,
                sleep_duration=sleep_duration,
                surrounding_code=surrounding_code,
                optimization_suggestion=suggestion,
                priority=priority,
            )

            self.sleep_calls.append(sleep_call)

    def _determine_context(
        self, content: str, file_path: Path, position: int
    ) -> SleepContext:
        """确定sleep调用的上下文"""
        # 获取当前行及周围几行
        lines_before = content[:position].split("\n")[-10:]
        lines_after = content[position:].split("\n")[:10]
        context_lines = lines_before + lines_after
        context_text = "\n".join(context_lines)

        file_path_str = str(file_path)

        # 测试文件
        if "/tests/" in file_path_str or file_path.name.startswith("test_"):
            return SleepContext.TEST_MOCK

        # 脚本工具
        if "/scripts/" in file_path_str:
            return SleepContext.SCRIPT_TOOL

        # Celery任务上下文
        if any(keyword in context_text for keyword in self.celery_keywords):
            return SleepContext.CELERY_TASK

        # 重试机制
        if any(
            word in context_text.lower() for word in ["retry", "attempt", "backoff"]
        ):
            return SleepContext.RETRY_MECHANISM

        # 轮询循环
        if any(
            word in context_text.lower() for word in ["while", "poll", "wait", "check"]
        ):
            return SleepContext.POLLING_LOOP

        # 异步函数
        if any(keyword in context_text for keyword in self.async_keywords):
            return SleepContext.ASYNC_FUNCTION

        return SleepContext.SYNC_FUNCTION

    def _find_function_name(self, content: str, position: int) -> str:
        """查找包含sleep的函数名"""
        lines_before = content[:position].split("\n")

        for line in reversed(lines_before[-20:]):  # 检查前20行
            if line.strip().startswith("def ") or line.strip().startswith("async def "):
                func_match = re.search(r"def\s+(\w+)", line)
                if func_match:
                    return func_match.group(1)

        return "unknown"

    def _extract_sleep_duration(self, duration_str: str) -> Optional[float]:
        """提取sleep持续时间"""
        try:
            # 去除注释和空格
            duration_str = duration_str.split("#")[0].strip()

            # 尝试评估简单表达式
            if (
                duration_str.replace(".", "")
                .replace("*", "")
                .replace("/", "")
                .replace("+", "")
                .replace("-", "")
                .replace("(", "")
                .replace(")", "")
                .isdigit()
            ):
                return float(eval(duration_str))

            # 提取数字
            numbers = re.findall(r"\d+\.?\d*", duration_str)
            if numbers:
                return float(numbers[0])
        except:
            pass
        return None

    def _get_surrounding_code(
        self, content: str, position: int, lines_context: int = 3
    ) -> str:
        """获取周围代码上下文"""
        lines = content.split("\n")
        line_number = content[:position].count("\n")

        start_line = max(0, line_number - lines_context)
        end_line = min(len(lines), line_number + lines_context + 1)

        context_lines = []
        for i in range(start_line, end_line):
            marker = ">>> " if i == line_number else "    "
            context_lines.append(f"{marker}{i+1:3d}: {lines[i]}")

        return "\n".join(context_lines)

    def _generate_optimization_suggestion(
        self, context: SleepContext, duration: Optional[float], file_path: Path
    ) -> str:
        """生成优化建议"""
        suggestions = {
            SleepContext.ASYNC_FUNCTION: "替换为 await asyncio.sleep() 以避免阻塞事件循环",
            SleepContext.CELERY_TASK: "Celery任务中保持time.sleep()，但考虑使用更短的延迟或指数退避",
            SleepContext.TEST_MOCK: "测试中的模拟延迟，考虑减少延迟时间或使用mock.patch('time.sleep')",
            SleepContext.RETRY_MECHANISM: "重试机制：在异步上下文中使用await asyncio.sleep()，同步上下文保持time.sleep()",
            SleepContext.POLLING_LOOP: "轮询循环：考虑使用事件驱动或回调机制替代轮询",
            SleepContext.SCRIPT_TOOL: "独立脚本：如果脚本内部有异步操作，考虑使用asyncio.sleep()",
            SleepContext.SYNC_FUNCTION: "同步函数：检查是否在异步上下文中调用，如有则需要优化调用链",
        }

        base_suggestion = suggestions.get(context, "需要详细分析上下文")

        # 添加持续时间相关建议
        if duration:
            if duration > 1.0:
                base_suggestion += f" | 延迟时间较长({duration}s)，考虑优化"
            elif duration < 0.01:
                base_suggestion += f" | 延迟时间很短({duration}s)，影响较小"

        return base_suggestion

    def _determine_priority(self, context: SleepContext, file_path: Path) -> str:
        """确定优化优先级"""
        # 高优先级：异步函数中的阻塞调用
        if context == SleepContext.ASYNC_FUNCTION:
            return "HIGH"

        # 高优先级：主要业务代码中的重试机制
        if context == SleepContext.RETRY_MECHANISM and "/utils/" in str(file_path):
            return "HIGH"

        # 中优先级：Celery任务中的延迟
        if context == SleepContext.CELERY_TASK:
            return "MEDIUM"

        # 中优先级：轮询循环
        if context == SleepContext.POLLING_LOOP:
            return "MEDIUM"

        # 低优先级：测试和脚本
        if context in [SleepContext.TEST_MOCK, SleepContext.SCRIPT_TOOL]:
            return "LOW"

        return "MEDIUM"

    def generate_report(self) -> str:
        """生成分析报告"""
        if not self.sleep_calls:
            return "✅ 未发现time.sleep()调用"

        # 按优先级分组
        high_priority = [call for call in self.sleep_calls if call.priority == "HIGH"]
        medium_priority = [
            call for call in self.sleep_calls if call.priority == "MEDIUM"
        ]
        low_priority = [call for call in self.sleep_calls if call.priority == "LOW"]

        report_lines = [
            f"🔍 TextLoom Sleep调用分析报告",
            f"=" * 50,
            f"",
            f"📊 总体统计:",
            f"  总调用数: {len(self.sleep_calls)}",
            f"  高优先级: {len(high_priority)}",
            f"  中优先级: {len(medium_priority)}",
            f"  低优先级: {len(low_priority)}",
            f"",
        ]

        # 按优先级详细报告
        for priority_name, calls in [
            ("🚨 高优先级", high_priority),
            ("⚠️ 中优先级", medium_priority),
            ("ℹ️ 低优先级", low_priority),
        ]:
            if not calls:
                continue

            report_lines.extend(
                [
                    f"{priority_name} ({len(calls)}个):",
                    f"-" * 30,
                ]
            )

            for call in calls:
                duration_str = (
                    f" [{call.sleep_duration}s]" if call.sleep_duration else ""
                )
                report_lines.extend(
                    [
                        f"📁 {call.file_path}:{call.line_number}",
                        f"   函数: {call.function_name}{duration_str}",
                        f"   上下文: {call.context.value}",
                        f"   建议: {call.optimization_suggestion}",
                        f"",
                    ]
                )

        return "\n".join(report_lines)


class SleepOptimizer:
    """Sleep调用优化器"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.logger = logging.getLogger("sleep_optimizer")

    def optimize_file(self, sleep_call: SleepCall, dry_run: bool = True) -> bool:
        """优化单个文件中的sleep调用"""
        file_path = self.project_root / sleep_call.file_path

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 根据上下文决定优化策略
            new_content = self._apply_optimization(content, sleep_call)

            if new_content == content:
                self.logger.info(f"⏭️  跳过 {sleep_call.file_path} - 无需优化")
                return False

            if dry_run:
                self.logger.info(
                    f"🔄 [DRY-RUN] 将优化 {sleep_call.file_path}:{sleep_call.line_number}"
                )
                self._show_diff(content, new_content, sleep_call)
                return True
            else:
                # 备份原文件
                backup_path = file_path.with_suffix(".py.backup")
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(content)

                # 写入优化后的内容
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)

                self.logger.info(
                    f"✅ 已优化 {sleep_call.file_path}:{sleep_call.line_number}"
                )
                return True

        except Exception as e:
            self.logger.error(f"❌ 优化失败 {sleep_call.file_path}: {e}")
            return False

    def _apply_optimization(self, content: str, sleep_call: SleepCall) -> str:
        """应用具体的优化策略"""
        lines = content.split("\n")
        line_index = sleep_call.line_number - 1

        if line_index >= len(lines):
            return content

        original_line = lines[line_index]

        # 根据上下文应用不同优化
        if sleep_call.context == SleepContext.ASYNC_FUNCTION:
            # 替换为 await asyncio.sleep()
            new_line = re.sub(
                r"time\.sleep\s*\(", "await asyncio.sleep(", original_line
            )

            # 确保文件顶部有asyncio导入
            if "import asyncio" not in content and "from asyncio" not in content:
                # 找到合适的位置插入导入
                import_index = self._find_import_insert_position(lines)
                lines.insert(import_index, "import asyncio")
                line_index += 1  # 调整行索引

            lines[line_index] = new_line

        elif sleep_call.context == SleepContext.RETRY_MECHANISM:
            # 检查是否在异步上下文中
            if self._is_in_async_context(content, sleep_call.line_number):
                new_line = re.sub(
                    r"time\.sleep\s*\(", "await asyncio.sleep(", original_line
                )
                lines[line_index] = new_line

                # 确保导入asyncio
                if "import asyncio" not in content:
                    import_index = self._find_import_insert_position(lines)
                    lines.insert(import_index, "import asyncio")

        elif sleep_call.context == SleepContext.TEST_MOCK:
            # 测试中减少延迟时间
            if sleep_call.sleep_duration and sleep_call.sleep_duration > 0.05:
                new_line = re.sub(
                    r"time\.sleep\s*\([^)]+\)",
                    "time.sleep(0.01)",  # 减少到10ms
                    original_line,
                )
                lines[line_index] = new_line + "  # 优化：减少测试延迟"

        elif sleep_call.context == SleepContext.CELERY_TASK:
            # Celery任务中保持time.sleep但添加注释说明
            if "# Celery任务同步延迟" not in original_line:
                lines[line_index] = original_line + "  # Celery任务同步延迟"

        return "\n".join(lines)

    def _find_import_insert_position(self, lines: List[str]) -> int:
        """找到合适的导入插入位置"""
        # 跳过文档字符串和编码声明
        insert_pos = 0
        in_docstring = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # 跳过空行和注释
            if not stripped or stripped.startswith("#"):
                continue

            # 处理文档字符串
            if '"""' in stripped or "'''" in stripped:
                in_docstring = not in_docstring
                continue

            if in_docstring:
                continue

            # 找到第一个import语句
            if stripped.startswith(("import ", "from ")):
                return i

            # 如果遇到其他代码，插入到这里
            if stripped and not stripped.startswith(("#!/", "# -*-", "# coding")):
                return i

        return 0

    def _is_in_async_context(self, content: str, line_number: int) -> bool:
        """检查是否在异步上下文中"""
        lines = content.split("\n")

        # 往前查找函数定义
        for i in range(line_number - 1, -1, -1):
            line = lines[i].strip()
            if line.startswith("async def "):
                return True
            elif line.startswith("def "):
                return False

        return False

    def _show_diff(self, original: str, optimized: str, sleep_call: SleepCall):
        """显示优化前后的差异"""
        orig_lines = original.split("\n")
        opt_lines = optimized.split("\n")

        line_idx = sleep_call.line_number - 1
        context_range = 2

        start_idx = max(0, line_idx - context_range)
        end_idx = min(len(orig_lines), line_idx + context_range + 1)

        print(f"\n  📝 差异预览 ({sleep_call.file_path}):")
        print(f"     {'='*60}")

        for i in range(start_idx, end_idx):
            if i < len(orig_lines):
                orig_line = orig_lines[i] if i < len(orig_lines) else ""
                opt_line = opt_lines[i] if i < len(opt_lines) else ""

                if i == line_idx:
                    print(f"  -  {i+1:3d}: {orig_line}")
                    print(f"  +  {i+1:3d}: {opt_line}")
                else:
                    print(f"     {i+1:3d}: {orig_line}")
        print()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="TextLoom Sleep调用优化器")
    parser.add_argument("--analyze", action="store_true", help="分析sleep调用")
    parser.add_argument("--optimize", action="store_true", help="优化sleep调用")
    parser.add_argument(
        "--dry-run", action="store_true", help="干运行模式（不实际修改文件）"
    )
    parser.add_argument("--apply", action="store_true", help="应用优化（实际修改文件）")
    parser.add_argument(
        "--priority", choices=["HIGH", "MEDIUM", "LOW"], help="只处理指定优先级的调用"
    )
    parser.add_argument("--file", help="只处理指定文件")

    args = parser.parse_args()

    if not any([args.analyze, args.optimize]):
        parser.error("必须指定 --analyze 或 --optimize")

    project_root = Path(__file__).parent.parent
    analyzer = SleepAnalyzer(str(project_root))

    # 分析阶段
    sleep_calls = analyzer.scan_project()

    if args.analyze:
        report = analyzer.generate_report()
        print(report)
        return

    # 优化阶段
    if args.optimize:
        optimizer = SleepOptimizer(str(project_root))

        # 过滤要处理的调用
        calls_to_process = sleep_calls

        if args.priority:
            calls_to_process = [
                call for call in calls_to_process if call.priority == args.priority
            ]

        if args.file:
            calls_to_process = [
                call for call in calls_to_process if args.file in call.file_path
            ]

        if not calls_to_process:
            print("✅ 没有需要优化的调用")
            return

        dry_run = not args.apply
        if dry_run:
            print("🔍 干运行模式 - 仅预览更改")

        success_count = 0
        for call in calls_to_process:
            if optimizer.optimize_file(call, dry_run=dry_run):
                success_count += 1

        print(f"\n📊 优化完成: {success_count}/{len(calls_to_process)} 个文件")

        if dry_run:
            print("\n💡 使用 --apply 参数实际应用优化")


if __name__ == "__main__":
    main()
