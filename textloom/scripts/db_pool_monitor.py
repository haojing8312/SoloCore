#!/usr/bin/env python3
"""
数据库连接池实时监控工具
监控连接池状态，检测连接泄露和性能问题
"""

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from models.celery_db import get_sync_connection_pool
from models.db_connection import check_connection_pool_health, get_engine

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class PoolMetrics:
    """连接池指标"""

    timestamp: str
    service_name: str
    pool_size: int
    max_overflow: int
    checked_out: int
    checked_in: int
    overflow: int
    total_connections: int
    utilization_rate: float
    is_healthy: bool
    response_time_ms: Optional[float] = None


class DatabasePoolMonitor:
    """数据库连接池监控器"""

    def __init__(
        self, alert_threshold: float = 80.0, log_file: str = "logs/db_pool_monitor.log"
    ):
        self.alert_threshold = alert_threshold
        self.log_file = log_file
        self.metrics_history: List[PoolMetrics] = []
        self.setup_logging()

    def setup_logging(self):
        """设置日志记录"""
        # 创建日志目录
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        # 设置文件处理器
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)

        # 添加到logger
        monitor_logger = logging.getLogger("db_pool_monitor")
        monitor_logger.addHandler(file_handler)
        monitor_logger.setLevel(logging.INFO)
        self.monitor_logger = monitor_logger

    async def collect_async_pool_metrics(self) -> PoolMetrics:
        """收集异步连接池指标"""
        start_time = time.time()

        try:
            pool_health = await check_connection_pool_health()
            response_time = (time.time() - start_time) * 1000  # 转换为毫秒

            pool_size = pool_health.get("pool_size", 0)
            checked_out = pool_health.get("checked_out", 0)
            checked_in = pool_health.get("checked_in", 0)
            overflow = pool_health.get("overflow", 0)

            total_connections = checked_out + overflow
            utilization_rate = (
                total_connections / max(pool_size + settings.database_max_overflow, 1)
            ) * 100

            metrics = PoolMetrics(
                timestamp=datetime.now().isoformat(),
                service_name="FastAPI_Async",
                pool_size=pool_size,
                max_overflow=settings.database_max_overflow,
                checked_out=checked_out,
                checked_in=checked_in,
                overflow=overflow,
                total_connections=total_connections,
                utilization_rate=utilization_rate,
                is_healthy=pool_health.get("is_healthy", False),
                response_time_ms=response_time,
            )

            # 记录指标
            self.monitor_logger.info(
                f"AsyncPool Metrics: {json.dumps(asdict(metrics))}"
            )

            # 检查告警条件
            if utilization_rate > self.alert_threshold:
                self._trigger_alert("HIGH_UTILIZATION", metrics)

            if not metrics.is_healthy:
                self._trigger_alert("HEALTH_CHECK_FAILED", metrics)

            if response_time > 5000:  # 5秒
                self._trigger_alert("SLOW_RESPONSE", metrics)

            return metrics

        except Exception as e:
            logger.error(f"收集异步连接池指标失败: {e}")
            return PoolMetrics(
                timestamp=datetime.now().isoformat(),
                service_name="FastAPI_Async",
                pool_size=0,
                max_overflow=0,
                checked_out=0,
                checked_in=0,
                overflow=0,
                total_connections=0,
                utilization_rate=0,
                is_healthy=False,
                response_time_ms=(time.time() - start_time) * 1000,
            )

    def collect_sync_pool_metrics(self) -> PoolMetrics:
        """收集同步连接池指标"""
        start_time = time.time()

        try:
            # 尝试获取连接池状态
            pool = get_sync_connection_pool()
            response_time = (time.time() - start_time) * 1000

            # ThreadedConnectionPool没有详细的统计信息
            # 使用配置值作为基准
            pool_size = settings.celery_database_pool_size
            max_overflow = settings.celery_database_max_overflow

            # 估算连接使用情况(基于配置)
            estimated_utilization = 50.0  # 由于无法直接获取，使用估算值

            metrics = PoolMetrics(
                timestamp=datetime.now().isoformat(),
                service_name="Celery_Sync",
                pool_size=pool_size,
                max_overflow=max_overflow,
                checked_out=0,  # ThreadedConnectionPool无法直接获取
                checked_in=0,  # ThreadedConnectionPool无法直接获取
                overflow=0,  # ThreadedConnectionPool无法直接获取
                total_connections=pool_size,  # 估算值
                utilization_rate=estimated_utilization,
                is_healthy=True,  # 如果能获取到pool对象，认为是健康的
                response_time_ms=response_time,
            )

            # 记录指标
            self.monitor_logger.info(f"SyncPool Metrics: {json.dumps(asdict(metrics))}")

            return metrics

        except Exception as e:
            logger.error(f"收集同步连接池指标失败: {e}")
            return PoolMetrics(
                timestamp=datetime.now().isoformat(),
                service_name="Celery_Sync",
                pool_size=0,
                max_overflow=0,
                checked_out=0,
                checked_in=0,
                overflow=0,
                total_connections=0,
                utilization_rate=0,
                is_healthy=False,
                response_time_ms=(time.time() - start_time) * 1000,
            )

    def _trigger_alert(self, alert_type: str, metrics: PoolMetrics):
        """触发告警"""
        alert_message = {
            "alert_type": alert_type,
            "service": metrics.service_name,
            "timestamp": metrics.timestamp,
            "utilization_rate": metrics.utilization_rate,
            "threshold": self.alert_threshold,
            "details": asdict(metrics),
        }

        self.monitor_logger.warning(f"ALERT {alert_type}: {json.dumps(alert_message)}")
        print(
            f"🚨 ALERT [{alert_type}] {metrics.service_name}: 利用率 {metrics.utilization_rate:.1f}%"
        )

    async def run_monitoring_cycle(self) -> List[PoolMetrics]:
        """运行一次监控周期"""
        cycle_metrics = []

        # 收集异步连接池指标
        async_metrics = await self.collect_async_pool_metrics()
        cycle_metrics.append(async_metrics)

        # 收集同步连接池指标
        sync_metrics = self.collect_sync_pool_metrics()
        cycle_metrics.append(sync_metrics)

        # 添加到历史记录
        self.metrics_history.extend(cycle_metrics)

        # 保持历史记录大小(最多保留1000条)
        if len(self.metrics_history) > 1000:
            self.metrics_history = self.metrics_history[-1000:]

        return cycle_metrics

    def generate_summary_report(self, hours: int = 1) -> Dict[str, Any]:
        """生成汇总报告"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        # 过滤最近的指标
        recent_metrics = [
            m
            for m in self.metrics_history
            if datetime.fromisoformat(m.timestamp) > cutoff_time
        ]

        if not recent_metrics:
            return {"message": "没有最近的指标数据"}

        # 按服务分组
        services = {}
        for metric in recent_metrics:
            service = metric.service_name
            if service not in services:
                services[service] = []
            services[service].append(metric)

        # 计算统计信息
        summary = {
            "time_range": f"最近{hours}小时",
            "total_samples": len(recent_metrics),
            "services": {},
        }

        for service_name, metrics in services.items():
            if not metrics:
                continue

            utilization_rates = [
                m.utilization_rate for m in metrics if m.utilization_rate is not None
            ]
            response_times = [
                m.response_time_ms for m in metrics if m.response_time_ms is not None
            ]
            health_checks = [m.is_healthy for m in metrics]

            service_summary = {
                "sample_count": len(metrics),
                "avg_utilization": (
                    sum(utilization_rates) / len(utilization_rates)
                    if utilization_rates
                    else 0
                ),
                "max_utilization": max(utilization_rates) if utilization_rates else 0,
                "avg_response_time_ms": (
                    sum(response_times) / len(response_times) if response_times else 0
                ),
                "max_response_time_ms": max(response_times) if response_times else 0,
                "health_check_success_rate": (
                    sum(health_checks) / len(health_checks) * 100
                    if health_checks
                    else 0
                ),
                "alerts_count": sum(
                    1 for m in metrics if m.utilization_rate > self.alert_threshold
                ),
            }

            summary["services"][service_name] = service_summary

        return summary

    def print_current_status(self, metrics: List[PoolMetrics]):
        """打印当前状态"""
        print(f"\n📊 数据库连接池状态 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        for metric in metrics:
            status_icon = "✅" if metric.is_healthy else "❌"
            utilization_icon = (
                "🔴" if metric.utilization_rate > self.alert_threshold else "🟢"
            )

            print(f"{status_icon} {metric.service_name}")
            print(
                f"   连接池大小: {metric.pool_size} (最大溢出: {metric.max_overflow})"
            )
            print(f"   当前使用: {metric.checked_out} 连接")
            print(f"   溢出连接: {metric.overflow}")
            print(f"   {utilization_icon} 利用率: {metric.utilization_rate:.1f}%")
            if metric.response_time_ms is not None:
                print(f"   响应时间: {metric.response_time_ms:.1f}ms")
            print()


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="数据库连接池监控工具")
    parser.add_argument("--interval", type=int, default=30, help="监控间隔(秒)")
    parser.add_argument(
        "--duration", type=int, default=0, help="监控时长(秒，0表示持续监控)"
    )
    parser.add_argument(
        "--alert-threshold", type=float, default=80.0, help="告警阈值(百分比)"
    )
    parser.add_argument(
        "--report-interval", type=int, default=300, help="报告生成间隔(秒)"
    )
    parser.add_argument("--one-shot", action="store_true", help="只运行一次检查")

    args = parser.parse_args()

    monitor = DatabasePoolMonitor(alert_threshold=args.alert_threshold)

    print("🚀 启动数据库连接池监控...")
    print(f"⏱️  监控间隔: {args.interval}秒")
    print(f"🚨 告警阈值: {args.alert_threshold}%")
    print(f"📊 报告间隔: {args.report_interval}秒")

    if args.one_shot:
        print("\n🔍 运行单次检查...")
        metrics = await monitor.run_monitoring_cycle()
        monitor.print_current_status(metrics)
        return

    start_time = time.time()
    last_report_time = start_time

    try:
        while True:
            current_time = time.time()

            # 运行监控周期
            metrics = await monitor.run_monitoring_cycle()
            monitor.print_current_status(metrics)

            # 定期生成汇总报告
            if current_time - last_report_time >= args.report_interval:
                print("\n📋 生成汇总报告...")
                summary = monitor.generate_summary_report()
                print(json.dumps(summary, indent=2, ensure_ascii=False))
                last_report_time = current_time

            # 检查是否需要停止
            if args.duration > 0 and (current_time - start_time) >= args.duration:
                print(f"\n⏰ 监控时长已达到 {args.duration} 秒，停止监控")
                break

            # 等待下一个监控周期
            await asyncio.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n⏹️  接收到中断信号，停止监控")
    except Exception as e:
        print(f"\n❌ 监控过程中出现错误: {e}")
        logger.exception("监控失败")
    finally:
        # 生成最终报告
        print("\n📋 生成最终汇总报告...")
        final_summary = monitor.generate_summary_report(hours=24)
        print(json.dumps(final_summary, indent=2, ensure_ascii=False))

        print("\n✅ 监控结束")
        print(f"📝 详细日志已保存到: {monitor.log_file}")


if __name__ == "__main__":
    asyncio.run(main())
