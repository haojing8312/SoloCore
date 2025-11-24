#!/usr/bin/env python3
"""
数据库连接池配置测试脚本
验证配置更改是否正确，并测试在负载下的表现
"""

import asyncio
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List

import asyncpg
import psycopg2

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from models.celery_db import get_sync_connection_pool, sync_check_database_health
from models.db_connection import (
    check_connection_pool_health,
    get_db_session,
    get_engine,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseConfigTester:
    """数据库配置测试器"""

    def __init__(self):
        self.results: Dict[str, Any] = {
            "config_verification": {},
            "connection_tests": {},
            "load_tests": {},
            "recommendations": [],
        }

    def verify_config_consistency(self) -> Dict[str, Any]:
        """验证配置一致性"""
        logger.info("🔍 验证数据库连接池配置一致性...")

        config_issues = []
        config_info = {
            "async_pool": {
                "pool_size": settings.database_pool_size,
                "max_overflow": settings.database_max_overflow,
                "pool_recycle": settings.database_pool_recycle,
                "pool_timeout": settings.database_pool_timeout,
                "pool_pre_ping": settings.database_pool_pre_ping,
            },
            "celery_pool": {
                "pool_size": settings.celery_database_pool_size,
                "max_overflow": settings.celery_database_max_overflow,
                "min_connections": settings.celery_database_min_connections,
                "pool_recycle": settings.database_pool_recycle,
            },
        }

        # 检查配置合理性
        if settings.database_max_overflow == 0:
            config_issues.append("异步连接池max_overflow为0，可能导致连接饥饿")

        if settings.database_pool_size < 5:
            config_issues.append("异步连接池池大小可能过小")

        if (
            settings.celery_database_pool_size
            < settings.celery_database_min_connections
        ):
            config_issues.append("Celery连接池最大连接数小于最小连接数")

        # 检查总连接数是否合理
        max_total_connections = (
            settings.database_pool_size
            + settings.database_max_overflow
            + settings.celery_database_pool_size
            + settings.celery_database_max_overflow
        )

        if max_total_connections > 50:
            config_issues.append(f"总最大连接数({max_total_connections})可能过高")

        result = {
            "config_info": config_info,
            "issues": config_issues,
            "max_total_connections": max_total_connections,
            "status": "OK" if not config_issues else "WARNING",
        }

        self.results["config_verification"] = result
        return result

    async def test_async_connection_pool(self) -> Dict[str, Any]:
        """测试异步连接池"""
        logger.info("🧪 测试异步数据库连接池...")

        test_results = {
            "basic_connection": False,
            "pool_health": {},
            "concurrent_connections": 0,
            "response_times": [],
        }

        try:
            # 基础连接测试
            start_time = time.time()
            async with get_db_session() as session:
                result = await session.execute(text("SELECT 1 as test"))
                test_value = result.scalar()
                if test_value == 1:
                    test_results["basic_connection"] = True

            test_results["response_times"].append(time.time() - start_time)

            # 连接池健康检查
            pool_health = await check_connection_pool_health()
            test_results["pool_health"] = pool_health

            # 并发连接测试
            concurrent_tasks = []
            for i in range(5):  # 创建5个并发连接
                concurrent_tasks.append(self._async_db_task(i))

            concurrent_results = await asyncio.gather(
                *concurrent_tasks, return_exceptions=True
            )
            successful_connections = sum(
                1 for r in concurrent_results if not isinstance(r, Exception)
            )
            test_results["concurrent_connections"] = successful_connections

            logger.info(f"异步连接池测试完成: {successful_connections}/5 个连接成功")

        except Exception as e:
            logger.error(f"异步连接池测试失败: {e}")
            test_results["error"] = str(e)

        self.results["connection_tests"]["async"] = test_results
        return test_results

    async def _async_db_task(self, task_id: int) -> bool:
        """异步数据库任务"""
        try:
            async with get_db_session() as session:
                # 模拟一些数据库操作
                await asyncio.sleep(0.1)
                result = await session.execute(text(f"SELECT {task_id} as task_id"))
                return result.scalar() == task_id
        except Exception as e:
            logger.warning(f"异步任务{task_id}失败: {e}")
            return False

    def test_sync_connection_pool(self) -> Dict[str, Any]:
        """测试同步连接池"""
        logger.info("🧪 测试同步数据库连接池(Celery)...")

        test_results = {
            "basic_connection": False,
            "health_check": {},
            "concurrent_connections": 0,
            "response_times": [],
        }

        try:
            # 基础健康检查
            start_time = time.time()
            health_status = sync_check_database_health()
            test_results["health_check"] = health_status
            test_results["response_times"].append(time.time() - start_time)

            if health_status.get("status") == "healthy":
                test_results["basic_connection"] = True

            # 并发连接测试
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(self._sync_db_task, i) for i in range(3)]
                successful_connections = sum(
                    1 for future in as_completed(futures) if future.result()
                )
                test_results["concurrent_connections"] = successful_connections

            logger.info(f"同步连接池测试完成: {successful_connections}/3 个连接成功")

        except Exception as e:
            logger.error(f"同步连接池测试失败: {e}")
            test_results["error"] = str(e)

        self.results["connection_tests"]["sync"] = test_results
        return test_results

    def _sync_db_task(self, task_id: int) -> bool:
        """同步数据库任务"""
        try:
            from models.celery_db import get_sync_db_connection

            with get_sync_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SELECT {task_id} as task_id")
                    result = cursor.fetchone()
                    return result[0] == task_id
        except Exception as e:
            logger.warning(f"同步任务{task_id}失败: {e}")
            return False

    async def run_load_test(self, duration_seconds: int = 30) -> Dict[str, Any]:
        """运行负载测试"""
        logger.info(f"🚀 开始{duration_seconds}秒负载测试...")

        start_time = time.time()
        end_time = start_time + duration_seconds

        async_tasks = []
        sync_tasks = []
        async_success_count = 0
        sync_success_count = 0
        error_count = 0

        # 异步任务负载测试
        async def async_load_worker():
            nonlocal async_success_count, error_count
            while time.time() < end_time:
                try:
                    success = await self._async_db_task(1)
                    if success:
                        async_success_count += 1
                    await asyncio.sleep(0.1)  # 100ms间隔
                except Exception as e:
                    error_count += 1
                    logger.warning(f"负载测试异步任务失败: {e}")

        # 启动异步任务
        for i in range(3):
            async_tasks.append(asyncio.create_task(async_load_worker()))

        # 同步任务负载测试(在线程池中运行)
        def sync_load_worker():
            nonlocal sync_success_count, error_count
            while time.time() < end_time:
                try:
                    success = self._sync_db_task(1)
                    if success:
                        sync_success_count += 1
                    time.sleep(0.05)  # 优化：减少负载测试间隔到50ms
                except Exception as e:
                    error_count += 1
                    logger.warning(f"负载测试同步任务失败: {e}")

        # 启动同步任务
        with ThreadPoolExecutor(max_workers=2) as executor:
            sync_futures = [executor.submit(sync_load_worker) for _ in range(2)]

            # 等待异步任务完成
            await asyncio.gather(*async_tasks, return_exceptions=True)

            # 等待同步任务完成
            for future in as_completed(sync_futures, timeout=duration_seconds + 5):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"同步负载测试任务异常: {e}")

        total_operations = async_success_count + sync_success_count
        ops_per_second = (
            total_operations / duration_seconds if duration_seconds > 0 else 0
        )

        load_test_results = {
            "duration_seconds": duration_seconds,
            "async_operations": async_success_count,
            "sync_operations": sync_success_count,
            "total_operations": total_operations,
            "errors": error_count,
            "ops_per_second": round(ops_per_second, 2),
            "success_rate": (
                round((total_operations / (total_operations + error_count)) * 100, 2)
                if (total_operations + error_count) > 0
                else 0
            ),
        }

        logger.info(
            f"负载测试完成: {total_operations}次操作, {ops_per_second:.2f} ops/sec, 错误: {error_count}"
        )

        self.results["load_tests"] = load_test_results
        return load_test_results

    def generate_recommendations(self) -> List[str]:
        """生成配置建议"""
        recommendations = []

        # 基于配置验证结果
        config_result = self.results.get("config_verification", {})
        if config_result.get("issues"):
            recommendations.extend(
                [
                    "配置问题需要修复:",
                    *[f"  • {issue}" for issue in config_result["issues"]],
                ]
            )

        # 基于连接测试结果
        async_test = self.results.get("connection_tests", {}).get("async", {})
        sync_test = self.results.get("connection_tests", {}).get("sync", {})

        if not async_test.get("basic_connection"):
            recommendations.append("异步连接池连接失败，检查数据库配置和网络")

        if not sync_test.get("basic_connection"):
            recommendations.append("同步连接池连接失败，检查Celery数据库配置")

        # 基于负载测试结果
        load_test = self.results.get("load_tests", {})
        if load_test.get("success_rate", 100) < 95:
            recommendations.append(
                f"负载测试成功率({load_test.get('success_rate')}%)过低，考虑增加连接池大小"
            )

        if load_test.get("ops_per_second", 0) < 10:
            recommendations.append("数据库操作性能较低，考虑优化查询或增加连接池大小")

        # 通用建议
        recommendations.extend(
            [
                "定期监控连接池使用情况",
                "设置连接池告警阈值",
                "考虑使用连接池管理工具(如pgbouncer)进行进一步优化",
            ]
        )

        self.results["recommendations"] = recommendations
        return recommendations

    def print_test_report(self):
        """打印测试报告"""
        print("\n" + "=" * 80)
        print("📋 数据库连接池配置测试报告")
        print("=" * 80)
        print(f"⏰ 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 配置验证结果
        config_result = self.results.get("config_verification", {})
        print(f"\n📊 配置验证: {config_result.get('status', 'UNKNOWN')}")
        print(f"   最大总连接数: {config_result.get('max_total_connections', 'N/A')}")
        if config_result.get("issues"):
            print("   配置问题:")
            for issue in config_result["issues"]:
                print(f"     ⚠️  {issue}")

        # 连接测试结果
        print(f"\n🔗 连接测试结果:")
        async_test = self.results.get("connection_tests", {}).get("async", {})
        sync_test = self.results.get("connection_tests", {}).get("sync", {})

        async_status = "✅" if async_test.get("basic_connection") else "❌"
        sync_status = "✅" if sync_test.get("basic_connection") else "❌"

        print(
            f"   {async_status} 异步连接池: {async_test.get('concurrent_connections', 0)}/5 并发连接成功"
        )
        print(
            f"   {sync_status} 同步连接池: {sync_test.get('concurrent_connections', 0)}/3 并发连接成功"
        )

        # 负载测试结果
        load_test = self.results.get("load_tests", {})
        if load_test:
            print(f"\n🚀 负载测试结果 ({load_test.get('duration_seconds')}秒):")
            print(f"   总操作数: {load_test.get('total_operations', 0)}")
            print(f"   操作速度: {load_test.get('ops_per_second', 0)} ops/sec")
            print(f"   成功率: {load_test.get('success_rate', 0)}%")
            print(f"   错误数: {load_test.get('errors', 0)}")

        # 建议
        recommendations = self.results.get("recommendations", [])
        if recommendations:
            print(f"\n💡 优化建议:")
            for rec in recommendations:
                if rec.startswith("  "):
                    print(f"     {rec}")
                else:
                    print(f"   • {rec}")

        print("\n" + "=" * 80)


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="数据库连接池配置测试")
    parser.add_argument(
        "--load-test-duration", type=int, default=10, help="负载测试时长(秒)"
    )
    parser.add_argument("--skip-load-test", action="store_true", help="跳过负载测试")

    args = parser.parse_args()

    tester = DatabaseConfigTester()

    try:
        print("🚀 开始数据库连接池配置测试...")

        # 1. 配置验证
        tester.verify_config_consistency()

        # 2. 连接测试
        await tester.test_async_connection_pool()
        tester.test_sync_connection_pool()

        # 3. 负载测试(可选)
        if not args.skip_load_test:
            await tester.run_load_test(args.load_test_duration)

        # 4. 生成建议
        tester.generate_recommendations()

        # 5. 打印报告
        tester.print_test_report()

        print("\n✅ 所有测试完成！")

    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        logger.exception("测试失败")
        sys.exit(1)


if __name__ == "__main__":
    # 需要导入text以支持SQL语句
    from sqlalchemy import text

    asyncio.run(main())
