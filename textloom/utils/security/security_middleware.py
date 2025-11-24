"""
安全中间件 - 实施多层防护策略

这个模块提供了全面的安全中间件，包括：
1. 请求频率限制
2. 安全头设置
3. 请求大小限制
4. 恶意请求检测
5. IP白名单/黑名单
6. 安全审计日志

符合OWASP安全防护最佳实践
"""

import asyncio
import hashlib
import ipaddress
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


@dataclass
class SecurityConfig:
    """安全配置"""

    # 速率限制配置
    rate_limit_requests: int = 100  # 每分钟请求数
    rate_limit_window: int = 60  # 时间窗口（秒）
    burst_limit: int = 20  # 突发限制

    # 请求大小限制
    max_request_size: int = 52428800  # 50MB
    max_json_size: int = 10485760  # 10MB
    max_form_size: int = 52428800  # 50MB

    # IP访问控制
    ip_whitelist: Set[str] = field(default_factory=set)
    ip_blacklist: Set[str] = field(default_factory=set)
    enable_geo_blocking: bool = False
    blocked_countries: Set[str] = field(default_factory=set)

    # 安全头配置
    enable_security_headers: bool = True
    hsts_max_age: int = 31536000  # 1年
    csp_policy: str = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    )

    # 恶意请求检测
    enable_threat_detection: bool = True
    suspicious_user_agents: Set[str] = field(
        default_factory=lambda: {
            "sqlmap",
            "nmap",
            "nikto",
            "dirb",
            "gobuster",
            "wfuzz",
            "burp",
            "zap",
            "acunetix",
            "nessus",
            "openvas",
        }
    )

    # 审计配置
    enable_audit_logging: bool = True
    audit_log_file: str = "logs/security_audit.log"
    log_sensitive_data: bool = False


class RateLimiter:
    """速率限制器"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.blocked_ips: Dict[str, float] = {}

    def is_allowed(self, client_ip: str) -> bool:
        """检查是否允许请求"""
        current_time = time.time()

        # 检查是否在封禁列表中
        if client_ip in self.blocked_ips:
            if current_time < self.blocked_ips[client_ip]:
                return False
            else:
                del self.blocked_ips[client_ip]

        # 清理过期请求记录
        cutoff_time = current_time - self.config.rate_limit_window
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip] if req_time > cutoff_time
        ]

        # 检查请求数量
        request_count = len(self.requests[client_ip])

        # 突发限制检查
        recent_requests = [
            req_time
            for req_time in self.requests[client_ip]
            if req_time > current_time - 10  # 最近10秒
        ]

        if len(recent_requests) > self.config.burst_limit:
            # 临时封禁5分钟
            self.blocked_ips[client_ip] = current_time + 300
            logger.warning(f"IP {client_ip} 触发突发限制，临时封禁5分钟")
            return False

        if request_count >= self.config.rate_limit_requests:
            logger.warning(
                f"IP {client_ip} 超过速率限制: {request_count}/{self.config.rate_limit_requests}"
            )
            return False

        # 记录当前请求
        self.requests[client_ip].append(current_time)
        return True


class ThreatDetector:
    """威胁检测器"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.suspicious_patterns = [
            # SQL注入模式
            r"(\bUNION\b|\bSELECT\b|\bINSERT\b|\bDELETE\b|\bDROP\b)",
            # XSS模式
            r"(<script|javascript:|vbscript:|onload=|onerror=)",
            # 命令注入模式
            r"(;|\||&|`|\$\(|nc\s|netcat|wget|curl)",
            # 路径遍历模式
            r"(\.\./|\.\.\\|/etc/|/bin/|/usr/)",
            # XXE模式
            r"(<!ENTITY|<!DOCTYPE.*ENTITY)",
        ]

        # 编译正则表达式
        import re

        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.suspicious_patterns
        ]

    def detect_threats(self, request: Request) -> List[str]:
        """检测请求中的威胁"""
        threats = []

        # 检查User-Agent
        user_agent = request.headers.get("user-agent", "").lower()
        for suspicious_ua in self.config.suspicious_user_agents:
            if suspicious_ua in user_agent:
                threats.append(f"可疑User-Agent: {suspicious_ua}")

        # 检查URL路径
        path = str(request.url.path)
        for pattern in self.compiled_patterns:
            if pattern.search(path):
                threats.append(f"URL路径包含可疑模式: {pattern.pattern}")

        # 检查查询参数
        query_string = str(request.url.query)
        if query_string:
            for pattern in self.compiled_patterns:
                if pattern.search(query_string):
                    threats.append(f"查询参数包含可疑模式: {pattern.pattern}")

        # 检查请求头
        for header_name, header_value in request.headers.items():
            if header_name.lower() in ["referer", "x-forwarded-for", "x-real-ip"]:
                for pattern in self.compiled_patterns:
                    if pattern.search(header_value):
                        threats.append(
                            f"请求头 {header_name} 包含可疑模式: {pattern.pattern}"
                        )

        return threats


