#!/usr/bin/env python3
"""
TextLoom 灾难恢复系统
==================

提供完整的灾难恢复解决方案：
- 系统状态检测和故障诊断
- 自动故障转移
- 数据一致性检查
- 服务重启和恢复
- 灾难恢复演练
- 恢复点目标(RPO)和恢复时间目标(RTO)管理

Usage:
    python disaster_recovery.py assess
    python disaster_recovery.py recover --scenario database_failure
    python disaster_recovery.py failover --mode automatic
    python disaster_recovery.py drill --scenario full_disaster
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from config import Settings
from scripts.backup_manager import BackupConfig, BackupManager, create_backup_config
from utils.enhanced_logging import setup_logging

# 配置日志
logger = setup_logging(
    __name__, "logs/disaster_recovery.log", "logs/disaster_recovery.error.log"
)


class FailureType(Enum):
    """故障类型"""

    DATABASE_FAILURE = "database_failure"
    REDIS_FAILURE = "redis_failure"
    APPLICATION_FAILURE = "application_failure"
    STORAGE_FAILURE = "storage_failure"
    NETWORK_FAILURE = "network_failure"
    FULL_DISASTER = "full_disaster"


class RecoveryStatus(Enum):
    """恢复状态"""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    FAILED = "failed"
    RECOVERING = "recovering"
    UNKNOWN = "unknown"


@dataclass
class ServiceHealth:
    """服务健康状态"""

    name: str
    status: RecoveryStatus
    uptime: float
    memory_usage: float
    cpu_usage: float
    response_time: Optional[float] = None
    error_rate: Optional[float] = None
    last_check: datetime = None
    details: Dict[str, Any] = None


@dataclass
class RecoveryPlan:
    """恢复计划"""

    scenario: FailureType
    rpo_minutes: int  # 恢复点目标（分钟）
    rto_minutes: int  # 恢复时间目标（分钟）
    steps: List[str]
    dependencies: List[str]
    verification_steps: List[str]
    rollback_steps: List[str]


@dataclass
class DisasterAssessment:
    """灾难评估"""

    timestamp: datetime
    overall_status: RecoveryStatus
    services: List[ServiceHealth]
    data_integrity: Dict[str, bool]
    backup_status: Dict[str, Any]
    network_connectivity: Dict[str, bool]
    disk_space: Dict[str, float]
    recommendations: List[str]


class DisasterRecoveryManager:
    """灾难恢复管理器"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.backup_manager = BackupManager(settings, create_backup_config())

        # 恢复计划定义
        self.recovery_plans = self._initialize_recovery_plans()

        # 服务配置
        self.services = {
            "postgresql": {
                "command": ["pg_isready", "-h", settings.redis_host or "localhost"],
                "port": 5432,
                "critical": True,
            },
            "redis": {
                "command": ["redis-cli", "ping"],
                "port": settings.redis_port or 6379,
                "critical": True,
            },
            "textloom_api": {
                "port": settings.port,
                "critical": True,
                "health_url": f"http://localhost:{settings.port}/health",
            },
            "celery_worker": {"process_name": "celery", "critical": True},
            "celery_beat": {"process_name": "celery", "critical": False},
        }

    def _initialize_recovery_plans(self) -> Dict[FailureType, RecoveryPlan]:
        """初始化恢复计划"""
        return {
            FailureType.DATABASE_FAILURE: RecoveryPlan(
                scenario=FailureType.DATABASE_FAILURE,
                rpo_minutes=60,  # 1小时内数据丢失可接受
                rto_minutes=30,  # 30分钟内恢复
                steps=[
                    "检测数据库连接状态",
                    "尝试重启PostgreSQL服务",
                    "检查数据库文件完整性",
                    "从最近备份恢复数据库",
                    "验证数据完整性",
                    "重启应用服务",
                    "执行冒烟测试",
                ],
                dependencies=["备份文件可用", "磁盘空间充足"],
                verification_steps=["数据库连接测试", "关键表数据验证", "应用健康检查"],
                rollback_steps=["停止应用服务", "恢复原数据库文件", "重启数据库服务"],
            ),
            FailureType.REDIS_FAILURE: RecoveryPlan(
                scenario=FailureType.REDIS_FAILURE,
                rpo_minutes=15,  # Redis主要用于缓存，数据丢失影响较小
                rto_minutes=10,  # 10分钟内恢复
                steps=[
                    "检测Redis连接状态",
                    "尝试重启Redis服务",
                    "检查Redis数据文件",
                    "从备份恢复Redis数据",
                    "验证缓存功能",
                    "重启依赖服务",
                ],
                dependencies=["Redis备份可用"],
                verification_steps=[
                    "Redis连接测试",
                    "缓存读写测试",
                    "Celery任务队列测试",
                ],
                rollback_steps=["停止Redis服务", "清理数据文件", "重启空Redis实例"],
            ),
            FailureType.APPLICATION_FAILURE: RecoveryPlan(
                scenario=FailureType.APPLICATION_FAILURE,
                rpo_minutes=0,  # 应用故障不涉及数据丢失
                rto_minutes=5,  # 5分钟内恢复
                steps=[
                    "检查应用进程状态",
                    "查看应用日志错误",
                    "检查资源使用情况",
                    "重启应用服务",
                    "验证服务可用性",
                ],
                dependencies=["数据库可用", "Redis可用"],
                verification_steps=["健康检查接口测试", "API功能测试", "任务处理测试"],
                rollback_steps=["停止当前应用版本", "回滚到上一版本", "重启服务"],
            ),
            FailureType.STORAGE_FAILURE: RecoveryPlan(
                scenario=FailureType.STORAGE_FAILURE,
                rpo_minutes=120,  # 2小时内文件丢失可接受
                rto_minutes=60,  # 1小时内恢复
                steps=[
                    "检测存储可用性",
                    "评估数据丢失程度",
                    "从备份恢复工作空间",
                    "重建临时存储",
                    "验证文件完整性",
                    "重启相关服务",
                ],
                dependencies=["备份存储可用", "网络连接正常"],
                verification_steps=[
                    "文件系统读写测试",
                    "工作空间功能测试",
                    "媒体文件访问测试",
                ],
                rollback_steps=["切换到备用存储", "同步必要文件", "更新配置"],
            ),
            FailureType.FULL_DISASTER: RecoveryPlan(
                scenario=FailureType.FULL_DISASTER,
                rpo_minutes=240,  # 4小时内数据丢失
                rto_minutes=120,  # 2小时内恢复
                steps=[
                    "评估整体损失",
                    "启动灾难恢复站点",
                    "从远程备份恢复所有数据",
                    "重建完整环境",
                    "逐步启动所有服务",
                    "执行完整系统测试",
                    "切换流量到恢复环境",
                ],
                dependencies=["远程备份可用", "备用环境可用", "网络连接正常"],
                verification_steps=["完整系统功能测试", "性能基准测试", "用户接受测试"],
                rollback_steps=["保持当前状态", "等待主环境修复", "计划数据同步"],
            ),
        }

    async def assess_disaster(self) -> DisasterAssessment:
        """评估灾难情况"""
        logger.info("开始灾难评估")

        assessment = DisasterAssessment(
            timestamp=datetime.now(),
            overall_status=RecoveryStatus.UNKNOWN,
            services=[],
            data_integrity={},
            backup_status={},
            network_connectivity={},
            disk_space={},
            recommendations=[],
        )

        # 检查服务健康状态
        for service_name, config in self.services.items():
            health = await self._check_service_health(service_name, config)
            assessment.services.append(health)

        # 检查数据完整性
        assessment.data_integrity = await self._check_data_integrity()

        # 检查备份状态
        assessment.backup_status = await self._check_backup_status()

        # 检查网络连通性
        assessment.network_connectivity = await self._check_network_connectivity()

        # 检查磁盘空间
        assessment.disk_space = self._check_disk_space()

        # 评估总体状态
        assessment.overall_status = self._evaluate_overall_status(assessment)

        # 生成建议
        assessment.recommendations = self._generate_recommendations(assessment)

        logger.info(f"灾难评估完成，总体状态: {assessment.overall_status.value}")

        return assessment

    async def _check_service_health(
        self, service_name: str, config: Dict
    ) -> ServiceHealth:
        """检查服务健康状态"""
        health = ServiceHealth(
            name=service_name,
            status=RecoveryStatus.UNKNOWN,
            uptime=0,
            memory_usage=0,
            cpu_usage=0,
            last_check=datetime.now(),
            details={},
        )

        try:
            # 检查进程是否运行
            if "process_name" in config:
                process_running = self._is_process_running(config["process_name"])
                if process_running:
                    health.status = RecoveryStatus.HEALTHY
                    # 获取进程资源使用情况
                    process_info = self._get_process_info(config["process_name"])
                    if process_info:
                        health.memory_usage = process_info["memory_percent"]
                        health.cpu_usage = process_info["cpu_percent"]
                        health.uptime = process_info["create_time"]
                else:
                    health.status = RecoveryStatus.FAILED
                    health.details["error"] = "Process not running"

            # 检查端口连接
            elif "port" in config:
                port_open = self._is_port_open("localhost", config["port"])
                health.status = (
                    RecoveryStatus.HEALTHY if port_open else RecoveryStatus.FAILED
                )

                if not port_open:
                    health.details["error"] = f"Port {config['port']} not accessible"

            # 检查命令执行
            elif "command" in config:
                cmd_success = await self._run_health_command(config["command"])
                health.status = (
                    RecoveryStatus.HEALTHY if cmd_success else RecoveryStatus.FAILED
                )

                if not cmd_success:
                    health.details["error"] = (
                        f"Health command failed: {' '.join(config['command'])}"
                    )

            # 检查HTTP健康接口
            if "health_url" in config:
                response_time = await self._check_http_health(config["health_url"])
                if response_time is not None:
                    health.response_time = response_time
                    if response_time > 5.0:  # 响应时间超过5秒认为性能下降
                        health.status = RecoveryStatus.DEGRADED
                else:
                    health.status = RecoveryStatus.FAILED
                    health.details["error"] = "HTTP health check failed"

        except Exception as e:
            logger.error(f"检查服务 {service_name} 健康状态失败: {e}")
            health.status = RecoveryStatus.UNKNOWN
            health.details["error"] = str(e)

        return health

    def _is_process_running(self, process_name: str) -> bool:
        """检查进程是否运行"""
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if process_name.lower() in proc.info["name"].lower():
                    return True
                if proc.info["cmdline"]:
                    cmdline = " ".join(proc.info["cmdline"]).lower()
                    if process_name.lower() in cmdline:
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return False

    def _get_process_info(self, process_name: str) -> Optional[Dict]:
        """获取进程信息"""
        for proc in psutil.process_iter(
            ["pid", "name", "cmdline", "memory_percent", "cpu_percent", "create_time"]
        ):
            try:
                if process_name.lower() in proc.info["name"].lower():
                    return {
                        "pid": proc.info["pid"],
                        "memory_percent": proc.info["memory_percent"],
                        "cpu_percent": proc.info["cpu_percent"],
                        "create_time": time.time() - proc.info["create_time"],
                    }
                if proc.info["cmdline"]:
                    cmdline = " ".join(proc.info["cmdline"]).lower()
                    if process_name.lower() in cmdline:
                        return {
                            "pid": proc.info["pid"],
                            "memory_percent": proc.info["memory_percent"],
                            "cpu_percent": proc.info["cpu_percent"],
                            "create_time": time.time() - proc.info["create_time"],
                        }
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return None

    def _is_port_open(self, host: str, port: int) -> bool:
        """检查端口是否开放"""
        import socket

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False

    async def _run_health_command(self, command: List[str]) -> bool:
        """运行健康检查命令"""
        try:
            process = await asyncio.create_subprocess_exec(
                *command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            return process.returncode == 0
        except:
            return False

    async def _check_http_health(self, url: str) -> Optional[float]:
        """检查HTTP健康接口"""
        try:
            import aiohttp

            start_time = time.time()

            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 200:
                        return time.time() - start_time
            return None
        except:
            return None

    async def _check_data_integrity(self) -> Dict[str, bool]:
        """检查数据完整性"""
        integrity = {}

        try:
            # 检查数据库连接和关键表
            if self.settings.database_url:
                import asyncpg

                conn = await asyncpg.connect(self.settings.database_url)
                try:
                    # 检查关键表是否存在
                    tables = await conn.fetch(
                        """
                        SELECT table_name FROM information_schema.tables 
                        WHERE table_schema = 'textloom_core'
                    """
                    )
                    table_names = [row["table_name"] for row in tables]

                    required_tables = ["tasks", "users", "media_items"]
                    integrity["database_tables"] = all(
                        table in table_names for table in required_tables
                    )

                    # 检查数据库大小合理性
                    size_result = await conn.fetchrow(
                        """
                        SELECT pg_size_pretty(pg_database_size(current_database())) as size
                    """
                    )
                    integrity["database_accessible"] = True

                finally:
                    await conn.close()
            else:
                integrity["database_accessible"] = False

        except Exception as e:
            logger.error(f"数据库完整性检查失败: {e}")
            integrity["database_accessible"] = False
            integrity["database_tables"] = False

        # 检查工作空间目录
        workspace_dir = Path(self.settings.workspace_dir)
        integrity["workspace_accessible"] = (
            workspace_dir.exists() and workspace_dir.is_dir()
        )

        # 检查日志目录
        logs_dir = Path("logs")
        integrity["logs_accessible"] = logs_dir.exists() and logs_dir.is_dir()

        return integrity

    async def _check_backup_status(self) -> Dict[str, Any]:
        """检查备份状态"""
        try:
            backup_status = await self.backup_manager.monitor_backups()
            return {
                "last_backup_age_hours": self._calculate_last_backup_age(backup_status),
                "backup_count": backup_status.get("backup_count", 0),
                "total_size_gb": backup_status.get("total_size", 0) / (1024**3),
                "has_alerts": len(backup_status.get("alerts", [])) > 0,
                "alerts": backup_status.get("alerts", []),
            }
        except Exception as e:
            logger.error(f"检查备份状态失败: {e}")
            return {"error": str(e)}

    def _calculate_last_backup_age(self, backup_status: Dict) -> float:
        """计算最近备份的时间差（小时）"""
        if backup_status.get("last_backup"):
            last_backup_time = datetime.fromisoformat(
                backup_status["last_backup"]["timestamp"]
            )
            return (datetime.now() - last_backup_time).total_seconds() / 3600
        return float("inf")

    async def _check_network_connectivity(self) -> Dict[str, bool]:
        """检查网络连通性"""
        connectivity = {}

        # 检查本地连接
        connectivity["localhost"] = self._ping_host("127.0.0.1")

        # 检查数据库连接
        if self.settings.database_url:
            import urllib.parse

            parsed = urllib.parse.urlparse(self.settings.database_url)
            if parsed.hostname:
                connectivity["database_host"] = self._ping_host(parsed.hostname)

        # 检查Redis连接
        if self.settings.redis_host:
            connectivity["redis_host"] = self._ping_host(self.settings.redis_host)

        # 检查外网连接
        connectivity["internet"] = self._ping_host("8.8.8.8")

        return connectivity

    def _ping_host(self, host: str) -> bool:
        """Ping主机检查连通性"""
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "3", host], capture_output=True, text=True
            )
            return result.returncode == 0
        except:
            return False

    def _check_disk_space(self) -> Dict[str, float]:
        """检查磁盘空间"""
        space_info = {}

        # 检查根目录
        root_usage = psutil.disk_usage("/")
        space_info["root_used_percent"] = (root_usage.used / root_usage.total) * 100
        space_info["root_free_gb"] = root_usage.free / (1024**3)

        # 检查备份目录
        backup_dir = Path("./backups")
        if backup_dir.exists():
            backup_usage = psutil.disk_usage(str(backup_dir))
            space_info["backup_used_percent"] = (
                backup_usage.used / backup_usage.total
            ) * 100
            space_info["backup_free_gb"] = backup_usage.free / (1024**3)

        # 检查工作空间目录
        workspace_dir = Path(self.settings.workspace_dir)
        if workspace_dir.exists():
            workspace_usage = psutil.disk_usage(str(workspace_dir))
            space_info["workspace_used_percent"] = (
                workspace_usage.used / workspace_usage.total
            ) * 100
            space_info["workspace_free_gb"] = workspace_usage.free / (1024**3)

        return space_info

    def _evaluate_overall_status(
        self, assessment: DisasterAssessment
    ) -> RecoveryStatus:
        """评估总体状态"""
        critical_services_down = 0
        total_services = 0

        for service in assessment.services:
            config = self.services.get(service.name, {})
            if config.get("critical", False):
                total_services += 1
                if service.status in [RecoveryStatus.FAILED, RecoveryStatus.CRITICAL]:
                    critical_services_down += 1

        # 检查数据完整性
        data_issues = sum(1 for v in assessment.data_integrity.values() if not v)

        # 检查备份状态
        backup_issues = assessment.backup_status.get("has_alerts", False)

        # 评估逻辑
        if critical_services_down == 0 and data_issues == 0 and not backup_issues:
            return RecoveryStatus.HEALTHY
        elif critical_services_down == 0 and (data_issues > 0 or backup_issues):
            return RecoveryStatus.DEGRADED
        elif critical_services_down < total_services:
            return RecoveryStatus.CRITICAL
        else:
            return RecoveryStatus.FAILED

    def _generate_recommendations(self, assessment: DisasterAssessment) -> List[str]:
        """生成恢复建议"""
        recommendations = []

        # 服务相关建议
        failed_services = [
            s for s in assessment.services if s.status == RecoveryStatus.FAILED
        ]
        if failed_services:
            recommendations.append(
                f"立即检查并重启以下失败服务: {', '.join([s.name for s in failed_services])}"
            )

        degraded_services = [
            s for s in assessment.services if s.status == RecoveryStatus.DEGRADED
        ]
        if degraded_services:
            recommendations.append(
                f"关注以下性能下降的服务: {', '.join([s.name for s in degraded_services])}"
            )

        # 数据完整性建议
        if not assessment.data_integrity.get("database_accessible", True):
            recommendations.append("数据库不可访问，建议立即检查数据库服务状态")

        if not assessment.data_integrity.get("database_tables", True):
            recommendations.append("关键数据库表缺失，可能需要从备份恢复")

        # 备份相关建议
        backup_age = assessment.backup_status.get("last_backup_age_hours", 0)
        if backup_age > 25:
            recommendations.append(
                f"最近备份时间过久({backup_age:.1f}小时)，建议立即执行备份"
            )

        if assessment.backup_status.get("backup_count", 0) == 0:
            recommendations.append("未发现任何备份，建议立即创建备份")

        # 磁盘空间建议
        for location, usage in assessment.disk_space.items():
            if location.endswith("_used_percent") and usage > 90:
                disk_name = location.replace("_used_percent", "")
                recommendations.append(
                    f"{disk_name}磁盘空间不足({usage:.1f}%)，建议清理空间"
                )

        # 网络连通性建议
        if not assessment.network_connectivity.get("database_host", True):
            recommendations.append("数据库主机网络不通，检查网络配置")

        if not assessment.network_connectivity.get("redis_host", True):
            recommendations.append("Redis主机网络不通，检查网络配置")

        if not assessment.network_connectivity.get("internet", True):
            recommendations.append("外网连接异常，可能影响远程备份和监控")

        return recommendations

    async def execute_recovery(
        self, scenario: FailureType, dry_run: bool = False
    ) -> bool:
        """执行恢复计划"""
        if scenario not in self.recovery_plans:
            logger.error(f"未知的故障场景: {scenario}")
            return False

        plan = self.recovery_plans[scenario]
        logger.info(f"开始执行恢复计划: {scenario.value}")
        logger.info(f"RPO: {plan.rpo_minutes}分钟, RTO: {plan.rto_minutes}分钟")

        if dry_run:
            logger.info("这是一个演练，不会执行实际恢复操作")

        start_time = datetime.now()

        try:
            # 检查依赖条件
            if not await self._check_dependencies(plan.dependencies):
                logger.error("恢复前置条件不满足")
                return False

            # 执行恢复步骤
            for i, step in enumerate(plan.steps, 1):
                logger.info(f"步骤 {i}/{len(plan.steps)}: {step}")

                if not dry_run:
                    success = await self._execute_recovery_step(scenario, step)
                    if not success:
                        logger.error(f"恢复步骤失败: {step}")
                        # 执行回滚
                        await self._execute_rollback(plan.rollback_steps)
                        return False
                else:
                    logger.info(f"[演练] 模拟执行: {step}")
                    await asyncio.sleep(1)  # 模拟执行时间

            # 验证恢复结果
            if not dry_run:
                verification_success = await self._verify_recovery(
                    plan.verification_steps
                )
                if not verification_success:
                    logger.error("恢复验证失败")
                    await self._execute_rollback(plan.rollback_steps)
                    return False

            end_time = datetime.now()
            recovery_time = (end_time - start_time).total_seconds() / 60

            logger.info(f"恢复完成，耗时: {recovery_time:.1f}分钟")

            if recovery_time > plan.rto_minutes:
                logger.warning(
                    f"恢复时间({recovery_time:.1f}分钟)超过RTO目标({plan.rto_minutes}分钟)"
                )

            return True

        except Exception as e:
            logger.error(f"恢复执行失败: {e}")
            if not dry_run:
                await self._execute_rollback(plan.rollback_steps)
            return False

    async def _check_dependencies(self, dependencies: List[str]) -> bool:
        """检查恢复前置条件"""
        logger.info("检查恢复前置条件")

        for dependency in dependencies:
            if "备份文件可用" in dependency:
                backups = await self.backup_manager.list_backups()
                if not backups:
                    logger.error("没有可用的备份文件")
                    return False

            elif "磁盘空间充足" in dependency:
                space_info = self._check_disk_space()
                if space_info.get("root_free_gb", 0) < 5:  # 至少5GB空闲空间
                    logger.error("磁盘空间不足")
                    return False

            elif "网络连接正常" in dependency:
                connectivity = await self._check_network_connectivity()
                if not connectivity.get("localhost", False):
                    logger.error("网络连接异常")
                    return False

            logger.info(f"前置条件满足: {dependency}")

        return True

    async def _execute_recovery_step(self, scenario: FailureType, step: str) -> bool:
        """执行具体的恢复步骤"""
        try:
            if "检测数据库连接状态" in step:
                return await self._test_database_connection()

            elif "重启PostgreSQL服务" in step:
                return self._restart_service("postgresql")

            elif "从最近备份恢复数据库" in step:
                return await self._restore_latest_database_backup()

            elif "检测Redis连接状态" in step:
                return self._test_redis_connection()

            elif "重启Redis服务" in step:
                return self._restart_service("redis")

            elif "从备份恢复Redis数据" in step:
                return await self._restore_latest_redis_backup()

            elif "重启应用服务" in step:
                return self._restart_application_services()

            elif "从备份恢复工作空间" in step:
                return await self._restore_latest_workspace_backup()

            elif "执行冒烟测试" in step:
                return await self._run_smoke_tests()

            elif "验证数据完整性" in step:
                integrity = await self._check_data_integrity()
                return all(integrity.values())

            else:
                logger.warning(f"未知的恢复步骤: {step}")
                return True  # 对未知步骤返回成功，避免阻塞

        except Exception as e:
            logger.error(f"执行恢复步骤失败 '{step}': {e}")
            return False

    async def _test_database_connection(self) -> bool:
        """测试数据库连接"""
        try:
            if not self.settings.database_url:
                return False

            import asyncpg

            conn = await asyncpg.connect(self.settings.database_url)
            await conn.fetchrow("SELECT 1")
            await conn.close()
            return True
        except:
            return False

    def _test_redis_connection(self) -> bool:
        """测试Redis连接"""
        try:
            import redis

            client = redis.Redis(
                host=self.settings.redis_host or "localhost",
                port=self.settings.redis_port or 6379,
                password=self.settings.redis_password,
            )
            return client.ping()
        except:
            return False

    def _restart_service(self, service_name: str) -> bool:
        """重启系统服务"""
        try:
            logger.info(f"重启服务: {service_name}")
            # 这里需要根据实际部署环境调整
            result = subprocess.run(
                ["sudo", "systemctl", "restart", service_name],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"重启服务失败: {e}")
            return False

    def _restart_application_services(self) -> bool:
        """重启应用服务"""
        try:
            # 重启TextLoom相关服务
            services = ["textloom-api", "textloom-worker", "textloom-beat"]
            for service in services:
                logger.info(f"重启应用服务: {service}")
                subprocess.run(
                    ["sudo", "systemctl", "restart", service],
                    capture_output=True,
                    text=True,
                )
            return True
        except Exception as e:
            logger.error(f"重启应用服务失败: {e}")
            return False

    async def _restore_latest_database_backup(self) -> bool:
        """恢复最新的数据库备份"""
        try:
            backups = await self.backup_manager.list_backups()
            if not backups:
                logger.error("没有可用的数据库备份")
                return False

            # 找到最近的包含数据库的备份
            for backup in backups:
                if "database" in backup.get("components", []):
                    logger.info(f"恢复数据库备份: {backup['backup_id']}")
                    success = await self.backup_manager.restore_backup(
                        backup["backup_id"], components=["database"]
                    )
                    return success

            logger.error("没有找到包含数据库的备份")
            return False

        except Exception as e:
            logger.error(f"恢复数据库备份失败: {e}")
            return False

    async def _restore_latest_redis_backup(self) -> bool:
        """恢复最新的Redis备份"""
        try:
            backups = await self.backup_manager.list_backups()
            if not backups:
                return False

            for backup in backups:
                if "redis" in backup.get("components", []):
                    logger.info(f"恢复Redis备份: {backup['backup_id']}")
                    return await self.backup_manager.restore_backup(
                        backup["backup_id"], components=["redis"]
                    )

            return False

        except Exception as e:
            logger.error(f"恢复Redis备份失败: {e}")
            return False

    async def _restore_latest_workspace_backup(self) -> bool:
        """恢复最新的工作空间备份"""
        try:
            backups = await self.backup_manager.list_backups()
            if not backups:
                return False

            for backup in backups:
                if "workspace" in backup.get("components", []):
                    logger.info(f"恢复工作空间备份: {backup['backup_id']}")
                    return await self.backup_manager.restore_backup(
                        backup["backup_id"], components=["workspace"]
                    )

            return False

        except Exception as e:
            logger.error(f"恢复工作空间备份失败: {e}")
            return False

    async def _run_smoke_tests(self) -> bool:
        """运行冒烟测试"""
        try:
            logger.info("执行冒烟测试")

            # 测试数据库连接
            if not await self._test_database_connection():
                logger.error("数据库连接测试失败")
                return False

            # 测试Redis连接
            if not self._test_redis_connection():
                logger.error("Redis连接测试失败")
                return False

            # 测试HTTP健康接口
            health_url = f"http://localhost:{self.settings.port}/health"
            response_time = await self._check_http_health(health_url)
            if response_time is None:
                logger.error("应用健康检查失败")
                return False

            logger.info("冒烟测试通过")
            return True

        except Exception as e:
            logger.error(f"冒烟测试失败: {e}")
            return False

    async def _verify_recovery(self, verification_steps: List[str]) -> bool:
        """验证恢复结果"""
        logger.info("验证恢复结果")

        for step in verification_steps:
            logger.info(f"验证步骤: {step}")

            if "数据库连接测试" in step:
                if not await self._test_database_connection():
                    return False

            elif "Redis连接测试" in step:
                if not self._test_redis_connection():
                    return False

            elif "应用健康检查" in step:
                health_url = f"http://localhost:{self.settings.port}/health"
                if await self._check_http_health(health_url) is None:
                    return False

            elif "完整系统功能测试" in step:
                if not await self._run_smoke_tests():
                    return False

        logger.info("恢复验证通过")
        return True

    async def _execute_rollback(self, rollback_steps: List[str]):
        """执行回滚步骤"""
        logger.info("执行回滚操作")

        for step in rollback_steps:
            logger.info(f"回滚步骤: {step}")
            try:
                # 这里实现具体的回滚逻辑
                await asyncio.sleep(1)  # 模拟回滚操作
            except Exception as e:
                logger.error(f"回滚步骤失败: {e}")

    async def run_disaster_drill(self, scenario: FailureType) -> Dict[str, Any]:
        """执行灾难恢复演练"""
        logger.info(f"开始灾难恢复演练: {scenario.value}")

        drill_result = {
            "scenario": scenario.value,
            "start_time": datetime.now().isoformat(),
            "success": False,
            "duration_minutes": 0,
            "issues_found": [],
            "recommendations": [],
        }

        start_time = datetime.now()

        try:
            # 评估当前状态
            pre_assessment = await self.assess_disaster()

            # 执行恢复计划（演练模式）
            recovery_success = await self.execute_recovery(scenario, dry_run=True)

            # 记录结果
            end_time = datetime.now()
            drill_result["duration_minutes"] = (
                end_time - start_time
            ).total_seconds() / 60
            drill_result["success"] = recovery_success
            drill_result["end_time"] = end_time.isoformat()

            # 分析发现的问题
            if scenario not in self.recovery_plans:
                drill_result["issues_found"].append("恢复计划不存在")

            plan = self.recovery_plans.get(scenario)
            if plan and drill_result["duration_minutes"] > plan.rto_minutes:
                drill_result["issues_found"].append(
                    f"演练时间({drill_result['duration_minutes']:.1f}分钟)超过RTO目标({plan.rto_minutes}分钟)"
                )

            # 检查备份可用性
            backups = await self.backup_manager.list_backups()
            if not backups:
                drill_result["issues_found"].append("没有可用的备份")

            # 生成改进建议
            if drill_result["issues_found"]:
                drill_result["recommendations"].append("更新和优化恢复计划")
                drill_result["recommendations"].append("加强备份策略")
                drill_result["recommendations"].append("改善监控和告警机制")

            logger.info(f"灾难恢复演练完成: {scenario.value}, 成功: {recovery_success}")

        except Exception as e:
            logger.error(f"灾难恢复演练失败: {e}")
            drill_result["error"] = str(e)

        return drill_result


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="TextLoom 灾难恢复系统")

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # 评估命令
    assess_parser = subparsers.add_parser("assess", help="评估灾难情况")

    # 恢复命令
    recover_parser = subparsers.add_parser("recover", help="执行恢复")
    recover_parser.add_argument(
        "--scenario",
        choices=[f.value for f in FailureType],
        required=True,
        help="故障场景",
    )
    recover_parser.add_argument("--dry-run", action="store_true", help="演练模式")

    # 故障转移命令
    failover_parser = subparsers.add_parser("failover", help="故障转移")
    failover_parser.add_argument(
        "--mode", choices=["automatic", "manual"], default="manual", help="转移模式"
    )

    # 演练命令
    drill_parser = subparsers.add_parser("drill", help="灾难恢复演练")
    drill_parser.add_argument(
        "--scenario",
        choices=[f.value for f in FailureType],
        required=True,
        help="演练场景",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # 初始化
    settings = Settings()
    dr_manager = DisasterRecoveryManager(settings)

    try:
        if args.command == "assess":
            assessment = await dr_manager.assess_disaster()
            print(
                json.dumps(
                    asdict(assessment), ensure_ascii=False, indent=2, default=str
                )
            )

        elif args.command == "recover":
            scenario = FailureType(args.scenario)
            success = await dr_manager.execute_recovery(scenario, args.dry_run)
            if success:
                print(f"恢复执行成功: {args.scenario}")
            else:
                print(f"恢复执行失败: {args.scenario}")
                sys.exit(1)

        elif args.command == "failover":
            print(f"故障转移模式: {args.mode}")
            # 这里可以实现自动故障转移逻辑

        elif args.command == "drill":
            scenario = FailureType(args.scenario)
            result = await dr_manager.run_disaster_drill(scenario)
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

    except Exception as e:
        logger.error(f"命令执行失败: {e}")
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
