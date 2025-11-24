#!/usr/bin/env python3
"""
TextLoom 依赖包更新管理工具
===========================

功能：
1. 依赖版本分析和比较
2. 安全更新检查和推荐
3. 兼容性检查和测试
4. 自动化更新建议
5. 依赖锁定文件管理
"""

import argparse
import asyncio
import json
import logging
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
import tomli
from packaging import version
from packaging.requirements import Requirement

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class UpdateType(Enum):
    """更新类型"""

    MAJOR = "major"  # 主版本更新 (1.x.x -> 2.x.x)
    MINOR = "minor"  # 次版本更新 (1.1.x -> 1.2.x)
    PATCH = "patch"  # 补丁更新 (1.1.1 -> 1.1.2)
    SECURITY = "security"  # 安全更新
    PRERELEASE = "prerelease"  # 预发布版本


class UpdatePriority(Enum):
    """更新优先级"""

    CRITICAL = "critical"  # 严重安全漏洞，立即更新
    HIGH = "high"  # 重要功能或安全更新
    MEDIUM = "medium"  # 一般功能更新
    LOW = "low"  # 可选更新
    IGNORE = "ignore"  # 忽略更新


@dataclass
class PackageInfo:
    """包信息"""

    name: str
    current_version: str
    latest_version: str
    latest_stable_version: Optional[str]
    update_type: UpdateType
    priority: UpdatePriority
    security_advisory: Optional[str] = None
    changelog_url: Optional[str] = None
    release_date: Optional[str] = None
    compatibility_notes: List[str] = None

    def __post_init__(self):
        if self.compatibility_notes is None:
            self.compatibility_notes = []


@dataclass
class UpdatePlan:
    """更新计划"""

    timestamp: str
    total_packages: int
    updatable_packages: List[PackageInfo]
    security_updates: List[PackageInfo]
    breaking_changes: List[PackageInfo]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "total_packages": self.total_packages,
            "updatable_packages": [asdict(pkg) for pkg in self.updatable_packages],
            "security_updates": [asdict(pkg) for pkg in self.security_updates],
            "breaking_changes": [asdict(pkg) for pkg in self.breaking_changes],
            "recommendations": self.recommendations,
        }