class SecurityAuditor:
    """安全审计器"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.audit_logger = self._setup_audit_logger()

    def _setup_audit_logger(self) -> logging.Logger:
        """设置审计日志器"""
        audit_logger = logging.getLogger("security_audit")
        audit_logger.setLevel(logging.INFO)

        # 确保日志目录存在
        log_file = Path(self.config.audit_log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        # 文件处理器
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        audit_logger.addHandler(file_handler)

        return audit_logger

    def log_security_event(
        self, event_type: str, request: Request, details: Dict[str, Any]
    ):
        """记录安全事件"""
        if not self.config.enable_audit_logging:
            return

        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        audit_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "client_ip": client_ip,
            "method": request.method,
            "url": str(request.url),
            "user_agent": user_agent if self.config.log_sensitive_data else "***",
            "details": details,
        }

        # 移除敏感信息
        if not self.config.log_sensitive_data:
            if "headers" in audit_data["details"]:
                audit_data["details"]["headers"] = "***"
            if "body" in audit_data["details"]:
                audit_data["details"]["body"] = "***"

        self.audit_logger.info(json.dumps(audit_data, ensure_ascii=False))

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        # 检查代理头
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件"""

    def __init__(self, app, config: Optional[SecurityConfig] = None):
        super().__init__(app)
        self.config = config or SecurityConfig()
        self.rate_limiter = RateLimiter(self.config)
        self.threat_detector = ThreatDetector(self.config)
        self.auditor = SecurityAuditor(self.config)

    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        start_time = time.time()
        client_ip = self._get_client_ip(request)

        try:
            # 1. IP访问控制检查
            if not self._check_ip_access(client_ip):
                await self._log_blocked_request(
                    request,
                    "IP_BLOCKED",
                    {"reason": "IP in blacklist or not in whitelist"},
                )
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"error": "Access denied"},
                )

            # 2. 速率限制检查
            if not self.rate_limiter.is_allowed(client_ip):
                await self._log_blocked_request(
                    request, "RATE_LIMITED", {"reason": "Rate limit exceeded"}
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"error": "Rate limit exceeded"},
                    headers={"Retry-After": str(self.config.rate_limit_window)},
                )

            # 3. 请求大小检查
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > self.config.max_request_size:
                await self._log_blocked_request(
                    request, "REQUEST_TOO_LARGE", {"size": content_length}
                )
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={"error": "Request too large"},
                )

            # 4. 威胁检测
            if self.config.enable_threat_detection:
                threats = self.threat_detector.detect_threats(request)
                if threats:
                    await self._log_security_threat(request, threats)
                    # 根据威胁等级决定是否阻止请求
                    if self._is_high_threat(threats):
                        return JSONResponse(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            content={"error": "Malicious request detected"},
                        )

            # 5. 处理请求
            response = await call_next(request)

            # 6. 添加安全头
            if self.config.enable_security_headers:
                response = self._add_security_headers(response)

            # 7. 记录成功请求
            processing_time = time.time() - start_time
            await self._log_successful_request(
                request, response.status_code, processing_time
            )

            return response

        except Exception as e:
            # 记录异常
            await self._log_error(request, str(e))
            raise

    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        # 检查代理头
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"

    def _check_ip_access(self, client_ip: str) -> bool:
        """检查IP访问权限"""
        try:
            ip = ipaddress.ip_address(client_ip)

            # 检查黑名单
            for blocked_ip in self.config.ip_blacklist:
                if ip in ipaddress.ip_network(blocked_ip, strict=False):
                    return False

            # 检查白名单（如果配置了白名单）
            if self.config.ip_whitelist:
                for allowed_ip in self.config.ip_whitelist:
                    if ip in ipaddress.ip_network(allowed_ip, strict=False):
                        return True
                return False  # 有白名单但IP不在其中

            return True

        except ValueError:
            # 无效IP地址
            logger.warning(f"无效IP地址: {client_ip}")
            return False

    def _is_high_threat(self, threats: List[str]) -> bool:
        """判断是否为高威胁"""
        high_threat_keywords = ["SQL", "UNION", "script", "javascript", "ENTITY"]

        for threat in threats:
            for keyword in high_threat_keywords:
                if keyword.lower() in threat.lower():
                    return True

        return len(threats) >= 3  # 多个威胁指标

    def _add_security_headers(self, response):
        """添加安全响应头"""
        # HSTS
        response.headers["Strict-Transport-Security"] = (
            f"max-age={self.config.hsts_max_age}; includeSubDomains"
        )

        # CSP
        response.headers["Content-Security-Policy"] = self.config.csp_policy

        # 其他安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )

        # 移除敏感服务器信息
        response.headers.pop("Server", None)
        response.headers.pop("X-Powered-By", None)

        return response

    async def _log_blocked_request(
        self, request: Request, event_type: str, details: Dict[str, Any]
    ):
        """记录被阻止的请求"""
        self.auditor.log_security_event(event_type, request, details)

    async def _log_security_threat(self, request: Request, threats: List[str]):
        """记录安全威胁"""
        self.auditor.log_security_event(
            "THREAT_DETECTED", request, {"threats": threats}
        )

    async def _log_successful_request(
        self, request: Request, status_code: int, processing_time: float
    ):
        """记录成功请求"""
        # 只记录重要的成功请求或异常状态码
        if status_code >= 400 or request.method in ["POST", "PUT", "DELETE"]:
            self.auditor.log_security_event(
                "REQUEST_PROCESSED",
                request,
                {"status_code": status_code, "processing_time": processing_time},
            )

    async def _log_error(self, request: Request, error: str):
        """记录错误"""
        self.auditor.log_security_event("ERROR", request, {"error": error})


