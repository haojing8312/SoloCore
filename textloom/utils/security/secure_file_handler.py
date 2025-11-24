"""
安全文件处理器 - 集成多层安全验证

这个模块提供了安全的文件上传和处理功能，包括：
1. 集成文件验证器
2. 临时文件安全处理
3. 文件隔离和沙箱
4. 病毒扫描集成
5. 安全的文件存储
6. 完整的审计日志

符合OWASP文件上传安全最佳实践
"""

import hashlib
import logging
import mimetypes
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from fastapi import HTTPException, UploadFile

from .file_validator import (
    FileValidationResult,
    SecureFileValidator,
    SecurityThreatLevel,
)
from .input_validator import SecureInputValidator

logger = logging.getLogger(__name__)


@dataclass
class SecureUploadConfig:
    """安全上传配置"""

    max_file_size: int = 52428800  # 50MB
    max_files_per_request: int = 50
    allowed_extensions: List[str] = None
    quarantine_directory: str = "./quarantine"
    safe_storage_directory: str = "./secure_uploads"
    enable_virus_scan: bool = False
    enable_content_scan: bool = True
    auto_cleanup_hours: int = 24


@dataclass
class SecureFileInfo:
    """安全文件信息"""

    original_filename: str
    sanitized_filename: str
    file_size: int
    mime_type: str
    file_hash: str
    validation_result: FileValidationResult
    temp_path: Optional[str] = None
    final_path: Optional[str] = None
    quarantined: bool = False
    scan_results: Dict[str, Any] = None