class DependencyUpdater:
    """依赖包更新管理器"""

    # 关键依赖包配置
    CRITICAL_PACKAGES = {
        "fastapi",
        "sqlalchemy",
        "pydantic",
        "uvicorn",
        "celery",
        "redis",
        "openai",
        "requests",
        "httpx",
    }

    # 安全相关包
    SECURITY_PACKAGES = {
        "cryptography",
        "pyjwt",
        "passlib",
        "python-jose",
        "bcrypt",
        "pillow",
        "urllib3",
    }

    # 版本策略配置
    VERSION_POLICY = {
        "fastapi": {"max_major": False, "max_minor": True},  # 只允许次版本更新
        "sqlalchemy": {"max_major": False, "max_minor": True},
        "pydantic": {"max_major": False, "max_minor": True},
        "celery": {"max_major": False, "max_minor": True},
        "openai": {"max_major": True, "max_minor": True},  # 允许所有更新
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.reports_dir = project_root / "security_reports"
        self.reports_dir.mkdir(exist_ok=True)

    def _run_command(self, cmd: List[str]) -> Tuple[int, str, str]:
        """运行命令并返回结果"""
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=self.project_root, timeout=300
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"命令执行超时: {' '.join(cmd)}")
            return 1, "", "命令执行超时"
        except Exception as e:
            logger.error(f"命令执行失败: {e}")
            return 1, "", str(e)

    def _parse_pyproject_dependencies(self) -> Dict[str, str]:
        """解析 pyproject.toml 中的依赖"""
        pyproject_file = self.project_root / "pyproject.toml"
        dependencies = {}

        if not pyproject_file.exists():
            logger.warning("pyproject.toml 文件不存在")
            return dependencies

        try:
            with open(pyproject_file, "rb") as f:
                pyproject_data = tomli.load(f)

            # 解析主要依赖
            main_deps = pyproject_data.get("project", {}).get("dependencies", [])
            for dep_str in main_deps:
                req = Requirement(dep_str)
                dependencies[req.name] = (
                    str(req.specifier) if req.specifier else "latest"
                )

            # 解析开发依赖
            dev_deps = pyproject_data.get("dependency-groups", {}).get("dev", [])
            for dep_str in dev_deps:
                req = Requirement(dep_str)
                dependencies[f"{req.name}[dev]"] = (
                    str(req.specifier) if req.specifier else "latest"
                )

        except Exception as e:
            logger.error(f"解析 pyproject.toml 失败: {e}")

        return dependencies

    def _get_current_versions(self) -> Dict[str, str]:
        """获取当前安装的包版本"""
        cmd = ["uv", "run", "pip", "list", "--format=json"]
        returncode, stdout, stderr = self._run_command(cmd)

        versions = {}
        if returncode == 0 and stdout:
            try:
                pip_list = json.loads(stdout)
                versions = {pkg["name"].lower(): pkg["version"] for pkg in pip_list}
            except json.JSONDecodeError:
                logger.warning("无法解析 pip list 输出")

        return versions

    def _get_package_info_from_pypi(self, package_name: str) -> Dict[str, Any]:
        """从 PyPI 获取包信息"""
        try:
            url = f"https://pypi.org/pypi/{package_name}/json"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.warning(f"获取 {package_name} PyPI 信息失败: {e}")
            return {}

    def _determine_update_type(self, current: str, latest: str) -> UpdateType:
        """确定更新类型"""
        try:
            curr_version = version.parse(current)
            new_version = version.parse(latest)

            # 预发布版本检查
            if new_version.is_prerelease:
                return UpdateType.PRERELEASE

            # 版本比较
            if new_version.major > curr_version.major:
                return UpdateType.MAJOR
            elif new_version.minor > curr_version.minor:
                return UpdateType.MINOR
            elif new_version.micro > curr_version.micro:
                return UpdateType.PATCH
            else:
                return UpdateType.PATCH

        except Exception:
            return UpdateType.PATCH

    def _determine_update_priority(
        self, package_name: str, update_type: UpdateType, has_security_advisory: bool
    ) -> UpdatePriority:
        """确定更新优先级"""

        # 安全更新最高优先级
        if has_security_advisory:
            return UpdatePriority.CRITICAL

        # 关键包处理
        if package_name.lower() in self.CRITICAL_PACKAGES:
            if update_type == UpdateType.MAJOR:
                return UpdatePriority.MEDIUM  # 主版本更新需要仔细测试
            elif update_type == UpdateType.MINOR:
                return UpdatePriority.HIGH
            else:
                return UpdatePriority.HIGH

        # 安全相关包
        if package_name.lower() in self.SECURITY_PACKAGES:
            if update_type in [UpdateType.PATCH, UpdateType.MINOR]:
                return UpdatePriority.HIGH
            else:
                return UpdatePriority.MEDIUM

        # 一般包
        if update_type == UpdateType.MAJOR:
            return UpdatePriority.LOW
        elif update_type == UpdateType.MINOR:
            return UpdatePriority.MEDIUM
        else:
            return UpdatePriority.HIGH  # 补丁更新通常是安全的

    def _check_compatibility_issues(
        self, package_name: str, current: str, latest: str
    ) -> List[str]:
        """检查兼容性问题"""
        issues = []

        try:
            curr_version = version.parse(current)
            new_version = version.parse(latest)

            # 主版本更新警告
            if new_version.major > curr_version.major:
                issues.append(f"主版本更新可能包含破坏性变更")

            # 特定包的已知兼容性问题
            compatibility_warnings = {
                "pydantic": {
                    (1, 2): "Pydantic v2 包含重大API变更，需要代码适配",
                },
                "sqlalchemy": {
                    (1, 2): "SQLAlchemy v2 语法有显著变化",
                },
                "fastapi": {
                    (0, 1): "FastAPI v1.0 可能包含API变更",
                },
            }

            pkg_warnings = compatibility_warnings.get(package_name.lower(), {})
            for (from_major, to_major), warning in pkg_warnings.items():
                if curr_version.major == from_major and new_version.major == to_major:
                    issues.append(warning)

        except Exception:
            pass

        return issues

    def _generate_update_recommendations(
        self, packages: List[PackageInfo]
    ) -> List[str]:
        """生成更新建议"""
        recommendations = []

        # 按优先级分组
        critical_updates = [
            p for p in packages if p.priority == UpdatePriority.CRITICAL
        ]
        high_updates = [p for p in packages if p.priority == UpdatePriority.HIGH]
        medium_updates = [p for p in packages if p.priority == UpdatePriority.MEDIUM]

        if critical_updates:
            recommendations.append(
                f"🚨 立即处理 {len(critical_updates)} 个关键安全更新"
            )

        if high_updates:
            recommendations.append(f"⚡ 优先处理 {len(high_updates)} 个高优先级更新")

        # 更新策略建议
        recommendations.extend(
            [
                "📝 更新前创建备份和测试环境",
                "🧪 运行完整测试套件验证兼容性",
                "📊 监控更新后的系统性能和错误率",
                "🔄 建议采用分阶段更新策略",
            ]
        )

        if medium_updates:
            recommendations.append(f"📦 考虑更新 {len(medium_updates)} 个中优先级包")

        return recommendations

    async def analyze_dependencies(self) -> UpdatePlan:
        """分析依赖更新情况"""
        logger.info("开始分析依赖包更新...")

        timestamp = datetime.now().isoformat()
        current_versions = self._get_current_versions()
        declared_deps = self._parse_pyproject_dependencies()

        updatable_packages = []
        security_updates = []
        breaking_changes = []

        # 分析每个包
        for package_name, current_ver in current_versions.items():
            if package_name in ["pip", "setuptools", "wheel"]:
                continue  # 跳过基础包

            logger.info(f"分析包: {package_name} ({current_ver})")

            # 获取PyPI信息
            pypi_info = self._get_package_info_from_pypi(package_name)
            if not pypi_info:
                continue

            latest_version = pypi_info.get("info", {}).get("version", current_ver)

            # 跳过相同版本
            if current_ver == latest_version:
                continue

            # 确定更新类型和优先级
            update_type = self._determine_update_type(current_ver, latest_version)

            # 检查安全公告 (简化版，实际需要集成安全数据库)
            has_security_advisory = package_name.lower() in self.SECURITY_PACKAGES

            priority = self._determine_update_priority(
                package_name, update_type, has_security_advisory
            )

            # 检查兼容性问题
            compatibility_notes = self._check_compatibility_issues(
                package_name, current_ver, latest_version
            )

            # 获取发布信息
            release_info = pypi_info.get("releases", {}).get(latest_version, [{}])
            release_date = None
            if release_info:
                upload_time = release_info[0].get("upload_time")
                if upload_time:
                    release_date = upload_time.split("T")[0]

            package_info = PackageInfo(
                name=package_name,
                current_version=current_ver,
                latest_version=latest_version,
                latest_stable_version=latest_version,  # 简化处理
                update_type=update_type,
                priority=priority,
                security_advisory=None,  # 需要集成安全数据库
                changelog_url=pypi_info.get("info", {})
                .get("project_urls", {})
                .get("Changelog"),
                release_date=release_date,
                compatibility_notes=compatibility_notes,
            )

            updatable_packages.append(package_info)

            # 分类
            if has_security_advisory or priority == UpdatePriority.CRITICAL:
                security_updates.append(package_info)

            if update_type == UpdateType.MAJOR or compatibility_notes:
                breaking_changes.append(package_info)

        # 生成建议
        recommendations = self._generate_update_recommendations(updatable_packages)

        update_plan = UpdatePlan(
            timestamp=timestamp,
            total_packages=len(current_versions),
            updatable_packages=sorted(
                updatable_packages, key=lambda x: x.priority.value
            ),
            security_updates=security_updates,
            breaking_changes=breaking_changes,
            recommendations=recommendations,
        )

        # 保存分析结果
        self._save_update_plan(update_plan)

        return update_plan

    def _save_update_plan(self, plan: UpdatePlan):
        """保存更新计划"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plan_file = self.reports_dir / f"update_plan_{timestamp}.json"

        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(plan.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"更新计划已保存到: {plan_file}")

    def generate_update_script(
        self, plan: UpdatePlan, priority_threshold: str = "medium"
    ) -> str:
        """生成更新脚本"""
        script_lines = [
            "#!/bin/bash",
            "# TextLoom 依赖更新脚本",
            f"# 生成时间: {plan.timestamp}",
            "# 使用前请确保已备份项目和数据库",
            "",
            "set -e  # 遇到错误立即退出",
            "",
            "echo '🔄 开始依赖包更新...'",
            "",
        ]

        # 根据优先级过滤包
        priority_order = ["critical", "high", "medium", "low"]
        threshold_index = priority_order.index(priority_threshold)

        filtered_packages = [
            p
            for p in plan.updatable_packages
            if priority_order.index(p.priority.value) <= threshold_index
        ]

        if not filtered_packages:
            script_lines.append("echo '📦 没有需要更新的包'")
        else:
            # 分阶段更新
            critical_packages = [
                p for p in filtered_packages if p.priority == UpdatePriority.CRITICAL
            ]
            high_packages = [
                p for p in filtered_packages if p.priority == UpdatePriority.HIGH
            ]
            medium_packages = [
                p for p in filtered_packages if p.priority == UpdatePriority.MEDIUM
            ]

            if critical_packages:
                script_lines.extend(["echo '🚨 第一阶段: 关键安全更新'", ""])
                for pkg in critical_packages:
                    script_lines.append(
                        f"echo '更新 {pkg.name}: {pkg.current_version} -> {pkg.latest_version}'"
                    )
                    script_lines.append(f"uv add '{pkg.name}=={pkg.latest_version}'")
                    script_lines.append("")

                script_lines.extend(
                    [
                        "echo '✅ 关键更新完成，运行测试...'",
                        "uv run pytest tests/ --tb=short || (echo '❌ 测试失败，请检查' && exit 1)",
                        "",
                    ]
                )

            if high_packages:
                script_lines.extend(["echo '⚡ 第二阶段: 高优先级更新'", ""])
                for pkg in high_packages:
                    script_lines.append(
                        f"echo '更新 {pkg.name}: {pkg.current_version} -> {pkg.latest_version}'"
                    )
                    if pkg.compatibility_notes:
                        script_lines.append(
                            f"echo '  ⚠️ 注意: {pkg.compatibility_notes[0]}'"
                        )
                    script_lines.append(f"uv add '{pkg.name}=={pkg.latest_version}'")
                    script_lines.append("")

                script_lines.extend(
                    [
                        "echo '✅ 高优先级更新完成，运行测试...'",
                        "uv run pytest tests/ --tb=short || (echo '❌ 测试失败，请检查' && exit 1)",
                        "",
                    ]
                )

            if medium_packages:
                script_lines.extend(
                    [
                        "echo '📦 第三阶段: 中优先级更新 (可选)'",
                        "read -p '是否继续中优先级更新? (y/N): ' -n 1 -r",
                        "echo",
                        "if [[ $REPLY =~ ^[Yy]$ ]]; then",
                        "",
                    ]
                )
                for pkg in medium_packages:
                    script_lines.append(
                        f"  echo '更新 {pkg.name}: {pkg.current_version} -> {pkg.latest_version}'"
                    )
                    if pkg.compatibility_notes:
                        script_lines.append(
                            f"  echo '  ⚠️ 注意: {pkg.compatibility_notes[0]}'"
                        )
                    script_lines.append(f"  uv add '{pkg.name}=={pkg.latest_version}'")
                    script_lines.append("")

                script_lines.extend(
                    [
                        "  echo '✅ 中优先级更新完成，运行测试...'",
                        "  uv run pytest tests/ --tb=short || (echo '❌ 测试失败，请检查' && exit 1)",
                        "fi",
                        "",
                    ]
                )

        script_lines.extend(
            [
                "echo '🎉 依赖更新完成!'",
                "echo '📋 建议执行以下检查:'",
                "echo '  - 运行完整测试套件'",
                "echo '  - 检查应用启动和基本功能'",
                "echo '  - 监控系统性能和错误日志'",
            ]
        )

        return "\n".join(script_lines)

    def generate_markdown_report(self, plan: UpdatePlan) -> str:
        """生成 Markdown 更新报告"""
        report_lines = [
            "# TextLoom 依赖更新分析报告",
            "",
            f"**分析时间**: {plan.timestamp}",
            f"**总包数**: {plan.total_packages}",
            f"**可更新包数**: {len(plan.updatable_packages)}",
            f"**安全更新**: {len(plan.security_updates)}",
            f"**破坏性更新**: {len(plan.breaking_changes)}",
            "",
        ]

        # 优先级统计
        priority_counts = {}
        for pkg in plan.updatable_packages:
            priority_counts[pkg.priority] = priority_counts.get(pkg.priority, 0) + 1

        if priority_counts:
            report_lines.extend(["## 更新优先级分布", ""])

            for priority in [
                UpdatePriority.CRITICAL,
                UpdatePriority.HIGH,
                UpdatePriority.MEDIUM,
                UpdatePriority.LOW,
            ]:
                count = priority_counts.get(priority, 0)
                if count > 0:
                    emoji = {
                        "critical": "🚨",
                        "high": "⚡",
                        "medium": "📦",
                        "low": "🔹",
                    }.get(priority.value, "⚪")
                    report_lines.append(
                        f"- {emoji} {priority.value.upper()}: {count} 个"
                    )

            report_lines.append("")

        # 安全更新详情
        if plan.security_updates:
            report_lines.extend(["## 🚨 安全更新 (立即处理)", ""])

            for pkg in plan.security_updates:
                report_lines.extend(
                    [
                        f"### {pkg.name}",
                        f"- **当前版本**: {pkg.current_version}",
                        f"- **最新版本**: {pkg.latest_version}",
                        f"- **更新类型**: {pkg.update_type.value}",
                        "",
                    ]
                )

        # 破坏性更新详情
        if plan.breaking_changes:
            report_lines.extend(["## ⚠️ 破坏性更新 (需要仔细测试)", ""])

            for pkg in plan.breaking_changes:
                report_lines.extend(
                    [
                        f"### {pkg.name}",
                        f"- **当前版本**: {pkg.current_version}",
                        f"- **最新版本**: {pkg.latest_version}",
                        f"- **更新类型**: {pkg.update_type.value}",
                    ]
                )

                if pkg.compatibility_notes:
                    report_lines.append("- **兼容性注意事项**:")
                    for note in pkg.compatibility_notes:
                        report_lines.append(f"  - {note}")

                report_lines.append("")

        # 所有可更新包
        if plan.updatable_packages:
            report_lines.extend(
                [
                    "## 📦 所有可更新包",
                    "",
                    "| 包名 | 当前版本 | 最新版本 | 类型 | 优先级 | 发布日期 |",
                    "|------|----------|----------|------|--------|----------|",
                ]
            )

            for pkg in plan.updatable_packages:
                priority_emoji = {
                    "critical": "🚨",
                    "high": "⚡",
                    "medium": "📦",
                    "low": "🔹",
                }.get(pkg.priority.value, "⚪")
                type_emoji = {
                    "major": "🔴",
                    "minor": "🟡",
                    "patch": "🟢",
                    "security": "🚨",
                }.get(pkg.update_type.value, "⚪")

                report_lines.append(
                    f"| {pkg.name} | {pkg.current_version} | {pkg.latest_version} | "
                    f"{type_emoji} {pkg.update_type.value} | {priority_emoji} {pkg.priority.value} | {pkg.release_date or 'N/A'} |"
                )

        # 更新建议
        if plan.recommendations:
            report_lines.extend(["", "## 💡 更新建议", ""])
            for rec in plan.recommendations:
                report_lines.append(f"- {rec}")

        return "\n".join(report_lines)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="TextLoom 依赖包更新管理工具")
    parser.add_argument(
        "--output",
        "-o",
        default="console",
        choices=["console", "markdown", "json", "script"],
        help="输出格式 (默认: console)",
    )
    parser.add_argument(
        "--priority",
        default="medium",
        choices=["critical", "high", "medium", "low"],
        help="最低更新优先级 (默认: medium)",
    )
    parser.add_argument("--generate-script", action="store_true", help="生成更新脚本")

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    updater = DependencyUpdater(project_root)

    try:
        # 执行分析
        plan = await updater.analyze_dependencies()

        # 输出结果
        if args.output == "json":
            print(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False))
        elif args.output == "markdown":
            print(updater.generate_markdown_report(plan))
        elif args.output == "script" or args.generate_script:
            print(updater.generate_update_script(plan, args.priority))
        else:  # console
            print(f"\n📊 TextLoom 依赖更新分析")
            print(f"{'='*50}")
            print(f"分析时间: {plan.timestamp}")
            print(f"总包数: {plan.total_packages}")
            print(f"可更新包数: {len(plan.updatable_packages)}")
            print(f"安全更新: {len(plan.security_updates)}")
            print(f"破坏性更新: {len(plan.breaking_changes)}")

            if plan.security_updates:
                print(f"\n🚨 关键安全更新:")
                for pkg in plan.security_updates[:5]:
                    print(
                        f"  - {pkg.name}: {pkg.current_version} -> {pkg.latest_version}"
                    )

            if plan.updatable_packages:
                print(f"\n📦 最近更新的包:")
                sorted_by_date = sorted(
                    [p for p in plan.updatable_packages if p.release_date],
                    key=lambda x: x.release_date or "",
                    reverse=True,
                )
                for pkg in sorted_by_date[:10]:
                    priority_emoji = {
                        "critical": "🚨",
                        "high": "⚡",
                        "medium": "📦",
                        "low": "🔹",
                    }.get(pkg.priority.value, "⚪")
                    print(
                        f"  {priority_emoji} {pkg.name}: {pkg.current_version} -> {pkg.latest_version} ({pkg.release_date})"
                    )

            if plan.recommendations:
                print(f"\n💡 更新建议:")
                for rec in plan.recommendations[:5]:
                    print(f"  - {rec}")

        print(f"\n✅ 依赖分析完成")

    except Exception as e:
        logger.error(f"分析过程中出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
