#!/usr/bin/env python3
"""
CORS 安全配置测试脚本
验证 CORS 配置是否符合安全最佳实践
"""

import json
from dataclasses import dataclass
from typing import Any, Dict, List

import requests


@dataclass
class CORSTestResult:
    """CORS 测试结果"""

    test_name: str
    passed: bool
    details: str
    risk_level: str = "INFO"


class CORSSecurityTester:
    """CORS 安全测试器"""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.results: List[CORSTestResult] = []

    def test_wildcard_origins(self) -> CORSTestResult:
        """测试是否禁用了通配符源域名"""
        try:
            # 发送预检请求
            headers = {
                "Origin": "https://malicious-site.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            }

            response = requests.options(f"{self.base_url}/health", headers=headers)

            # 检查是否返回了 Access-Control-Allow-Origin: *
            allow_origin = response.headers.get("Access-Control-Allow-Origin", "")

            if allow_origin == "*":
                return CORSTestResult(
                    test_name="通配符源域名检查",
                    passed=False,
                    details="发现通配符源域名配置 '*'，存在 CSRF 风险",
                    risk_level="HIGH",
                )
            elif allow_origin:
                return CORSTestResult(
                    test_name="通配符源域名检查",
                    passed=False,
                    details=f"允许了非预期的源域名: {allow_origin}",
                    risk_level="MEDIUM",
                )
            else:
                return CORSTestResult(
                    test_name="通配符源域名检查",
                    passed=True,
                    details="正确拒绝了非白名单域名",
                    risk_level="INFO",
                )

        except Exception as e:
            return CORSTestResult(
                test_name="通配符源域名检查",
                passed=False,
                details=f"测试失败: {str(e)}",
                risk_level="ERROR",
            )

    def test_allowed_methods(self) -> CORSTestResult:
        """测试是否正确限制了 HTTP 方法"""
        try:
            # 测试危险的 HTTP 方法
            dangerous_methods = ["TRACE", "CONNECT", "PATCH"]

            for method in dangerous_methods:
                headers = {
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": method,
                }

                response = requests.options(f"{self.base_url}/health", headers=headers)
                allowed_methods = response.headers.get(
                    "Access-Control-Allow-Methods", ""
                )

                if method in allowed_methods:
                    return CORSTestResult(
                        test_name="HTTP方法限制检查",
                        passed=False,
                        details=f"允许了危险的 HTTP 方法: {method}",
                        risk_level="MEDIUM",
                    )

            return CORSTestResult(
                test_name="HTTP方法限制检查",
                passed=True,
                details="正确限制了危险的 HTTP 方法",
                risk_level="INFO",
            )

        except Exception as e:
            return CORSTestResult(
                test_name="HTTP方法限制检查",
                passed=False,
                details=f"测试失败: {str(e)}",
                risk_level="ERROR",
            )

    def test_credentials_security(self) -> CORSTestResult:
        """测试凭证配置安全性"""
        try:
            headers = {
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            }

            response = requests.options(f"{self.base_url}/health", headers=headers)

            allow_credentials = response.headers.get(
                "Access-Control-Allow-Credentials", ""
            ).lower()
            allow_origin = response.headers.get("Access-Control-Allow-Origin", "")

            # 检查是否同时启用了凭证和通配符源域名（违反 CORS 规范）
            if allow_credentials == "true" and allow_origin == "*":
                return CORSTestResult(
                    test_name="凭证安全性检查",
                    passed=False,
                    details="同时启用了凭证和通配符源域名，违反 CORS 规范",
                    risk_level="HIGH",
                )
            elif allow_credentials == "true":
                return CORSTestResult(
                    test_name="凭证安全性检查",
                    passed=True,
                    details="凭证已启用但源域名已正确限制",
                    risk_level="INFO",
                )
            else:
                return CORSTestResult(
                    test_name="凭证安全性检查",
                    passed=True,
                    details="凭证已禁用，安全配置",
                    risk_level="INFO",
                )

        except Exception as e:
            return CORSTestResult(
                test_name="凭证安全性检查",
                passed=False,
                details=f"测试失败: {str(e)}",
                risk_level="ERROR",
            )

    def test_header_restrictions(self) -> CORSTestResult:
        """测试请求头限制"""
        try:
            # 测试敏感头部
            sensitive_headers = ["X-Forwarded-For", "X-Real-IP", "Cookie"]

            for header in sensitive_headers:
                headers = {
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": header,
                }

                response = requests.options(f"{self.base_url}/health", headers=headers)
                allowed_headers = response.headers.get(
                    "Access-Control-Allow-Headers", ""
                )

                if "*" in allowed_headers:
                    return CORSTestResult(
                        test_name="请求头限制检查",
                        passed=False,
                        details="使用了通配符头部配置，可能泄露敏感信息",
                        risk_level="MEDIUM",
                    )

            return CORSTestResult(
                test_name="请求头限制检查",
                passed=True,
                details="正确限制了请求头",
                risk_level="INFO",
            )

        except Exception as e:
            return CORSTestResult(
                test_name="请求头限制检查",
                passed=False,
                details=f"测试失败: {str(e)}",
                risk_level="ERROR",
            )

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有 CORS 安全测试"""
        tests = [
            self.test_wildcard_origins,
            self.test_allowed_methods,
            self.test_credentials_security,
            self.test_header_restrictions,
        ]

        self.results = []
        for test in tests:
            result = test()
            self.results.append(result)

        # 生成报告
        passed_tests = sum(1 for r in self.results if r.passed)
        total_tests = len(self.results)

        high_risk_issues = [
            r for r in self.results if r.risk_level == "HIGH" and not r.passed
        ]
        medium_risk_issues = [
            r for r in self.results if r.risk_level == "MEDIUM" and not r.passed
        ]

        return {
            "summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "success_rate": f"{(passed_tests / total_tests * 100):.1f}%",
            },
            "security_score": self._calculate_security_score(),
            "risk_analysis": {
                "high_risk_issues": len(high_risk_issues),
                "medium_risk_issues": len(medium_risk_issues),
                "critical_findings": [r.details for r in high_risk_issues],
                "recommendations": self._get_recommendations(),
            },
            "detailed_results": [
                {
                    "test_name": r.test_name,
                    "status": "PASS" if r.passed else "FAIL",
                    "risk_level": r.risk_level,
                    "details": r.details,
                }
                for r in self.results
            ],
        }

    def _calculate_security_score(self) -> int:
        """计算安全评分（0-100）"""
        if not self.results:
            return 0

        score = 100
        for result in self.results:
            if not result.passed:
                if result.risk_level == "HIGH":
                    score -= 30
                elif result.risk_level == "MEDIUM":
                    score -= 15
                elif result.risk_level == "LOW":
                    score -= 5

        return max(0, score)

    def _get_recommendations(self) -> List[str]:
        """获取安全建议"""
        recommendations = []

        for result in self.results:
            if not result.passed:
                if "通配符" in result.details:
                    recommendations.append("明确指定允许的源域名，避免使用通配符")
                elif "危险的 HTTP 方法" in result.details:
                    recommendations.append("限制 HTTP 方法为业务必需的方法")
                elif "凭证" in result.details:
                    recommendations.append("正确配置凭证选项，避免与通配符同时使用")
                elif "请求头" in result.details:
                    recommendations.append("限制允许的请求头为最小必要集合")

        if not recommendations:
            recommendations.append("CORS 配置已符合安全最佳实践")

        return recommendations


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="CORS 安全配置测试")
    parser.add_argument("--url", default="http://localhost:8000", help="API 基础 URL")
    parser.add_argument(
        "--format", choices=["json", "text"], default="text", help="输出格式"
    )

    args = parser.parse_args()

    print(f"🔍 开始测试 CORS 安全配置: {args.url}")
    print("=" * 60)

    tester = CORSSecurityTester(args.url)
    report = tester.run_all_tests()

    if args.format == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        # 文本格式输出
        print(f"📊 测试概要:")
        summary = report["summary"]
        print(f"   总测试数: {summary['total_tests']}")
        print(f"   通过数: {summary['passed_tests']}")
        print(f"   失败数: {summary['failed_tests']}")
        print(f"   成功率: {summary['success_rate']}")
        print(f"   安全评分: {report['security_score']}/100")

        print(f"\n🚨 风险分析:")
        risk = report["risk_analysis"]
        print(f"   高风险问题: {risk['high_risk_issues']}")
        print(f"   中风险问题: {risk['medium_risk_issues']}")

        if risk["critical_findings"]:
            print(f"\n❌ 关键发现:")
            for finding in risk["critical_findings"]:
                print(f"   • {finding}")

        print(f"\n💡 安全建议:")
        for rec in risk["recommendations"]:
            print(f"   • {rec}")

        print(f"\n📋 详细结果:")
        for result in report["detailed_results"]:
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            risk_color = {
                "HIGH": "🔴",
                "MEDIUM": "🟡",
                "LOW": "🟢",
                "INFO": "ℹ️",
                "ERROR": "💥",
            }.get(result["risk_level"], "")

            print(f"   {status_icon} {result['test_name']} {risk_color}")
            print(f"      {result['details']}")


if __name__ == "__main__":
    main()
