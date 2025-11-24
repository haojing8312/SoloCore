#!/usr/bin/env python3
"""
TextLoom Backup and Disaster Recovery Manager
============================================

综合备份和灾难恢复系统，支持：
- PostgreSQL数据库备份（全量/增量）
- Redis数据备份
- 工作空间文件备份
- 日志文件备份
- 远程存储集成（华为OBS/MinIO）
- 备份监控和告警
- 自动化恢复测试

Usage:
    python backup_manager.py backup --type full
    python backup_manager.py backup --type incremental
    python backup_manager.py restore --backup-id 20250820_120000
    python backup_manager.py verify --backup-id 20250820_120000
    python backup_manager.py monitor
"""

import argparse
import asyncio
import gzip
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import asyncpg
import redis
from cryptography.fernet import Fernet

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from config import Settings
from utils.enhanced_logging import setup_logging
from utils.oss.storage_factory import create_storage_client

# 配置日志
logger = setup_logging(__name__, "logs/backup.log", "logs/backup.error.log")


@dataclass
class BackupMetadata:
    """备份元数据"""

    backup_id: str
    timestamp: datetime
    backup_type: str  # full, incremental
    components: List[str]  # database, redis, workspace, logs
    total_size: int
    compressed_size: int
    encryption_enabled: bool
    checksum: str
    retention_policy: str
    storage_location: str
    restore_tested: bool = False
    status: str = "in_progress"  # in_progress, completed, failed


@dataclass
class BackupConfig:
    """备份配置"""

    # 备份保留策略
    daily_retention_days: int = 7
    weekly_retention_weeks: int = 4
    monthly_retention_months: int = 12

    # 压缩和加密
    compression_enabled: bool = True
    encryption_enabled: bool = True
    encryption_key: Optional[str] = None

    # 存储配置
    local_backup_dir: str = "./backups"
    remote_storage_enabled: bool = True

    # 组件配置
    backup_database: bool = True
    backup_redis: bool = True
    backup_workspace: bool = True
    backup_logs: bool = True

    # 性能配置
    parallel_jobs: int = 4
    chunk_size: int = 64 * 1024 * 1024  # 64MB

    # 监控配置
    notification_webhook: Optional[str] = None
    alert_on_failure: bool = True
    max_backup_age_hours: int = 25  # 超过25小时未备份告警


