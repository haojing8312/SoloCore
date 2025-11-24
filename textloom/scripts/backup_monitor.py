#!/usr/bin/env python3
"""
TextLoom 备份监控和告警系统
========================

实时监控备份系统状态并提供告警功能：
- 实时备份状态监控
- 备份成功率统计
- 存储空间监控
- 自动告警和通知
- 健康状况仪表板
- 性能指标收集
- SLA监控

Usage:
    python backup_monitor.py start --daemon
    python backup_monitor.py status
    python backup_monitor.py alert --test
    python backup_monitor.py dashboard --port 8080
"""

import argparse
import asyncio
import json
import logging
import os
import smtplib
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from email.mime.multipart import MimeMultipart
from email.mime.text import MimeText
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
import aiohttp
import jinja2
from aiohttp import web

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from config import Settings
from scripts.backup_manager import BackupConfig, BackupManager, create_backup_config
from utils.enhanced_logging import setup_logging

# 配置日志
logger = setup_logging(
    __name__, "logs/backup_monitor.log", "logs/backup_monitor.error.log"
)


@dataclass
class AlertRule:
    """告警规则"""

    name: str
    condition: str  # 告警条件
    severity: str  # info, warning, error, critical
    cooldown_minutes: int  # 冷却时间
    enabled: bool = True
    last_triggered: Optional[datetime] = None


@dataclass
class MonitoringMetrics:
    """监控指标"""

    timestamp: datetime
    backup_success_rate: float  # 24小时成功率
    last_backup_age_hours: float
    backup_count_24h: int
    failed_backups_24h: int
    avg_backup_size_gb: float
    disk_space_used_percent: float
    disk_space_free_gb: float
    database_backup_age_hours: float
    redis_backup_age_hours: float
    workspace_backup_age_hours: float
    backup_duration_avg_minutes: float
    backup_throughput_mbps: float


@dataclass
class AlertNotification:
    """告警通知"""

    alert_id: str
    rule_name: str
    severity: str
    message: str
    timestamp: datetime
    acknowledged: bool = False
    resolved: bool = False
    resolved_at: Optional[datetime] = None


