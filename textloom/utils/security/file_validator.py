"""
文件安全验证工具 - 实施OWASP文件上传安全最佳实践

这个模块提供了全面的文件验证功能，包括：
1. MIME类型验证（魔数检查）
2. 文件头二进制特征识别
3. 文件内容安全扫描
4. 文件名安全化
5. 病毒扫描接口
6. 恶意内容检测

符合OWASP Top 10防护要求和安全编码最佳实践
"""

import hashlib
import logging
import mimetypes
import os
import re
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import magic

logger = logging.getLogger(__name__)


class SecurityThreatLevel(Enum):
    """安全威胁等级"""

    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FileType(Enum):
    """支持的文件类型"""

    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


@dataclass
class FileValidationResult:
    """文件验证结果"""

    is_valid: bool
    file_type: FileType
    detected_mime: str
    actual_extension: str
    threat_level: SecurityThreatLevel
    security_issues: List[str]
    warnings: List[str]
    file_hash: str
    file_size: int
    metadata: Dict[str, Any]


class SecureFileValidator:
    """
    安全文件验证器

    实施多层防护策略：
    1. 扩展名白名单
    2. MIME类型验证
    3. 文件头魔数检查
    4. 内容安全扫描
    5. 文件大小限制
    6. 文件名安全化
    """

    # 文件类型白名单 - 仅允许安全的业务文件类型
    ALLOWED_EXTENSIONS = {
        FileType.IMAGE: {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"},
        FileType.VIDEO: {".mp4", ".mov", ".mkv", ".avi", ".wmv", ".flv", ".webm"},
        FileType.DOCUMENT: {".md", ".markdown", ".txt"},
    }

    # MIME类型白名单
    ALLOWED_MIMES = {
        # 图片
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/bmp",
        # 视频
        "video/mp4",
        "video/quicktime",
        "video/x-msvideo",
        "video/x-ms-wmv",
        "video/x-flv",
        "video/webm",
        "video/x-matroska",
        # 文档
        "text/plain",
        "text/markdown",
        "text/x-markdown",
    }

    # 文件头魔数签名 - 用于检测真实文件类型
    MAGIC_SIGNATURES = {
        # 图片格式
        b"\xff\xd8\xff": "image/jpeg",  # JPEG
        b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a": "image/png",  # PNG
        b"\x47\x49\x46\x38\x37\x61": "image/gif",  # GIF87a
        b"\x47\x49\x46\x38\x39\x61": "image/gif",  # GIF89a
        b"\x42\x4d": "image/bmp",  # BMP
        b"\x52\x49\x46\x46": "image/webp",  # WEBP (需要进一步检查)
        # 视频格式
        b"\x00\x00\x00\x18\x66\x74\x79\x70": "video/mp4",  # MP4
        b"\x00\x00\x00\x20\x66\x74\x79\x70": "video/mp4",  # MP4
        b"\x1a\x45\xdf\xa3": "video/x-matroska",  # MKV
        b"\x46\x4c\x56\x01": "video/x-flv",  # FLV
    }

    # 危险文件扩展名黑名单
    DANGEROUS_EXTENSIONS = {
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
        ".ps1xml",
        ".ps2",
        ".ps2xml",
        ".psc1",
        ".psc2",
        ".msh",
        ".msh1",
        ".msh2",
        ".mshxml",
        ".msh1xml",
        ".msh2xml",
        ".scf",
        ".lnk",
        ".inf",
        ".reg",
        ".doc",
        ".xls",
        ".ppt",
        ".docx",
        ".xlsx",
        ".pptx",
        ".pdf",
        ".zip",
        ".rar",
        ".7z",
        ".tar",
        ".gz",
        ".bz2",
        ".xz",
        ".dmg",
        ".iso",
        ".img",
    }

    # 恶意内容模式
    MALICIOUS_PATTERNS = [
        rb"<script[^>]*>",  # Script标签
        rb"javascript:",  # JavaScript协议
        rb"vbscript:",  # VBScript协议
        rb"data:",  # Data URL
        rb"<?php",  # PHP代码
        rb"<%",  # ASP代码
        rb"\x00",  # 空字节
    ]

    def __init__(self, max_file_size: int = 52428800):  # 50MB
        """
        初始化文件验证器

        Args:
            max_file_size: 最大文件大小（字节）
        """
        self.max_file_size = max_file_size
        self.magic_detector = magic.Magic(mime=True)

    def validate_file(
        self, file_path: Union[str, Path], filename: Optional[str] = None
    ) -> FileValidationResult:
        """
        验证文件安全性

        Args:
            file_path: 文件路径
            filename: 原始文件名（可选）

        Returns:
            FileValidationResult: 验证结果
        """
        file_path = Path(file_path)
        if not file_path.exists():
            return FileValidationResult(
                is_valid=False,
                file_type=FileType.UNKNOWN,
                detected_mime="",
                actual_extension="",
                threat_level=SecurityThreatLevel.HIGH,
                security_issues=["文件不存在"],
                warnings=[],
                file_hash="",
                file_size=0,
                metadata={},
            )

        original_filename = filename or file_path.name
        security_issues = []
        warnings = []

        # 1. 基础文件信息
        file_size = file_path.stat().st_size
        file_hash = self._calculate_file_hash(file_path)

        # 2. 文件大小检查
        if file_size > self.max_file_size:
            security_issues.append(f"文件大小超限: {file_size} > {self.max_file_size}")

        if file_size == 0:
            security_issues.append("空文件")

        # 3. 文件名安全检查
        filename_issues = self._validate_filename(original_filename)
        security_issues.extend(filename_issues)

        # 4. 扩展名验证
        ext_validation = self._validate_extension(original_filename)
        if not ext_validation[0]:
            security_issues.append(f"不允许的文件扩展名: {ext_validation[1]}")
        file_type = ext_validation[2]

        # 5. MIME类型检测与验证
        detected_mime = self._detect_mime_type(file_path)
        mime_validation = self._validate_mime_type(detected_mime)
        if not mime_validation:
            security_issues.append(f"不允许的MIME类型: {detected_mime}")

        # 6. 文件头魔数验证
        magic_validation = self._validate_file_signature(file_path)
        if not magic_validation[0]:
            security_issues.append(f"文件头验证失败: {magic_validation[1]}")

        # 7. 扩展名与实际类型一致性检查
        consistency_check = self._check_type_consistency(
            original_filename, detected_mime
        )
        if not consistency_check[0]:
            warnings.append(f"扩展名与实际类型不匹配: {consistency_check[1]}")

        # 8. 恶意内容扫描
        malicious_content = self._scan_malicious_content(file_path)
        if malicious_content:
            security_issues.extend(malicious_content)

        # 9. 计算威胁等级
        threat_level = self._calculate_threat_level(security_issues, warnings)

        # 10. 提取文件元数据
        metadata = self._extract_metadata(file_path, detected_mime)

        return FileValidationResult(
            is_valid=len(security_issues) == 0,
            file_type=file_type,
            detected_mime=detected_mime,
            actual_extension=Path(original_filename).suffix.lower(),
            threat_level=threat_level,
            security_issues=security_issues,
            warnings=warnings,
            file_hash=file_hash,
            file_size=file_size,
            metadata=metadata,
        )

    def sanitize_filename(self, filename: str) -> str:
        """
        安全化文件名

        Args:
            filename: 原始文件名

        Returns:
            str: 安全化后的文件名
        """
        # 移除危险字符
        safe_name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", filename)

        # 移除控制字符和特殊字符
        safe_name = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", safe_name)

        # 限制长度
        if len(safe_name) > 255:
            name_part = Path(safe_name).stem[:200]
            ext_part = Path(safe_name).suffix
            safe_name = f"{name_part}{ext_part}"

        # 避免系统保留名称
        reserved_names = {
            "con",
            "prn",
            "aux",
            "nul",
            "com1",
            "com2",
            "com3",
            "com4",
            "com5",
            "com6",
            "com7",
            "com8",
            "com9",
            "lpt1",
            "lpt2",
            "lpt3",
            "lpt4",
            "lpt5",
            "lpt6",
            "lpt7",
            "lpt8",
            "lpt9",
        }

        name_without_ext = Path(safe_name).stem.lower()
        if name_without_ext in reserved_names:
            safe_name = f"file_{safe_name}"

        # 确保不以点开头或结尾
        safe_name = safe_name.strip(".")

        return safe_name or "untitled"

    def _validate_filename(self, filename: str) -> List[str]:
        """验证文件名安全性"""
        issues = []

        # 检查危险字符
        dangerous_chars = '<>:"/\\|?*\x00'
        for char in dangerous_chars:
            if char in filename:
                issues.append(f"文件名包含危险字符: {repr(char)}")

        # 检查控制字符
        if any(ord(c) < 32 for c in filename):
            issues.append("文件名包含控制字符")

        # 检查长度
        if len(filename) > 255:
            issues.append(f"文件名过长: {len(filename)} > 255")

        # 检查路径遍历
        if ".." in filename or filename.startswith("/") or filename.startswith("\\"):
            issues.append("文件名包含路径遍历字符")

        return issues

    def _validate_extension(self, filename: str) -> Tuple[bool, str, FileType]:
        """验证文件扩展名"""
        ext = Path(filename).suffix.lower()

        # 检查是否在危险扩展名列表中
        if ext in self.DANGEROUS_EXTENSIONS:
            return False, ext, FileType.UNKNOWN

        # 检查是否在白名单中
        for file_type, allowed_exts in self.ALLOWED_EXTENSIONS.items():
            if ext in allowed_exts:
                return True, ext, file_type

        return False, ext, FileType.UNKNOWN

    def _detect_mime_type(self, file_path: Path) -> str:
        """检测文件MIME类型"""
        try:
            # 使用python-magic获取更准确的MIME类型
            return self.magic_detector.from_file(str(file_path))
        except Exception as e:
            logger.warning(f"MIME类型检测失败: {e}")
            # 回退到标准库
            mime_type, _ = mimetypes.guess_type(str(file_path))
            return mime_type or "application/octet-stream"

    def _validate_mime_type(self, mime_type: str) -> bool:
        """验证MIME类型是否在白名单中"""
        return mime_type in self.ALLOWED_MIMES

    def _validate_file_signature(self, file_path: Path) -> Tuple[bool, str]:
        """验证文件头签名（魔数）"""
        try:
            with open(file_path, "rb") as f:
                header = f.read(32)  # 读取前32字节

            # 检查已知的文件签名
            for signature, expected_mime in self.MAGIC_SIGNATURES.items():
                if header.startswith(signature):
                    return True, expected_mime

            # 特殊处理WEBP
            if header.startswith(b"\x52\x49\x46\x46") and b"WEBP" in header[:12]:
                return True, "image/webp"

            # 未识别的文件头
            return False, f"未识别的文件头: {header[:8].hex()}"

        except Exception as e:
            return False, f"文件头读取失败: {e}"

    def _check_type_consistency(
        self, filename: str, detected_mime: str
    ) -> Tuple[bool, str]:
        """检查扩展名与实际类型的一致性"""
        ext = Path(filename).suffix.lower()

        # 扩展名到MIME类型的映射
        ext_to_mime = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
            ".avi": "video/x-msvideo",
            ".mkv": "video/x-matroska",
            ".wmv": "video/x-ms-wmv",
            ".flv": "video/x-flv",
            ".webm": "video/webm",
            ".md": "text/markdown",
            ".markdown": "text/markdown",
            ".txt": "text/plain",
        }

        expected_mime = ext_to_mime.get(ext)
        if expected_mime and detected_mime != expected_mime:
            return False, f"扩展名 {ext} 期望 {expected_mime}，但检测到 {detected_mime}"

        return True, ""

    def _scan_malicious_content(self, file_path: Path) -> List[str]:
        """扫描恶意内容"""
        issues = []

        try:
            # 读取文件前几KB进行快速扫描
            with open(file_path, "rb") as f:
                content = f.read(8192)  # 读取前8KB

            # 检查恶意模式
            for pattern in self.MALICIOUS_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    issues.append(
                        f"检测到潜在恶意内容: {pattern.decode('utf-8', errors='ignore')}"
                    )

            # 检查可疑的文件结构
            if b"<?xml" in content and b"<!ENTITY" in content:
                issues.append("检测到XML外部实体引用（XXE风险）")

            # 检查PHP/ASP代码
            if any(marker in content for marker in [b"<?php", b"<%@", b"<%="]):
                issues.append("检测到服务器端脚本代码")

        except Exception as e:
            logger.warning(f"恶意内容扫描失败: {e}")

        return issues

    def _calculate_threat_level(
        self, security_issues: List[str], warnings: List[str]
    ) -> SecurityThreatLevel:
        """计算威胁等级"""
        if not security_issues and not warnings:
            return SecurityThreatLevel.SAFE

        # 检查高威胁关键词
        high_threat_keywords = ["恶意", "危险", "script", "php", "xml", "外部实体"]
        for issue in security_issues:
            if any(keyword in issue.lower() for keyword in high_threat_keywords):
                return SecurityThreatLevel.CRITICAL

        # 检查中等威胁
        medium_threat_keywords = ["类型不匹配", "文件头", "扩展名"]
        if len(security_issues) > 2:
            return SecurityThreatLevel.HIGH
        elif any(
            keyword in " ".join(security_issues).lower()
            for keyword in medium_threat_keywords
        ):
            return SecurityThreatLevel.MEDIUM
        elif security_issues:
            return SecurityThreatLevel.LOW

        return SecurityThreatLevel.SAFE

    def _extract_metadata(self, file_path: Path, mime_type: str) -> Dict[str, Any]:
        """提取文件元数据"""
        metadata = {
            "created_time": file_path.stat().st_ctime,
            "modified_time": file_path.stat().st_mtime,
            "mime_type": mime_type,
        }

        # 图片元数据提取
        if mime_type.startswith("image/"):
            try:
                from PIL import Image

                with Image.open(file_path) as img:
                    metadata.update(
                        {
                            "width": img.width,
                            "height": img.height,
                            "format": img.format,
                            "mode": img.mode,
                        }
                    )

                    # EXIF数据（需要谨慎处理）
                    if hasattr(img, "_getexif") and img._getexif():
                        # 只提取安全的EXIF信息
                        exif = img._getexif()
                        safe_exif = {}
                        for tag_id, value in exif.items():
                            if tag_id in [0x0100, 0x0101]:  # 宽度和高度
                                safe_exif[str(tag_id)] = value
                        metadata["exif"] = safe_exif

            except Exception as e:
                logger.warning(f"图片元数据提取失败: {e}")

        return metadata

    def _calculate_file_hash(self, file_path: Path) -> str:
        """计算文件SHA256哈希"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            logger.warning(f"文件哈希计算失败: {e}")
            return ""


class AntivirusScanner:
    """
    反病毒扫描器接口

    支持多种反病毒引擎集成
    """

    def __init__(self):
        self.enabled = False
        self.scanner_type = None

    def scan_file(
        self, file_path: Union[str, Path]
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        扫描文件是否包含病毒

        Args:
            file_path: 文件路径

        Returns:
            Tuple[bool, str, Dict]: (是否干净, 扫描结果, 详细信息)
        """
        if not self.enabled:
            return True, "反病毒扫描已禁用", {}

        # 这里可以集成各种反病毒引擎
        # 例如：ClamAV, Windows Defender, 第三方API等
        return self._mock_scan(file_path)

    def _mock_scan(self, file_path: Path) -> Tuple[bool, str, Dict[str, Any]]:
        """模拟扫描（用于演示）"""
        return (
            True,
            "文件清洁",
            {"scanner": "mock", "scan_time": 0.1, "definitions_version": "2024-01-01"},
        )


# 全局实例
secure_validator = SecureFileValidator()
antivirus_scanner = AntivirusScanner()