# 预定义安全配置
DEVELOPMENT_CONFIG = SecurityConfig(
    rate_limit_requests=1000,  # 开发环境更宽松的限制
    enable_geo_blocking=False,
    log_sensitive_data=True,  # 开发环境可以记录敏感数据用于调试
)

PRODUCTION_CONFIG = SecurityConfig(
    rate_limit_requests=100,
    burst_limit=10,
    enable_geo_blocking=True,
    log_sensitive_data=False,  # 生产环境不记录敏感数据
    csp_policy="default-src 'self'; script-src 'self'; style-src 'self'",  # 更严格的CSP
)


# 工厂函数
def create_security_middleware(app, environment: str = "production"):
    """创建安全中间件"""
    if environment == "development":
        config = DEVELOPMENT_CONFIG
    else:
        config = PRODUCTION_CONFIG

    return SecurityMiddleware(app, config)


# 装饰器：为路由添加额外安全检查
def require_api_key(api_key_header: str = "X-API-Key"):
    """API密钥验证装饰器"""

    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            api_key = request.headers.get(api_key_header)
            if not api_key:
                raise HTTPException(status_code=401, detail="API key required")

            # 这里应该验证API密钥的有效性
            # 示例：从数据库或配置中验证

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


def require_https(func):
    """HTTPS强制装饰器"""

    async def wrapper(request: Request, *args, **kwargs):
        if (
            request.url.scheme != "https"
            and not request.headers.get("x-forwarded-proto") == "https"
        ):
            raise HTTPException(status_code=426, detail="HTTPS required")

        return await func(request, *args, **kwargs)

    return wrapper
