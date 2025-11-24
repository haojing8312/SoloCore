from utils.enhanced_logging import (
    log_critical,
    log_debug,
    log_error,
    log_info,
    log_warning,
)

#!/usr/bin/env python3
"""
数据库连接池配置优化脚本
分析当前配置并提供优化建议
"""

import asyncio
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Dict, List

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from models.celery_db import get_sync_connection_pool
from models.db_connection import check_connection_pool_health, get_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ConnectionPoolAnalysis:
    """连接池分析结果"""

    service_name: str
    pool_size: int
    max_overflow: int
    current_connections: int
    available_connections: int
    max_possible_connections: int
    utilization_rate: float
    recommendations: List[str]


class DatabaseConnectionOptimizer:
    """数据库连接池优化器"""

    def __init__(self):
        self.analyses: List[ConnectionPoolAnalysis] = []

    async def analyze_async_pool(self) -> ConnectionPoolAnalysis:
        """分析异步连接池(FastAPI)"""
        try:
            pool_health = await check_connection_pool_health()

            recommendations = []

            # 分析连接池配置
            pool_size = pool_health.get("pool_size", 5)
            checked_out = pool_health.get("checked_out", 0)
            overflow = pool_health.get("overflow", 0)

            # 计算利用率
            utilization_rate = checked_out / max(pool_size, 1) * 100

            # 生成建议
            if utilization_rate > 80:
                recommendations.append("连接池利用率过高，建议增加pool_size")

            if overflow > 0:
                recommendations.append(
                    f"当前有{overflow}个溢出连接，考虑优化查询或增加基础连接池大小"
                )

            if not pool_health.get("is_healthy", False):
                recommendations.append("连接池健康检查失败，需要检查数据库连接配置")

            return ConnectionPoolAnalysis(
                service_name="FastAPI (Async)",
                pool_size=pool_size,
                max_overflow=10,  # 硬编码值
                current_connections=checked_out,
                available_connections=pool_size - checked_out,
                max_possible_connections=pool_size + 10,
                utilization_rate=utilization_rate,
                recommendations=recommendations,
            )
        except Exception as e:
            logger.error(f"分析异步连接池失败: {e}")
            return ConnectionPoolAnalysis(
                service_name="FastAPI (Async)",
                pool_size=0,
                max_overflow=0,
                current_connections=0,
                available_connections=0,
                max_possible_connections=0,
                utilization_rate=0,
                recommendations=[f"连接池分析失败: {str(e)}"],
            )

    def analyze_sync_pool(self) -> ConnectionPoolAnalysis:
        """分析同步连接池(Celery)"""
        recommendations = []

        try:
            # 获取连接池信息
            pool = get_sync_connection_pool()

            # ThreadedConnectionPool 没有直接的统计API，使用配置值
            pool_size = 10  # maxconn from celery_db.py
            min_conn = 2  # minconn from celery_db.py

            recommendations.extend(
                [
                    "Celery使用ThreadedConnectionPool，统计信息有限",
                    "建议监控连接获取超时情况",
                    "考虑将连接池配置移到环境变量中统一管理",
                ]
            )

            return ConnectionPoolAnalysis(
                service_name="Celery (Sync)",
                pool_size=pool_size,
                max_overflow=0,
                current_connections=0,  # 无法直接获取
                available_connections=0,  # 无法直接获取
                max_possible_connections=pool_size,
                utilization_rate=0,
                recommendations=recommendations,
            )
        except Exception as e:
            logger.error(f"分析同步连接池失败: {e}")
            return ConnectionPoolAnalysis(
                service_name="Celery (Sync)",
                pool_size=0,
                max_overflow=0,
                current_connections=0,
                available_connections=0,
                max_possible_connections=0,
                utilization_rate=0,
                recommendations=[f"连接池分析失败: {str(e)}"],
            )

    async def run_analysis(self) -> Dict[str, Any]:
        """运行完整分析"""
        log_debug("🔍 开始数据库连接池分析...")

        # 分析异步连接池
        log_info("📊 分析FastAPI异步连接池...")
        async_analysis = await self.analyze_async_pool()
        self.analyses.append(async_analysis)

        # 分析同步连接池
        log_info("📊 分析Celery同步连接池...")
        sync_analysis = self.analyze_sync_pool()
        self.analyses.append(sync_analysis)

        # 生成总体建议
        overall_recommendations = self._generate_overall_recommendations()

        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "analyses": self.analyses,
            "overall_recommendations": overall_recommendations,
            "configuration_issues": self._detect_configuration_issues(),
            "optimization_suggestions": self._generate_optimization_suggestions(),
        }

    def _generate_overall_recommendations(self) -> List[str]:
        """生成总体建议"""
        recommendations = [
            "统一连接池配置，避免硬编码值与config.py配置不一致",
            "实施连接池监控，定期检查连接泄露情况",
            "考虑引入连接池管理中间件(如pgbouncer)进行连接复用",
            "建立连接池使用规范，确保连接正确释放",
            "设置连接池告警机制，在连接数接近上限时及时通知",
        ]
        return recommendations

    def _detect_configuration_issues(self) -> List[Dict[str, Any]]:
        """检测配置问题"""
        issues = []

        # 检查配置不一致问题
        issues.append(
            {
                "type": "CONFIG_INCONSISTENCY",
                "severity": "HIGH",
                "description": "db_connection.py中硬编码的连接池配置与config.py不一致",
                "current_config": {
                    "config.py": {
                        "pool_size": settings.database_pool_size,
                        "max_overflow": settings.database_max_overflow,
                    },
                    "db_connection.py": {"pool_size": 5, "max_overflow": 10},
                },
                "recommendation": "使用settings配置替换硬编码值",
            }
        )

        # 检查零溢出配置风险
        if settings.database_max_overflow == 0:
            issues.append(
                {
                    "type": "ZERO_OVERFLOW_RISK",
                    "severity": "HIGH",
                    "description": "config.py中max_overflow=0可能导致连接饥饿",
                    "recommendation": "设置适当的max_overflow值(建议5-10)",
                }
            )

        return issues

    def _generate_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """生成优化建议"""
        suggestions = []

        # 基于系统架构的建议
        suggestions.append(
            {
                "category": "CONNECTION_POOLING",
                "priority": "HIGH",
                "title": "统一连接池配置管理",
                "description": "将所有连接池配置统一到环境变量中管理",
                "implementation": [
                    "修改db_connection.py使用settings配置",
                    "修改celery_db.py使用settings配置",
                    "添加连接池配置验证",
                ],
            }
        )

        suggestions.append(
            {
                "category": "MONITORING",
                "priority": "MEDIUM",
                "title": "连接池监控和告警",
                "description": "实施连接池状态监控",
                "implementation": [
                    "添加连接池指标收集",
                    "设置连接数告警阈值",
                    "定期检查连接泄露",
                ],
            }
        )

        suggestions.append(
            {
                "category": "PERFORMANCE",
                "priority": "MEDIUM",
                "title": "连接池性能调优",
                "description": "基于实际负载调整连接池参数",
                "implementation": [
                    "监控连接池利用率",
                    "调整pool_size和max_overflow",
                    "优化长时间运行的查询",
                ],
            }
        )

        return suggestions

    def print_analysis_report(self, analysis_result: Dict[str, Any]):
        """打印分析报告"""
        log_info("\n" + "=" * 80)
        log_info("📋 数据库连接池分析报告")
        log_info("=" * 80)
        log_info(f"⏰ 分析时间: {analysis_result['timestamp']}")

        # 打印各连接池分析结果
        log_info("\n📊 连接池状态分析:")
        for analysis in analysis_result["analyses"]:
            log_info(f"\n🔸 {analysis.service_name}")
            log_info(f"   池大小: {analysis.pool_size}")
            log_info(f"   最大溢出: {analysis.max_overflow}")
            log_info(f"   当前连接: {analysis.current_connections}")
            log_info(f"   可用连接: {analysis.available_connections}")
            log_info(f"   最大可能连接: {analysis.max_possible_connections}")
            log_info(f"   利用率: {analysis.utilization_rate:.1f}%")

            if analysis.recommendations:
                log_info("   建议:")
                for rec in analysis.recommendations:
                    log_info(f"     • {rec}")

        # 打印配置问题
        log_warning(
            f"\n⚠️  配置问题 ({len(analysis_result['configuration_issues'])}个):"
        )
        for issue in analysis_result["configuration_issues"]:
            severity_icon = "🔴" if issue["severity"] == "HIGH" else "🟡"
            log_info(f"{severity_icon} {issue['type']}: {issue['description']}")
            log_info(f"   建议: {issue['recommendation']}")

        # 打印优化建议
        log_info(
            f"\n🚀 优化建议 ({len(analysis_result['optimization_suggestions'])}个):"
        )
        for suggestion in analysis_result["optimization_suggestions"]:
            priority_icon = "🔥" if suggestion["priority"] == "HIGH" else "⭐"
            log_info(
                f"{priority_icon} {suggestion['title']} ({suggestion['category']})"
            )
            log_info(f"   {suggestion['description']}")

        # 打印总体建议
        log_info(f"\n💡 总体建议:")
        for rec in analysis_result["overall_recommendations"]:
            log_info(f"   • {rec}")

        log_info("\n" + "=" * 80)


async def main():
    """主函数"""
    optimizer = DatabaseConnectionOptimizer()

    try:
        # 运行分析
        analysis_result = await optimizer.run_analysis()

        # 打印报告
        optimizer.print_analysis_report(analysis_result)

        log_info("\n✅ 分析完成！")
        log_error("📝 建议查看生成的优化建议并逐步实施改进。")

    except Exception as e:
        log_error(f"❌ 分析过程中出现错误: {e}")
        logger.exception("分析失败")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