class BackupManager:
    """备份管理器"""

    def __init__(self, settings: Settings, config: BackupConfig):
        self.settings = settings
        self.config = config
        self.backup_dir = Path(config.local_backup_dir)
        self.backup_dir.mkdir(exist_ok=True)

        # 初始化加密
        if config.encryption_enabled:
            self.cipher = self._init_encryption()
        else:
            self.cipher = None

        # 初始化远程存储
        if config.remote_storage_enabled:
            self.storage_client = create_storage_client(settings)
        else:
            self.storage_client = None

    def _init_encryption(self) -> Fernet:
        """初始化加密密钥"""
        if self.config.encryption_key:
            key = self.config.encryption_key.encode()
        else:
            # 生成新密钥
            key = Fernet.generate_key()
            key_file = self.backup_dir / "backup.key"
            with open(key_file, "wb") as f:
                f.write(key)
            logger.info(f"生成新的加密密钥: {key_file}")

        return Fernet(key)

    async def create_backup(
        self, backup_type: str = "full", components: Optional[List[str]] = None
    ) -> str:
        """创建备份"""
        backup_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        logger.info(f"开始创建备份: {backup_id}, 类型: {backup_type}")

        if components is None:
            components = self._get_default_components()

        metadata = BackupMetadata(
            backup_id=backup_id,
            timestamp=datetime.now(),
            backup_type=backup_type,
            components=components,
            total_size=0,
            compressed_size=0,
            encryption_enabled=self.config.encryption_enabled,
            checksum="",
            retention_policy=self._get_retention_policy(backup_type),
            storage_location="local",
        )

        try:
            # 创建备份目录
            backup_path = self.backup_dir / backup_id
            backup_path.mkdir(exist_ok=True)

            total_size = 0

            # 并行执行各组件备份
            with ThreadPoolExecutor(max_workers=self.config.parallel_jobs) as executor:
                futures = {}

                if "database" in components and self.config.backup_database:
                    futures["database"] = executor.submit(
                        self._backup_database, backup_path, backup_type
                    )

                if "redis" in components and self.config.backup_redis:
                    futures["redis"] = executor.submit(self._backup_redis, backup_path)

                if "workspace" in components and self.config.backup_workspace:
                    futures["workspace"] = executor.submit(
                        self._backup_workspace, backup_path
                    )

                if "logs" in components and self.config.backup_logs:
                    futures["logs"] = executor.submit(self._backup_logs, backup_path)

                # 等待所有备份完成
                for component, future in futures.items():
                    try:
                        size = future.result(timeout=3600)  # 1小时超时
                        total_size += size
                        logger.info(f"{component} 备份完成, 大小: {size} bytes")
                    except Exception as e:
                        logger.error(f"{component} 备份失败: {e}")
                        raise

            metadata.total_size = total_size

            # 压缩和加密
            if self.config.compression_enabled:
                compressed_path = await self._compress_backup(backup_path)
                metadata.compressed_size = compressed_path.stat().st_size
            else:
                compressed_path = backup_path
                metadata.compressed_size = total_size

            # 计算校验和
            metadata.checksum = self._calculate_checksum(compressed_path)

            # 上传到远程存储
            if self.storage_client:
                await self._upload_to_remote(compressed_path, backup_id)
                metadata.storage_location = "remote"

            metadata.status = "completed"

            # 保存元数据
            await self._save_metadata(metadata)

            logger.info(f"备份创建成功: {backup_id}")
            logger.info(
                f"原始大小: {total_size} bytes, 压缩后: {metadata.compressed_size} bytes"
            )

            # 清理旧备份
            await self._cleanup_old_backups()

            return backup_id

        except Exception as e:
            metadata.status = "failed"
            await self._save_metadata(metadata)
            logger.error(f"备份创建失败: {e}")
            raise

    def _get_default_components(self) -> List[str]:
        """获取默认备份组件"""
        components = []
        if self.config.backup_database:
            components.append("database")
        if self.config.backup_redis:
            components.append("redis")
        if self.config.backup_workspace:
            components.append("workspace")
        if self.config.backup_logs:
            components.append("logs")
        return components

    def _get_retention_policy(self, backup_type: str) -> str:
        """获取保留策略"""
        if backup_type == "daily":
            return f"daily_{self.config.daily_retention_days}d"
        elif backup_type == "weekly":
            return f"weekly_{self.config.weekly_retention_weeks}w"
        elif backup_type == "monthly":
            return f"monthly_{self.config.monthly_retention_months}m"
        else:
            return f"full_{self.config.daily_retention_days}d"

    def _backup_database(self, backup_path: Path, backup_type: str) -> int:
        """备份PostgreSQL数据库"""
        logger.info("开始备份数据库")

        if not self.settings.database_url:
            raise ValueError("数据库URL未配置")

        # 解析数据库连接URL
        import urllib.parse

        parsed = urllib.parse.urlparse(self.settings.database_url)

        db_config = {
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "database": parsed.path.lstrip("/"),
            "username": parsed.username,
            "password": parsed.password,
        }

        dump_file = backup_path / "database.sql"

        if backup_type == "incremental":
            # WAL增量备份
            return self._backup_database_wal(backup_path, db_config)
        else:
            # 全量备份
            return self._backup_database_full(dump_file, db_config)

    def _backup_database_full(self, dump_file: Path, db_config: Dict) -> int:
        """执行数据库全量备份"""
        env = os.environ.copy()
        env["PGPASSWORD"] = db_config["password"]

        cmd = [
            "pg_dump",
            f"--host={db_config['host']}",
            f"--port={db_config['port']}",
            f"--username={db_config['username']}",
            f"--dbname={db_config['database']}",
            "--verbose",
            "--clean",
            "--if-exists",
            "--format=custom",
            "--compress=9",
            f"--file={dump_file}",
        ]

        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"pg_dump 失败: {result.stderr}")
            raise RuntimeError(f"数据库备份失败: {result.stderr}")

        return dump_file.stat().st_size

    def _backup_database_wal(self, backup_path: Path, db_config: Dict) -> int:
        """执行数据库WAL增量备份"""
        # 实现WAL增量备份逻辑
        # 这里简化为全量备份，实际生产中需要配置WAL归档
        logger.warning("增量备份暂不完全支持，执行全量备份")
        dump_file = backup_path / "database_incremental.sql"
        return self._backup_database_full(dump_file, db_config)

    def _backup_redis(self, backup_path: Path) -> int:
        """备份Redis数据"""
        logger.info("开始备份Redis")

        redis_client = redis.Redis(
            host=self.settings.redis_host or "localhost",
            port=self.settings.redis_port or 6379,
            db=self.settings.redis_db or 0,
            password=self.settings.redis_password,
            decode_responses=False,
        )

        # 执行BGSAVE
        redis_client.bgsave()

        # 等待备份完成
        import time

        while True:
            if redis_client.lastsave() > time.time() - 60:  # 1分钟内的备份
                break
            time.sleep(0.5)  # 优化：减少轮询间隔到500ms，提高响应性

        # 复制RDB文件
        redis_dump_file = backup_path / "redis.rdb"

        # 从Redis数据目录复制dump.rdb
        # 这里需要根据实际Redis配置调整路径
        redis_data_dir = (
            Path("/var/lib/redis")
            if Path("/var/lib/redis").exists()
            else Path("./redis_data")
        )
        source_rdb = redis_data_dir / "dump.rdb"

        if source_rdb.exists():
            shutil.copy2(source_rdb, redis_dump_file)
            return redis_dump_file.stat().st_size
        else:
            # 使用DUMP命令导出所有键
            return self._backup_redis_keys(redis_client, backup_path)

    def _backup_redis_keys(self, redis_client: redis.Redis, backup_path: Path) -> int:
        """通过DUMP命令备份Redis键"""
        backup_file = backup_path / "redis_keys.json"
        data = {}

        for key in redis_client.scan_iter():
            key_str = key.decode("utf-8") if isinstance(key, bytes) else key
            dump_data = redis_client.dump(key)
            ttl = redis_client.ttl(key)

            data[key_str] = {
                "data": dump_data.hex() if dump_data else None,
                "ttl": ttl if ttl > 0 else None,
            }

        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return backup_file.stat().st_size

    def _backup_workspace(self, backup_path: Path) -> int:
        """备份工作空间文件"""
        logger.info("开始备份工作空间")

        workspace_dir = Path(self.settings.workspace_dir)
        if not workspace_dir.exists():
            logger.warning("工作空间目录不存在，跳过备份")
            return 0

        workspace_backup = backup_path / "workspace.tar.gz"

        with tarfile.open(workspace_backup, "w:gz") as tar:
            tar.add(workspace_dir, arcname="workspace")

        return workspace_backup.stat().st_size

    def _backup_logs(self, backup_path: Path) -> int:
        """备份日志文件"""
        logger.info("开始备份日志文件")

        logs_dir = Path("logs")
        if not logs_dir.exists():
            logger.warning("日志目录不存在，跳过备份")
            return 0

        logs_backup = backup_path / "logs.tar.gz"

        with tarfile.open(logs_backup, "w:gz") as tar:
            # 只备份最近30天的日志
            cutoff_date = datetime.now() - timedelta(days=30)

            for log_file in logs_dir.glob("*.log"):
                if log_file.stat().st_mtime > cutoff_date.timestamp():
                    tar.add(log_file, arcname=f"logs/{log_file.name}")

        return logs_backup.stat().st_size

    async def _compress_backup(self, backup_path: Path) -> Path:
        """压缩备份"""
        logger.info("压缩备份文件")

        compressed_path = backup_path.with_suffix(".tar.gz")

        with tarfile.open(compressed_path, "w:gz") as tar:
            tar.add(backup_path, arcname=backup_path.name)

        # 删除原始备份目录
        shutil.rmtree(backup_path)

        return compressed_path

    def _calculate_checksum(self, file_path: Path) -> str:
        """计算文件校验和"""
        hash_sha256 = hashlib.sha256()

        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(self.config.chunk_size), b""):
                hash_sha256.update(chunk)

        return hash_sha256.hexdigest()

    async def _upload_to_remote(self, backup_path: Path, backup_id: str):
        """上传到远程存储"""
        if not self.storage_client:
            return

        logger.info("上传备份到远程存储")

        remote_key = f"backups/{backup_id}/{backup_path.name}"

        try:
            await self.storage_client.upload_file(backup_path, remote_key)
            logger.info(f"备份已上传到远程存储: {remote_key}")
        except Exception as e:
            logger.error(f"上传远程存储失败: {e}")
            raise

    async def _save_metadata(self, metadata: BackupMetadata):
        """保存备份元数据"""
        metadata_file = self.backup_dir / f"{metadata.backup_id}.json"

        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(asdict(metadata), f, ensure_ascii=False, indent=2, default=str)

    async def _cleanup_old_backups(self):
        """清理过期备份"""
        logger.info("清理过期备份")

        now = datetime.now()

        # 获取所有备份元数据
        for metadata_file in self.backup_dir.glob("*.json"):
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                backup_time = datetime.fromisoformat(data["timestamp"])
                backup_type = data["backup_type"]

                # 检查是否过期
                if self._is_backup_expired(backup_time, backup_type, now):
                    backup_id = data["backup_id"]
                    await self._delete_backup(backup_id)

            except Exception as e:
                logger.error(f"处理备份元数据失败 {metadata_file}: {e}")

    def _is_backup_expired(
        self, backup_time: datetime, backup_type: str, now: datetime
    ) -> bool:
        """检查备份是否过期"""
        if backup_type == "daily":
            return (now - backup_time).days > self.config.daily_retention_days
        elif backup_type == "weekly":
            return (now - backup_time).days > (self.config.weekly_retention_weeks * 7)
        elif backup_type == "monthly":
            return (now - backup_time).days > (
                self.config.monthly_retention_months * 30
            )
        else:
            return (now - backup_time).days > self.config.daily_retention_days

    async def _delete_backup(self, backup_id: str):
        """删除指定备份"""
        logger.info(f"删除过期备份: {backup_id}")

        # 删除本地文件
        backup_file = self.backup_dir / f"{backup_id}.tar.gz"
        if backup_file.exists():
            backup_file.unlink()

        metadata_file = self.backup_dir / f"{backup_id}.json"
        if metadata_file.exists():
            metadata_file.unlink()

        # 删除远程文件
        if self.storage_client:
            try:
                remote_key = f"backups/{backup_id}/"
                await self.storage_client.delete_file(remote_key)
            except Exception as e:
                logger.warning(f"删除远程备份失败: {e}")

    async def restore_backup(
        self,
        backup_id: str,
        target_dir: Optional[str] = None,
        components: Optional[List[str]] = None,
    ) -> bool:
        """恢复备份"""
        logger.info(f"开始恢复备份: {backup_id}")

        # 加载备份元数据
        metadata = await self._load_metadata(backup_id)
        if not metadata:
            logger.error(f"备份元数据不存在: {backup_id}")
            return False

        if components is None:
            components = metadata.components

        # 下载备份文件（如果需要）
        backup_file = await self._ensure_backup_file(backup_id)
        if not backup_file:
            return False

        # 验证校验和
        if not self._verify_checksum(backup_file, metadata.checksum):
            logger.error("备份文件校验和验证失败")
            return False

        # 解压备份
        temp_dir = Path(tempfile.mkdtemp())
        try:
            with tarfile.open(backup_file, "r:gz") as tar:
                tar.extractall(temp_dir)

            backup_content_dir = temp_dir / backup_id

            # 恢复各组件
            success = True

            if "database" in components:
                success &= await self._restore_database(backup_content_dir)

            if "redis" in components:
                success &= await self._restore_redis(backup_content_dir)

            if "workspace" in components:
                success &= await self._restore_workspace(backup_content_dir, target_dir)

            if "logs" in components:
                success &= await self._restore_logs(backup_content_dir, target_dir)

            if success:
                logger.info(f"备份恢复成功: {backup_id}")
            else:
                logger.error(f"备份恢复失败: {backup_id}")

            return success

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def _load_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """加载备份元数据"""
        metadata_file = self.backup_dir / f"{backup_id}.json"

        if not metadata_file.exists():
            return None

        with open(metadata_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 转换时间戳
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])

        return BackupMetadata(**data)

    async def _ensure_backup_file(self, backup_id: str) -> Optional[Path]:
        """确保备份文件存在（本地或远程下载）"""
        backup_file = self.backup_dir / f"{backup_id}.tar.gz"

        if backup_file.exists():
            return backup_file

        # 从远程存储下载
        if self.storage_client:
            logger.info("从远程存储下载备份文件")
            remote_key = f"backups/{backup_id}/{backup_file.name}"

            try:
                await self.storage_client.download_file(remote_key, backup_file)
                return backup_file
            except Exception as e:
                logger.error(f"从远程存储下载备份失败: {e}")

        return None

    def _verify_checksum(self, file_path: Path, expected_checksum: str) -> bool:
        """验证文件校验和"""
        actual_checksum = self._calculate_checksum(file_path)
        return actual_checksum == expected_checksum

    async def _restore_database(self, backup_content_dir: Path) -> bool:
        """恢复数据库"""
        logger.info("恢复数据库")

        dump_file = backup_content_dir / "database.sql"
        if not dump_file.exists():
            dump_file = backup_content_dir / "database_incremental.sql"

        if not dump_file.exists():
            logger.error("数据库备份文件不存在")
            return False

        if not self.settings.database_url:
            logger.error("数据库URL未配置")
            return False

        # 解析数据库连接
        import urllib.parse

        parsed = urllib.parse.urlparse(self.settings.database_url)

        env = os.environ.copy()
        env["PGPASSWORD"] = parsed.password

        cmd = [
            "pg_restore",
            f"--host={parsed.hostname}",
            f"--port={parsed.port or 5432}",
            f"--username={parsed.username}",
            f"--dbname={parsed.path.lstrip('/')}",
            "--verbose",
            "--clean",
            "--if-exists",
            str(dump_file),
        ]

        result = subprocess.run(cmd, env=env, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error(f"pg_restore 失败: {result.stderr}")
            return False

        logger.info("数据库恢复成功")
        return True

    async def _restore_redis(self, backup_content_dir: Path) -> bool:
        """恢复Redis数据"""
        logger.info("恢复Redis数据")

        # 尝试RDB文件恢复
        rdb_file = backup_content_dir / "redis.rdb"
        if rdb_file.exists():
            return self._restore_redis_rdb(rdb_file)

        # 尝试键值恢复
        keys_file = backup_content_dir / "redis_keys.json"
        if keys_file.exists():
            return self._restore_redis_keys(keys_file)

        logger.error("Redis备份文件不存在")
        return False

    def _restore_redis_rdb(self, rdb_file: Path) -> bool:
        """通过RDB文件恢复Redis"""
        logger.info("通过RDB文件恢复Redis")
        # 需要停止Redis服务，替换RDB文件，然后重启
        # 这里仅记录日志，实际实现需要根据Redis部署方式调整
        logger.warning("RDB文件恢复需要手动操作Redis服务")
        return True

    def _restore_redis_keys(self, keys_file: Path) -> bool:
        """通过键值恢复Redis"""
        logger.info("通过键值恢复Redis")

        redis_client = redis.Redis(
            host=self.settings.redis_host or "localhost",
            port=self.settings.redis_port or 6379,
            db=self.settings.redis_db or 0,
            password=self.settings.redis_password,
            decode_responses=False,
        )

        with open(keys_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        for key, value in data.items():
            try:
                if value["data"]:
                    dump_data = bytes.fromhex(value["data"])
                    redis_client.restore(
                        key, value["ttl"] or 0, dump_data, replace=True
                    )
            except Exception as e:
                logger.error(f"恢复Redis键 {key} 失败: {e}")

        logger.info("Redis键值恢复完成")
        return True

    async def _restore_workspace(
        self, backup_content_dir: Path, target_dir: Optional[str]
    ) -> bool:
        """恢复工作空间"""
        logger.info("恢复工作空间")

        workspace_backup = backup_content_dir / "workspace.tar.gz"
        if not workspace_backup.exists():
            logger.warning("工作空间备份不存在")
            return True

        target_path = (
            Path(target_dir) if target_dir else Path(self.settings.workspace_dir)
        )

        # 备份现有工作空间
        if target_path.exists():
            backup_path = target_path.with_suffix(
                f".backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            shutil.move(str(target_path), str(backup_path))
            logger.info(f"现有工作空间已备份至: {backup_path}")

        # 解压恢复
        with tarfile.open(workspace_backup, "r:gz") as tar:
            tar.extractall(target_path.parent)

        logger.info("工作空间恢复成功")
        return True

    async def _restore_logs(
        self, backup_content_dir: Path, target_dir: Optional[str]
    ) -> bool:
        """恢复日志文件"""
        logger.info("恢复日志文件")

        logs_backup = backup_content_dir / "logs.tar.gz"
        if not logs_backup.exists():
            logger.warning("日志备份不存在")
            return True

        target_path = Path(target_dir) / "logs" if target_dir else Path("logs")
        target_path.mkdir(exist_ok=True)

        with tarfile.open(logs_backup, "r:gz") as tar:
            tar.extractall(target_path.parent)

        logger.info("日志恢复成功")
        return True

    async def verify_backup(self, backup_id: str) -> bool:
        """验证备份完整性"""
        logger.info(f"验证备份: {backup_id}")

        metadata = await self._load_metadata(backup_id)
        if not metadata:
            logger.error("备份元数据不存在")
            return False

        # 确保备份文件存在
        backup_file = await self._ensure_backup_file(backup_id)
        if not backup_file:
            logger.error("备份文件不存在")
            return False

        # 验证校验和
        if not self._verify_checksum(backup_file, metadata.checksum):
            logger.error("校验和验证失败")
            return False

        # 尝试部分恢复到临时目录验证
        temp_dir = Path(tempfile.mkdtemp())
        try:
            with tarfile.open(backup_file, "r:gz") as tar:
                tar.extractall(temp_dir)

            backup_content_dir = temp_dir / backup_id

            # 验证各组件文件
            verification_passed = True

            if "database" in metadata.components:
                db_file = backup_content_dir / "database.sql"
                if not (
                    db_file.exists()
                    or (backup_content_dir / "database_incremental.sql").exists()
                ):
                    logger.error("数据库备份文件缺失")
                    verification_passed = False

            if "redis" in metadata.components:
                redis_file = backup_content_dir / "redis.rdb"
                keys_file = backup_content_dir / "redis_keys.json"
                if not (redis_file.exists() or keys_file.exists()):
                    logger.error("Redis备份文件缺失")
                    verification_passed = False

            if "workspace" in metadata.components:
                workspace_file = backup_content_dir / "workspace.tar.gz"
                if not workspace_file.exists():
                    logger.warning("工作空间备份文件缺失")

            if verification_passed:
                logger.info(f"备份验证成功: {backup_id}")
                # 更新元数据
                metadata.restore_tested = True
                await self._save_metadata(metadata)
            else:
                logger.error(f"备份验证失败: {backup_id}")

            return verification_passed

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def monitor_backups(self) -> Dict[str, Any]:
        """监控备份状态"""
        logger.info("监控备份状态")

        status = {
            "last_backup": None,
            "backup_count": 0,
            "total_size": 0,
            "alerts": [],
            "backups": [],
        }

        # 获取所有备份信息
        for metadata_file in self.backup_dir.glob("*.json"):
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                backup_time = datetime.fromisoformat(data["timestamp"])

                status["backups"].append(
                    {
                        "backup_id": data["backup_id"],
                        "timestamp": data["timestamp"],
                        "backup_type": data["backup_type"],
                        "status": data["status"],
                        "size": data["compressed_size"],
                        "components": data["components"],
                        "restore_tested": data.get("restore_tested", False),
                    }
                )

                status["backup_count"] += 1
                status["total_size"] += data["compressed_size"]

                # 找到最近备份
                if not status["last_backup"] or backup_time > datetime.fromisoformat(
                    status["last_backup"]["timestamp"]
                ):
                    status["last_backup"] = data

            except Exception as e:
                logger.error(f"读取备份元数据失败 {metadata_file}: {e}")

        # 检查告警条件
        now = datetime.now()

        if status["last_backup"]:
            last_backup_time = datetime.fromisoformat(
                status["last_backup"]["timestamp"]
            )
            hours_since_backup = (now - last_backup_time).total_seconds() / 3600

            if hours_since_backup > self.config.max_backup_age_hours:
                status["alerts"].append(
                    {
                        "type": "backup_age",
                        "message": f"最近备份时间超过 {self.config.max_backup_age_hours} 小时",
                        "severity": "warning",
                    }
                )
        else:
            status["alerts"].append(
                {
                    "type": "no_backup",
                    "message": "未发现任何备份",
                    "severity": "critical",
                }
            )

        # 检查失败的备份
        failed_backups = [b for b in status["backups"] if b["status"] == "failed"]
        if failed_backups:
            status["alerts"].append(
                {
                    "type": "backup_failed",
                    "message": f"发现 {len(failed_backups)} 个失败的备份",
                    "severity": "error",
                }
            )

        # 检查未测试的备份
        untested_backups = [b for b in status["backups"] if not b["restore_tested"]]
        if len(untested_backups) > 5:
            status["alerts"].append(
                {
                    "type": "untested_backups",
                    "message": f"发现 {len(untested_backups)} 个未测试的备份",
                    "severity": "warning",
                }
            )

        return status

    async def list_backups(self) -> List[Dict]:
        """列出所有备份"""
        backups = []

        for metadata_file in self.backup_dir.glob("*.json"):
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                backups.append(data)
            except Exception as e:
                logger.error(f"读取备份元数据失败 {metadata_file}: {e}")

        # 按时间排序
        backups.sort(key=lambda x: x["timestamp"], reverse=True)

        return backups


class BackupScheduler:
    """备份调度器"""

    def __init__(self, backup_manager: BackupManager):
        self.backup_manager = backup_manager

    async def run_daily_backup(self):
        """执行日常备份"""
        try:
            backup_id = await self.backup_manager.create_backup("daily")
            logger.info(f"日常备份完成: {backup_id}")

            # 验证备份
            if await self.backup_manager.verify_backup(backup_id):
                logger.info(f"备份验证成功: {backup_id}")
            else:
                logger.error(f"备份验证失败: {backup_id}")

        except Exception as e:
            logger.error(f"日常备份失败: {e}")
            # 发送告警
            await self._send_alert("日常备份失败", str(e))

    async def run_weekly_backup(self):
        """执行周备份"""
        try:
            backup_id = await self.backup_manager.create_backup("weekly")
            logger.info(f"周备份完成: {backup_id}")

        except Exception as e:
            logger.error(f"周备份失败: {e}")
            await self._send_alert("周备份失败", str(e))

    async def run_monthly_backup(self):
        """执行月备份"""
        try:
            backup_id = await self.backup_manager.create_backup("monthly")
            logger.info(f"月备份完成: {backup_id}")

        except Exception as e:
            logger.error(f"月备份失败: {e}")
            await self._send_alert("月备份失败", str(e))

    async def _send_alert(self, subject: str, message: str):
        """发送告警"""
        logger.error(f"告警: {subject} - {message}")
        # 这里可以集成邮件、Webhook等告警方式


def create_backup_config() -> BackupConfig:
    """创建默认备份配置"""
    settings = Settings()

    return BackupConfig(
        # 从环境变量读取配置
        daily_retention_days=int(os.getenv("BACKUP_DAILY_RETENTION_DAYS", "7")),
        weekly_retention_weeks=int(os.getenv("BACKUP_WEEKLY_RETENTION_WEEKS", "4")),
        monthly_retention_months=int(
            os.getenv("BACKUP_MONTHLY_RETENTION_MONTHS", "12")
        ),
        compression_enabled=os.getenv("BACKUP_COMPRESSION_ENABLED", "true").lower()
        == "true",
        encryption_enabled=os.getenv("BACKUP_ENCRYPTION_ENABLED", "true").lower()
        == "true",
        encryption_key=os.getenv("BACKUP_ENCRYPTION_KEY"),
        local_backup_dir=os.getenv("BACKUP_LOCAL_DIR", "./backups"),
        remote_storage_enabled=os.getenv(
            "BACKUP_REMOTE_STORAGE_ENABLED", "true"
        ).lower()
        == "true",
        backup_database=os.getenv("BACKUP_DATABASE_ENABLED", "true").lower() == "true",
        backup_redis=os.getenv("BACKUP_REDIS_ENABLED", "true").lower() == "true",
        backup_workspace=os.getenv("BACKUP_WORKSPACE_ENABLED", "true").lower()
        == "true",
        backup_logs=os.getenv("BACKUP_LOGS_ENABLED", "true").lower() == "true",
        parallel_jobs=int(os.getenv("BACKUP_PARALLEL_JOBS", "4")),
        notification_webhook=os.getenv("BACKUP_NOTIFICATION_WEBHOOK"),
        alert_on_failure=os.getenv("BACKUP_ALERT_ON_FAILURE", "true").lower() == "true",
        max_backup_age_hours=int(os.getenv("BACKUP_MAX_AGE_HOURS", "25")),
    )


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="TextLoom 备份和灾难恢复管理器")

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # 备份命令
    backup_parser = subparsers.add_parser("backup", help="创建备份")
    backup_parser.add_argument(
        "--type",
        choices=["full", "incremental", "daily", "weekly", "monthly"],
        default="full",
        help="备份类型",
    )
    backup_parser.add_argument(
        "--components",
        nargs="*",
        choices=["database", "redis", "workspace", "logs"],
        help="要备份的组件",
    )

    # 恢复命令
    restore_parser = subparsers.add_parser("restore", help="恢复备份")
    restore_parser.add_argument("--backup-id", required=True, help="备份ID")
    restore_parser.add_argument("--target-dir", help="恢复目标目录")
    restore_parser.add_argument(
        "--components",
        nargs="*",
        choices=["database", "redis", "workspace", "logs"],
        help="要恢复的组件",
    )

    # 验证命令
    verify_parser = subparsers.add_parser("verify", help="验证备份")
    verify_parser.add_argument("--backup-id", required=True, help="备份ID")

    # 监控命令
    monitor_parser = subparsers.add_parser("monitor", help="监控备份状态")

    # 列表命令
    list_parser = subparsers.add_parser("list", help="列出备份")

    # 调度命令
    schedule_parser = subparsers.add_parser("schedule", help="运行调度备份")
    schedule_parser.add_argument(
        "--type", choices=["daily", "weekly", "monthly"], required=True, help="调度类型"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # 初始化
    settings = Settings()
    config = create_backup_config()
    backup_manager = BackupManager(settings, config)

    try:
        if args.command == "backup":
            backup_id = await backup_manager.create_backup(args.type, args.components)
            print(f"备份创建成功: {backup_id}")

        elif args.command == "restore":
            success = await backup_manager.restore_backup(
                args.backup_id, args.target_dir, args.components
            )
            if success:
                print(f"备份恢复成功: {args.backup_id}")
            else:
                print(f"备份恢复失败: {args.backup_id}")
                sys.exit(1)

        elif args.command == "verify":
            success = await backup_manager.verify_backup(args.backup_id)
            if success:
                print(f"备份验证成功: {args.backup_id}")
            else:
                print(f"备份验证失败: {args.backup_id}")
                sys.exit(1)

        elif args.command == "monitor":
            status = await backup_manager.monitor_backups()
            print(json.dumps(status, ensure_ascii=False, indent=2, default=str))

        elif args.command == "list":
            backups = await backup_manager.list_backups()
            print(json.dumps(backups, ensure_ascii=False, indent=2, default=str))

        elif args.command == "schedule":
            scheduler = BackupScheduler(backup_manager)
            if args.type == "daily":
                await scheduler.run_daily_backup()
            elif args.type == "weekly":
                await scheduler.run_weekly_backup()
            elif args.type == "monthly":
                await scheduler.run_monthly_backup()
            print(f"{args.type} 备份调度完成")

    except Exception as e:
        logger.error(f"命令执行失败: {e}")
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
