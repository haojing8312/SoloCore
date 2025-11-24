#!/usr/bin/env python3
"""
TextLoom 依赖包安全扫描工具
==========================

功能：
1. 依赖漏洞扫描（safety, pip-audit）
2. 代码安全扫描（bandit, semgrep）
3. 版本分析和更新建议
4. 安全报告生成
5. CI/CD集成支持
"""

import argparse
import asyncio
import json
import logging
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 设置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SeverityLevel(Enum):
    """漏洞严重程度"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Vulnerability:
    """漏洞信息"""

    package: str
    installed_version: str
    vulnerability_id: str
    title: str
    description: str
    severity: SeverityLevel
    affected_versions: str
    fixed_version: Optional[str]
    published_date: Optional[str]
    advisory_url: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SecurityScanResult:
    """安全扫描结果"""

    scan_time: str
    total_packages: int
    vulnerable_packages: int
    vulnerabilities: List[Vulnerability]
    scan_errors: List[str]
    recommendations: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scan_time": self.scan_time,
            "total_packages": self.total_packages,
            "vulnerable_packages": self.vulnerable_packages,
            "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
            "scan_errors": self.scan_errors,
            "recommendations": self.recommendations,
        }


class DependencySecurityScanner:
    """依赖包安全扫描器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.reports_dir = project_root / "security_reports"
        self.reports_dir.mkdir(exist_ok=True)

    def _run_command(
        self, cmd: List[str], capture_output: bool = True
    ) -> Tuple[int, str, str]:
        """运行命令并返回结果"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                cwd=self.project_root,
                timeout=300,  # 5分钟超时
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            logger.error(f"命令执行超时: {' '.join(cmd)}")
            return 1, "", "命令执行超时"
        except Exception as e:
            logger.error(f"命令执行失败: {e}")
            return 1, "", str(e)

    async def scan_with_safety(self) -> List[Vulnerability]:
        """使用 safety 扫描依赖漏洞"""
        logger.info("开始 Safety 安全扫描...")
        vulnerabilities = []

        # 使用 safety 扫描
        cmd = ["uv", "run", "safety", "check", "--json", "--continue-on-error"]
        returncode, stdout, stderr = self._run_command(cmd)

        if returncode != 0 and not stdout:
            logger.warning(f"Safety 扫描出错: {stderr}")
            return vulnerabilities

        try:
            # Safety 输出格式解析
            if stdout:
                safety_data = json.loads(stdout)
                if isinstance(safety_data, list):
                    for item in safety_data:
                        vuln = Vulnerability(
                            package=item.get("package", ""),
                            installed_version=item.get("installed_version", ""),
                            vulnerability_id=item.get("id", ""),
                            title=item.get("advisory", "Unknown vulnerability"),
                            description=item.get("advisory", ""),
                            severity=self._parse_severity(
                                item.get("severity", "medium")
                            ),
                            affected_versions=item.get("specs", ""),
                            fixed_version=None,  # Safety 通常不提供修复版本
                            published_date=None,
                            advisory_url=None,
                        )
                        vulnerabilities.append(vuln)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"解析 Safety 输出失败: {e}")

        logger.info(f"Safety 扫描完成，发现 {len(vulnerabilities)} 个漏洞")
        return vulnerabilities

    async def scan_with_pip_audit(self) -> List[Vulnerability]:
        """使用 pip-audit 扫描依赖漏洞"""
        logger.info("开始 pip-audit 安全扫描...")
        vulnerabilities = []

        # 使用 pip-audit 扫描
        cmd = ["uv", "run", "pip-audit", "--format=json", "--desc"]
        returncode, stdout, stderr = self._run_command(cmd)

        if returncode != 0 and not stdout:
            logger.warning(f"pip-audit 扫描出错: {stderr}")
            return vulnerabilities

        try:
            if stdout:
                audit_data = json.loads(stdout)
                vulnerabilities_data = audit_data.get("vulnerabilities", [])

                for item in vulnerabilities_data:
                    package = item.get("package", "")
                    installed_version = item.get("installed_version", "")

                    for vuln_detail in item.get("vulnerabilities", []):
                        vuln = Vulnerability(
                            package=package,
                            installed_version=installed_version,
                            vulnerability_id=vuln_detail.get("id", ""),
                            title=vuln_detail.get("summary", "Unknown vulnerability"),
                            description=vuln_detail.get("description", ""),
                            severity=self._parse_severity(
                                "medium"
                            ),  # pip-audit 默认严重程度
                            affected_versions=", ".join(
                                vuln_detail.get("affected_versions", [])
                            ),
                            fixed_version=", ".join(
                                vuln_detail.get("fixed_versions", [])
                            ),
                            published_date=vuln_detail.get("published", ""),
                            advisory_url=vuln_detail.get("advisory_url", ""),
                        )
                        vulnerabilities.append(vuln)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"解析 pip-audit 输出失败: {e}")

        logger.info(f"pip-audit 扫描完成，发现 {len(vulnerabilities)} 个漏洞")
        return vulnerabilities

    async def scan_with_bandit(self) -> Dict[str, Any]:
        """使用 bandit 扫描代码安全问题"""
        logger.info("开始 Bandit 代码安全扫描...")

        cmd = [
            "uv",
            "run",
            "bandit",
            "-r",
            ".",
            "-f",
            "json",
            "--exclude",
            ".venv,venv,__pycache__,logs,workspace,test,tests",
        ]
        returncode, stdout, stderr = self._run_command(cmd)

        try:
            if stdout:
                bandit_data = json.loads(stdout)
                return bandit_data
        except json.JSONDecodeError as e:
            logger.error(f"解析 Bandit 输出失败: {e}")

        return {"results": [], "metrics": {}}

    async def scan_with_semgrep(self) -> Dict[str, Any]:
        """使用 semgrep 扫描安全问题"""
        logger.info("开始 Semgrep 安全扫描...")

        cmd = [
            "uv",
            "run",
            "semgrep",
            "--config=auto",
            "--json",
            "--exclude=.venv",
            "--exclude=venv",
            "--exclude=logs",
            "--exclude=workspace",
        ]
        returncode, stdout, stderr = self._run_command(cmd)

        try:
            if stdout:
                semgrep_data = json.loads(stdout)
                return semgrep_data
        except json.JSONDecodeError as e:
            logger.error(f"解析 Semgrep 输出失败: {e}")

        return {"results": []}

    def _parse_severity(self, severity_str: str) -> SeverityLevel:
        """解析严重程度字符串"""
        severity_map = {
            "critical": SeverityLevel.CRITICAL,
            "high": SeverityLevel.HIGH,
            "medium": SeverityLevel.MEDIUM,
            "low": SeverityLevel.LOW,
            "info": SeverityLevel.INFO,
        }
        return severity_map.get(severity_str.lower(), SeverityLevel.MEDIUM)

    def _get_package_info(self) -> Dict[str, str]:
        """获取已安装包信息"""
        cmd = ["uv", "run", "pip", "list", "--format=json"]
        returncode, stdout, stderr = self._run_command(cmd)

        packages = {}
        if returncode == 0 and stdout:
            try:
                pip_list = json.loads(stdout)
                packages = {pkg["name"]: pkg["version"] for pkg in pip_list}
            except json.JSONDecodeError:
                logger.warning("无法解析 pip list 输出")

        return packages

    def _generate_recommendations(
        self, vulnerabilities: List[Vulnerability]
    ) -> List[str]:
        """生成修复建议"""
        recommendations = []

        # 按包名分组漏洞
        package_vulns = {}
        for vuln in vulnerabilities:
            if vuln.package not in package_vulns:
                package_vulns[vuln.package] = []
            package_vulns[vuln.package].append(vuln)

        # 为每个有漏洞的包生成建议
        for package, vulns in package_vulns.items():
            high_severity_count = sum(
                1
                for v in vulns
                if v.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]
            )

            if high_severity_count > 0:
                recommendations.append(f"🚨 高优先级: 立即更新 {package}")

            fixed_versions = [v.fixed_version for v in vulns if v.fixed_version]
            if fixed_versions:
                recommendations.append(
                    f"📦 {package}: 建议升级到 {', '.join(fixed_versions)}"
                )
            else:
                recommendations.append(f"⚠️ {package}: 检查是否有可用更新")

        # 通用建议
        if vulnerabilities:
            recommendations.extend(
                [
                    "🔄 定期运行 'uv sync --upgrade' 更新依赖",
                    "📋 考虑使用 Dependabot 自动化依赖更新",
                    "🔍 在 CI/CD 中集成安全扫描",
                    "📊 建立漏洞响应流程和SLA",
                ]
            )

        return recommendations

    async def run_full_scan(self) -> SecurityScanResult:
        """执行完整的安全扫描"""
        logger.info("开始完整安全扫描...")
        scan_time = datetime.now().isoformat()

        # 获取包信息
        packages = self._get_package_info()
        total_packages = len(packages)

        # 并发运行所有扫描
        safety_task = asyncio.create_task(self.scan_with_safety())
        pip_audit_task = asyncio.create_task(self.scan_with_pip_audit())
        bandit_task = asyncio.create_task(self.scan_with_bandit())
        semgrep_task = asyncio.create_task(self.scan_with_semgrep())

        # 收集结果
        safety_vulns = await safety_task
        pip_audit_vulns = await pip_audit_task
        bandit_results = await bandit_task
        semgrep_results = await semgrep_task

        # 合并漏洞（去重）
        all_vulnerabilities = safety_vulns + pip_audit_vulns
        unique_vulnerabilities = self._deduplicate_vulnerabilities(all_vulnerabilities)

        # 统计有漏洞的包数量
        vulnerable_packages = len(set(v.package for v in unique_vulnerabilities))

        # 生成建议
        recommendations = self._generate_recommendations(unique_vulnerabilities)

        # 收集扫描错误
        scan_errors = []

        result = SecurityScanResult(
            scan_time=scan_time,
            total_packages=total_packages,
            vulnerable_packages=vulnerable_packages,
            vulnerabilities=unique_vulnerabilities,
            scan_errors=scan_errors,
            recommendations=recommendations,
        )

        # 保存详细结果
        self._save_detailed_results(result, bandit_results, semgrep_results)

        return result

    def _deduplicate_vulnerabilities(
        self, vulnerabilities: List[Vulnerability]
    ) -> List[Vulnerability]:
        """去重漏洞信息"""
        seen = set()
        unique_vulns = []

        for vuln in vulnerabilities:
            key = (vuln.package, vuln.vulnerability_id, vuln.installed_version)
            if key not in seen:
                seen.add(key)
                unique_vulns.append(vuln)

        return unique_vulns

    def _save_detailed_results(
        self,
        scan_result: SecurityScanResult,
        bandit_results: Dict[str, Any],
        semgrep_results: Dict[str, Any],
    ):
        """保存详细扫描结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存依赖漏洞扫描结果
        deps_file = self.reports_dir / f"dependency_scan_{timestamp}.json"
        with open(deps_file, "w", encoding="utf-8") as f:
            json.dump(scan_result.to_dict(), f, indent=2, ensure_ascii=False)

        # 保存代码安全扫描结果
        code_scan_results = {
            "scan_time": scan_result.scan_time,
            "bandit": bandit_results,
            "semgrep": semgrep_results,
        }
        code_file = self.reports_dir / f"code_security_scan_{timestamp}.json"
        with open(code_file, "w", encoding="utf-8") as f:
            json.dump(code_scan_results, f, indent=2, ensure_ascii=False)

        logger.info(f"详细扫描结果已保存到:")
        logger.info(f"  - 依赖漏洞: {deps_file}")
        logger.info(f"  - 代码安全: {code_file}")

    def generate_markdown_report(self, scan_result: SecurityScanResult) -> str:
        """生成 Markdown 格式报告"""
        report_lines = [
            f"# TextLoom 安全扫描报告",
            f"",
            f"**扫描时间**: {scan_result.scan_time}",
            f"**总包数**: {scan_result.total_packages}",
            f"**有漏洞包数**: {scan_result.vulnerable_packages}",
            f"**漏洞总数**: {len(scan_result.vulnerabilities)}",
            f"",
        ]

        # 按严重程度统计
        severity_counts = {}
        for vuln in scan_result.vulnerabilities:
            severity_counts[vuln.severity] = severity_counts.get(vuln.severity, 0) + 1

        if severity_counts:
            report_lines.extend(["## 漏洞分布", ""])

            for severity in [
                SeverityLevel.CRITICAL,
                SeverityLevel.HIGH,
                SeverityLevel.MEDIUM,
                SeverityLevel.LOW,
            ]:
                count = severity_counts.get(severity, 0)
                if count > 0:
                    emoji = {
                        "critical": "🔴",
                        "high": "🟠",
                        "medium": "🟡",
                        "low": "🟢",
                    }.get(severity.value, "⚪")
                    report_lines.append(
                        f"- {emoji} {severity.value.upper()}: {count} 个"
                    )

            report_lines.append("")

        # 漏洞详情
        if scan_result.vulnerabilities:
            report_lines.extend(["## 漏洞详情", ""])

            # 按严重程度排序
            sorted_vulns = sorted(
                scan_result.vulnerabilities,
                key=lambda v: ["critical", "high", "medium", "low"].index(
                    v.severity.value
                ),
            )

            current_package = None
            for vuln in sorted_vulns:
                if vuln.package != current_package:
                    report_lines.extend(
                        [f"### 📦 {vuln.package} ({vuln.installed_version})", ""]
                    )
                    current_package = vuln.package

                severity_emoji = {
                    "critical": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🟢",
                }.get(vuln.severity.value, "⚪")
                report_lines.extend(
                    [
                        f"**{severity_emoji} {vuln.vulnerability_id}**: {vuln.title}",
                        f"- **严重程度**: {vuln.severity.value.upper()}",
                        f"- **描述**: {vuln.description[:200]}{'...' if len(vuln.description) > 200 else ''}",
                    ]
                )

                if vuln.fixed_version:
                    report_lines.append(f"- **修复版本**: {vuln.fixed_version}")
                if vuln.advisory_url:
                    report_lines.append(f"- **详情链接**: {vuln.advisory_url}")

                report_lines.append("")

        # 修复建议
        if scan_result.recommendations:
            report_lines.extend(["## 修复建议", ""])
            for rec in scan_result.recommendations:
                report_lines.append(f"- {rec}")
            report_lines.append("")

        return "\n".join(report_lines)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="TextLoom 依赖包安全扫描工具")
    parser.add_argument(
        "--output",
        "-o",
        default="console",
        choices=["console", "markdown", "json"],
        help="输出格式 (默认: console)",
    )
    parser.add_argument(
        "--severity-threshold",
        default="low",
        choices=["critical", "high", "medium", "low"],
        help="最低严重程度阈值 (默认: low)",
    )
    parser.add_argument(
        "--fail-on-vuln", action="store_true", help="发现漏洞时退出码非零 (用于CI/CD)"
    )

    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    scanner = DependencySecurityScanner(project_root)

    try:
        # 执行扫描
        result = await scanner.run_full_scan()

        # 根据严重程度过滤
        threshold_levels = ["critical", "high", "medium", "low"]
        min_level = threshold_levels.index(args.severity_threshold)

        filtered_vulns = [
            v
            for v in result.vulnerabilities
            if threshold_levels.index(v.severity.value) <= min_level
        ]

        # 输出结果
        if args.output == "json":
            result.vulnerabilities = filtered_vulns
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
        elif args.output == "markdown":
            result.vulnerabilities = filtered_vulns
            print(scanner.generate_markdown_report(result))
        else:  # console
            print(f"\n🔍 TextLoom 安全扫描结果")
            print(f"{'='*50}")
            print(f"扫描时间: {result.scan_time}")
            print(f"总包数: {result.total_packages}")
            print(f"有漏洞包数: {result.vulnerable_packages}")
            print(f"漏洞总数: {len(filtered_vulns)}")

            if filtered_vulns:
                print(f"\n⚠️ 发现的漏洞:")
                for vuln in filtered_vulns[:10]:  # 只显示前10个
                    severity_color = {
                        "critical": "🔴",
                        "high": "🟠",
                        "medium": "🟡",
                        "low": "🟢",
                    }.get(vuln.severity.value, "⚪")

                    print(f"{severity_color} {vuln.package} ({vuln.installed_version})")
                    print(f"   ID: {vuln.vulnerability_id}")
                    print(
                        f"   {vuln.title[:80]}{'...' if len(vuln.title) > 80 else ''}"
                    )
                    if vuln.fixed_version:
                        print(f"   修复版本: {vuln.fixed_version}")
                    print()

                if len(filtered_vulns) > 10:
                    print(
                        f"... 还有 {len(filtered_vulns) - 10} 个漏洞，查看完整报告获取详情"
                    )

            if result.recommendations:
                print(f"\n💡 修复建议:")
                for rec in result.recommendations[:5]:
                    print(f"- {rec}")

        # CI/CD 集成：根据漏洞数量决定退出码
        if args.fail_on_vuln and filtered_vulns:
            logger.error(f"发现 {len(filtered_vulns)} 个漏洞，退出")
            sys.exit(1)

        print(f"\n✅ 安全扫描完成")

    except Exception as e:
        logger.error(f"扫描过程中出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