class BackupMonitor:
    """备份监控器"""

    def __init__(self, settings: Settings, config: BackupConfig):
        self.settings = settings
        self.config = config
        self.backup_manager = BackupManager(settings, config)

        # 监控配置
        self.monitor_interval = int(
            os.getenv("BACKUP_MONITOR_INTERVAL", "300")
        )  # 5分钟
        self.metrics_retention_days = int(
            os.getenv("BACKUP_METRICS_RETENTION_DAYS", "30")
        )

        # 告警规则
        self.alert_rules = self._initialize_alert_rules()

        # 通知配置
        self.notification_config = {
            "email_enabled": os.getenv("BACKUP_EMAIL_ALERTS_ENABLED", "false").lower()
            == "true",
            "smtp_server": os.getenv("BACKUP_SMTP_SERVER"),
            "smtp_port": int(os.getenv("BACKUP_SMTP_PORT", "587")),
            "smtp_username": os.getenv("BACKUP_SMTP_USERNAME"),
            "smtp_password": os.getenv("BACKUP_SMTP_PASSWORD"),
            "email_from": os.getenv("BACKUP_EMAIL_FROM"),
            "email_to": os.getenv("BACKUP_EMAIL_TO", "").split(","),
            "webhook_enabled": os.getenv(
                "BACKUP_WEBHOOK_ALERTS_ENABLED", "false"
            ).lower()
            == "true",
            "webhook_url": os.getenv("BACKUP_WEBHOOK_URL"),
            "webhook_secret": os.getenv("BACKUP_WEBHOOK_SECRET"),
            "slack_enabled": os.getenv("BACKUP_SLACK_ALERTS_ENABLED", "false").lower()
            == "true",
            "slack_webhook_url": os.getenv("BACKUP_SLACK_WEBHOOK_URL"),
            "slack_channel": os.getenv("BACKUP_SLACK_CHANNEL", "#alerts"),
        }

        # 存储目录
        self.data_dir = Path("./backup_monitor_data")
        self.data_dir.mkdir(exist_ok=True)

        # 运行状态
        self.is_running = False
        self.active_alerts = {}  # 活跃告警

    def _initialize_alert_rules(self) -> List[AlertRule]:
        """初始化告警规则"""
        return [
            AlertRule(
                name="backup_age_warning",
                condition="last_backup_age_hours > 25",
                severity="warning",
                cooldown_minutes=60,
            ),
            AlertRule(
                name="backup_age_critical",
                condition="last_backup_age_hours > 48",
                severity="critical",
                cooldown_minutes=30,
            ),
            AlertRule(
                name="backup_failure_rate",
                condition="backup_success_rate < 0.8",
                severity="error",
                cooldown_minutes=45,
            ),
            AlertRule(
                name="disk_space_warning",
                condition="disk_space_used_percent > 85",
                severity="warning",
                cooldown_minutes=120,
            ),
            AlertRule(
                name="disk_space_critical",
                condition="disk_space_used_percent > 95",
                severity="critical",
                cooldown_minutes=30,
            ),
            AlertRule(
                name="no_recent_backups",
                condition="backup_count_24h == 0",
                severity="critical",
                cooldown_minutes=60,
            ),
            AlertRule(
                name="database_backup_stale",
                condition="database_backup_age_hours > 72",
                severity="error",
                cooldown_minutes=180,
            ),
            AlertRule(
                name="backup_duration_long",
                condition="backup_duration_avg_minutes > 120",
                severity="warning",
                cooldown_minutes=240,
            ),
            AlertRule(
                name="low_backup_throughput",
                condition="backup_throughput_mbps < 10",
                severity="warning",
                cooldown_minutes=180,
            ),
        ]

    async def start_monitoring(self):
        """开始监控"""
        logger.info("启动备份监控系统")
        self.is_running = True

        try:
            while self.is_running:
                await self._monitor_cycle()
                await asyncio.sleep(self.monitor_interval)

        except KeyboardInterrupt:
            logger.info("收到停止信号")
        except Exception as e:
            logger.error(f"监控系统异常: {e}")
        finally:
            self.is_running = False
            logger.info("备份监控系统已停止")

    async def _monitor_cycle(self):
        """监控周期"""
        try:
            # 收集监控指标
            metrics = await self._collect_metrics()

            # 保存指标
            await self._save_metrics(metrics)

            # 检查告警规则
            alerts = await self._check_alert_rules(metrics)

            # 发送告警通知
            for alert in alerts:
                await self._send_alert_notification(alert)

            # 清理过期数据
            await self._cleanup_old_data()

            logger.debug(f"监控周期完成，收集了 {len(asdict(metrics))} 个指标")

        except Exception as e:
            logger.error(f"监控周期执行失败: {e}")

    async def _collect_metrics(self) -> MonitoringMetrics:
        """收集监控指标"""
        now = datetime.now()

        # 获取备份状态
        backup_status = await self.backup_manager.monitor_backups()
        backups = await self.backup_manager.list_backups()

        # 计算24小时内的备份统计
        recent_backups = [
            b
            for b in backups
            if datetime.fromisoformat(b["timestamp"]) > (now - timedelta(hours=24))
        ]

        failed_backups = [b for b in recent_backups if b["status"] == "failed"]
        successful_backups = [b for b in recent_backups if b["status"] == "completed"]

        # 计算成功率
        total_recent = len(recent_backups)
        success_rate = (
            len(successful_backups) / total_recent if total_recent > 0 else 1.0
        )

        # 计算平均备份大小
        avg_size = (
            sum(b.get("compressed_size", 0) for b in successful_backups)
            / len(successful_backups)
            if successful_backups
            else 0
        )
        avg_size_gb = avg_size / (1024**3)

        # 计算各组件的最新备份时间
        db_backup_age = self._get_component_backup_age(backups, "database")
        redis_backup_age = self._get_component_backup_age(backups, "redis")
        workspace_backup_age = self._get_component_backup_age(backups, "workspace")

        # 计算备份性能指标
        backup_durations = []
        backup_throughputs = []

        for backup in successful_backups:
            # 估算备份持续时间（基于时间戳，实际应该记录开始和结束时间）
            duration = 30  # 默认30分钟，实际应该从备份元数据获取
            backup_durations.append(duration)

            # 计算吞吐量
            size_mb = backup.get("compressed_size", 0) / (1024**2)
            throughput = size_mb / duration if duration > 0 else 0
            backup_throughputs.append(throughput)

        avg_duration = (
            sum(backup_durations) / len(backup_durations) if backup_durations else 0
        )
        avg_throughput = (
            sum(backup_throughputs) / len(backup_throughputs)
            if backup_throughputs
            else 0
        )

        # 磁盘空间信息
        disk_info = self._get_disk_space_info()

        return MonitoringMetrics(
            timestamp=now,
            backup_success_rate=success_rate,
            last_backup_age_hours=self._calculate_last_backup_age(backup_status),
            backup_count_24h=len(recent_backups),
            failed_backups_24h=len(failed_backups),
            avg_backup_size_gb=avg_size_gb,
            disk_space_used_percent=disk_info["used_percent"],
            disk_space_free_gb=disk_info["free_gb"],
            database_backup_age_hours=db_backup_age,
            redis_backup_age_hours=redis_backup_age,
            workspace_backup_age_hours=workspace_backup_age,
            backup_duration_avg_minutes=avg_duration,
            backup_throughput_mbps=avg_throughput,
        )

    def _get_component_backup_age(self, backups: List[Dict], component: str) -> float:
        """获取指定组件的最新备份时间差"""
        now = datetime.now()
        latest_time = None

        for backup in backups:
            if component in backup.get("components", []):
                backup_time = datetime.fromisoformat(backup["timestamp"])
                if latest_time is None or backup_time > latest_time:
                    latest_time = backup_time

        if latest_time:
            return (now - latest_time).total_seconds() / 3600
        else:
            return float("inf")

    def _calculate_last_backup_age(self, backup_status: Dict) -> float:
        """计算最近备份的时间差（小时）"""
        if backup_status.get("last_backup"):
            last_backup_time = datetime.fromisoformat(
                backup_status["last_backup"]["timestamp"]
            )
            return (datetime.now() - last_backup_time).total_seconds() / 3600
        return float("inf")

    def _get_disk_space_info(self) -> Dict[str, float]:
        """获取磁盘空间信息"""
        import psutil

        backup_dir = Path(self.config.local_backup_dir)
        if backup_dir.exists():
            usage = psutil.disk_usage(str(backup_dir))
            return {
                "used_percent": (usage.used / usage.total) * 100,
                "free_gb": usage.free / (1024**3),
                "total_gb": usage.total / (1024**3),
            }
        else:
            # 使用根目录信息
            usage = psutil.disk_usage("/")
            return {
                "used_percent": (usage.used / usage.total) * 100,
                "free_gb": usage.free / (1024**3),
                "total_gb": usage.total / (1024**3),
            }

    async def _save_metrics(self, metrics: MonitoringMetrics):
        """保存监控指标"""
        metrics_file = (
            self.data_dir / f"metrics_{datetime.now().strftime('%Y%m%d')}.jsonl"
        )

        async with aiofiles.open(metrics_file, "a", encoding="utf-8") as f:
            await f.write(json.dumps(asdict(metrics), default=str) + "\n")

    async def _check_alert_rules(
        self, metrics: MonitoringMetrics
    ) -> List[AlertNotification]:
        """检查告警规则"""
        alerts = []
        metrics_dict = asdict(metrics)

        for rule in self.alert_rules:
            if not rule.enabled:
                continue

            # 检查冷却时间
            if rule.last_triggered and rule.last_triggered > (
                datetime.now() - timedelta(minutes=rule.cooldown_minutes)
            ):
                continue

            try:
                # 评估告警条件
                if self._evaluate_condition(rule.condition, metrics_dict):
                    alert = AlertNotification(
                        alert_id=f"{rule.name}_{int(time.time())}",
                        rule_name=rule.name,
                        severity=rule.severity,
                        message=self._generate_alert_message(rule, metrics_dict),
                        timestamp=datetime.now(),
                    )

                    alerts.append(alert)
                    rule.last_triggered = datetime.now()
                    self.active_alerts[alert.alert_id] = alert

                    logger.warning(f"触发告警: {rule.name} - {alert.message}")

            except Exception as e:
                logger.error(f"评估告警规则失败 {rule.name}: {e}")

        return alerts

    def _evaluate_condition(self, condition: str, metrics: Dict[str, Any]) -> bool:
        """评估告警条件"""
        try:
            # 创建安全的执行环境
            safe_dict = {**metrics, "__builtins__": {}}  # 移除内置函数以提高安全性

            return eval(condition, safe_dict)
        except Exception as e:
            logger.error(f"条件评估失败: {condition} - {e}")
            return False

    def _generate_alert_message(self, rule: AlertRule, metrics: Dict[str, Any]) -> str:
        """生成告警消息"""
        messages = {
            "backup_age_warning": f"备份时间过久: {metrics.get('last_backup_age_hours', 0):.1f}小时前",
            "backup_age_critical": f"备份时间严重过久: {metrics.get('last_backup_age_hours', 0):.1f}小时前",
            "backup_failure_rate": f"备份成功率过低: {metrics.get('backup_success_rate', 0):.1%}",
            "disk_space_warning": f"磁盘空间不足: {metrics.get('disk_space_used_percent', 0):.1f}% 已使用",
            "disk_space_critical": f"磁盘空间严重不足: {metrics.get('disk_space_used_percent', 0):.1f}% 已使用",
            "no_recent_backups": "24小时内没有执行任何备份",
            "database_backup_stale": f"数据库备份过期: {metrics.get('database_backup_age_hours', 0):.1f}小时前",
            "backup_duration_long": f"备份时间过长: 平均 {metrics.get('backup_duration_avg_minutes', 0):.1f} 分钟",
            "low_backup_throughput": f"备份吞吐量过低: {metrics.get('backup_throughput_mbps', 0):.1f} MB/s",
        }

        return messages.get(rule.name, f"告警规则触发: {rule.name}")

    async def _send_alert_notification(self, alert: AlertNotification):
        """发送告警通知"""
        try:
            # 发送邮件通知
            if self.notification_config["email_enabled"]:
                await self._send_email_alert(alert)

            # 发送Webhook通知
            if self.notification_config["webhook_enabled"]:
                await self._send_webhook_alert(alert)

            # 发送Slack通知
            if self.notification_config["slack_enabled"]:
                await self._send_slack_alert(alert)

            logger.info(f"告警通知已发送: {alert.rule_name}")

        except Exception as e:
            logger.error(f"发送告警通知失败: {e}")

    async def _send_email_alert(self, alert: AlertNotification):
        """发送邮件告警"""
        if not all(
            [
                self.notification_config["smtp_server"],
                self.notification_config["smtp_username"],
                self.notification_config["smtp_password"],
                self.notification_config["email_from"],
                self.notification_config["email_to"],
            ]
        ):
            return

        try:
            msg = MimeMultipart()
            msg["From"] = self.notification_config["email_from"]
            msg["To"] = ", ".join(self.notification_config["email_to"])
            msg["Subject"] = (
                f"[{alert.severity.upper()}] TextLoom备份告警: {alert.rule_name}"
            )

            body = f"""
TextLoom备份系统告警

告警名称: {alert.rule_name}
严重程度: {alert.severity}
时间: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
消息: {alert.message}

请及时处理该告警。

--
TextLoom备份监控系统
            """.strip()

            msg.attach(MimeText(body, "plain", "utf-8"))

            server = smtplib.SMTP(
                self.notification_config["smtp_server"],
                self.notification_config["smtp_port"],
            )
            server.starttls()
            server.login(
                self.notification_config["smtp_username"],
                self.notification_config["smtp_password"],
            )

            server.send_message(msg)
            server.quit()

            logger.info("邮件告警发送成功")

        except Exception as e:
            logger.error(f"发送邮件告警失败: {e}")

    async def _send_webhook_alert(self, alert: AlertNotification):
        """发送Webhook告警"""
        if not self.notification_config["webhook_url"]:
            return

        try:
            payload = {
                "alert_id": alert.alert_id,
                "rule_name": alert.rule_name,
                "severity": alert.severity,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "service": "textloom-backup",
            }

            headers = {"Content-Type": "application/json"}

            # 添加签名
            if self.notification_config["webhook_secret"]:
                import hashlib
                import hmac

                signature = hmac.new(
                    self.notification_config["webhook_secret"].encode(),
                    json.dumps(payload).encode(),
                    hashlib.sha256,
                ).hexdigest()

                headers["X-Signature"] = f"sha256={signature}"

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.notification_config["webhook_url"],
                    json=payload,
                    headers=headers,
                    timeout=10,
                ) as response:
                    if response.status == 200:
                        logger.info("Webhook告警发送成功")
                    else:
                        logger.error(f"Webhook告警发送失败: {response.status}")

        except Exception as e:
            logger.error(f"发送Webhook告警失败: {e}")

    async def _send_slack_alert(self, alert: AlertNotification):
        """发送Slack告警"""
        if not self.notification_config["slack_webhook_url"]:
            return

        try:
            # 根据严重程度设置颜色
            colors = {
                "info": "#36a64f",
                "warning": "#ff9900",
                "error": "#ff0000",
                "critical": "#8b0000",
            }

            payload = {
                "channel": self.notification_config["slack_channel"],
                "username": "TextLoom Backup Monitor",
                "icon_emoji": ":warning:",
                "attachments": [
                    {
                        "color": colors.get(alert.severity, "#ff0000"),
                        "title": f"备份系统告警: {alert.rule_name}",
                        "text": alert.message,
                        "fields": [
                            {
                                "title": "严重程度",
                                "value": alert.severity.upper(),
                                "short": True,
                            },
                            {
                                "title": "时间",
                                "value": alert.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                                "short": True,
                            },
                        ],
                        "footer": "TextLoom备份监控",
                        "ts": int(alert.timestamp.timestamp()),
                    }
                ],
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.notification_config["slack_webhook_url"],
                    json=payload,
                    timeout=10,
                ) as response:
                    if response.status == 200:
                        logger.info("Slack告警发送成功")
                    else:
                        logger.error(f"Slack告警发送失败: {response.status}")

        except Exception as e:
            logger.error(f"发送Slack告警失败: {e}")

    async def _cleanup_old_data(self):
        """清理过期数据"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.metrics_retention_days)
            cutoff_str = cutoff_date.strftime("%Y%m%d")

            for file_path in self.data_dir.glob("metrics_*.jsonl"):
                file_date = file_path.stem.split("_")[1]
                if file_date < cutoff_str:
                    file_path.unlink()
                    logger.info(f"删除过期监控数据: {file_path.name}")

        except Exception as e:
            logger.error(f"清理过期数据失败: {e}")

    async def get_current_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        try:
            # 获取最新指标
            metrics = await self._collect_metrics()

            # 获取活跃告警
            active_alerts = [
                asdict(alert)
                for alert in self.active_alerts.values()
                if not alert.resolved
            ]

            # 获取历史数据统计
            history_stats = await self._get_history_stats()

            return {
                "monitoring_status": "running" if self.is_running else "stopped",
                "last_update": datetime.now().isoformat(),
                "current_metrics": asdict(metrics),
                "active_alerts": active_alerts,
                "active_alert_count": len(active_alerts),
                "history_stats": history_stats,
                "alert_rules_count": len(self.alert_rules),
                "enabled_rules_count": len([r for r in self.alert_rules if r.enabled]),
            }

        except Exception as e:
            logger.error(f"获取当前状态失败: {e}")
            return {"error": str(e)}

    async def _get_history_stats(self) -> Dict[str, Any]:
        """获取历史统计数据"""
        try:
            # 读取最近7天的数据
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)

            all_metrics = []

            for days_ago in range(8):  # 包含今天
                date = end_date - timedelta(days=days_ago)
                metrics_file = (
                    self.data_dir / f"metrics_{date.strftime('%Y%m%d')}.jsonl"
                )

                if metrics_file.exists():
                    async with aiofiles.open(metrics_file, "r", encoding="utf-8") as f:
                        async for line in f:
                            try:
                                metric = json.loads(line)
                                metric_time = datetime.fromisoformat(
                                    metric["timestamp"]
                                )
                                if metric_time >= start_date:
                                    all_metrics.append(metric)
                            except:
                                continue

            if not all_metrics:
                return {}

            # 计算统计数据
            success_rates = [m["backup_success_rate"] for m in all_metrics]
            backup_ages = [
                m["last_backup_age_hours"]
                for m in all_metrics
                if m["last_backup_age_hours"] != float("inf")
            ]
            disk_usage = [m["disk_space_used_percent"] for m in all_metrics]

            return {
                "avg_success_rate": (
                    sum(success_rates) / len(success_rates) if success_rates else 0
                ),
                "min_success_rate": min(success_rates) if success_rates else 0,
                "avg_backup_age_hours": (
                    sum(backup_ages) / len(backup_ages) if backup_ages else 0
                ),
                "max_backup_age_hours": max(backup_ages) if backup_ages else 0,
                "avg_disk_usage": (
                    sum(disk_usage) / len(disk_usage) if disk_usage else 0
                ),
                "max_disk_usage": max(disk_usage) if disk_usage else 0,
                "data_points": len(all_metrics),
                "time_range_days": 7,
            }

        except Exception as e:
            logger.error(f"获取历史统计失败: {e}")
            return {}

    async def test_alerts(self) -> Dict[str, Any]:
        """测试告警系统"""
        test_alert = AlertNotification(
            alert_id="test_alert",
            rule_name="test_rule",
            severity="info",
            message="这是一个测试告警，请忽略",
            timestamp=datetime.now(),
        )

        results = {}

        # 测试邮件
        if self.notification_config["email_enabled"]:
            try:
                await self._send_email_alert(test_alert)
                results["email"] = "success"
            except Exception as e:
                results["email"] = f"failed: {e}"

        # 测试Webhook
        if self.notification_config["webhook_enabled"]:
            try:
                await self._send_webhook_alert(test_alert)
                results["webhook"] = "success"
            except Exception as e:
                results["webhook"] = f"failed: {e}"

        # 测试Slack
        if self.notification_config["slack_enabled"]:
            try:
                await self._send_slack_alert(test_alert)
                results["slack"] = "success"
            except Exception as e:
                results["slack"] = f"failed: {e}"

        return results


class BackupDashboard:
    """备份监控仪表板"""

    def __init__(self, monitor: BackupMonitor):
        self.monitor = monitor
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self):
        """设置路由"""
        self.app.router.add_get("/", self.dashboard_home)
        self.app.router.add_get("/api/status", self.api_status)
        self.app.router.add_get("/api/metrics", self.api_metrics)
        self.app.router.add_get("/api/alerts", self.api_alerts)
        self.app.router.add_post(
            "/api/alerts/{alert_id}/acknowledge", self.api_acknowledge_alert
        )
        self.app.router.add_static("/static/", path="./static", name="static")

    async def dashboard_home(self, request):
        """仪表板首页"""
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>TextLoom 备份监控</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
                .header { background: #2c3e50; color: white; padding: 20px; margin: -20px -20px 20px; }
                .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; }
                .metric-card { background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; padding: 15px; }
                .metric-value { font-size: 2em; font-weight: bold; color: #28a745; }
                .metric-label { color: #6c757d; margin-top: 5px; }
                .alerts { margin-top: 30px; }
                .alert { padding: 15px; margin: 10px 0; border-radius: 5px; }
                .alert.critical { background: #f8d7da; border: 1px solid #f5c6cb; }
                .alert.error { background: #f8d7da; border: 1px solid #f5c6cb; }
                .alert.warning { background: #fff3cd; border: 1px solid #ffeaa7; }
                .alert.info { background: #d4edda; border: 1px solid #c3e6cb; }
                .refresh-btn { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; }
            </style>
            <script>
                async function refreshData() {
                    const response = await fetch('/api/status');
                    const data = await response.json();
                    updateDashboard(data);
                }
                
                function updateDashboard(data) {
                    document.getElementById('status').innerHTML = JSON.stringify(data, null, 2);
                }
                
                setInterval(refreshData, 30000); // 30秒刷新
                window.onload = refreshData;
            </script>
        </head>
        <body>
            <div class="header">
                <h1>TextLoom 备份监控系统</h1>
                <button class="refresh-btn" onclick="refreshData()">刷新</button>
            </div>
            
            <div id="dashboard">
                <pre id="status">加载中...</pre>
            </div>
        </body>
        </html>
        """

        return web.Response(text=html_template, content_type="text/html")

    async def api_status(self, request):
        """API: 获取状态"""
        status = await self.monitor.get_current_status()
        return web.json_response(status)

    async def api_metrics(self, request):
        """API: 获取指标"""
        try:
            metrics = await self.monitor._collect_metrics()
            return web.json_response(asdict(metrics), dumps=json.dumps, default=str)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def api_alerts(self, request):
        """API: 获取告警"""
        alerts = [asdict(alert) for alert in self.monitor.active_alerts.values()]
        return web.json_response(alerts, dumps=json.dumps, default=str)

    async def api_acknowledge_alert(self, request):
        """API: 确认告警"""
        alert_id = request.match_info["alert_id"]

        if alert_id in self.monitor.active_alerts:
            self.monitor.active_alerts[alert_id].acknowledged = True
            return web.json_response({"success": True})
        else:
            return web.json_response({"error": "Alert not found"}, status=404)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="TextLoom 备份监控系统")

    subparsers = parser.add_subparsers(dest="command", help="命令")

    # 启动命令
    start_parser = subparsers.add_parser("start", help="启动监控")
    start_parser.add_argument("--daemon", action="store_true", help="后台运行")

    # 状态命令
    status_parser = subparsers.add_parser("status", help="查看状态")

    # 测试告警命令
    alert_parser = subparsers.add_parser("alert", help="告警相关操作")
    alert_parser.add_argument("--test", action="store_true", help="测试告警")

    # 仪表板命令
    dashboard_parser = subparsers.add_parser("dashboard", help="启动仪表板")
    dashboard_parser.add_argument("--port", type=int, default=8080, help="端口号")
    dashboard_parser.add_argument("--host", default="0.0.0.0", help="主机地址")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # 初始化
    settings = Settings()
    config = create_backup_config()
    monitor = BackupMonitor(settings, config)

    try:
        if args.command == "start":
            if args.daemon:
                # TODO: 实现守护进程模式
                logger.info("后台模式启动")

            await monitor.start_monitoring()

        elif args.command == "status":
            status = await monitor.get_current_status()
            print(json.dumps(status, ensure_ascii=False, indent=2, default=str))

        elif args.command == "alert":
            if args.test:
                results = await monitor.test_alerts()
                print("告警测试结果:")
                for method, result in results.items():
                    print(f"  {method}: {result}")

        elif args.command == "dashboard":
            dashboard = BackupDashboard(monitor)

            # 启动监控任务
            monitor_task = asyncio.create_task(monitor.start_monitoring())

            print(f"启动备份监控仪表板: http://{args.host}:{args.port}")

            # 启动Web服务器
            runner = web.AppRunner(dashboard.app)
            await runner.setup()
            site = web.TCPSite(runner, args.host, args.port)
            await site.start()

            try:
                await monitor_task
            except KeyboardInterrupt:
                logger.info("收到停止信号")
            finally:
                await runner.cleanup()

    except Exception as e:
        logger.error(f"命令执行失败: {e}")
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
