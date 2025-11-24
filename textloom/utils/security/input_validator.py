"""
输入验证和清理工具 - 实施OWASP输入验证最佳实践

这个模块提供了全面的输入验证功能，包括：
1. URL安全验证和清理
2. 用户输入清理和转义
3. SQL注入防护
4. XSS防护
5. 命令注入防护
6. 路径遍历防护

符合OWASP Top 10防护要求
"""

import html
import ipaddress
import logging
import re
import urllib.parse
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """验证严格程度"""

    STRICT = "strict"  # 最严格验证
    STANDARD = "standard"  # 标准验证
    LENIENT = "lenient"  # 宽松验证


@dataclass
class ValidationResult:
    """验证结果"""

    is_valid: bool
    cleaned_value: str
    issues: List[str]
    warnings: List[str]
    risk_score: int  # 0-100，100为最高风险


class SecureInputValidator:
    """
    安全输入验证器

    实施多重防护策略防止各种注入攻击
    """

    # 危险字符模式
    DANGEROUS_PATTERNS = {
        "sql_injection": [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|JOIN)\b)",
            r"('|(\\')|(;)|(--)|(\/\*))",
            r"(\bOR\s+\w+\s*=\s*\w+)",
            r"(\bAND\s+\w+\s*=\s*\w+)",
            r"(\s*(=|<|>|!=)\s*\w+\s*(=|<|>|!=))",
            r"(0x[0-9A-Fa-f]+)",  # 十六进制编码
        ],
        "xss": [
            r"(<script[^>]*>.*?</script>)",
            r"(<.*?on\w+\s*=.*?>)",  # 事件处理器
            r"(javascript\s*:)",
            r"(vbscript\s*:)",
            r"(<iframe[^>]*>)",
            r"(<object[^>]*>)",
            r"(<embed[^>]*>)",
            r"(<link[^>]*>)",
            r"(<meta[^>]*>)",
        ],
        "command_injection": [
            r"(;|\||&|`|\$\(|\$\{)",  # 命令分隔符
            r"(\.\.|\\|/etc/|/bin/|/usr/)",  # 路径遍历
            r"(nc|netcat|wget|curl|ping|nslookup|dig)",  # 常见命令
            r"(>|<|>>|<<|\|)",  # 重定向
        ],
        "path_traversal": [
            r"(\.\./|\.\.\\)",  # 目录遍历
            r"(/etc/|/bin/|/usr/|/var/|/tmp/)",  # 敏感目录
            r"(\\windows\\|\\system32\\)",  # Windows系统目录
            r"(%2e%2e%2f|%2e%2e%5c)",  # URL编码的遍历
        ],
    }

    # 安全的URL协议白名单
    SAFE_URL_SCHEMES = {"http", "https", "ftp", "ftps"}

    # 私有IP地址范围
    PRIVATE_IP_RANGES = [
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
        ipaddress.ip_network("127.0.0.0/8"),  # 回环地址
        ipaddress.ip_network("169.254.0.0/16"),  # 链路本地地址
    ]

    def __init__(self, validation_level: ValidationLevel = ValidationLevel.STANDARD):
        """
        初始化验证器

        Args:
            validation_level: 验证严格程度
        """
        self.validation_level = validation_level

    def validate_url(
        self, url: str, allow_private_ips: bool = False
    ) -> ValidationResult:
        """
        验证和清理URL

        Args:
            url: 待验证的URL
            allow_private_ips: 是否允许私有IP地址

        Returns:
            ValidationResult: 验证结果
        """
        issues = []
        warnings = []
        risk_score = 0

        if not url or not isinstance(url, str):
            return ValidationResult(
                is_valid=False,
                cleaned_value="",
                issues=["URL为空或类型无效"],
                warnings=[],
                risk_score=100,
            )

        # 清理URL
        cleaned_url = self._clean_url(url)

        try:
            parsed = urlparse(cleaned_url)

            # 1. 协议验证
            if not parsed.scheme:
                issues.append("缺少协议")
                risk_score += 20
            elif parsed.scheme.lower() not in self.SAFE_URL_SCHEMES:
                issues.append(f"不安全的协议: {parsed.scheme}")
                risk_score += 50

            # 2. 主机名验证
            if not parsed.netloc:
                issues.append("缺少主机名")
                risk_score += 30
            else:
                host_validation = self._validate_hostname(
                    parsed.netloc, allow_private_ips
                )
                if not host_validation[0]:
                    issues.extend(host_validation[1])
                    risk_score += host_validation[2]
                warnings.extend(host_validation[3])

            # 3. 路径验证
            if parsed.path:
                path_validation = self._validate_path(parsed.path)
                if not path_validation[0]:
                    issues.extend(path_validation[1])
                    risk_score += 30
                warnings.extend(path_validation[2])

            # 4. 查询参数验证
            if parsed.query:
                query_validation = self._validate_query_params(parsed.query)
                if not query_validation[0]:
                    issues.extend(query_validation[1])
                    risk_score += 20
                warnings.extend(query_validation[2])

            # 5. 危险模式检测
            danger_check = self._check_dangerous_patterns(cleaned_url)
            if danger_check[1]:
                issues.extend(danger_check[1])
                risk_score += 40
            warnings.extend(danger_check[2])

        except Exception as e:
            issues.append(f"URL解析失败: {e}")
            risk_score = 100

        return ValidationResult(
            is_valid=len(issues) == 0,
            cleaned_value=cleaned_url,
            issues=issues,
            warnings=warnings,
            risk_score=min(risk_score, 100),
        )

    def validate_filename(self, filename: str) -> ValidationResult:
        """
        验证和清理文件名

        Args:
            filename: 待验证的文件名

        Returns:
            ValidationResult: 验证结果
        """
        issues = []
        warnings = []
        risk_score = 0

        if not filename or not isinstance(filename, str):
            return ValidationResult(
                is_valid=False,
                cleaned_value="",
                issues=["文件名为空或类型无效"],
                warnings=[],
                risk_score=100,
            )

        # 清理文件名
        cleaned_filename = self._clean_filename(filename)

        # 1. 长度检查
        if len(cleaned_filename) > 255:
            issues.append(f"文件名过长: {len(cleaned_filename)} > 255")
            risk_score += 20

        # 2. 危险字符检查
        dangerous_chars = '<>:"/\\|?*\x00'
        found_chars = [c for c in dangerous_chars if c in cleaned_filename]
        if found_chars:
            issues.append(f"包含危险字符: {found_chars}")
            risk_score += 30

        # 3. 路径遍历检查
        if ".." in cleaned_filename or cleaned_filename.startswith("/"):
            issues.append("包含路径遍历字符")
            risk_score += 50

        # 4. 扩展名检查
        ext_validation = self._validate_file_extension(cleaned_filename)
        if not ext_validation[0]:
            issues.extend(ext_validation[1])
            risk_score += ext_validation[2]
        warnings.extend(ext_validation[3])

        return ValidationResult(
            is_valid=len(issues) == 0,
            cleaned_value=cleaned_filename,
            issues=issues,
            warnings=warnings,
            risk_score=min(risk_score, 100),
        )

    def validate_text_input(
        self, text: str, max_length: int = 10000
    ) -> ValidationResult:
        """
        验证和清理文本输入

        Args:
            text: 待验证的文本
            max_length: 最大长度

        Returns:
            ValidationResult: 验证结果
        """
        issues = []
        warnings = []
        risk_score = 0

        if not isinstance(text, str):
            return ValidationResult(
                is_valid=False,
                cleaned_value="",
                issues=["输入不是字符串类型"],
                warnings=[],
                risk_score=100,
            )

        # 清理文本
        cleaned_text = self._clean_text_input(text)

        # 1. 长度检查
        if len(cleaned_text) > max_length:
            issues.append(f"文本过长: {len(cleaned_text)} > {max_length}")
            risk_score += 20

        # 2. 危险模式检测
        danger_check = self._check_dangerous_patterns(cleaned_text)
        if danger_check[1]:
            issues.extend(danger_check[1])
            risk_score += 40
        warnings.extend(danger_check[2])

        # 3. 编码检查
        encoding_check = self._check_encoding_issues(cleaned_text)
        if encoding_check[1]:
            warnings.extend(encoding_check[1])
            risk_score += 10

        return ValidationResult(
            is_valid=len(issues) == 0,
            cleaned_value=cleaned_text,
            issues=issues,
            warnings=warnings,
            risk_score=min(risk_score, 100),
        )

    def sanitize_for_html(self, text: str) -> str:
        """HTML安全化（防XSS）"""
        if not text:
            return ""

        # HTML转义
        sanitized = html.escape(text, quote=True)

        # 移除或转义危险属性
        sanitized = re.sub(
            r"on\w+\s*=", "data-blocked=", sanitized, flags=re.IGNORECASE
        )

        # 移除javascript:和vbscript:协议
        sanitized = re.sub(
            r"javascript\s*:", "blocked:", sanitized, flags=re.IGNORECASE
        )
        sanitized = re.sub(r"vbscript\s*:", "blocked:", sanitized, flags=re.IGNORECASE)

        return sanitized

    def sanitize_for_sql(self, text: str) -> str:
        """SQL安全化（防SQL注入）"""
        if not text:
            return ""

        # 转义单引号
        sanitized = text.replace("'", "''")

        # 移除或转义其他危险字符
        sanitized = re.sub(r"[;\-\-\/\*]", "", sanitized)

        return sanitized

    def sanitize_for_shell(self, text: str) -> str:
        """Shell命令安全化（防命令注入）"""
        if not text:
            return ""

        # 移除危险字符
        dangerous_chars = ";|&`$<>(){}[]"
        for char in dangerous_chars:
            text = text.replace(char, "")

        # 转义空格和特殊字符
        import shlex

        return shlex.quote(text)

    def _clean_url(self, url: str) -> str:
        """清理URL"""
        # 移除前后空白
        url = url.strip()

        # 规范化协议
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", url):
            if url.startswith("//"):
                url = "https:" + url
            elif not url.startswith("http"):
                url = "https://" + url

        # URL编码规范化
        try:
            parsed = urlparse(url)
            # 重新构建URL以确保正确编码
            clean_query = urlencode(parse_qs(parsed.query), doseq=True)
            clean_parsed = parsed._replace(query=clean_query)
            return urlunparse(clean_parsed)
        except Exception:
            return url

    def _validate_hostname(
        self, hostname: str, allow_private_ips: bool
    ) -> Tuple[bool, List[str], int, List[str]]:
        """验证主机名"""
        issues = []
        warnings = []
        risk_score = 0

        # 移除端口号
        host = hostname.split(":")[0]

        # 检查是否为IP地址
        try:
            ip = ipaddress.ip_address(host)

            # 检查私有IP地址
            if not allow_private_ips:
                for private_range in self.PRIVATE_IP_RANGES:
                    if ip in private_range:
                        issues.append(f"不允许访问私有IP地址: {ip}")
                        risk_score += 40
                        break

            # 检查特殊IP地址
            if ip.is_multicast:
                issues.append("不允许访问组播地址")
                risk_score += 30
            elif ip.is_loopback and not allow_private_ips:
                issues.append("不允许访问回环地址")
                risk_score += 30

        except ValueError:
            # 域名验证
            domain_validation = self._validate_domain_name(host)
            if not domain_validation[0]:
                issues.extend(domain_validation[1])
                risk_score += domain_validation[2]
            warnings.extend(domain_validation[3])

        return len(issues) == 0, issues, risk_score, warnings

    def _validate_domain_name(
        self, domain: str
    ) -> Tuple[bool, List[str], int, List[str]]:
        """验证域名"""
        issues = []
        warnings = []
        risk_score = 0

        # 基本格式检查
        if not re.match(r"^[a-zA-Z0-9.-]+$", domain):
            issues.append("域名包含无效字符")
            risk_score += 20

        # 长度检查
        if len(domain) > 253:
            issues.append("域名过长")
            risk_score += 10

        # 检查可疑域名模式
        suspicious_patterns = [
            r"\d+\.\d+\.\d+\.\d+",  # IP地址格式
            r"[0-9]{6,}",  # 长数字串
            r"[a-z]{20,}",  # 长随机字符串
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, domain):
                warnings.append(f"可疑的域名模式: {pattern}")
                risk_score += 5

        return len(issues) == 0, issues, risk_score, warnings

    def _validate_path(self, path: str) -> Tuple[bool, List[str], List[str]]:
        """验证URL路径"""
        issues = []
        warnings = []

        # 路径遍历检查
        if ".." in path:
            issues.append("路径包含目录遍历字符")

        # 检查敏感路径
        sensitive_paths = [
            "/etc/",
            "/bin/",
            "/usr/",
            "/var/",
            "/tmp/",
            "/admin/",
            "/wp-admin/",
            "/.env",
            "/config/",
        ]

        for sensitive in sensitive_paths:
            if sensitive in path.lower():
                warnings.append(f"访问敏感路径: {sensitive}")

        return len(issues) == 0, issues, warnings

    def _validate_query_params(self, query: str) -> Tuple[bool, List[str], List[str]]:
        """验证查询参数"""
        issues = []
        warnings = []

        try:
            params = parse_qs(query)

            # 检查参数数量
            if len(params) > 50:
                warnings.append(f"查询参数过多: {len(params)}")

            # 检查每个参数
            for key, values in params.items():
                # 检查参数名
                if not re.match(r"^[a-zA-Z0-9_-]+$", key):
                    warnings.append(f"可疑的参数名: {key}")

                # 检查参数值
                for value in values:
                    if len(value) > 1000:
                        warnings.append(f"参数值过长: {key}")

                    # 检查危险模式
                    danger_check = self._check_dangerous_patterns(value)
                    if danger_check[1]:
                        issues.extend(
                            [f"参数 {key}: {issue}" for issue in danger_check[1]]
                        )

        except Exception:
            warnings.append("查询参数解析失败")

        return len(issues) == 0, issues, warnings

    def _validate_file_extension(
        self, filename: str
    ) -> Tuple[bool, List[str], int, List[str]]:
        """验证文件扩展名"""
        issues = []
        warnings = []
        risk_score = 0

        ext = Path(filename).suffix.lower()

        # 危险扩展名检查
        dangerous_exts = {
            ".exe",
            ".bat",
            ".cmd",
            ".com",
            ".scr",
            ".pif",
            ".vbs",
            ".vbe",
            ".js",
            ".jse",
            ".wsf",
            ".wsh",
            ".ps1",
            ".msh",
            ".scf",
            ".lnk",
            ".inf",
            ".reg",
            ".asp",
            ".aspx",
            ".php",
            ".jsp",
            ".pl",
            ".py",
            ".rb",
            ".sh",
            ".jar",
            ".war",
        }

        if ext in dangerous_exts:
            issues.append(f"危险的文件扩展名: {ext}")
            risk_score += 50

        # 双扩展名检查
        parts = filename.split(".")
        if len(parts) > 2:
            warnings.append("多重扩展名文件")
            risk_score += 10

        return len(issues) == 0, issues, risk_score, warnings

    def _clean_filename(self, filename: str) -> str:
        """清理文件名"""
        # 移除控制字符
        cleaned = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", filename)

        # 规范化Unicode
        import unicodedata

        cleaned = unicodedata.normalize("NFKC", cleaned)

        return cleaned.strip()

    def _clean_text_input(self, text: str) -> str:
        """清理文本输入"""
        # 移除控制字符（保留换行和制表符）
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

        # 规范化Unicode
        import unicodedata

        cleaned = unicodedata.normalize("NFKC", cleaned)

        return cleaned.strip()

    def _check_dangerous_patterns(self, text: str) -> Tuple[bool, List[str], List[str]]:
        """检查危险模式"""
        issues = []
        warnings = []

        text_lower = text.lower()

        for category, patterns in self.DANGEROUS_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    if self.validation_level == ValidationLevel.STRICT:
                        issues.append(f"检测到{category}模式: {pattern}")
                    else:
                        warnings.append(f"可疑的{category}模式: {pattern}")

        return len(issues) == 0, issues, warnings

    def _check_encoding_issues(self, text: str) -> Tuple[bool, List[str]]:
        """检查编码问题"""
        warnings = []

        # 检查混合编码
        try:
            text.encode("ascii")
        except UnicodeEncodeError:
            warnings.append("包含非ASCII字符")

        # 检查可疑的Unicode字符
        suspicious_unicode = [
            "\u200b",  # 零宽空格
            "\u200c",  # 零宽非连接符
            "\u200d",  # 零宽连接符
            "\ufeff",  # 字节顺序标记
        ]

        for char in suspicious_unicode:
            if char in text:
                warnings.append(f"包含可疑Unicode字符: {repr(char)}")

        return len(warnings) == 0, warnings


# 全局实例
secure_input_validator = SecureInputValidator()
strict_validator = SecureInputValidator(ValidationLevel.STRICT)
lenient_validator = SecureInputValidator(ValidationLevel.LENIENT)