class SecureFileHandler:
    """
    安全文件处理器

    提供文件上传的完整安全处理流程
    """

    def __init__(self, config: Optional[SecureUploadConfig] = None):
        """
        初始化安全文件处理器

        Args:
            config: 安全上传配置
        """
        self.config = config or SecureUploadConfig()
        self.validator = SecureFileValidator(self.config.max_file_size)
        self.input_validator = SecureInputValidator()

        # 确保目录存在
        self._ensure_directories()

    def _ensure_directories(self):
        """确保必要的目录存在"""
        directories = [
            self.config.quarantine_directory,
            self.config.safe_storage_directory,
            os.path.join(self.config.safe_storage_directory, "temp"),
            os.path.join(self.config.safe_storage_directory, "validated"),
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

            # 设置目录权限（仅所有者可读写）
            try:
                os.chmod(directory, 0o700)
            except Exception as e:
                logger.warning(f"无法设置目录权限 {directory}: {e}")

    async def handle_upload(self, file: UploadFile) -> SecureFileInfo:
        """
        处理单个文件上传

        Args:
            file: FastAPI上传文件对象

        Returns:
            SecureFileInfo: 安全文件信息

        Raises:
            HTTPException: 如果文件不安全
        """
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")

        # 1. 验证文件名
        filename_result = self.input_validator.validate_filename(file.filename)
        if not filename_result.is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"不安全的文件名: {', '.join(filename_result.issues)}",
            )

        # 2. 清理文件名
        sanitized_filename = self.validator.sanitize_filename(file.filename)

        # 3. 读取文件内容
        try:
            content = await file.read()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"文件读取失败: {e}")

        # 4. 基础检查
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="空文件")

        if len(content) > self.config.max_file_size:
            raise HTTPException(
                status_code=413,
                detail=f"文件过大: {len(content)} > {self.config.max_file_size}",
            )

        # 5. 创建临时文件
        temp_file_info = await self._create_temp_file(content, sanitized_filename)

        try:
            # 6. 文件验证
            validation_result = self.validator.validate_file(
                temp_file_info["temp_path"], file.filename
            )

            # 7. 创建文件信息对象
            file_info = SecureFileInfo(
                original_filename=file.filename,
                sanitized_filename=sanitized_filename,
                file_size=len(content),
                mime_type=validation_result.detected_mime,
                file_hash=validation_result.file_hash,
                validation_result=validation_result,
                temp_path=temp_file_info["temp_path"],
            )

            # 8. 安全级别判断
            if validation_result.threat_level in [
                SecurityThreatLevel.HIGH,
                SecurityThreatLevel.CRITICAL,
            ]:
                # 高威胁文件：隔离
                await self._quarantine_file(file_info)
                raise HTTPException(
                    status_code=400,
                    detail=f"文件被隔离: {', '.join(validation_result.security_issues)}",
                )

            elif validation_result.threat_level == SecurityThreatLevel.MEDIUM:
                # 中等威胁：需要额外验证
                if not validation_result.is_valid:
                    await self._quarantine_file(file_info)
                    raise HTTPException(
                        status_code=400,
                        detail=f"文件验证失败: {', '.join(validation_result.security_issues)}",
                    )

            elif not validation_result.is_valid:
                # 一般错误
                await self._cleanup_temp_file(temp_file_info["temp_path"])
                raise HTTPException(
                    status_code=400,
                    detail=f"文件验证失败: {', '.join(validation_result.security_issues)}",
                )

            # 9. 病毒扫描（如果启用）
            if self.config.enable_virus_scan:
                scan_result = await self._virus_scan(file_info)
                file_info.scan_results = scan_result

                if not scan_result.get("clean", True):
                    await self._quarantine_file(file_info)
                    raise HTTPException(status_code=400, detail="文件包含恶意内容")

            # 10. 移动到安全存储区
            final_path = await self._move_to_safe_storage(file_info)
            file_info.final_path = final_path

            # 11. 记录审计日志
            await self._log_upload_success(file_info)

            return file_info

        except HTTPException:
            # 清理临时文件
            await self._cleanup_temp_file(temp_file_info["temp_path"])
            raise
        except Exception as e:
            # 清理临时文件并记录错误
            await self._cleanup_temp_file(temp_file_info["temp_path"])
            logger.error(f"文件处理异常: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="文件处理失败")

    async def handle_multiple_uploads(
        self, files: List[UploadFile]
    ) -> List[SecureFileInfo]:
        """
        处理多文件上传

        Args:
            files: 上传文件列表

        Returns:
            List[SecureFileInfo]: 安全文件信息列表
        """
        if len(files) > self.config.max_files_per_request:
            raise HTTPException(
                status_code=400,
                detail=f"文件数量超限: {len(files)} > {self.config.max_files_per_request}",
            )

        results = []
        failed_files = []

        for file in files:
            try:
                file_info = await self.handle_upload(file)
                results.append(file_info)
            except HTTPException as e:
                failed_files.append({"filename": file.filename, "error": str(e.detail)})

        # 如果有失败的文件，记录并可选择性地抛出异常
        if failed_files:
            logger.warning(f"部分文件上传失败: {failed_files}")
            # 根据配置决定是否允许部分成功
            # 这里选择记录警告但继续处理成功的文件

        return results

    async def _create_temp_file(self, content: bytes, filename: str) -> Dict[str, Any]:
        """创建临时文件"""
        # 使用安全的临时文件创建
        temp_dir = os.path.join(self.config.safe_storage_directory, "temp")

        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = hashlib.md5(content[:1024]).hexdigest()[:8]  # 使用内容头部生成ID
        safe_filename = f"{timestamp}_{unique_id}_{filename}"

        temp_path = os.path.join(temp_dir, safe_filename)

        try:
            with open(temp_path, "wb") as f:
                f.write(content)

            # 设置文件权限（仅所有者可读）
            os.chmod(temp_path, 0o600)

            return {
                "temp_path": temp_path,
                "unique_id": unique_id,
                "timestamp": timestamp,
            }

        except Exception as e:
            logger.error(f"创建临时文件失败: {e}")
            raise

    async def _quarantine_file(self, file_info: SecureFileInfo):
        """隔离危险文件"""
        if not file_info.temp_path or not os.path.exists(file_info.temp_path):
            return

        # 创建隔离文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        quarantine_filename = (
            f"{timestamp}_{file_info.file_hash[:8]}_{file_info.sanitized_filename}"
        )
        quarantine_path = os.path.join(
            self.config.quarantine_directory, quarantine_filename
        )

        try:
            # 移动文件到隔离区
            shutil.move(file_info.temp_path, quarantine_path)
            file_info.quarantined = True

            # 记录隔离日志
            logger.warning(
                f"文件已隔离: {file_info.original_filename} -> {quarantine_path}"
            )
            logger.warning(f"安全问题: {file_info.validation_result.security_issues}")

            # 创建隔离信息文件
            info_path = quarantine_path + ".info"
            with open(info_path, "w", encoding="utf-8") as f:
                import json

                quarantine_info = {
                    "original_filename": file_info.original_filename,
                    "quarantine_time": datetime.now().isoformat(),
                    "file_hash": file_info.file_hash,
                    "file_size": file_info.file_size,
                    "mime_type": file_info.mime_type,
                    "threat_level": file_info.validation_result.threat_level.value,
                    "security_issues": file_info.validation_result.security_issues,
                    "warnings": file_info.validation_result.warnings,
                }
                json.dump(quarantine_info, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"文件隔离失败: {e}")

    async def _virus_scan(self, file_info: SecureFileInfo) -> Dict[str, Any]:
        """病毒扫描"""
        # 这里集成实际的病毒扫描引擎
        # 例如：ClamAV, Windows Defender API, 第三方服务等

        # 模拟扫描结果
        return {
            "clean": True,
            "scanner": "mock_scanner",
            "scan_time": datetime.now().isoformat(),
            "definitions_version": "2024-01-01",
        }

    async def _move_to_safe_storage(self, file_info: SecureFileInfo) -> str:
        """移动文件到安全存储区"""
        if not file_info.temp_path or not os.path.exists(file_info.temp_path):
            raise ValueError("临时文件不存在")

        # 创建存储目录结构：按日期分组
        date_dir = datetime.now().strftime("%Y/%m/%d")
        storage_dir = os.path.join(
            self.config.safe_storage_directory, "validated", date_dir
        )
        Path(storage_dir).mkdir(parents=True, exist_ok=True)

        # 生成最终文件名
        final_filename = f"{file_info.file_hash[:16]}_{file_info.sanitized_filename}"
        final_path = os.path.join(storage_dir, final_filename)

        try:
            # 移动文件
            shutil.move(file_info.temp_path, final_path)

            # 设置最终文件权限
            os.chmod(final_path, 0o644)

            logger.info(
                f"文件已安全存储: {file_info.original_filename} -> {final_path}"
            )
            return final_path

        except Exception as e:
            logger.error(f"文件移动失败: {e}")
            raise

    async def _cleanup_temp_file(self, temp_path: str):
        """清理临时文件"""
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            logger.warning(f"临时文件清理失败: {temp_path}, {e}")

    async def _log_upload_success(self, file_info: SecureFileInfo):
        """记录上传成功日志"""
        logger.info(f"文件上传成功: {file_info.original_filename}")
        logger.info(
            f"文件信息: 大小={file_info.file_size}, MIME={file_info.mime_type}, 哈希={file_info.file_hash[:16]}"
        )

        if file_info.validation_result.warnings:
            logger.warning(f"文件警告: {file_info.validation_result.warnings}")

    def cleanup_old_files(self, hours: int = None):
        """清理旧的临时文件和隔离文件"""
        cleanup_hours = hours or self.config.auto_cleanup_hours
        cutoff_time = datetime.now().timestamp() - (cleanup_hours * 3600)

        directories_to_clean = [
            os.path.join(self.config.safe_storage_directory, "temp"),
            self.config.quarantine_directory,
        ]

        for directory in directories_to_clean:
            if not os.path.exists(directory):
                continue

            try:
                for filename in os.listdir(directory):
                    file_path = os.path.join(directory, filename)
                    if os.path.isfile(file_path):
                        file_mtime = os.path.getmtime(file_path)
                        if file_mtime < cutoff_time:
                            os.remove(file_path)
                            logger.info(f"清理旧文件: {file_path}")

            except Exception as e:
                logger.error(f"清理目录失败 {directory}: {e}")


class SecureUrlValidator:
    """
    安全URL验证器

    用于验证用户提供的URL安全性
    """

    def __init__(self):
        self.input_validator = SecureInputValidator()

    def validate_media_urls(self, urls: List[str]) -> Tuple[List[str], List[str]]:
        """
        验证媒体URL列表

        Args:
            urls: URL列表

        Returns:
            Tuple[List[str], List[str]]: (有效URL列表, 错误信息列表)
        """
        valid_urls = []
        errors = []

        for url in urls:
            try:
                # URL验证
                result = self.input_validator.validate_url(url, allow_private_ips=False)

                if result.is_valid:
                    valid_urls.append(result.cleaned_value)
                else:
                    errors.append(f"URL {url}: {', '.join(result.issues)}")

                # 记录警告
                if result.warnings:
                    logger.warning(f"URL警告 {url}: {', '.join(result.warnings)}")

            except Exception as e:
                errors.append(f"URL {url}: 验证异常 {e}")

        return valid_urls, errors


# 全局实例
secure_file_handler = SecureFileHandler()
secure_url_validator = SecureUrlValidator()
